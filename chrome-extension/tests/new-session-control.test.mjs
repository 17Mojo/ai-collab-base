/**
 * 「新对话」入口的定位 / 点击 / 会话重置 —— 用 5 个活跃站的**真实 DOM 形状**摆出来的守护。
 *
 * 为什么要有这份测试：这些结构全部来自 2026-11-11 的只读探测
 * （evidence/new-session-probe-2026-11-11.chatglm-kimi-qianwen-yiyan-yuanbao.json），
 * 但此前它们只活在 adapter 的注释里，没有任何一层能在 `npm test` 里验证。
 * 站点改一次 DOM，就只能等下一轮 4–7 分钟的真机 L2 才知道。
 *
 * 这里把 DOM 摆进 jsdom，注入生产用的 findVisibleElement / isElementRendered /
 * findElements，断言三层兜底、`<a>` 导航拦截、以及 `durationMs` 都真的生效。
 *
 * 判据一律是**行为**：点完消息数有没有下降，而不是「源码里有没有这行字」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import {
  handleNewSession,
  findNewSessionControl,
  NEW_SESSION_TEXTS,
} from "../src/content/new-session-control.js";
import {
  findVisibleElement,
  findElements,
  isElementRendered,
} from "../src/platforms/adapter-utils.js";
// 直接拿生产配置，不另抄一份：抄一份的话「adapter 选择器被改坏」在单测里
// 永远不会红，只能等真机 L2 跑 4–7 分钟才发现。
import { SELECTORS as CHATGLM_SELECTORS } from "../src/platforms/chatglm-adapter.js";
import { SELECTORS as YUANBAO_SELECTORS } from "../src/platforms/yuanbao-adapter.js";
import { SELECTORS as KIMI_SELECTORS } from "../src/platforms/kimi-adapter.js";
import { SELECTORS as YIYAN_SELECTORS } from "../src/platforms/yiyan-adapter.js";
import { SELECTORS as LONGCAT_SELECTORS } from "../src/platforms/longcat-adapter.js";

const MESSAGE_LIST = [".msg"];

/**
 * 摆一个站点。返回的 `wireReset` 把「点入口」接到「清消息」上——
 * 模拟站点自己的 click 处理器；不接就等于「点了没生效」。
 *
 * @param {string} bodyHtml
 * @param {object} config
 * @param {{messages?: number, attrs?: string}} [opts]
 */
function makeSite(bodyHtml, config, { messages = 12, attrs = "" } = {}) {
  const bubbles = Array.from({ length: messages }, (_, i) => `<div class="msg" id="m${i}">消息 ${i}</div>`).join("");
  const dom = new JSDOM(
    `<!doctype html><html><body ${attrs}>${bodyHtml}<div id="thread">${bubbles}</div></body></html>`,
    { pretendToBeVisual: true },
  );
  global.window = dom.window;
  global.document = dom.window.document;
  // jsdom 不会真的导航；我们不希望控制台被 "Not implemented: navigation" 刷屏，
  // 导航拦截是否生效改由 event.defaultPrevented 断言。
  const deps = {
    document: dom.window.document,
    config: { messageList: MESSAGE_LIST, ...config },
    findVisibleElement,
    isElementRendered,
    findElements,
    resetTimeout: 900,
  };
  const wireReset = (el) => {
    el.addEventListener("click", () => {
      dom.window.document.querySelectorAll(".msg").forEach((n) => n.remove());
    });
  };
  return { dom, deps, wireReset, doc: dom.window.document };
}

// ─────────────────────────────────────────────────────────────────────
// 一、adapter 选择器优先（精度最高）
// ─────────────────────────────────────────────────────────────────────

test("chatglm：div.new-session 不是 button，仍被 adapter-selector 命中并真的清空 12→0", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<aside><div class="new-session"><div class="text">新对话</div></div></aside>',
    { newChat: CHATGLM_SELECTORS.newChat },
  );
  wireReset(doc.querySelector(".new-session"));

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "adapter-selector");
  assert.equal(r.messageCountBefore, 12);
  assert.equal(r.messageCountAfter, 0);
  assert.ok(Number.isInteger(r.durationMs) && r.durationMs >= 0, "重置耗时必须是可复核的非负整数");
});

