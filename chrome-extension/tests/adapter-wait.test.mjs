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

import { waitForResponseGeneric } from "../src/platforms/adapter-utils.js";
import PlatformAdapter from "../src/platforms/adapter.js";

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
