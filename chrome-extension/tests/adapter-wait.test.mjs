/**
 * adapter 侧等待收口（waitForResponseGeneric + 基类 waitForResponse）
 *
 * ## 为什么要有这份测试
 *
 * 2026-11-04 台账 N14「太早成功」修掉执行器路径后，残留面在 observer 路径：
 * `waitForResponseGeneric` 与 10 个平台的 `waitForResponse` 副本仍跑旧判据
 * 「消息数增长 且 不在生成中」——观测器并行跑的正是这套生产等待，
 * 证据会把流式开头当完成。收口的修法：
 *
 *   1. `waitForResponseGeneric` 升级为内容稳定判据（wait-policy.sampleWaitState，
 *      与 content-script.handleWaitForResponse 同一个纯函数）；
 *   2. 基类 PlatformAdapter.waitForResponse 统一实现，10 份平台副本删除；
 *   3. 抽取差异收敛到钩子：`_extractContent` 覆写优先，否则走
 *      extractMessageContent 的「自身→后代→空串」契约。
 *
 * 这份测试钉死三件事：内容没稳住不许返回、空内容永不判完成、
 * 委托链（钩子/兜底）真的通。
 *
 * 用法：node --test tests/adapter-wait.test.mjs（run-tests.mjs 会自动收）
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

import { waitForResponseGeneric } from "../src/platforms/adapter-utils.js";
import PlatformAdapter from "../src/platforms/adapter.js";

const HERE = dirname(fileURLToPath(import.meta.url));
/** 每次导入换 query，让内容脚本模块重新求值（模块级状态是 per-instance 的） */
let importCounter = 0;

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

/** 一个最小 adapter 子类：消息列表可变，抽取钩子可选。 */
class FakeAdapter extends PlatformAdapter {
  constructor({ extract, selectors = {} } = {}) {
    super("fake");
    this.messages = [];
    this.typing = false;
    this.selectors = selectors;
    if (extract) this._extractContent = extract;
  }

  getMessageList() {
    return this.messages;
  }

  isTyping() {
    return this.typing;
  }
}

test("内容没稳住不许返回（太早成功回归锚：旧判据在第一个采样就返回）", async () => {
  let tick = 0;
  const messages = [];
  setTimeout(() => messages.push({ id: 1 }), 50);
  // 每个采样内容都变——流式生成的真实形态，永远不该判完成
  const pending = waitForResponseGeneric({
    getMessageList: () => messages,
    extractContent: () => `流式片段第 ${tick += 1} 段`,
    timeout: 1600,
    stableMs: 60000,
  });
  await assert.rejects(pending, /Response timeout/);
});

test("空内容永不判完成（'收到，' 都没有的空壳更不许算）", async () => {
  const messages = [];
  const pending = waitForResponseGeneric({
    getMessageList: () => messages,
    extractContent: () => "   ",
    timeout: 1600,
    stableMs: 100,
  });
  setTimeout(() => messages.push({ id: 1 }), 50);
  await assert.rejects(pending, /Response timeout/);
});

test("isTyping 期间不许返回（指示器认得准的平台靠它挡思考停顿）", async () => {
  const messages = [];
  const pending = waitForResponseGeneric({
    getMessageList: () => messages,
    extractContent: () => "内容早就稳住了",
    isTyping: () => true,
    timeout: 1600,
    stableMs: 100,
  });
  setTimeout(() => messages.push({ id: 1 }), 50);
  await assert.rejects(pending, /fake: Response timeout|Response timeout/);
});

test("内容稳住后返回全文（messageCount/content/duration 三件套）", async () => {
  const messages = [];
  const pending = waitForResponseGeneric({
    getMessageList: () => messages,
    extractContent: (el) => el.text,
    timeout: 8000,
    stableMs: 100,
    label: "fake",
  });
  setTimeout(() => messages.push({ text: "完整回答正文，一段就位后不再变化。" }), 50);
  const result = await pending;
  assert.equal(result.messageCount, 1);
  assert.equal(result.content, "完整回答正文，一段就位后不再变化。");
  assert.ok(typeof result.duration === "number" && result.duration > 0);
});

test("基类 waitForResponse 必须走 _extractContent 钩子取全文", async () => {
  const adapter = new FakeAdapter({
    extract: () => "钩子抽取的全文，不能被兜底覆盖",
  });
  const pending = adapter.waitForResponse(8000, 100);
  setTimeout(() => adapter.messages.push({}), 50);
  const result = await pending;
  assert.equal(
    result.content,
    "钩子抽取的全文，不能被兜底覆盖",
    "子类的 _extractContent 是抽取的第一优先——基类不许绕过它",
  );
});