test("元宝：div.yb-new-chat-entry__item 用「新建对话」措辞，仍走 adapter-selector", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<div class="yb-new-chat-entry"><div class="yb-new-chat-entry__item" role="button" aria-label="新建对话" tabindex="0"><p>新建对话</p></div></div>',
    { newChat: YUANBAO_SELECTORS.newChat },
  );
  wireReset(doc.querySelector(".yb-new-chat-entry__item"));

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "adapter-selector");
  assert.equal(r.messageCountAfter, 0);
});

test("文心：div.new-dialog-container-plain 走 adapter-selector（此前只有 DOM 证据）", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<div class="_btn-box_x"><div class="new-dialog-container"><div class="new-dialog-container-plain"><i></i><span>新对话</span></div></div></div>',
    { newChat: YIYAN_SELECTORS.newChat },
  );
  wireReset(doc.querySelector(".new-dialog-container-plain"));

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "adapter-selector");
  assert.equal(r.messageCountAfter, 0);
});

test("Kimi：a.new-chat-btn 是 <a>，点击时默认跳转必须被拦掉（否则内容脚本被销毁）", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<div class="sidebar-new-chat"><a class="new-chat-btn" data-testid="sidebar-new-chat" href="/?chat_enter_method=new_chat"><span></span></a></div>',
    { newChat: KIMI_SELECTORS.newChat },
  );
  const a = doc.querySelector("a.new-chat-btn");
  wireReset(a);
  let prevented = null;
  a.addEventListener("click", (e) => { prevented = e.defaultPrevented; });

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "adapter-selector");
  assert.equal(prevented, true, "捕获阶段必须 preventDefault，否则整页导航会把 sendResponse 一起带走");
});

/** longcat 侧栏真结构，来自 evidence/new-session-probe-2026-11-12.longcat.json */
const LONGCAT_SIDEBAR =
  '<div class="slider-menus-content"><div class="v-slider-header"><div class="slider-header">' +
  '<div class="new-content"><span data-v-3dbf79c6="">开启新对话</span></div>' +
  '</div></div></div>' +
  // 诱饵：历史会话列表里的「新对话」标题，点它只会切回旧会话
  '<div class="conversation-list"><div class="conv-item"><div class="conv-title">新对话</div></div></div>';

test("longcat：真入口是 div.new-content 里的「开启新对话」，不是历史项 div.conv-title", async () => {
  const { deps, wireReset, doc } = makeSite(LONGCAT_SIDEBAR, {
    newChat: LONGCAT_SELECTORS.newChat,
  });
  const control = doc.querySelector(".v-slider-header .new-content");
  assert.ok(control, "夹具必须摆出探针里的真入口结构");
  wireReset(control);

  const r = await handleNewSession(deps);
  assert.equal(r.available, true, "B 组要成立，边界必须真的执行成功（available === true）");
  assert.equal(r.strategy, "adapter-selector", "只能靠 adapter 精确声明命中");
  assert.equal(r.messageCountBefore, 12);
  assert.equal(r.messageCountAfter, 0, "消息数必须真的下降，否则不算重置成功");
  assert.ok(Number.isInteger(r.durationMs) && r.durationMs >= 0);
});

test("longcat：没声明 newChat 时宁可降级，也不许误点历史会话项", async () => {
  // 这正是 A/B 第 4 轮 longcat B 的现场：available:false / strategy:"none" /
  // 6→6。守护要钉的是「不许为了让它成功而放宽公共兜底去点 conv-title」。
  const { deps } = makeSite(LONGCAT_SIDEBAR, {});
  const found = findNewSessionControl({
    document: deps.document,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found, null, "div.conv-title「新对话」是历史会话诱饵，不是新对话入口");

  const r = await handleNewSession(deps);
  assert.equal(r.available, false);
  assert.equal(r.strategy, "none");
  assert.match(r.reason, /找不到「新对话」入口/);
  assert.equal(r.messageCountAfter, r.messageCountBefore);
});

// ─────────────────────────────────────────────────────────────────────
// 二、文案兜底 + 隐藏语义兜底
// ─────────────────────────────────────────────────────────────────────

test("没有 adapter 声明时，「新建会话」文案也要能兜住 Kimi 的 a.logo", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<a class="logo" aria-label="新建会话" href="/?chat_enter_method=new_chat"></a>',
    {},
  );
  wireReset(doc.querySelector("a.logo"));

  assert.ok(NEW_SESSION_TEXTS.includes("新建会话"), "Kimi 用的就是这个措辞，别把它删掉");
  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "text-match");
});

