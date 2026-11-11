/**
 * messageList 的「基准」不能跨选择器跳变 —— 2026-11-11 文心 L2 超时 243.6s 的守护。
 *
 * ## 缺陷长什么样
 *
 * `findElements(selectors)` 是**按优先级取第一个有命中的选择器**（不是合并）。
 * 文心新 UI 的落地页上：
 *   - `div.answer-container`（发送前）= 0
 *   - `[class*="message"]` = 8，命中的全是「通知中心」元素，不是气泡
 *
 * 于是发送前 `baselineCount` 取到了 8（通知中心那一组）；AI 回答落地后
 * `div.answer-container` 变成 1，`findElements` **改取第一条选择器**返回 1。
 * `countGrew = 1 > 8` 恒 false ⇒ 明明答完了还一直判 Response timeout，
 * 续等 4 个 60s 窗口（243.6s ≈ 4×60+3.6）才失败。
 *
 * 这类缺陷不会报错、不会在截图里露出「没答」，只会表现为「平台很慢」——
 * 所以必须有一条测试钉住「发送前的基准」和「回答后的容器」是**同一组元素**。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import { findElements } from "../src/platforms/adapter-utils.js";
import { SELECTORS as YIYAN_SELECTORS } from "../src/platforms/yiyan-adapter.js";

/** 文心新 UI 落地页：8 个恒在的「通知中心」元素，一个气泡都没有。 */
const NOTIFICATION_CENTER = `
  <div class="message-center-container _message-center_x"></div>
  <div class="message-panel-container-wrapper"></div>
  <div class="message-center-icon">通知</div>
  <div class="message-panel-item"></div>
  <div class="message-panel-title"></div>
  <div class="message-tab-item"></div>
  <div class="message-list-container"></div>
  <div class="message-empty-tip"></div>`;

function site(html) {
  const dom = new JSDOM(`<!doctype html><html><body>${html}</body></html>`);
  global.window = dom.window;
  global.document = dom.window.document;
  return dom.window.document;
}

const answer = (text) =>
  `<div class="answer-container"><div class="ai-entry"><div class="cosd-markdown-content"><div class="marklang"><p class="marklang-paragraph">${text}</p></div></div></div></div>`;

test("文心落地页：通知中心恒在 8 个，但发送前的气泡基准必须是 0", () => {
  const doc = site(NOTIFICATION_CENTER);
  assert.equal(doc.querySelectorAll('[class*="message"]').length, 8, "先确认诱饵真的在");
  assert.equal(
    findElements(YIYAN_SELECTORS.messageList).length,
    0,
    "基准不能取通知中心那一组——否则回答落地后会换成另一组元素，countGrew 永远为 false",
  );
});

test("文心：回答落地后基准从 0 → 1，countGrew 成立", () => {
  const doc = site(NOTIFICATION_CENTER);
  const baseline = findElements(YIYAN_SELECTORS.messageList).length;
  doc.body.insertAdjacentHTML("beforeend", answer("普通AI等你一步步下指令"));
  const after = findElements(YIYAN_SELECTORS.messageList).length;
  assert.equal(baseline, 0);
  assert.equal(after, 1);
  assert.ok(after > baseline, "这就是 handleWaitForResponse 的完成判据");
});

test("文心已有会话页：旧回答 1 条 → 新回答 2 条，基准不跳组", () => {
  const doc = site(NOTIFICATION_CENTER + answer("旧回答"));
  const baseline = findElements(YIYAN_SELECTORS.messageList).length;
  doc.body.insertAdjacentHTML("beforeend", answer("新回答"));
  const after = findElements(YIYAN_SELECTORS.messageList).length;
  assert.equal(baseline, 1);
  assert.equal(after, 2);
  assert.ok(after > baseline);
});

test("取回的正文来自答案容器，不是通知中心", () => {
  const doc = site(NOTIFICATION_CENTER + answer("这是 AI 正文"));
  const latest = findElements(YIYAN_SELECTORS.messageList).at(-1);
  assert.ok(latest);
  assert.match(latest.textContent, /这是 AI 正文/);
  assert.doesNotMatch(latest.className, /message-center|message-panel/);
});
