/**
 * 千问 adapter 的 DOM 契约测试
 *
 * ## 为什么需要这份测试
 *
 * 2026-10-25 真机实测（B-3）发现：千问 adapter 原来的六条选择器
 * （.response-content / .prose / [class*="chat-item"] / .typing-indicator …）
 * 在千问自己的 56 个资源 / 15.45 MB 静态资源里**一次都没出现过**（普查见
 * tests/real-machine/evidence/qianwen-asset-census.json）——它们是照着别的站点
 * 抄来的，在千问上永远命中 0 个。
 *
 * 问题是：千问的会话 DOM **采不到**（需要已登录的浏览器 profile，那是 L2
 * 真机会话的事）。采不到就没有「快照 → 选择器」的对账，缺陷就又会潜伏
 * 下去——这正是本仓 110/114 全绿的矩阵掩盖 4 个真机缺陷的老毛病。
 *
 * 所以这里的做法是：**用千问自己产物里的结构当契约**。
 * fixture（fixtures/qianwen-*.html）的每一处 class 与 data 属性都来自
 * 站点自己的 CSS / React 渲染代码 / 自己的文本选择功能声明，
 * 依据写在每个 fixture 的注释里。
 *
 * 判据是**生产 adapter 源码**（不是抄一份选择器表）跑出来的结果：
 * 抄一份表 = 又造一个平行宇宙，生产选择器漂移了这里照样全绿。
 *
 * ## 这份测试守什么
 *
 *   1. 消息计数**只算 AI 的回答**——不算提问卡，也不算界面外壳
 *      （旧的 '[class*="message"]' 会命中 message-list-container）；
 *   2. 正文取**整个** markdown 容器，不只第一段；
 *   3. 发送按钮认**不随语言变**的 data 属性，不认本地化文案；
 *   4. 「正在生成」认得出停止回答按钮与接收中卡片；
 *   5. waitForResponse **必须等「计数涨了」且「不再生成」**才返回。
 *
 * 每一条都有一条对应的变异检查（tests/real-machine/mutation-check.mjs），
 * 证明「改坏这处，对应测试会变红」——否则全绿什么都不能证明。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

import QianwenAdapter from "../../src/platforms/qianwen-adapter.js";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 载入千问 fixture 到 jsdom，并把全局对象接好。
 *
 * 生产 adapter 用的是裸 document / window，不接上就跑不起来。
 *
 * @param {"conversation"|"generating"|"waiting"} state
 * @returns {JSDOM}
 */
function loadFixture(state) {
  const html = readFileSync(join(HERE, "fixtures", `qianwen-${state}.html`), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://www.qianwen.com/",
    pretendToBeVisual: true,
  });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.location = dom.window.location;
  globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
  return dom;
}

/**
 * 轮询等待一小段时间。
 * @param {number} ms
 */
function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * 往 DOM 里追加一轮「刚写完的回答」，模拟模型答完。
 * @param {Document} doc
 */
function appendSecondAnswer(doc) {
  const round = doc.querySelector('[data-chat-list-key="chat-2"]');
  const answers = round.querySelector(".chat-answers-card-wrap");
  answers.insertAdjacentHTML(
    "beforeend",
    `<div class="answer-common-card undefined" data-mt="custom/markdown">
       <div class="answer-text md-text-card">
         <div class="qk-markdown qk-markdown-react qk-markdown-code-light">
           <p><span class="qk-md-text">明天多云，气温 16 到 25 摄氏度。</span></p>
           <p><span class="qk-md-text">有短时阵雨，建议带伞。</span></p>
         </div>
       </div>
     </div>`,
  );
}

/**
 * 把输入区的「停止回答」换成「发送消息」——生成结束。
 * @param {Document} doc
 */
function finishGenerating(doc) {
  const stop = doc.querySelector('[data-probe-role="stop-button"]');
  if (!stop) return;
  stop.outerHTML = `<button type="button" aria-label="Send message"
      data-session-switch-target="send-query" data-probe-role="send-button"
      class="inline-flex size-8 shrink-0 items-center justify-center rounded-full"></button>`;
}