test("无覆写时按 extractMessageContent 兜底（自身→后代→空串契约）", async () => {
  const adapter = new FakeAdapter({ selectors: { messageContent: [] } });
  // 兜底路径：无选择器时取元素自身文本（fake 元素模拟 textContent）
  const pending = adapter.waitForResponse(8000, 100);
  setTimeout(() => adapter.messages.push({ textContent: "兜底契约取到的全文" }), 50);
  const result = await pending;
  assert.equal(result.content, "兜底契约取到的全文");
});

test("超时错误带平台前缀（定位是谁家的等待超了）", async () => {
  const adapter = new FakeAdapter();
  await assert.rejects(adapter.waitForResponse(600, 100), /fake: Response timeout/);
});

test("收口不变量：waitForResponseGeneric 与 content-script 同一判据函数（sampleWaitState）", async () => {
  // 委托链上任何一处再分叉出自己的「完成」定义，这里就会红：
  // generic 必须是唯二消费者之一（另一个是 content-script.handleWaitForResponse）。
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const utils = readFileSync(
    fileURLToPath(new URL("../src/platforms/adapter-utils.js", import.meta.url)),
    "utf-8",
  );
  const cs = readFileSync(
    fileURLToPath(new URL("../src/content/content-script.js", import.meta.url)),
    "utf-8",
  );
  assert.match(utils, /sampleWaitState/, "waitForResponseGeneric 必须用 wait-policy.sampleWaitState 判定完成");
  assert.match(cs, /sampleWaitState/, "content-script 的等待也必须是同一个判据函数");
  assert.doesNotMatch(
    utils,
    /currentMessageCount > initialMessageCount && !isStillTyping/,
    "旧判据「计数增长且不在生成中」不许回来（太早成功）",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 生产内容脚本的等待行为（不是抄一份逻辑）
//
// 上面测的是 adapter 侧 `waitForResponseGeneric`；真正跑 Pack 的是
// content-script.handleWaitForResponse。两者共用 sampleWaitState，但
// 「基准怎么记、超时信封带什么」只在生产内容脚本里。所以这里把生产脚本
// 本体在 jsdom 里跑起来，重放 2026-11-11~12 冻结站 A/B 四轮的假超时现场。
//
// 放在本文件而不是 extension-wiring.test.mjs：后者被 33 条变异锚指着，
// 每条锚都要重跑一次整个文件；把 9 秒的虚拟列表时间线放进去，
// 会让全量变异凭空多出好几分钟。
// ─────────────────────────────────────────────────────────────────────

async function loadContentScript(fixtureName, adapterId) {
  const html = readFileSync(
    join(HERE, "real-machine", "fixtures", fixtureName),
    "utf-8",
  );
  const dom = new JSDOM(html, {
    url: "https://chat.deepseek.com/",
    pretendToBeVisual: true,
  });
  const listeners = [];
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.location = dom.window.location;
  globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
  globalThis.chrome = {
    runtime: {
      sendMessage: async (msg) =>
        msg?.type === "GET_ADAPTER" ? { adapterId } : undefined,
      onMessage: { addListener: (fn) => listeners.push(fn) },
    },
  };
  // jsdom 没有浏览器的编辑能力；生产代码还会用**全局** Event 构造事件，
  // 而 Node 的全局 Event 与 jsdom 的不是同一个类（dispatchEvent 会拒收）。
  dom.window.document.execCommand = () => true;
  globalThis.Event = dom.window.Event;
  globalThis.KeyboardEvent = dom.window.KeyboardEvent;
  globalThis.MouseEvent = dom.window.MouseEvent;
  globalThis.InputEvent = dom.window.InputEvent;

  importCounter += 1;
  await import(`../src/content/content-script.js?bust=${importCounter}`);
  await new Promise((r) => setTimeout(r, 0)); // 等 initialize() 拿到 adapterId
  return { dom, listeners };
}

test("虚拟列表：消息数不涨但正文换了，SEND_TO_AI 仍把新回答带回来", async () => {
  // 长会话里旧回答被卸载，新回答落地时条数仍是 3 ⇒ countGrew 恒 false
  // ⇒ AI 明明答完也判 723.x s（4×180s）假超时。这里重放那条 DOM 时间线。
  const { dom, listeners } = await loadContentScript(
    "qianwen-conversation.html",
    "chat.deepseek.com",
  );
  const doc = dom.window.document;

  // deepseek 的 typingIndicator 含 [class*="loading"] / [class*="generating"]，
  // fixture 里任何常驻同类元素都会让 isTyping() 恒 true（jsdom 无几何）。
  doc
    .querySelectorAll(
      '[class*="loading"], [class*="generating"], .typing-indicator, button[aria-label="Stop generating"], button[aria-label="Stop"]',
    )
    .forEach((n) => n.remove());

  // deepseek 的 chatInput 第一选择器是 textarea；fixture 里没有 textarea，
  // 补一个就能走生产注入路径（不依赖 Slate 站点模拟）。
  const composer = doc.createElement("div");
  composer.innerHTML = '<textarea id="ds-input"></textarea>';
  doc.body.appendChild(composer);

  const thread = doc.createElement("div");
  thread.id = "ds-thread";
  thread.innerHTML = [1, 2, 3]
    .map(
      (i) =>
        `<div class="ds-message"><div class="ds-markdown ds-assistant-message-main-content">` +
        `<p>旧回答 ${i}</p></div></div>`,
    )
    .join("");
  doc.body.appendChild(thread);

  const NEW_ANSWER =
    "这是本轮 AI 新生成的完整回答正文，长度足够通过可用内容闸，且与发送前最新一条完全不同。";
  // 站点在发送后先卸掉最旧一条，再挂上新回答 ⇒ 条数从头到尾都是 3。
  // 用定时而非发送按钮 click 驱动：本测试验的是「等待判据」，发送接线
  // 由 extension-wiring.test.mjs 的 SEND_TO_AI 行为测试单独钉住。
  setTimeout(() => {
    thread.querySelector(".ds-message")?.remove();
    thread.insertAdjacentHTML(
      "beforeend",
      `<div class="ds-message"><div class="ds-markdown ds-assistant-message-main-content">` +
        `<p>${NEW_ANSWER}</p></div></div>`,
    );
  }, 700);

  const listener = listeners[0];
  assert.ok(listener, "内容脚本必须注册 onMessage 监听器");

  const response = await new Promise((resolve, reject) => {
    const timer = setTimeout(
      () =>
        reject(
          new Error("虚拟列表下 SEND_TO_AI 一直没响应——仍在只认计数增长"),
        ),
      20000,
    );
    // 显式给生产等待一个 13s 上限：变异把内容通道改坏时，生产侧会在
    // 13s 超时并 clearInterval，**测试进程随即退出**。否则 setInterval
    // 会一直挂到 60s 默认超时，变异检查的每条锚都被拖一分钟。
    // 成功路径约 8.7s（700ms 落地 + 8s 稳定窗），留出 4s 余量。
    listener(
      {
        type: "SEND_TO_AI",
        prompt: "请回答本轮问题",
        config: { timeout: 13000 },
      },
      {},
      (r) => {
        clearTimeout(timer);
        resolve(r);
      },
    );
  });

  assert.equal(
    doc.querySelectorAll(".ds-assistant-message-main-content").length,
    3,
    "虚拟列表确实卸了一条：计数全程没涨，老判据在这里必然恒 false",
  );
  assert.equal(
    response?.success,
    true,
    `正文换了就该取回新回答，实际：${JSON.stringify(response)}`,
  );
  assert.equal(
    response.result?.content,
    NEW_ANSWER,
    "取回的必须是新回答正文，不是发送前那条旧回答",
  );
});

test("WAIT_FOR_RESPONSE 再超时：失败信封仍带回两个基准，续等链不许断", async () => {
  // 修复前 handleWaitForResponse 的超时分支什么都不挂：第一次续等再超时后，
  // 后台拿不到 baselineCount ⇒ 抛 RESUME_WAIT_NO_BASELINE，明明还能等却不许等。
  // 内容基准同理，丢了就等于把刚修好的内容通道关掉。
  const { listeners } = await loadContentScript(
    "qianwen-conversation.html",
    "qianwen.com",
  );
  const response = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("WAIT_FOR_RESPONSE 没有回话")), 5000);
    listeners[0](
      {
        type: "WAIT_FOR_RESPONSE",
        timeout: 120,
        baselineCount: 4,
        baselineContent: "发送前的最新回答正文",
      },
      {},
      (r) => {
        clearTimeout(timer);
        resolve(r);
      },
    );
  });

  assert.equal(response?.success, false);
  assert.equal(response?.code, "RESPONSE_TIMEOUT");
  assert.equal(response?.baselineCount, 4, "条数基准必须沿续等链传下去");
  assert.equal(
    response?.baselineContent,
    "发送前的最新回答正文",
    "内容基准也必须沿续等链传下去",
  );
});
