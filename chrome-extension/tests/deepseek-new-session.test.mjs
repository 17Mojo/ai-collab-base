/**
 * deepseek 的「新对话」入口 —— 按 11-11 只读探针的真实 DOM 形状摆出来的契约守护。
 *
 * ## 为什么单独成文件
 *
 * `new-session-control.test.mjs` 被大量变异锚指着，全量变异要跑十几分钟；
 * 本文件只服务「adapter 级精确文案逃生口」这一处新逻辑，锚指向它即可秒级预检。
 *
 * ## 为什么这份守护重要
 *
 * ab3 四轮真机 A/B 的 deepseek B 组回执写的是
 * `sessionResets[0] = {available:false, strategy:"none", 3→3, durationMs:4}`，
 * 原因「adapter 没有声明 newChat 选择器」。而只读探针
 * `evidence/new-session-probe-2026-11-11.deepseek-ab-diagnostic.json` 里
 * 真入口是 `<span>开启新对话</span>`：无 class/id/aria/title/role/testid、
 * `clickableAncestor:null`、六层祖先全是构建期哈希类名。
 *
 * ⇒ 写不出稳定 CSS 选择器，只能按**精确文案**找；
 * ⇒ 但绝不能为此把 `span` / `div` 放宽进公共标签兜底——longcat 历史会话里
 *    `div.conv-title`「新对话」是诱饵，点它会静默切回旧会话（§21.7）。
 *
 * 所以判据是行为：① 真形状能命中且消息数真的下降；② 没声明逃生口的平台
 * 一律不许命中裸 span；③ 近似文案 / 输入区 / 不可见元素都不许蒙混过关。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import {
  handleNewSession,
  findNewSessionControl,
  NEW_SESSION_TEXTS,
  NEW_SESSION_CONTROL_SELECTOR,
} from "../src/content/new-session-control.js";
import {
  findVisibleElement,
  findElements,
  isElementRendered,
} from "../src/platforms/adapter-utils.js";
import { SELECTORS as DEEPSEEK_SELECTORS } from "../src/platforms/deepseek-adapter.js";
import { SELECTORS as CHATGLM_SELECTORS } from "../src/platforms/chatglm-adapter.js";

const MESSAGE_LIST = [".msg"];

/** deepseek 落地页侧栏真形状（探针 ancestors 原样保留哈希类名） */
const DEEPSEEK_SIDEBAR = `
<div class="c3ecdb44">
  <div class="dc04ec1d">
    <div class="b8812f16 a2f3d50e">
      <div class="_7b40dad">
        <div class="dc1f7bee _4bcc731">
          <div class="_5a8ac7a"><span>开启新对话</span></div>
        </div>
      </div>
    </div>
  </div>
</div>`;

/**
 * @param {string} bodyHtml
 * @param {object} config 直接传生产 SELECTORS（或 {}），不另抄一份
 * @param {{messages?: number, resetTimeout?: number}} [opts]
 */
function makeSite(bodyHtml, config, { messages = 12, resetTimeout = 700 } = {}) {
  const bubbles = Array.from(
    { length: messages },
    (_, i) => `<div class="msg" id="m${i}">消息 ${i}</div>`,
  ).join("");
  const dom = new JSDOM(
    `<!doctype html><html><body>${bodyHtml}<div id="thread">${bubbles}</div></body></html>`,
    { pretendToBeVisual: true },
  );
  global.window = dom.window;
  global.document = dom.window.document;
  // messageList 必须放在 spread **之后**：adapter 自带自己的 messageList
  // （deepseek 是 .ds-assistant-message-main-content），若被它覆盖，
  // 夹具里那 12 条 .msg 就数成 0 ⇒ handleNewSession 直接走 already-empty，
  // 把「入口找没找到 / 点了有没有清空」这两件真正要验的事全绕过去。
  const deps = {
    document: dom.window.document,
    config: { ...config, messageList: MESSAGE_LIST },
    findVisibleElement,
    isElementRendered,
    findElements,
    resetTimeout,
  };
  /** 站点自己的 click 处理器挂在祖先上：验证 el.click() 的冒泡真的能触发重置 */
  const wireReset = (el) => {
    el.addEventListener("click", () => {
      dom.window.document.querySelectorAll(".msg").forEach((n) => n.remove());
    });
  };
  return { deps, wireReset, doc: dom.window.document };
}

// ─────────────────────────────────────────────────────────────────────
// 一、真形状必须命中，且「点到了 ≠ 重置了」
// ─────────────────────────────────────────────────────────────────────