// ─────────────────────────────────────────────────────────────────────
// 1. 消息计数：只算 AI 的回答
// ─────────────────────────────────────────────────────────────────────

test("消息数只算答案卡：提问卡与消息容器都不算数", () => {
  const dom = loadFixture("conversation");
  const adapter = new QianwenAdapter();

  const messages = adapter.getMessageList();

  // fixture 里有 2 轮完整回答 ⇒ 2 条消息
  assert.equal(
    messages.length,
    2,
    `应当只有 2 条（两轮回答），实际 ${messages.length}：` +
      messages.map((m) => m.className).join(" | "),
  );

  // 命中的必须都是答案正文卡
  for (const m of messages) {
    assert.ok(
      m.classList.contains("answer-text"),
      `命中的不该是提问卡或容器：${m.className}`,
    );
    assert.ok(
      !m.className.includes("message-list"),
      `消息容器被当成了消息：${m.className}`,
    );
  }

  // 反证：旧的宽松选择器确实会把计数撑大——这正是本次要修的病
  const loose = dom.window.document.querySelectorAll('[class*="message"]');
  assert.ok(
    loose.length > messages.length,
    `旧选择器 '[class*=\"message\"]' 在这份 fixture 上命中 ${loose.length} 个，` +
      `应当多于新选择器的 ${messages.length} 个（说明这次修复确实挡住了外壳）`,
  );
});

