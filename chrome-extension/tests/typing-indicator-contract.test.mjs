/**
 * typingIndicator 普查证据契约测试（2026-11-04 零发送静态普查）
 *
 * ## 为什么需要这份测试
 *
 * kimi / chatglm / yiyan / longcat / yuanbao 五家的 typingIndicator 此前是
 * 照抄的猜测（'.spinner' / '[class*="loading"]' / '.typing-indicator'……），
 * 在 2026-10-25 真机实测里被证明两类都会坏：宽泛类名空闲页恒 true
 * （60 秒必超时），具体猜测类名全站不存在（isTyping 恒 false ⇒ 太早成功）。
 * 2026-11-04 对五家站点 bundle 做了零发送静态普查，每条选择器都拿到了
 * **站点自己渲染代码里的字面量级证据**（出处写在各 adapter 的注释里）。
 *
 * ## 这份测试守什么
 *
 *   1. 每条证据选择器单独命中 ⇒ isTyping() 为 true（删掉任何一条都有一条测试变红，
 *      对应变异锚见 tests/real-machine/mutation-check.mjs）；
 *   2. 空闲 DOM ⇒ false；
 *   3. **排除项的反例**：被判定「不许算生成中」的字面量（chatglm 敏感态
 *      div.sensitive[ga-data="stop"]、kimi 通用加载组件 core-spiral-loading、
 *      longcat 思考完成后仍保留的 reason-title）出现时必须为 false——
 *      否则空闲页恒 true ⇒ 每次等待必超时。
 *
 * 判据是**生产 adapter 源码**跑出来的结果（不抄选择器表）。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import YiyanAdapter from "../src/platforms/yiyan-adapter.js";
import LongCatAdapter from "../src/platforms/longcat-adapter.js";
import YuanbaoAdapter from "../src/platforms/yuanbao-adapter.js";
import KimiAdapter from "../src/platforms/kimi-adapter.js";
import ChatGLMAdapter from "../src/platforms/chatglm-adapter.js";

/**
 * 把 HTML 片段挂进 jsdom 并接好全局对象（生产 adapter 用裸 document / window）。
 * @param {string} bodyHtml
 * @param {string} url
 * @returns {JSDOM}
 */
function mount(bodyHtml, url) {
  const dom = new JSDOM(`<!DOCTYPE html><html><body>${bodyHtml}</body></html>`, {
    url,
    pretendToBeVisual: true,
  });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.location = dom.window.location;
  globalThis.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
  return dom;
}

// ─────────────────────────────────────────────────────────────────────
// 1. 文心一言（yiyan）——main-130a629d.js 普查证据
// ─────────────────────────────────────────────────────────────────────

test("文心：thinking-loading 自定义元素判定 isTyping（普查证据）", () => {
  mount("<thinking-loading></thinking-loading>", "https://yiyan.baidu.com/");
  assert.equal(new YiyanAdapter().isTyping(), true);
});

test("文心：thinking-loading 类名变体判定 isTyping（普查证据）", () => {
  mount('<div class="thinking-loading"></div>', "https://yiyan.baidu.com/");
  assert.equal(new YiyanAdapter().isTyping(), true);
});

test("文心：text-loading「生成中...」加载行判定 isTyping（普查证据）", () => {
  mount('<div class="text-loading-show">生成中...</div>', "https://yiyan.baidu.com/");
  assert.equal(new YiyanAdapter().isTyping(), true);
});

test("文心：停止回答按钮（answer-generate-state-button data-module=stop）判定 isTyping（普查证据）", () => {
  mount(
    '<div class="answer-generate-state-button" data-module="stop">停止回答</div>',
    "https://yiyan.baidu.com/",
  );
  assert.equal(new YiyanAdapter().isTyping(), true);
});

test("文心：statusbox aria 停止回答兜底判定 isTyping（普查证据）", () => {
  mount(
    '<div class="statusbox"><div role="button" aria-label="停止回答">停止回答</div></div>',
    "https://yiyan.baidu.com/",
  );
  assert.equal(new YiyanAdapter().isTyping(), true);
});