test("deepseek：裸 span「开启新对话」+ 哈希祖先，仍能找到并真的清空 12→0", async () => {
  const { deps, wireReset, doc } = makeSite(DEEPSEEK_SIDEBAR, DEEPSEEK_SELECTORS);
  const control = doc.querySelector("div._5a8ac7a span");
  assert.ok(control, "夹具必须摆出探针里的真入口结构");
  // 处理器挂在祖先 div 上，验证冒泡；不挂在 span 自身
  wireReset(doc.querySelector("div._5a8ac7a"));

  const r = await handleNewSession(deps);
  assert.equal(r.available, true, "B 组要成立，边界必须真的执行成功");
  assert.equal(r.strategy, "adapter-text-match");
  assert.equal(r.messageCountBefore, 12);
  assert.equal(r.messageCountAfter, 0, "消息数必须真的下降，否则不算重置成功");
  assert.ok(Number.isInteger(r.durationMs) && r.durationMs >= 0);
});

test("deepseek：文案必须全等，近似文案「开启新对话（Pro）」不许蒙混过关", async () => {
  const { deps } = makeSite(
    '<div class="_5a8ac7a"><span>开启新对话（Pro）</span></div>',
    DEEPSEEK_SELECTORS,
  );
  const found = findNewSessionControl({
    document: deps.document,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found, null, "文案层用 includes 就会把营销后缀当成入口，等于静默点错");
  const r = await handleNewSession(deps);
  assert.equal(r.available, false);
  assert.equal(r.strategy, "none");
});

test("deepseek：输入区里的同名 span 不许认（COMPOSER_ZONE 闸不能省）", async () => {
  const { deps, doc, wireReset } = makeSite(
    '<div class="input-box-container"><span>开启新对话</span></div>' + DEEPSEEK_SIDEBAR,
    DEEPSEEK_SELECTORS,
  );
  const real = doc.querySelector("div._5a8ac7a span");
  wireReset(real.parentElement);
  const found = findNewSessionControl({
    document: doc,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.ok(found, "侧栏真入口仍要找得到");
  assert.equal(found.el, real, "先出现的输入区诱饵必须被跳过");
});

test("deepseek：不可见的同名 span 不许认（渲染闸不能省）", async () => {
  const { deps } = makeSite(
    '<div style="display:none"><span>开启新对话</span></div>',
    DEEPSEEK_SELECTORS,
  );
  const found = findNewSessionControl({
    document: deps.document,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found, null);
});

// ─────────────────────────────────────────────────────────────────────
// 二、逃生口必须是 adapter 级的：不许偷偷放宽公共兜底
// ─────────────────────────────────────────────────────────────────────

test("没声明 newChatText 的平台：裸 span「开启新对话」必须找不到，宁可降级", async () => {
  const { deps } = makeSite(DEEPSEEK_SIDEBAR, {});
  const found = findNewSessionControl({
    document: deps.document,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found, null, "一旦公共标签兜底被放宽到 span，这条就会红");

  const r = await handleNewSession(deps);
  assert.equal(r.available, false);
  assert.equal(r.strategy, "none");
  assert.equal(r.messageCountAfter, r.messageCountBefore);
});

test("活跃站不受影响：拿 chatglm 的 SELECTORS 摆在 deepseek 形状里仍不命中", async () => {
  const { deps } = makeSite(DEEPSEEK_SIDEBAR, CHATGLM_SELECTORS);
  const found = findNewSessionControl({
    document: deps.document,
    config: deps.config,
    findVisibleElement,
    isElementRendered,
  });
  assert.equal(found, null, "已绿 5 站行为一个字节都不许变");
});

test("公共层只加文案、不放宽标签：NEW_SESSION_TEXTS 有「开启新对话」，选择器表无裸 span/div", () => {
  assert.ok(NEW_SESSION_TEXTS.includes("开启新对话"));
  const tags = NEW_SESSION_CONTROL_SELECTOR.split(",").map((s) => s.trim());
  assert.ok(!tags.includes("span"), "span 进公共兜底会误点 longcat 历史会话诱饵");
  assert.ok(!tags.includes("div"), "div 进公共兜底会误点 longcat 历史会话诱饵");
});

// ─────────────────────────────────────────────────────────────────────
// 三、失败语义：点不动就如实降级，绝不假装重置
// ─────────────────────────────────────────────────────────────────────

test("deepseek：找到了入口但点了没清空，仍判 available:false（不假装重置）", async () => {
  const { deps } = makeSite(DEEPSEEK_SIDEBAR, DEEPSEEK_SELECTORS, {
    resetTimeout: 350,
  }); // 故意不 wireReset
  const r = await handleNewSession(deps);
  assert.equal(r.available, false);
  assert.equal(r.strategy, "click-no-effect");
  assert.match(r.reason, /消息数没有下降/);
});