test("最新消息是最后一轮的答案卡", () => {
  loadFixture("conversation");
  const adapter = new QianwenAdapter();

  const latest = adapter.getLatestMessage();
  assert.ok(latest, "getLatestMessage() 不该返回 null");
  assert.ok(
    latest.closest('[data-chat-list-key="chat-2"]'),
    `最新消息应当来自第二轮，实际来自 ${
      latest.closest("[data-chat-list-key]")?.getAttribute("data-chat-list-key")
    }`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 2. 正文提取
// ─────────────────────────────────────────────────────────────────────

test("答案正文取整个 markdown 容器，两段都要", () => {
  loadFixture("conversation");
  const adapter = new QianwenAdapter();

  const content = adapter._extractContent(adapter.getLatestMessage());

  assert.match(content, /明天多云/, `正文缺第一段：${content}`);
  assert.match(content, /有短时阵雨/, `正文缺第二段（只取到第一段）：${content}`);
});

test("markdown 容器与答案卡是同一个元素时也能取到完整正文", () => {
  // 这种形态下「答案卡」本身就带 qk-markdown 类，内部再没有第二个 markdown 容器。
  // 若只查后代，'.qk-markdown' 查不到 ⇒ 退到 '.qk-md-text' ⇒ 只拿到**第一段**。
  const dom = new JSDOM(
    `<div class="answer-common-card answer-text md-text-card qk-markdown">
       <p><span class="qk-md-text">第一段。</span></p>
       <p><span class="qk-md-text">第二段。</span></p>
     </div>`,
    { url: "https://www.qianwen.com/" },
  );
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);

  const adapter = new QianwenAdapter();
  const card = dom.window.document.querySelector(".answer-text");

  const content = adapter._extractContent(card);
  assert.match(content, /第一段/, `正文缺第一段：${content}`);
  assert.match(content, /第二段/, `正文缺第二段（只取到第一段）：${content}`);
});

// ─────────────────────────────────────────────────────────────────────
// 3. 输入框与发送按钮
// ─────────────────────────────────────────────────────────────────────

test("输入框命中 Slate 编辑器", () => {
  const dom = loadFixture("conversation");
  const adapter = new QianwenAdapter();

  const input = adapter.getChatInput();
  assert.ok(input, "getChatInput() 不该返回 null");
  assert.equal(
    input.getAttribute("data-slate-editor"),
    "true",
    `输入框应当是 Slate 编辑器，实际是 ${input.getAttribute("class")}`,
  );
});

test("发送按钮靠稳定属性命中，不依赖本地化文案", () => {
  const dom = loadFixture("conversation");
  const adapter = new QianwenAdapter();

  const button = adapter.getSendButton();
  assert.ok(button, "getSendButton() 不该返回 null");
  assert.equal(
    button.getAttribute("data-session-switch-target"),
    "send-query",
    "发送按钮应当靠 data 属性命中",
  );
  // fixture 的 aria-label 故意是英文：证明认的不是本地化文案
  assert.equal(
    button.getAttribute("aria-label"),
    "Send message",
    "fixture 的 aria-label 应为英文，用来证明适配器不依赖中文文案",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 4. 生成中判定
// ─────────────────────────────────────────────────────────────────────

test("空闲会话上 isTyping() 为 false", () => {
  loadFixture("conversation");
  const adapter = new QianwenAdapter();

  assert.equal(adapter.isTyping(), false, "空闲页不该判定为正在生成");
});

test("生成中 isTyping() 为 true（识别停止回答按钮）", () => {
  loadFixture("generating");
  const adapter = new QianwenAdapter();

  assert.equal(
    adapter.isTyping(),
    true,
    "流式输出中（有停止回答按钮）必须判定为正在生成，否则会提前返回半截答案",
  );
});

test("等待首个 token 时 isTyping() 为 true（识别接收中卡片）", () => {
  loadFixture("waiting");
  const adapter = new QianwenAdapter();

  assert.equal(
    adapter.isTyping(),
    true,
    "等待首个 token 时（接收中点点点卡片）必须判定为正在生成",
  );
});

test("只有接收中卡片（没有停止回答按钮）时 isTyping() 仍为 true", () => {
  const dom = loadFixture("waiting");
  const adapter = new QianwenAdapter();

  // 把「停止回答」按钮拿掉，只留接收中点点点卡片这一个信号——
  // 这样才测得出「接收中卡片本身被认出来了」，而不是被按钮顺带盖住。
  dom.window.document.querySelector('[data-probe-role="stop-button"]')?.remove();

  assert.equal(
    adapter.isTyping(),
    true,
    "接收中卡片本身就是生成中的信号，不能只靠停止回答按钮",
  );
});

test("等待首个 token 时消息数不因接收卡片而增加", () => {
  loadFixture("waiting");
  const adapter = new QianwenAdapter();

  assert.equal(
    adapter.getMessageList().length,
    1,
    "接收中卡片不是一条消息：用户一按下发送计数就 +1 会导致提前返回",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 5. 端到端：waitForResponse 的计数 + 生成中 双重条件
// ─────────────────────────────────────────────────────────────────────

test("waitForResponse 等到「计数涨了且不再生成」才返回", async () => {
  // 用「生成中」那份 fixture：输入区此时是「停止回答」按钮
  const dom = loadFixture("generating");
  const adapter = new QianwenAdapter();

  // 回到「第二轮刚问出去、还没答」的状态：提问卡留着，回答清空
  dom.window.document
    .querySelector('[data-chat-list-key="chat-2"] .chat-answers-card-wrap')
    .replaceChildren();

  let settled = false;
  const waiting = adapter.waitForResponse(8000).then((r) => {
    settled = true;
    return r;
  });

  // 第二轮答案出现 ⇒ 计数 +1，但仍在生成（停止回答按钮还在）
  await delay(200);
  appendSecondAnswer(dom.window.document);
  await delay(1200);
  assert.equal(
    settled,
    false,
    "还在生成中就必须继续等：提前返回会拿到半截答案",
  );

  // 生成结束：停止回答 → 发送消息
  finishGenerating(dom.window.document);

  const result = await waiting;
  assert.equal(result.messageCount, 2, "应当看到 2 条消息");
  assert.match(result.content, /有短时阵雨/, `应当拿到完整回答，实际：${result.content}`);
});