test("文心：空闲 DOM 不判定为生成中", () => {
  mount('<div class="answer-text"><p>你好</p></div>', "https://yiyan.baidu.com/");
  assert.equal(new YiyanAdapter().isTyping(), false);
});

// ─────────────────────────────────────────────────────────────────────
// 2. LongCat——chunk 8575268a/27443337/f8ccdd86 普查证据
// ─────────────────────────────────────────────────────────────────────

test("LongCat：stop-generate 停止生成按钮判定 isTyping（普查证据）", () => {
  mount('<div class="stop-generate">停止生成</div>', "https://longcat.chat/");
  assert.equal(new LongCatAdapter().isTyping(), true);
});

test("LongCat：v-loading-dot 打字点判定 isTyping（普查证据）", () => {
  mount('<div class="v-loading-dot"></div>', "https://longcat.chat/");
  assert.equal(new LongCatAdapter().isTyping(), true);
});

test("LongCat：assistant-main 消息气泡内的 v-loading-dot 判定 isTyping（普查证据）", () => {
  mount(
    '<div class="assistant-main"><div class="v-loading-dot"></div></div>',
    "https://longcat.chat/",
  );
  assert.equal(new LongCatAdapter().isTyping(), true);
});

test("LongCat：loading-dot-box 深研点点点判定 isTyping（普查证据）", () => {
  mount('<div class="loading-dot-box"><i></i><i></i></div>', "https://longcat.chat/");
  assert.equal(new LongCatAdapter().isTyping(), true);
});

test("LongCat：loading-text「正在生成图片...」判定 isTyping（普查证据）", () => {
  mount('<div class="loading-text">正在生成图片...</div>', "https://longcat.chat/");
  assert.equal(new LongCatAdapter().isTyping(), true);
});

test("LongCat：思考完成后的 reason-title（文案变『已深度思考』）不许算生成中", () => {
  // 排除项反例：reason-title 元素思考完成后**保留**（qianwen data-status=complete
  // 同类边界）。算进来 = isTyping 恒 true = 每次等待必超时。
  mount(
    '<div class="reason-content-item"><div class="reason-title">已深度思考</div></div>',
    "https://longcat.chat/",
  );
  assert.equal(new LongCatAdapter().isTyping(), false);
});

test("LongCat：空闲 DOM 不判定为生成中", () => {
  mount('<div class="chat-message">你好</div>', "https://longcat.chat/");
  assert.equal(new LongCatAdapter().isTyping(), false);
});

// ─────────────────────────────────────────────────────────────────────
// 3. 腾讯元宝（yuanbao）——yb_v2 chunks 136/7972/3807/6742/7538 普查证据
// ─────────────────────────────────────────────────────────────────────