test("千问：入口藏在 opacity-0/pointer-events-none 的 hover-reveal 层里，靠语义属性兜底", async () => {
  const { deps, wireReset, doc } = makeSite(
    '<div style="opacity:0; pointer-events:none"><div class="newChatReveal-x"><div data-session-switch-target="new-chat" class="flex hover:bg-option cursor-pointer"><span>新对话</span></div></div></div>',
    {},
  );
  const control = doc.querySelector('[data-session-switch-target="new-chat"]');
  // 先确认生产用的可见性判据确实把它判为不可见 —— 否则这条兜底就没必要存在
  assert.equal(isElementRendered(control), false);
  wireReset(control);

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "hidden-semantic");
  assert.equal(r.messageCountBefore, 12);
  assert.equal(r.messageCountAfter, 0);
});

test("千问 2026-11-18：hover-reveal 面板默认可见时，newChatReveal 容器不许抢在语义入口前面", async () => {
  // 证据：evidence/new-session-probe-2026-11-18.qianwen-n29.json。
  // 外层 newChatReveal-* 现在 rendered=true、textContent 也是「新对话」，
  // 宽泛文案层的 [class*="newChat"] 会先命中这个**没有 click handler 的容器**。
  const { deps, wireReset, doc } = makeSite(
    '<div class="col-start-1 row-start-1 flex min-h-0 min-w-0 flex-col">' +
      '<div class="newChatReveal-OikAdB newChatRevealFlat-hnO8At">' +
        '<div class="flex h-full gap-0.5">' +
          '<div data-session-switch-target="new-chat" class="flex h-full cursor-pointer">' +
            '<span class="truncate font-400">新对话</span>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>',
    {},
    { messages: 6 },
  );
  const control = doc.querySelector('[data-session-switch-target="new-chat"]');
  assert.equal(isElementRendered(control), true, "这层已经可见，不能再当作 hover 隐藏态");
  wireReset(control);

  const found = findNewSessionControl({
    document: doc,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found?.el, control, "必须点真入口，不是外层 newChatReveal 容器");
  assert.equal(found?.how, "semantic");

  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "semantic");
  assert.equal(r.messageCountBefore, 6);
  assert.equal(r.messageCountAfter, 0);
});

test("输入区里的同名诱饵不认（chatglm 的 div.enter.is-main-chat）", async () => {
  const { deps, doc } = makeSite(
    // 合成一个「本来会被选中」的输入区诱饵（真站那处是 div + display:none，
    // 但守护要挡的是「长得像入口、位置却在发送区」这一类，不该靠它恰好不可见）。
    '<div class="input-box-container"><button class="enter is-main-chat">新对话</button></div>' +
    '<aside><button class="real" aria-label="新对话"></button></aside>',
    {},
  );
  const found = findNewSessionControl({
    document: doc,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.ok(found, "侧栏里的真入口仍要找得到");
  assert.equal(found.el, doc.querySelector("button.real"));
});

// ─────────────────────────────────────────────────────────────────────
// 三、失败语义与降级可见性
// ─────────────────────────────────────────────────────────────────────

test("找不到入口：prefer 记 available:false（带原因与耗时），strict 直接抛错", async () => {
  const { deps } = makeSite("<div>什么都没有</div>", {});
  const r = await handleNewSession({ ...deps, strict: false });
  assert.equal(r.available, false);
  assert.equal(r.strategy, "none");
  assert.match(r.reason, /找不到「新对话」入口/);
  assert.equal(r.messageCountAfter, r.messageCountBefore);
  assert.ok(Number.isInteger(r.durationMs) && r.durationMs >= 0);

  await assert.rejects(
    () => handleNewSession({ ...deps, strict: true }),
    (e) => e.code === "NEW_SESSION_CONTROL_NOT_FOUND",
  );
});

test("点了没生效：消息数没下降就不能算成功（不假装重置）", async () => {
  const { deps } = makeSite(
    '<button aria-label="新对话"></button>',
    {},
  ); // 故意不 wireReset
  const r = await handleNewSession({ ...deps, resetTimeout: 350 });
  assert.equal(r.available, false);
  assert.equal(r.strategy, "click-no-effect");
  assert.match(r.reason, /消息数没有下降/);
});

test("本来就是空会话：不点任何东西，判 already-empty 而不是失败", async () => {
  const { deps } = makeSite('<button aria-label="新对话"></button>', {}, { messages: 0 });
  const r = await handleNewSession(deps);
  assert.equal(r.available, true);
  assert.equal(r.strategy, "already-empty");
  assert.equal(r.messageCountBefore, 0);
  assert.equal(r.messageCountAfter, 0);
});
