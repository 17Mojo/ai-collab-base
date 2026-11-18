/**
 * deepseek 的发送链路：**Enter 是主路径，而且现在有守护了**（A3，N54）。
 *
 * ## 这条链路此前是什么状态
 *
 * `SELECTORS.sendButton` 里四条 `button[...]` 选择器在真机上一命中都没命中过
 * （`fixtures/real/deepseek.json` 的 `sendButtonFound=false` 就是它们跑出来的），
 * 于是 `clickSend()` 一直在走 Enter 兜底——**但这条兜底没有任何测试**。
 * 它只是"顺便能用"，而不是"被验证过能用"。删掉 `dispatchEvent` 那三行，
 * 整套测试照样全绿，而 deepseek 会静默发不出消息、卡到 Response timeout。
 *
 * ## 现在守什么
 *
 *   1. 选择器必须是**空数组**（结论，不是遗漏）；想加回来必须先补 N60 的工件；
 *   2. `getSendButton()` 恒 null —— 空选择器 + fixture 无按钮，两件事同时成立；
 *   3. `clickSend()` 真的把 Enter keydown 派发到**输入框**，且事件形状正确
 *      （type / key / code / bubbles 一个都不能少）；
 *   4. 事件会**冒泡到 document**（真机把监听挂在祖先上，不冒泡就收不到）；
 *   5. 没输入框时不抛错也不乱发键（上层会以「等回复超时」的形式报出来）；
 *   6. 按钮分支还活着：一旦选择器被填回去，`clickSend()` 优先点按钮而不是敲 Enter，
 *      且按钮 disabled 时回落到 Enter —— 别被人当死代码顺手删掉。
 *
 * 对应变异锚共 4 条，见 mutation-check.mjs 的「deepseek 的 Enter 兜底…」两条、
 * 「deepseek 把猜出来的发送选择器塞回去」一条、「deepseek 的按钮分支被当死代码删掉」一条。
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { loadFixture } from "./adapter-matrix/adapter-test-utils.js";
import { SELECTORS, default as DeepSeekAdapter } from "../src/platforms/deepseek-adapter.js";

/** 装一份 deepseek 的手写 fixture，返回 {window, doc, adapter}。 */
function setup() {
  const dom = loadFixture("deepseek", "chat.deepseek.com");
  return { window: dom.window, doc: dom.window.document, adapter: new DeepSeekAdapter() };
}

/**
 * 在 document 上收集冒泡上来的 keydown。
 *
 * **必须是冒泡阶段（第三个参数 false/省略）**：写成 `true` 是捕获阶段，
 * 捕获会在事件下行时无条件调用，`bubbles:false` 也照样触发——
 * 那样测的就不是「冒泡」，而是「有祖先监听」。2026-11-19 踩过一次：
 * 变异锚「Enter 不再冒泡」在这条用例下**存活**，才发现用例写反了。
 */
function spyKeydown(doc) {
  const seen = [];
  doc.addEventListener("keydown", (e) => seen.push(e));
  return seen;
}

// ─────────────────────────────────────────────────────────────────────
// 1 · 选择器：空数组是结论
// ─────────────────────────────────────────────────────────────────────

test("deepseek 的 sendButton 选择器必须是空数组（N54 的结论，不是遗漏）", () => {
  assert.deepEqual(
    SELECTORS.sendButton,
    [],
    "这四条 button[...] 选择器在真机上一次都没命中过（fixtures/real/deepseek.json 的 " +
      "sendButtonFound=false 就是它们跑出来的）。想加回来：先补 N60 的发送区工件，" +
      "再同步改 fixture 的 data-expect-send-button 声明与矩阵断言。不许凭记忆加。",
  );
});

test("getSendButton() 在真机形状的 fixture 上返回 null", () => {
  const { adapter } = setup();
  assert.equal(adapter.getSendButton(), null, "空选择器 + 无按钮 fixture ⇒ 必须 null");
});

// ─────────────────────────────────────────────────────────────────────
// 2 · Enter 兜底：这是唯一的活路径，必须钉死
// ─────────────────────────────────────────────────────────────────────

test("clickSend() 把 Enter keydown 派发到输入框（形状：type/key/code/bubbles 一个都不能少）", async () => {
  const { doc, adapter } = setup();
  const input = adapter.getChatInput();
  assert.ok(input, "fixture 里必须有输入框，否则这条测不到东西");

  const got = [];
  input.addEventListener("keydown", (e) => got.push(e));

  await adapter.clickSend();

  assert.equal(got.length, 1, "应当恰好派发一次 keydown");
  const e = got[0];
  assert.equal(e.type, "keydown");
  assert.equal(e.key, "Enter", "只给 code 不给 key 时，部分实现读 event.key 会拿到空串");
  assert.equal(e.code, "Enter");
  assert.equal(e.bubbles, true, "真机把监听挂在祖先上，不冒泡就收不到");
});

test("Enter 事件会冒泡到 document（不是只落在输入框自己身上）", async () => {
  const { doc, adapter } = setup();
  const seen = spyKeydown(doc);

  await adapter.clickSend();

  assert.equal(seen.length, 1, "document 上应当收到冒泡上来的 keydown");
  assert.equal(seen[0].key, "Enter");
  assert.equal(
    seen[0].target,
    adapter.getChatInput(),
    "事件源必须是输入框，不能是 body 或别处",
  );
});

test("没有输入框时：不抛错、也不往别处乱发 Enter（上层会以「等回复超时」暴露）", async () => {
  const { doc, adapter } = setup();
  // 把输入框摘掉，模拟「选择器漂移 / 页面还没渲染好」
  for (const el of doc.querySelectorAll("textarea, [contenteditable='true']")) el.remove();
  assert.equal(adapter.getChatInput(), null, "前提：输入框确实没了");

  const seen = spyKeydown(doc);
  await adapter.clickSend(); // 不该抛

  assert.equal(seen.length, 0, "没有输入框就不该发键——发到 body 上是另一种静默错");
});

// ─────────────────────────────────────────────────────────────────────
// 3 · 按钮分支：现在是死分支，但不许被当死代码删掉
// ─────────────────────────────────────────────────────────────────────

test("若 getSendButton() 能返回按钮，clickSend() 优先点它而不是敲 Enter", async () => {
  const { doc, adapter } = setup();
  const seen = spyKeydown(doc);

  let clicked = 0;
  const fakeButton = { disabled: false, click: () => clicked++ };
  // 只替这一个方法：模拟「N60 补采到工件、选择器被填回去」之后的将来
  adapter.getSendButton = () => fakeButton;

  await adapter.clickSend();

  assert.equal(clicked, 1, "有按钮就该点按钮");
  assert.equal(seen.length, 0, "点了按钮就不该再敲 Enter（两条一起发 = 重复发送）");
});

test("按钮 disabled 时不点，回落到 Enter", async () => {
  const { doc, adapter } = setup();
  const seen = spyKeydown(doc);

  let clicked = 0;
  adapter.getSendButton = () => ({ disabled: true, click: () => clicked++ });

  await adapter.clickSend();

  assert.equal(clicked, 0, "disabled 的按钮点了也没用，不该点");
  assert.equal(seen.length, 1, "应当回落到 Enter");
  assert.equal(seen[0].key, "Enter");
});
