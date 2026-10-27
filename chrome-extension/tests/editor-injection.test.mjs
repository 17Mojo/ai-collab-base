/**
 * 编辑器注入的守护用例 —— 2026-10-26 W-D1 排演查出来的第 6 个断点
 *
 * ## 断点是什么
 *
 * 千问的输入框是 Slate 编辑器（`div[data-slate-editor="true"][role="textbox"]`）。
 * 内容不在 DOM 里，而在 **Slate 自己的模型**里。
 * 原来的注入走 `document.execCommand('insertText')`：
 *
 *   - 文字进了 DOM ✔
 *   - Slate 的模型**仍然是空的** ✘
 *
 * 于是站点读到「用户没输入」⇒ **发送按钮保持 disabled** ⇒ 点它等于没点
 * ⇒ 永远等不到回复 ⇒ 每次执行都超时。
 *
 * 真机实测（2026-10-26，千问）：execCommand 注入后发送按钮 `disabled` 依旧是
 * `true`；换成 `beforeinput` 事件后变成 `false`。
 *
 * 还有一个**分支顺序**的坑：Slate 的编辑区带 `role="textbox"`，而
 * `injectTextSmart` 原本把 `role="textbox"` 排在 `isContentEditable` 前面
 * ⇒ 千问走的是 `injectIntoTextbox`（纯 execCommand）⇒ 把修复写在
 * `injectIntoContentEditable` 里对千问是**死代码**。
 *
 * ## 这份测试守的是什么
 *
 * 用一个**按真机结构仿真**的 Slate 站点（模型与 DOM 分离、发送按钮读模型、
 * 选区要靠 selectionchange 同步进模型）驱动**生产代码**
 * （src/platforms/adapter-utils.js + src/platforms/slate-editor.js），
 * 断言四件事：
 *
 *   1. 注入后**模型**收到文本（不是只有 DOM 里有字），发送按钮解禁；
 *   2. 编辑器里已有内容时是**替换**而不是追加；
 *   3. 模型收不到时**抛错**——不许留一个「看起来成功、站点其实没收到」的假成功；
 *   4. 注入全程**不碰** `execCommand`（它只改 DOM、不改模型）。
 *
 * 仿真只负责**扮演第三方站点**（模型与选区的行为）；判定一律由生产代码给出。
 * 仿真本体在 tests/helpers/slate-site.mjs（矩阵与接线测试共用同一份）。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { JSDOM } from "jsdom";
import { installGlobals } from "./adapter-matrix/adapter-test-utils.js";
import { installSlateSiteBehavior } from "./helpers/slate-site.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLATFORMS_DIR = path.resolve(__dirname, "..", "src", "platforms");

/** 生产代码（直接引生产模块，不复制注入逻辑）。 */
const utils = await import(
  pathToFileURL(path.join(PLATFORMS_DIR, "adapter-utils.js")).href
);

/**
 * 搭一个按真机结构仿真的 Slate 站点。
 *
 * 真机结构（2026-10-26 千问实测）：
 *
 *   <div data-slate-editor="true" data-slate-node="value"
 *        role="textbox" contenteditable="true">
 *     <p data-slate-node="element">
 *       <span data-slate-node="text">
 *         <span data-slate-leaf="true">
 *           <!-- 模型为空时： -->
 *           <span data-slate-zero-width="n" data-slate-length="0"><br></span>
 *           <span data-slate-placeholder="true" contenteditable="false">向千问提问</span>
 *           <!-- 模型有文本时： -->
 *           <span data-slate-string="true">文本</span>
 *
 * @param {object} options
 * @param {boolean} options.acceptBeforeInput - false = 假装站点不处理 beforeinput
 * @returns {object}
 */