test("元宝：data-conv-outputting 状态属性判定 isTyping（普查证据）", () => {
  mount('<div data-conv-speaker="ai" data-conv-outputting="true"></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：ai-placeholder 等待首 token 占位判定 isTyping（普查证据）", () => {
  mount('<div class="ai-placeholder"></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：停止回答按钮（yuanbao-send-btn aria）判定 isTyping（普查证据）", () => {
  mount(
    '<button id="yuanbao-send-btn" aria-label="停止回答">停止回答</button>',
    "https://yuanbao.tencent.com/",
  );
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：SendButton_sendStop 类名（带哈希后缀）判定 isTyping（普查证据）", () => {
  mount('<div class="SendButton_sendStop__Qj6Ko"></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：深思考骨架屏 anim 图标判定 isTyping（普查证据）", () => {
  mount('<div class="hyc-deepthink-steps__header-icon--anim"></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：markdown 流式打字点判定 isTyping（普查证据）", () => {
  mount('<div class="hyc-common-markdown__code__generating-dots"></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), true);
});

test("元宝：空闲 DOM 不判定为生成中", () => {
  mount('<div data-conv-speaker="ai" data-conv-outputting="false"><p>你好</p></div>', "https://yuanbao.tencent.com/");
  assert.equal(new YuanbaoAdapter().isTyping(), false);
});

// ─────────────────────────────────────────────────────────────────────
// 4. Kimi——entry.js 段 16700/38420 + c8a0d849 + cfd0f68a 普查证据
// ─────────────────────────────────────────────────────────────────────

test("Kimi：segment-generate-tip 生成中状态行判定 isTyping（普查证据）", () => {
  mount(
    '<div class="segment"><div class="segment-generate-tip">正在生成中…</div></div>',
    "https://www.kimi.com/",
  );
  assert.equal(new KimiAdapter().isTyping(), true);
});

test("Kimi：awaiting-first-response 等待首响应判定 isTyping（普查证据）", () => {
  mount(
    '<div class="chat-content-item awaiting-first-response"><div class="awaiting-loading"></div></div>',
    "https://www.kimi.com/",
  );
  assert.equal(new KimiAdapter().isTyping(), true);
});

test("Kimi：segment-pending-loading PENDING 态判定 isTyping（普查证据）", () => {
  mount('<div class="segment"><div class="segment-pending-loading"></div></div>', "https://www.kimi.com/");
  assert.equal(new KimiAdapter().isTyping(), true);
});

test("Kimi：send-button-container.stop 停止输出按钮判定 isTyping（普查证据）", () => {
  mount('<div class="send-button-container stop"></div>', "https://www.kimi.com/");
  assert.equal(new KimiAdapter().isTyping(), true);
});

test("Kimi：core-spiral-loading（历史/文件卡复用，无 role=status）不许算生成中", () => {
  // 排除项反例：该组件在历史列表/文件卡等多处复用，裸类名算进来 = 空闲页恒 true。
  mount('<div class="core-spiral-loading"></div>', "https://www.kimi.com/");
  assert.equal(new KimiAdapter().isTyping(), false);
});

test("Kimi：空闲 DOM 不判定为生成中", () => {
  mount('<div class="segment"><p>你好</p></div>', "https://www.kimi.com/");
  assert.equal(new KimiAdapter().isTyping(), false);
});

// ─────────────────────────────────────────────────────────────────────
// 5. 智谱清言（chatglm）——StopGenerator/85202fed/8461 chunk 普查证据
// ─────────────────────────────────────────────────────────────────────

test("ChatGLM：button ga-data=stop 停止回答按钮判定 isTyping（普查证据）", () => {
  mount('<button ga-data="stop">停止回答</button>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), true);
});

test("ChatGLM：markdown 流式 loadingGif 光标判定 isTyping（普查证据）", () => {
  mount('<div class="markdown-body"><img class="loadingGif" /></div>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), true);
});

test("ChatGLM：loading-text is-no-data 心跳思考态判定 isTyping（普查证据）", () => {
  mount('<div class="loading-text is-no-data">还在思考中，你先忙别的吧～</div>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), true);
});

test("ChatGLM：stop-generate 编辑器停止生成按钮判定 isTyping（普查证据）", () => {
  mount('<div class="stop-generate">停止生成</div>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), true);
});

test("ChatGLM：div.sensitive[ga-data=stop]（内容安全敏感态）不许算生成中", () => {
  // 排除项反例：同名 ga-data="stop" 属性挂在 div.sensitive 上——那不是生成指示器。
  // 选择器必须限定 button 标签，否则敏感态误命中 ⇒ 空闲/敏感页恒 true。
  mount('<div class="sensitive" ga-data="stop">内容安全提示</div>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), false);
});

test("ChatGLM：空闲 DOM 不判定为生成中", () => {
  mount('<div class="chat-message">你好</div>', "https://www.chatglm.cn/");
  assert.equal(new ChatGLMAdapter().isTyping(), false);
});

// ─────────────────────────────────────────────────────────────────────
// 6. 可见性纪律（复用 kimi 信号做代表）：display:none 的指示器不算
// ─────────────────────────────────────────────────────────────────────

test("display:none 的生成中指示器不判定为 isTyping（可见性纪律）", () => {
  mount(
    '<div class="segment"><div class="segment-generate-tip" style="display:none">正在生成中…</div></div>',
    "https://www.kimi.com/",
  );
  assert.equal(new KimiAdapter().isTyping(), false);
});