function createSlateEditor({ acceptBeforeInput = true } = {}) {
  const dom = new JSDOM(
    `<!doctype html><html><body>
       <button id="send" disabled>发送</button>
     </body></html>`,
    { url: "https://www.qianwen.com/", pretendToBeVisual: true },
  );
  installGlobals(dom.window);

  const { window } = dom;
  const { document } = window;

  // ── 记录生产代码有没有碰 execCommand（它只改 DOM，不改模型）─────────
  const execCalls = [];
  const realExec = document.execCommand;
  document.execCommand = function (...args) {
    execCalls.push(args[0]);
    return realExec.apply(this, args);
  };

  const editor = document.createElement("div");
  editor.setAttribute("data-slate-editor", "true");
  editor.setAttribute("data-slate-node", "value");
  editor.setAttribute("role", "textbox");
  editor.setAttribute("contenteditable", "true");
  editor.setAttribute("aria-multiline", "true");
  editor.setAttribute("data-placeholder", "向千问提问");
  document.body.appendChild(editor);

  const sendButton = document.getElementById("send");

  const site = installSlateSiteBehavior(window, editor, {
    acceptBeforeInput,
    sendButton,
  });

  return {
    dom,
    editor,
    sendButton,
    model: site.model,
    execCalls,
    type: site.type,
  };
}

test("Slate：注入后模型收到文本、发送按钮解禁（不靠 execCommand）", async () => {
  const site = createSlateEditor();
  const { editor, sendButton, model, execCalls } = site;

  assert.equal(sendButton.disabled, true, "仿真起点：模型为空 ⇒ 发送按钮禁用");

  await utils.injectTextSmart(editor, "你好，世界");

  assert.equal(
    model.text,
    "你好，世界",
    "模型必须收到文本（站点据此判断「用户输入了」）",
  );
  assert.equal(
    editor.querySelector("[data-slate-zero-width]"),
    null,
    "模型有文本后，零宽叶子必须消失",
  );
  assert.equal(sendButton.disabled, false, "发送按钮必须解禁");
  assert.deepEqual(
    execCalls,
    [],
    "模型感知的注入不能碰 execCommand——它只改 DOM，模型看不见",
  );
});

test("Slate：编辑器里已有内容时是替换，不是追加", async () => {
  const site = createSlateEditor();
  const { editor, sendButton, model } = site;

  site.type("旧文字残留");
  assert.equal(model.text, "旧文字残留");

  await utils.injectTextSmart(editor, "新提示词");

  assert.equal(model.text, "新提示词", "旧内容必须被替换掉，不能追加在后面");
  assert.equal(sendButton.disabled, false);
});

test("Slate：多行提示词原样进模型", async () => {
  const site = createSlateEditor();
  const { editor, model } = site;

  const prompt = "第一行\n第二行\n第三行";
  await utils.injectTextSmart(editor, prompt);

  assert.equal(model.text, prompt, "多行提示词要原样进模型");
});

test("Slate：模型收不到文本时必须抛错，不许假成功", async () => {
  const site = createSlateEditor({ acceptBeforeInput: false });
  const { editor, sendButton } = site;

  await assert.rejects(
    () => utils.injectTextSmart(editor, "你好，世界"),
    /编辑器模型没有接收注入的文本/,
    "模型没收到 ⇒ 必须报错，不能让 Pack 拿着一个空结果继续往下走",
  );
  assert.equal(sendButton.disabled, true, "模型没收到 ⇒ 发送按钮就该是禁用的");
});

test("路由：带 role=textbox 的 Slate 编辑区必须走模型感知路径", async () => {
  const site = createSlateEditor();
  const { editor, model, execCalls } = site;

  // 前提：这个元素的 role 就是 textbox（真机实测千问如此）。
  assert.equal(editor.getAttribute("role"), "textbox");

  await utils.injectTextSmart(editor, "走对了分支");

  assert.equal(
    model.text,
    "走对了分支",
    "role=textbox 的 Slate 元素若走 injectIntoTextbox，模型会一直是空的",
  );
  assert.deepEqual(execCalls, []);
});

test("普通 contenteditable：仍走原来的注入路径，不受 Slate 逻辑影响", async () => {
  const dom = new JSDOM(
    `<!doctype html><html><body><div id="ed" contenteditable="true"></div></body></html>`,
    { url: "https://example.com/", pretendToBeVisual: true },
  );
  installGlobals(dom.window);

  const editor = dom.window.document.getElementById("ed");
  await utils.injectTextSmart(editor, "普通输入框");

  assert.ok(
    editor.textContent.includes("普通输入框"),
    `普通 contenteditable 应当照旧注入成功，实际 DOM：${editor.innerHTML}`,
  );
});
