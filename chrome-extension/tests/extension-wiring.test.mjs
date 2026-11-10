/**
 * 扩展内部的接线：popup ↔ 后台 ↔ 内容脚本
 *
 * ## 为什么要有这份测试
 *
 * Pack 的执行链路是三段：
 *
 *   popup  ─EXECUTE_PACK→  service-worker  ─SEND_TO_AI→  content-script
 *                                                              ↓
 *                                                    注入文本 / 点发送 / 等回复
 *
 * 2026-10-25 逐段查这条链路时发现：**三段都断**。
 *
 *   1. popup 用 `pack.id` 当 Pack 的 id —— 那个字段根本不存在
 *      （Pack 的 id 在 `metadata.pack_id` 里）⇒ data-id="undefined"；
 *   2. 执行器从来没拿到过 Pack —— `loadPack()` 定义了却没人调用，
 *      而 storage 才是 Pack 的事实源 ⇒ `getPack()` 恒为 null
 *      ⇒ 每次执行都是 "Pack not found"；
 *   3. 后台发 `SEND_TO_AI`，内容脚本**没有分支处理它** ⇒ 消息没人接
 *      ⇒ AI 步骤拿到 `undefined` 却仍被当成「成功」
 *      ⇒ Pack「执行成功」但产物是空的。
 *
 * 也就是说：**Pack 执行这条路今天是不通的**，而仓库里没有任何测试
 * 覆盖这条链路（矩阵只测 adapter 本身，不测接线）。
 *
 * ## 这份测试守四件事
 *
 *   1. **静态**：从 service-worker 出发把后台模块的 import 图走一遍，
 *      凡是后台发出去的消息类型，内容脚本必须都认；反过来内容脚本发出去的，
 *      后台必须都认。
 *      —— 这是「结构性」的护栏：以后谁再加一个 SEND_XXX 而忘了接，
 *      这里立刻红。
 *   2. **行为**：在 jsdom 里真的把生产内容脚本跑起来（不是抄一份逻辑），
 *      发一条 SEND_TO_AI，断言「提示词进了输入框、发送按钮被点了、
 *      AI 的回复被带回来了」。
 *   3. **Pack 接线**：storage 里的 Pack 要能真的被执行器找到并执行
 *      （钉住 "Pack not found" 那个洞）。
 *   4. **popup 接线**：列表里渲染出来的 data-id 必须是真正能执行的那个 id；
 *      popup 必须有「导入 Pack」的入口（此前没有 ⇒ 外部用户卡在第一步）。
 *   5. **发到哪里**：AI 步骤必须发到**用户当前所在的标签页**，
 *      而不是广播给每个打开的 AI 页面。
 *   6. **装完能不能用**：代码里 `getURL('public/xxx.html')` 指到的页面，
 *      在构建产物里必须真的存在（此前 404 ⇒ 「导入 Pack」断掉）。
 *
 * ## 为什么走 import 图而不是列一张表
 *
 * 列一张「后台会发哪些消息」的表，表本身就会和代码漂移。
 * 走 import 图意味着：**只有真的被 service-worker 引用到的模块**才算数，
 * 新加的模块自动进检查范围。
 *
 * 顺带说明 `src/background/multi-platform-executor.js`：它发的
 * `GET_LATEST_RESPONSE` 同样没人处理，但**没有任何模块 import 它**
 * ⇒ 它是死代码，不在检查范围内。一旦哪天有人把它接进 service-worker，
 * 本测试会立刻把它捞出来（那时才需要给它补 handler）。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { JSDOM } from "jsdom";
import vm from "node:vm";

import { loadServiceWorker } from "./helpers/service-worker-harness.mjs";
import { installSlateSiteIfNeeded } from "./helpers/slate-site.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "..");
const SRC = join(EXT_ROOT, "src");
const BG = join(SRC, "background");

const require = createRequire(import.meta.url);
const { copyStaticAssets } = require("../static-assets.cjs");

// ─────────────────────────────────────────────────────────────────────
// 静态分析工具
// ─────────────────────────────────────────────────────────────────────

/**
 * 从左括号开始，取出配对的调用实参文本。
 *
 * 只处理引号转义，不处理注释——本仓的源码里 sendMessage 调用都很短，
 * 注释里不会出现带括号的不平衡写法（真出现了，本测试会报「取不到实参」
 * 而不是悄悄放过）。
 *
 * @param {string} text
 * @param {number} openIdx - 左括号的下标
 * @returns {string}
 */
function extractCallArgs(text, openIdx) {
  let depth = 0;
  let quote = null;
  for (let i = openIdx; i < text.length; i += 1) {
    const ch = text[i];
    if (quote) {
      if (ch === "\\") {
        i += 1;
        continue;
      }
      if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") {
      quote = ch;
      continue;
    }
    if (ch === "(") depth += 1;
    else if (ch === ")") {
      depth -= 1;
      if (depth === 0) return text.slice(openIdx + 1, i);
    }
  }
  return "";
}

/**
 * 抽出文件里所有 sendMessage 发出去的消息类型。
 *
 * @param {string} text
 * @returns {Set<string>}
 */
function sentMessageTypes(text) {
  const types = new Set();
  const re = /chrome\.(?:runtime|tabs)\.sendMessage\s*\(/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const open = text.indexOf("(", m.index);
    const args = extractCallArgs(text, open);
    const t = args.match(/\btype\s*:\s*["']([^"']+)["']/);
    if (t) types.add(t[1]);
  }
  return types;
}

/**
 * 抽出文件里 `switch (message.type)` 处理的分支。
 *
 * @param {string} text
 * @returns {Set<string>}
 */
function handledMessageTypes(text) {
  const types = new Set();
  const start = text.indexOf("switch (message.type)");
  if (start === -1) return types;
  // 只看这个 switch 之后、下一个 switch 之前的部分
  const rest = text.slice(start);
  const next = rest.indexOf("switch (", 1);
  const scope = next === -1 ? rest : rest.slice(0, next);
  const re = /case\s+["']([^"']+)["']\s*:/g;
  let m;
  while ((m = re.exec(scope)) !== null) types.add(m[1]);
  return types;
}

/**
 * 从 service-worker 出发，把后台真正被引用到的模块全找出来。
 *
 * @returns {Set<string>} 绝对路径集合
 */
function reachableBackgroundModules() {
  const seen = new Set();
  const queue = [join(BG, "service-worker.js")];
  while (queue.length > 0) {
    const file = queue.pop();
    if (seen.has(file)) continue;
    seen.add(file);
    const text = readFileSync(file, "utf-8");
    for (const m of text.matchAll(/from\s+["'](\.[^"']+)["']/g)) {
      const target = resolve(dirname(file), m[1]);
      if (existsSync(target)) queue.push(target);
    }
  }
  return seen;
}

// ─────────────────────────────────────────────────────────────────────
// 1. 静态：消息类型必须两端都认
// ─────────────────────────────────────────────────────────────────────

test("后台发出去的消息类型，内容脚本必须都认", () => {
  const csText = readFileSync(join(SRC, "content", "content-script.js"), "utf-8");
  const handled = handledMessageTypes(csText);
  assert.ok(handled.size > 0, "解析不出内容脚本处理的消息类型——解析器本身坏了");

  const missing = [];
  for (const file of reachableBackgroundModules()) {
    for (const type of sentMessageTypes(readFileSync(file, "utf-8"))) {
      if (!handled.has(type)) {
        missing.push(`${type}（发自 ${file.replace(`${EXT_ROOT}/`, "")}）`);
      }
    }
  }

  assert.deepEqual(
    missing,
    [],
    "这些消息后台发了但内容脚本没有分支处理 ⇒ 发送方拿不到响应，" +
      "步骤会被当成成功但拿不到数据：" + missing.join("、"),
  );
});

test("内容脚本发出去的消息类型，后台必须都认", () => {
  const csText = readFileSync(join(SRC, "content", "content-script.js"), "utf-8");
  const swText = readFileSync(join(BG, "service-worker.js"), "utf-8");
  const handled = handledMessageTypes(swText);
  assert.ok(handled.size > 0, "解析不出后台处理的消息类型——解析器本身坏了");

  const missing = [];
  for (const type of sentMessageTypes(csText)) {
    if (!handled.has(type)) missing.push(type);
  }

  assert.deepEqual(
    missing,
    [],
    "内容脚本发了这些消息但后台没有分支处理：" + missing.join("、"),
  );
});

test("Pack 的 AI 步骤发的那条消息，内容脚本必须认", () => {
  // 单独钉一条：这是 Pack 执行能不能通的关键那一环，
  // 不依赖「消息类型集合」的整体推导。
  const executor = readFileSync(join(BG, "pack-executor.js"), "utf-8");
  const csText = readFileSync(join(SRC, "content", "content-script.js"), "utf-8");

  const sent = sentMessageTypes(executor);
  assert.ok(
    sent.has("SEND_TO_AI"),
    "pack-executor 应当发 SEND_TO_AI——它没发，说明执行链路又变了，" +
      "本测试的判据需要跟着改",
  );
  assert.ok(
    handledMessageTypes(csText).has("SEND_TO_AI"),
    "内容脚本必须处理 SEND_TO_AI：后台的 AI 步骤靠它才能拿到 AI 的回复",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 2. 行为：真的跑一次 SEND_TO_AI
// ─────────────────────────────────────────────────────────────────────

/** 每次导入都换 query，让内容脚本模块重新求值（模块级状态是 per-instance 的） */
let importCounter = 0;

/**
 * 在 jsdom 里把**生产内容脚本**跑起来。
 *
 * 跑的是 `src/content/content-script.js` 本体，不是抄一份逻辑——
 * 抄一份 = 又造一个平行宇宙，生产接线断了这里照样全绿。
 *
 * @param {string} fixtureName - tests/real-machine/fixtures/ 下的文件名
 * @param {string} adapterId - 让内容脚本认成哪个平台（= adapter.platformId）
 * @returns {Promise<{dom: JSDOM, listeners: Function[]}>}
 */
async function loadContentScript(fixtureName, adapterId) {
  const html = readFileSync(
    join(HERE, "real-machine", "fixtures", fixtureName),
    "utf-8",
  );
  const dom = new JSDOM(html, {
    url: "https://www.qianwen.com/",
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

  // jsdom 不实现浏览器才有的编辑能力，这里补上（生产代码依赖它们）：
  //   - document.execCommand：注入文本时用
  //   - input.isContentEditable：判断是不是富文本输入框
  //   - Event / KeyboardEvent：生产代码用**全局** Event 构造事件，
  //     而 Node 20+ 的全局 Event 与 jsdom 的 Event 不是同一个类，
  //     jsdom 的 dispatchEvent 会拒收 ⇒ 把全局指向 jsdom 的那一份。
  dom.window.document.execCommand = () => true;
  globalThis.Event = dom.window.Event;
  globalThis.KeyboardEvent = dom.window.KeyboardEvent;
  globalThis.MouseEvent = dom.window.MouseEvent;
  globalThis.InputEvent = dom.window.InputEvent;
  const input = dom.window.document.querySelector("[data-probe-role='chat-input']");
  if (input) {
    Object.defineProperty(input, "isContentEditable", {
      value: true,
      configurable: true,
    });
    // 快照是**静态**的：只有结构，没有行为。而千问的输入框是 Slate 编辑器，
    // 内容存在框架自己的模型里、只认 beforeinput（真机实测 2026-10-26）。
    // 不补上这个行为，生产代码的注入会正确地**报错**（模型没收到），
    // 而那正是我们要的诚实失败——快照自己得像真站点一样。
    installSlateSiteIfNeeded(dom.window, input, {
      sendButton: dom.window.document.querySelector(
        "[data-probe-role='send-button']",
      ),
    });
  }

  importCounter += 1;
  await import(`../src/content/content-script.js?bust=${importCounter}`);
  // initialize() 是异步的（要先问后台要适配器 id），等一个宏任务让它跑完
  await new Promise((r) => setTimeout(r, 0));

  return { dom, listeners };
}

/** 站点把 AI 回答贴上来时插入的卡片（结构照千问真实 DOM） */
const ANSWER_CARD = `<div class="answer-common-card undefined" data-mt="custom/markdown">
  <div class="answer-text md-text-card">
    <div class="qk-markdown qk-markdown-react qk-markdown-code-light">
      <p><span class="qk-md-text">明天多云，气温 16 到 25 摄氏度。</span></p>
      <p><span class="qk-md-text">有短时阵雨，建议带伞。</span></p>
    </div>
  </div>
</div>`;

test("SEND_TO_AI：提示词进了输入框、发送按钮被点了、AI 的回复被带回来", async () => {
  const { dom, listeners } = await loadContentScript(
    "qianwen-conversation.html",
    "qianwen.com",
  );
  const doc = dom.window.document;

  const listener = listeners[0];
  assert.ok(listener, "内容脚本必须注册 onMessage 监听器");

  let clicks = 0;
  const sendButton = doc.querySelector("[data-probe-role='send-button']");
  assert.ok(sendButton, "fixture 里必须有发送按钮");
  sendButton.addEventListener("click", () => {
    clicks += 1;
    // 站点是在发送**之后**才把回答贴上来的；这里延后一点，
    // 好让 waitForResponse 先记下基准消息数（否则计数不涨，永远等不到）
    setTimeout(() => {
      doc
        .querySelector('[data-chat-list-key="chat-2"] .chat-answers-card-wrap')
        .insertAdjacentHTML("beforeend", ANSWER_CARD);
    }, 700);
  });

  const response = await new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error("SEND_TO_AI 一直没有响应——内容脚本没有处理它")),
      10000,
    );
    const keepAlive = listener(
      { type: "SEND_TO_AI", prompt: "北京明天天气怎么样？" },
      {},
      (r) => {
        clearTimeout(timer);
        resolve(r);
      },
    );
    // 返回 true 才会保持消息通道开放（Chrome 的约定）
    assert.equal(keepAlive, true, "监听器必须返回 true 以保持消息通道开放");
  });

  assert.equal(response?.success, true, `SEND_TO_AI 应当成功：${JSON.stringify(response)}`);
  assert.equal(clicks, 1, "必须真的点了发送按钮");

  const input = doc.querySelector("[data-probe-role='chat-input']");
  assert.match(
    input.textContent,
    /北京明天天气怎么样/,
    "提示词必须被注入输入框",
  );

  assert.ok(response.result, "必须把 AI 的回复带回来");
  assert.match(
    response.result.content,
    /明天多云/,
    `回复正文不对：${response.result.content}`,
  );
  assert.match(
    response.result.content,
    /有短时阵雨/,
    `回复正文只拿到了第一段：${response.result.content}`,
  );
});

test("SEND_TO_AI：没有提示词就明确报错，不静默发空消息", async () => {
  const { listeners } = await loadContentScript(
    "qianwen-conversation.html",
    "qianwen.com",
  );
  const listener = listeners[0];

  const response = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("没有响应")), 5000);
    listener({ type: "SEND_TO_AI", prompt: "   " }, {}, (r) => {
      clearTimeout(timer);
      resolve(r);
    });
  });

  assert.equal(response?.success, false, "空提示词必须报错而不是发出去");
  assert.match(response?.error || "", /prompt/i, "错误信息要说清楚是提示词的问题");
});

// ─────────────────────────────────────────────────────────────────────
// 3. Pack 接线：storage → 执行器
// ─────────────────────────────────────────────────────────────────────

/** 一条只跑本地步骤的 Pack（不碰内容脚本，用来单独验证「找得到 Pack」） */
const LOCAL_PACK = {
  metadata: {
    pack_id: "wiring-local",
    pack_name: "接线自检",
    version: "1.0.0",
  },
  workflow: {
    steps: [
      {
        id: "step_1",
        type: "local",
        input_fields: ["topic"],
        output_field: "out",
        config: { required_fields: ["topic"] },
      },
    ],
  },
};


test("storage 里的 Pack 要能被执行器找到并执行（不许是 Pack not found）", async () => {
  const { send } = await loadServiceWorker([LOCAL_PACK]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "wiring-local",
    input: { topic: "冒烟" },
  });

  assert.equal(
    response?.success,
    true,
    `执行应当成功，实际：${JSON.stringify(response?.error || response)}`,
  );
  assert.equal(response.result.status, "completed", "执行状态应当是 completed");
  assert.equal(
    response.result.steps[0].output.topic,
    "冒烟",
    "本地步骤应当把输入带出来",
  );
});

test("storage 里没有的 Pack 仍然要报 Pack not found（别把这条测成永远成功）", async () => {
  const { send } = await loadServiceWorker([LOCAL_PACK]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "根本不存在",
    input: {},
  });

  assert.equal(response?.success, false, "不存在的 Pack 必须失败");
  assert.match(response?.error || "", /Pack not found/i, "错误要说清是找不到 Pack");
});

test("导入单个 Pack 文件（裸对象）也要进得来", async () => {
  // packs/examples/ 下的每个文件都是裸 Pack 对象，此前导入路径只认
  // { packs: [...] } ⇒ 目录里那 16 个文件一个都导不进来。
  const { send, store } = await loadServiceWorker([]);

  const response = await send({
    type: "IMPORT_PACKS",
    jsonData: JSON.stringify(LOCAL_PACK),
  });

  assert.deepEqual(response.imported, ["wiring-local"], "裸 Pack 应当被导入");
  assert.equal(store.packs.length, 1, "导入后 storage 里应当有一个 Pack");
});

test("后台要把目标标签页一路传到 AI 步骤（中间断一截就退回广播）", async () => {
  // 这一段（popup → 后台 → 执行器 → 内容脚本）中间断一截，
  // 用户看到的就是「提示词在每个打开的 AI 页面里都发了一遍」。
  // 每一段都要有测试守着，否则下一次重构就会悄悄断掉。
  const { send, tabMessages } = await loadServiceWorker([AI_PACK]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "wiring-ai",
    input: {},
    tabId: 42,
  });

  assert.equal(
    response?.success,
    true,
    `执行应当成功，实际：${JSON.stringify(response?.error || response)}`,
  );
  assert.equal(tabMessages.length, 1, "必须精确投递到一个标签页");
  assert.equal(tabMessages[0].tabId, 42, "投递目标必须是用户当前所在的标签页");
  assert.equal(tabMessages[0].msg.type, "SEND_TO_AI", "投递的必须是 SEND_TO_AI");
});

// ─────────────────────────────────────────────────────────────────────
// 4. popup 接线：渲染出来的 id 必须是真的能执行的那个
// ─────────────────────────────────────────────────────────────────────

test("popup 渲染出来的 data-id 必须是 metadata.pack_id", async () => {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const popupJs = readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8");

  // runScripts: "outside-only" —— 让 window.eval 在**窗口自己的 realm** 里跑。
  // 不加这一项时 jsdom 不会给窗口脚本环境，eval 会落到 Node 的 realm，
  // 于是 `document` 取到的是别的测试留下的全局（这里表现为元素全是 null）。
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });
  dom.window.chrome = {
    storage: {
      local: { get: async () => ({ packs: [LOCAL_PACK] }) },
    },
    runtime: {
      sendMessage: async () => ({ success: true }),
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async () => ({ id: 8 }),
    },
  };

  // popup.js 是普通脚本（不是模块），直接在页面上下文里跑
  dom.window.eval(popupJs);
  await new Promise((r) => setTimeout(r, 0));

  const item = dom.window.document.querySelector(".pack-item");
  assert.ok(item, "popup 必须渲染出 Pack 列表项");
  assert.equal(
    item.dataset.id,
    "wiring-local",
    "列表项的 data-id 必须是 metadata.pack_id——此前用的是不存在的 pack.id，" +
      "渲染出来是 undefined，点下去执行的是一个不存在的 Pack",
  );
  assert.match(
    item.textContent || "",
    /接线自检/,
    "列表项应当显示 Pack 名字（此前显示的是不存在的 pack.name ⇒ 空白）",
  );
});

test("popup 要把用户当前所在的标签页告诉后台（否则 AI 步骤只能广播）", async () => {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });

  const sent = [];
  dom.window.chrome = {
    storage: { local: { get: async () => ({ packs: [LOCAL_PACK] }) } },
    runtime: {
      sendMessage: async (msg) => {
        sent.push(msg);
        return { success: true };
      },
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async () => ({ id: 8 }),
    },
  };

  dom.window.eval(readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8"));
  await new Promise((r) => setTimeout(r, 0));

  const item = dom.window.document.querySelector(".pack-item");
  assert.ok(item, "popup 必须渲染出 Pack 列表项");
  item.click();
  await new Promise((r) => setTimeout(r, 0));

  const panel = dom.window.document.getElementById("pack-input-panel");
  assert.equal(panel.hidden, false, "有 input_fields 的 Pack 应渲染出输入面板");
  const field = dom.window.document.querySelector('#pack-input-fields input[data-field="topic"]');
  assert.ok(field, "应按 input_fields 渲染出 topic 输入框");
  field.value = "接线测试";
  dom.window.document.getElementById("run-pack-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  const exec = sent.find((m) => m?.type === "EXECUTE_PACK");
  assert.ok(exec, "点运行必须发出 EXECUTE_PACK");
  assert.equal(
    exec.tabId,
    7,
    "必须带上用户当前所在的标签页 id：后台据此精确投递，" +
      "不带就只能广播给每一个打开的 AI 页面",
  );
  assert.equal(exec.input?.topic, "接线测试", "popup 必须把用户填的 input 透传给后台");
});

test("popup 必填输入留空不放行（N3：空串出城会拼出残句提示词还报 completed）", async () => {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });

  const sent = [];
  dom.window.chrome = {
    storage: { local: { get: async () => ({ packs: [LOCAL_PACK] }) } },
    runtime: {
      sendMessage: async (msg) => {
        sent.push(msg);
        return { success: true };
      },
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async () => ({ id: 8 }),
    },
  };

  dom.window.eval(readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8"));
  await new Promise((r) => setTimeout(r, 0));

  dom.window.document.querySelector(".pack-item").click();
  await new Promise((r) => setTimeout(r, 0));

  const field = dom.window.document.querySelector('#pack-input-fields input[data-field="topic"]');
  assert.ok(field, "应渲染出 topic 输入框");
  assert.equal(field.dataset.required, "1", "必填字段要带 data-required 标记");
  field.value = "   "; // 纯空白也算空

  dom.window.document.getElementById("run-pack-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  const exec = sent.find((m) => m?.type === "EXECUTE_PACK");
  assert.equal(exec, undefined, "必填留空不许发出 EXECUTE_PACK——残句提示词就是这么出城的");
  assert.match(
    dom.window.document.getElementById("status").textContent || "",
    /请填写必填输入.*topic/,
    "状态行要指名道姓说清缺哪个字段",
  );
});

// ─────────────────────────────────────────────────────────────────────
// 4a. popup 不可信数据渲染（N2：Pack 作者控制的字符串不许当 HTML 解析）
// ─────────────────────────────────────────────────────────────────────

/**
 * 用给定的 packs 起一份 popup（JSDOM），返回 dom。
 * chrome API 模拟与 N3 测试同款。
 */
async function loadPopupWithPacks(packs, onMessage) {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });
  dom.window.chrome = {
    storage: { local: { get: async () => ({ packs }) } },
    runtime: {
      sendMessage: async (msg) => {
        if (onMessage) return onMessage(msg);
        return { success: true };
      },
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async () => ({ id: 8 }),
    },
  };
  dom.window.eval(readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8"));
  await new Promise((r) => setTimeout(r, 0));
  return dom;
}

test("N2：输入字段名含 HTML 时不得被解析（只当文本）", async () => {
  const EVIL_FIELD = '"><img src=x data-evil="1"><i x="';
  const evilPack = {
    metadata: { pack_id: "wiring-evil", pack_name: "注入探针", version: "1.0.0" },
    workflow: {
      steps: [
        {
          id: "step_1",
          type: "local",
          input_fields: [EVIL_FIELD],
          output_field: "out",
        },
      ],
    },
  };
  const dom = await loadPopupWithPacks([evilPack]);
  dom.window.document.querySelector(".pack-item").click();
  await new Promise((r) => setTimeout(r, 0));

  const panel = dom.window.document.getElementById("pack-input-fields");
  assert.equal(panel.querySelector("img"), null, "字段名里的 <img> 不许被解析成元素");
  assert.equal(panel.querySelector("i"), null, "字段名里的 <i> 不许被解析成元素");
  const input = panel.querySelector("input[data-field]");
  assert.ok(input, "输入框必须渲染出来");
  assert.equal(
    input.dataset.field,
    EVIL_FIELD,
    "data-field 必须原样保留字段名——setAttribute 转义，不许破出属性",
  );
  const label = input.closest("label");
  assert.ok(
    label.textContent.includes("<img"),
    "字段名只当纯文本显示（尖括号是字面量，不是标记）",
  );
});

test("N2：pack 列表 name/description 含 HTML 时不得被解析", async () => {
  const evilPack = {
    metadata: {
      pack_id: "wiring-evil2",
      pack_name: '<img src=x data-evil="1">伪造名字',
      description: '<b onclick="x">危险描述</b>',
    },
    workflow: { steps: [] },
  };
  const dom = await loadPopupWithPacks([evilPack]);
  const list = dom.window.document.getElementById("packList");
  assert.equal(list.querySelector("img"), null, "pack_name 里的 <img> 不许被解析成元素");
  assert.equal(list.querySelector("b"), null, "description 里的 <b> 不许被解析成元素");
  const item = list.querySelector(".pack-item");
  assert.equal(item.dataset.id, "wiring-evil2", "data-id 走 dataset，原样保留");
  assert.match(
    item.querySelector(".pack-name").textContent,
    /伪造名字/,
    "名字只当纯文本显示",
  );
});

test("N8：广播投递时 popup 要提示用户（不能让他以为只发了一次）", async () => {
  const pack = {
    metadata: { pack_id: "wiring-ai-2", pack_name: "广播提示", version: "1.0.0" },
    workflow: {
      steps: [
        {
          id: "step_1",
          type: "ai",
          input_fields: ["topic"],
          output_field: "out",
          prompt_template: "说说{{topic}}",
        },
      ],
    },
  };
  const dom = await loadPopupWithPacks([pack], async (msg) => {
    if (msg?.type === "EXECUTE_PACK") {
      return {
        success: true,
        result: {
          status: "completed",
          output: { out: "回声" },
          steps: [{ id: "step_1", delivery: "broadcast" }],
        },
      };
    }
    return { success: true };
  });
  dom.window.document.querySelector(".pack-item").click();
  await new Promise((r) => setTimeout(r, 0));
  dom.window.document
    .querySelector('#pack-input-fields input[data-field="topic"]')
    .value = "接线测试";
  dom.window.document.getElementById("run-pack-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  const status = dom.window.document.getElementById("status").textContent || "";
  assert.match(
    status,
    /已广播/,
    `状态行必须提示广播——用户开着多个 AI 页面时会各收到一次：${status}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 4a-2. Studio 状态区注入面（N20：后端回执/错误串不许当 HTML 解析）
//
// 信任边界与 N2 不同（数据来自 GENERATE_STUDIO_ARTIFACTS 后端回执与
// 消息错误串，不来自 Pack 作者），但修法同款：DOM 构建 + textContent；
// download_url 另加 ^https?:// 协议白名单——javascript: 伪协议是其中最实的一条。
// ─────────────────────────────────────────────────────────────────────

test("N20：Studio 回执字段含 HTML 时不得被解析", async () => {
  const EVIL_TYPE = '<img src=x data-evil="1">播客';
  const EVIL_MODE = '<i data-evil="1">异步</i>';
  const dom = await loadPopupWithPacks([], async (msg) => {
    if (msg?.type === "GENERATE_STUDIO_ARTIFACTS") {
      return {
        success: true,
        artifacts: [{ success: true, content_type: EVIL_TYPE, mode: EVIL_MODE }],
      };
    }
    return { success: true };
  });
  dom.window.document.getElementById("studio-audio").click();
  dom.window.document.getElementById("generate-studio-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  const status = dom.window.document.getElementById("studio-status");
  assert.equal(status.querySelector("img"), null, "content_type 里的 <img> 不许被解析成元素");
  assert.equal(status.querySelector("i"), null, "mode 里的 <i> 不许被解析成元素");
  assert.ok(
    status.textContent.includes("<img"),
    "回执字段只当纯文本显示（尖括号是字面量，不是标记）",
  );
});

test("N20：download_url 非 http(s) 时不许进 href", async () => {
  const dom = await loadPopupWithPacks([], async (msg) => {
    if (msg?.type === "GENERATE_STUDIO_ARTIFACTS") {
      return {
        success: true,
        artifacts: [
          {
            success: true,
            content_type: "audio",
            download_url: "javascript:alert(1)",
          },
          {
            success: true,
            content_type: "video",
            download_url: "https://example.com/a.mp3",
          },
        ],
      };
    }
    return { success: true };
  });
  dom.window.document.getElementById("studio-audio").click();
  dom.window.document.getElementById("generate-studio-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  const status = dom.window.document.getElementById("studio-status");
  const links = status.querySelectorAll("a");
  assert.equal(links.length, 1, "javascript: 伪协议不许变成链接，只有 https 那条可以");
  assert.equal(
    links[0].getAttribute("href"),
    "https://example.com/a.mp3",
    "白名单内的 URL 原样进 href",
  );
});

test("N20：错误串（response.error / error.message）含 HTML 时不得被解析", async () => {
  let call = 0;
  const dom = await loadPopupWithPacks([], async (msg) => {
    if (msg?.type === "GENERATE_STUDIO_ARTIFACTS") {
      call += 1;
      if (call === 1) {
        return { success: false, error: '<img src=x data-evil="1">失败原因' };
      }
      throw new Error('<img src=x data-evil="2">通信崩了');
    }
    return { success: true };
  });
  const doc = dom.window.document;
  doc.getElementById("studio-audio").click();

  doc.getElementById("generate-studio-btn").click();
  await new Promise((r) => setTimeout(r, 0));
  let status = doc.getElementById("studio-status");
  assert.equal(status.querySelector("img"), null, "response.error 里的 <img> 不许被解析成元素");
  assert.ok(status.textContent.includes("生成失败"), "错误行还得显示出来");

  doc.getElementById("generate-studio-btn").click();
  await new Promise((r) => setTimeout(r, 0));
  status = doc.getElementById("studio-status");
  assert.equal(status.querySelector("img"), null, "error.message 里的 <img> 不许被解析成元素");
  assert.ok(status.textContent.includes("通信错误"), "通信错误行还得显示出来");
});

// ─────────────────────────────────────────────────────────────────────
// 4b. popup 执行产出展示（N13：产出此前被丢弃，用户拿不到 Pack 产物）
// ─────────────────────────────────────────────────────────────────────

/**
 * 跑一遍 popup 的执行流（选 Pack → 填 topic → 点运行）。
 * EXECUTE_PACK 回执的产出由 outputs 决定。
 */
async function drivePopupExecution(outputs) {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });
  const sent = [];
  dom.window.chrome = {
    storage: { local: { get: async () => ({ packs: [LOCAL_PACK] }) } },
    runtime: {
      sendMessage: async (msg) => {
        sent.push(msg);
        if (msg?.type === "EXECUTE_PACK") {
          return { success: true, result: { status: "completed", output: outputs } };
        }
        return { success: true };
      },
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async () => ({ id: 8 }),
    },
  };
  dom.window.eval(readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8"));
  await new Promise((r) => setTimeout(r, 0));
  dom.window.document.querySelector(".pack-item").click();
  await new Promise((r) => setTimeout(r, 0));
  const field = dom.window.document.querySelector('#pack-input-fields input[data-field="topic"]');
  field.value = "接线测试";
  dom.window.document.getElementById("run-pack-btn").click();
  await new Promise((r) => setTimeout(r, 0));
  return { dom, sent };
}

test("popup 执行成功必须展示产出（N13：不许只报状态把产出丢掉）", async () => {
  const outputs = {
    hook_statement: "这是一句足够长的钩子，验证产出全文能被渲染出来。",
    topic_info: { topic: "接线测试", target_audience_level: "普通上班族" },
    empty_one: "",
  };
  const { dom } = await drivePopupExecution(outputs);

  const panel = dom.window.document.getElementById("pack-output-panel");
  assert.equal(
    panel.hidden,
    false,
    "执行成功后面板必须显示——此前只写「执行成功」，response.result.output 被直接丢弃",
  );
  const hookBlock = dom.window.document.querySelector('[data-field="hook_statement"]');
  assert.ok(hookBlock, "每个产出字段都要有对应块");
  assert.match(
    hookBlock.textContent || "",
    /钩子/,
    "产出全文必须可见（折叠块里），不是只有字段名",
  );
  assert.match(
    dom.window.document.getElementById("status").textContent || "",
    /2 个产出/,
    "状态行要报产出数（字段去空后是 2 个）",
  );
  assert.ok(
    !dom.window.document.querySelector('[data-field="empty_one"]'),
    "空产出不占块",
  );
  const topicBlock = dom.window.document.querySelector('[data-field="topic_info"]');
  assert.match(
    topicBlock.textContent || "",
    /"topic"/,
    "对象产出按 JSON 展开（不许是 [object Object]）",
  );
});

test("产出文本必须走 textContent（模型文本不许进 innerHTML）", async () => {
  const evil = '<img src=x onerror="window.__pwned=1">注入<script>window.__pwned=1</script>';
  const { dom } = await drivePopupExecution({ hook_statement: evil });

  assert.equal(dom.window.__pwned, undefined, "产出里的标签不许被执行");
  assert.ok(
    !dom.window.document.querySelector("#pack-output-fields img"),
    "产出里的标签不许变成真元素（innerHTML 回归会在这里现形）",
  );
  const hookBlock = dom.window.document.querySelector('[data-field="hook_statement"]');
  assert.match(
    hookBlock.textContent || "",
    /<img/,
    "产出必须按字面文本显示——模型文本是不可信内容，进 innerHTML 就是注入面",
  );
});

test("产出复制按钮把该字段全文放进剪贴板", async () => {
  const outputs = { hook_statement: "复制我，全文一个字都不能少。" };
  const { dom } = await drivePopupExecution(outputs);

  const copied = [];
  Object.defineProperty(dom.window.navigator, "clipboard", {
    value: { writeText: async (t) => copied.push(t) },
    configurable: true,
  });

  const copyBtn = dom.window.document.querySelector('button[data-copy-field="hook_statement"]');
  assert.ok(copyBtn, "每个产出块都要有复制按钮");
  copyBtn.click();
  await new Promise((r) => setTimeout(r, 0));

  assert.equal(copied.length, 1, "点复制要写一次剪贴板");
  assert.equal(copied[0], outputs.hook_statement, "复制的必须是该字段全文");
  assert.match(
    dom.window.document.getElementById("status").textContent || "",
    /已复制/,
    "复制后要有反馈",
  );
});

test("导出 JSON 按钮产出全量产出 JSON", async () => {
  const outputs = {
    hook_statement: "导出验证钩子",
    topic_info: { topic: "接线测试" },
  };
  const { dom } = await drivePopupExecution(outputs);

  // 记录 Blob 构造（jsdom 各版本 Blob API 不一，直接记 parts 最稳）
  const blobs = [];
  dom.window.Blob = class {
    constructor(parts, opts) {
      this.parts = parts;
      this.type = opts?.type || "";
      blobs.push(this);
    }
  };
  dom.window.URL.createObjectURL = () => "blob:fake";
  dom.window.URL.revokeObjectURL = () => {};

  dom.window.document.getElementById("export-output-btn").click();
  await new Promise((r) => setTimeout(r, 0));

  assert.equal(blobs.length, 1, "导出必须产生一个 Blob");
  assert.equal(blobs[0].type, "application/json", "导出 MIME 是 JSON");
  const parsed = JSON.parse(blobs[0].parts[0]);
  assert.equal(parsed.hook_statement, outputs.hook_statement, "导出的 JSON 必须含产出全文");
  assert.equal(parsed.topic_info.topic, "接线测试", "对象产出也要完整导出");
});

// ─────────────────────────────────────────────────────────────────────
// 5. public/ 下的脚本必须能被解析
// ─────────────────────────────────────────────────────────────────────

test("public/ 下的脚本必须语法正确（构建是原样复制的，语法错会一路发到用户手里）", () => {
  // 2026-10-25 改 popup.js 时真的写坏过一次（多一个右括号）。
  // 而 vite 的构建对 public/ 是**原样复制**，不解析 ⇒ 构建成功、
  // CI 全绿、用户点开扩展看到一个报错的 popup。
  // 门禁里没有任何东西能发现这件事——所以这里补一条。
  const files = readdirSync(join(EXT_ROOT, "public")).filter((f) =>
    f.endsWith(".js"),
  );
  assert.ok(files.length > 0, "public/ 下应当有脚本");

  const broken = [];
  for (const file of files) {
    const source = readFileSync(join(EXT_ROOT, "public", file), "utf-8");
    try {
      new vm.Script(source, { filename: file });
    } catch (error) {
      broken.push(`${file}: ${error.message}`);
    }
  }

  assert.deepEqual(broken, [], "这些脚本语法有错：" + broken.join("；"));
});

// ─────────────────────────────────────────────────────────────────────
// 6. 装好的扩展里必须真的有「代码要打开的那个页面」
// ─────────────────────────────────────────────────────────────────────

test("代码里 getURL 指到的页面，在构建产物里必须真的存在", () => {
  // 2026-10-25 准备外部用户试用材料时发现的断点：
  //   popup.js / settings.js 打开 Pack 编辑器用的是
  //     chrome.runtime.getURL('public/pack-editor.html')
  //   而构建产物里 Pack 编辑器只被复制成扁平的 dist/pack-editor.html
  //   ⇒ 那个 URL 在**装好的扩展**里 404
  //   ⇒ 外部用户点「导入 Pack」看到的是「文件不存在」
  //
  // 这类缺陷构建和 CI 都发现不了：构建是绿的，测试也不碰产物目录。
  // 这里把产物目录复制到一个临时目录里，逐个核对代码里用到的 URL。
  const dest = mkdtempSync(join(tmpdir(), "prompt-pack-dist-"));
  try {
    copyStaticAssets({ rootDir: EXT_ROOT, destDir: dest });

    // 收集代码里所有 getURL('...') 的路径
    const used = new Set();
    for (const file of readdirSync(join(EXT_ROOT, "public")).filter((f) => f.endsWith(".js"))) {
      const source = readFileSync(join(EXT_ROOT, "public", file), "utf-8");
      for (const m of source.matchAll(/getURL\(\s*["']([^"']+)["']\s*\)/g)) {
        used.add(m[1]);
      }
    }

    assert.ok(used.size > 0, "代码里应当有 getURL 引用——解析器坏了");

    const missing = [...used].filter((p) => !existsSync(join(dest, p)));
    assert.deepEqual(
      missing,
      [],
      "装好的扩展里没有这些页面（点开就是 404）：" + missing.join("、"),
    );
  } finally {
    rmSync(dest, { recursive: true, force: true });
  }
});

test("popup 必须有「导入 Pack」的入口（否则外部用户卡在第一步）", async () => {
  const html = readFileSync(join(EXT_ROOT, "public", "popup.html"), "utf-8");
  const dom = new JSDOM(html, {
    url: "https://localhost/",
    runScripts: "outside-only",
  });

  const opened = [];
  dom.window.chrome = {
    storage: { local: { get: async () => ({ packs: [] }) } },
    runtime: {
      sendMessage: async () => ({ success: true }),
      getURL: (p) => `chrome-extension://fake-id/${p}`,
    },
    tabs: {
      query: async () => [{ id: 7 }],
      create: async (opts) => {
        opened.push(opts?.url);
        return { id: 8 };
      },
    },
  };
  dom.window.eval(readFileSync(join(EXT_ROOT, "public", "popup.js"), "utf-8"));
  await new Promise((r) => setTimeout(r, 0));

  const btn = dom.window.document.querySelector('[data-testid="open-pack-editor"]');
  assert.ok(btn, "popup 必须有一个「导入 / 管理 Pack」按钮");
  assert.equal(btn.tagName, "BUTTON", "入口必须是个能点的按钮");

  btn.click();
  await new Promise((r) => setTimeout(r, 0));

  assert.equal(opened.length, 1, "点一下必须只打开一个标签页");
  assert.match(
    opened[0] || "",
    /pack-editor\.html$/,
    `打开的应当是 Pack 编辑器，实际是 ${opened[0]}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 7. AI 步骤要发到哪儿
// ─────────────────────────────────────────────────────────────────────

/** 只跑一个 AI 步骤的 Pack */
const AI_PACK = {
  metadata: { pack_id: "wiring-ai", pack_name: "接线自检·AI" },
  workflow: {
    steps: [
      {
        id: "step_ai",
        type: "ai",
        prompt_template: "你好",
        // 不重试：失败路径默认会重试 3 次、每次隔 1 秒，
        // 让单测每次多花 3 秒，而这里要验的是错误**怎么说**
        retry: false,
      },
    ],
  },
};

let executorImportCounter = 0;

/**
 * 回声正文。必须长于执行器的最短回复阈值（50 字符）——
 * 短回声会被「碎片判失败」闸门拦下，成功路径的测试会误红。
 */
const ECHO =
  "回声：这是一段足够长的模拟回复正文，用来通过 AI 回复可用性阈值校验，长度必须超过五十字符的默认下限才能不被碎片闸门误杀。";

/**
 * 在假 chrome 里跑**生产执行器**。
 *
 * @param {Object} [options] - 假 chrome 的行为开关
 * @param {Object} [options.pack] - 要装进执行器的 Pack（默认 AI_PACK）
 * @returns {Promise<{executor: Object, calls: Object}>}
 */
async function loadExecutor(options = {}) {
  const calls = { tabs: [], runtime: [] };
  globalThis.chrome = {
    runtime: {
      sendMessage: async (msg) => {
        calls.runtime.push(msg);
        return { success: true, result: { content: ECHO } };
      },
    },
    tabs: {
      sendMessage: async (tabId, msg) => {
        calls.tabs.push({ tabId, msg });
        if (options.tabsSendThrows) {
          throw new Error("Could not establish connection.");
        }
        return { success: true, result: { content: ECHO } };
      },
    },
  };

  executorImportCounter += 1;
  const mod = await import(
    `../src/background/pack-executor.js?bust=${executorImportCounter}`
  );
  const executor = new mod.default();
  executor.loadPack(options.pack || AI_PACK);
  return { executor, calls };
}

test("AI 步骤要发到指定标签页，不能广播给每个打开的 AI 页面", async () => {
  const { executor, calls } = await loadExecutor();

  const result = await executor.execute("wiring-ai", {}, { tabId: 42 });

  assert.equal(result.status, "completed", `执行应当完成：${JSON.stringify(result.errors)}`);
  assert.equal(calls.tabs.length, 1, "必须精确投递到一个标签页");
  assert.equal(calls.tabs[0].tabId, 42, "投递目标必须是用户当前所在的标签页");
  assert.equal(calls.tabs[0].msg.type, "SEND_TO_AI", "投递的必须是 SEND_TO_AI");
  assert.equal(
    calls.runtime.filter((m) => m?.type === "SEND_TO_AI").length,
    0,
    "不能广播：用户开着 3 个 AI 页面时，广播会让他在 3 个页面里各收到一次提示词",
  );
  assert.equal(result.steps[0].delivery, "precise", "精确投递要在结果里标 precise（N8 标记）");
});

test("没有目标标签页时才广播，并且要标明是广播", async () => {
  const { executor, calls } = await loadExecutor();

  const result = await executor.execute("wiring-ai", {}, {});

  assert.equal(
    calls.runtime.filter((m) => m?.type === "SEND_TO_AI").length,
    1,
    "没有目标标签页时应当广播",
  );
  assert.equal(calls.tabs.length, 0, "没有目标标签页时不该乱投到某个标签页");
  assert.equal(
    result.steps[0].output,
    ECHO,
    "广播的结果也应是解包后的回复内容，而不是信封对象",
  );
  assert.equal(
    result.steps[0].delivery,
    "broadcast",
    "结果里必须标明是广播——popup 据此提示「已广播到所有打开的 AI 页面」（N8 真消费者）",
  );
});

test("标签页发不过去时要说清楚原因（别让用户看到一串英文）", async () => {
  const { executor } = await loadExecutor({ tabsSendThrows: true });

  const result = await executor.execute("wiring-ai", {}, { tabId: 42 });

  assert.equal(result.status, "failed", "投递失败必须算失败");
  const message = result.errors.map((e) => e.message).join(" ");
  assert.match(message, /标签页/, `错误要说清是哪个标签页的问题：${message}`);
  assert.match(
    message,
    /AI 站点|刷新/,
    `错误要告诉用户下一步做什么：${message}`,
  );
});

test("交付给外部用户的那个冒烟 Pack，执行器必须真的能跑起来", async () => {
  // 外部用户拿到的是 `packs/examples/external-user-smoke.json` 这个文件。
  // 如果它跟运行时对不上（步骤类型不对、id 字段不对、提示词模板取不到），
  // 说明书就成了一份**假说明书**——所以用**生产执行器**跑它。
  //
  // 路径从**测试文件自己**往上数（HERE/../..），不从 EXT_ROOT 数：
  // 变异检查会把 tests/ 复制到临时副本里，按 EXT_ROOT 定位会读到**工作区**
  // 的原文件（副本里的改动对它无效），那条变异就永远杀不死。
  const packPath = resolve(
    HERE,
    "..",
    "..",
    "packs",
    "examples",
    "external-user-smoke.json",
  );
  const pack = JSON.parse(readFileSync(packPath, "utf-8"));

  const { executor, calls } = await loadExecutor({ pack });

  const result = await executor.execute(pack.metadata.pack_id, {}, { tabId: 42 });

  assert.equal(
    result.status,
    "completed",
    `这个 Pack 必须跑得通：${JSON.stringify(result.errors)}`,
  );
  assert.equal(calls.tabs.length, 1, "必须精确投递到一个标签页");
  assert.match(
    calls.tabs[0].msg.prompt,
    /你好，Prompt Pack 冒烟自检通过/,
    `发出去的提示词必须包含那句让 AI 复述的话，实际：${calls.tabs[0].msg.prompt}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// N10：首装零 Pack 体验（DEFAULT_PACKS 播种）
//
// 新装扩展的 storage 是空的 ⇒ 此前用户面对的是零 Pack 空列表
// （DEFAULT_PACKS 写了却从未接线，PR #13 连死代码一起删了）。
// 这三条钉住播种的边界：空仓才播、update 不播、已有绝不覆盖
// ——用户删光/自行导入的选择必须被尊重。
// ─────────────────────────────────────────────────────────────────────

test("N10：首次安装且 storage 为空时播种默认 Pack", async () => {
  const { store, fireInstalled } = await loadServiceWorker([]);
  assert.deepEqual(store.packs, [], "前置：起始必须是空仓");

  await fireInstalled({ reason: "install" });

  const ids = store.packs.map((p) => p.metadata.pack_id);
  assert.deepEqual(
    ids,
    ["knowledge-query", "article-writing"],
    `首装后 storage 里必须有这两张默认 Pack，实际：${ids.join(", ") || "（空）"}`,
  );
  for (const pack of store.packs) {
    assert.ok(
      pack.metadata?.pack_name,
      `播种的 Pack 必须带 pack_name（popup 靠它渲染列表）：${pack.metadata?.pack_id}`,
    );
  }
});

test("N10：已有 Pack 时不许被默认 Pack 覆盖", async () => {
  const EXISTING = {
    metadata: { pack_id: "wiring-local", pack_name: "用户自己的 Pack" },
    workflow: {
      steps: [{ id: "s1", name: "步", type: "local", config: { required_fields: [] } }],
    },
  };
  const { store, fireInstalled } = await loadServiceWorker([EXISTING]);

  await fireInstalled({ reason: "install" });

  const ids = store.packs.map((p) => p.metadata.pack_id);
  assert.deepEqual(
    ids,
    ["wiring-local"],
    `已有 Pack 时播种必须让路（备份还原/侧载场景），实际：${ids.join(", ")}`,
  );
});

test("N10：update 不播种——用户可能有意删光", async () => {
  const { store, fireInstalled } = await loadServiceWorker([]);

  await fireInstalled({ reason: "update" });

  assert.deepEqual(
    store.packs,
    [],
    "更新时绝不播种：用户可能有意删光默认 Pack，静默塞回去等于不尊重选择",
  );
});

// ─────────────────────────────────────────────────────────────────────
// N11：孤儿 pack_id 残留可见化（旧版 IMPORT_PACKS 的顶层 pack_id 僵尸数据）
//
// 收口「只认 metadata.pack_id」之后，历史残留会变成既不可见又不可清理的
// 僵尸行。最小防护（台账裁定）：GET_ALL_PACKS 打 unrecognized:true +
// popup 出可见警告——**数据保留，不静默删用户数据**。
// ─────────────────────────────────────────────────────────────────────

test("N11：GET_ALL_PACKS 给孤儿包打 unrecognized:true（且不静默删数据）", async () => {
  const LEGACY = { pack_id: "legacy-1", pack_name: "旧格式包", workflow: { steps: [] } };
  const NORMAL = {
    metadata: { pack_id: "wiring-ok", pack_name: "正常包" },
    workflow: { steps: [] },
  };
  const { send, store } = await loadServiceWorker([LEGACY, NORMAL]);

  const res = await send({ type: "GET_ALL_PACKS" });

  assert.equal(res.packs.length, 2, "不许静默删数据——两条都得回来");
  const legacy = res.packs.find((p) => p.pack_id === "legacy-1");
  const normal = res.packs.find((p) => p.metadata?.pack_id === "wiring-ok");
  assert.ok(legacy, "孤儿包必须原样返回");
  assert.equal(legacy.unrecognized, true, "孤儿包必须打 unrecognized:true");
  assert.equal(normal.unrecognized, undefined, "正常包不许被打标");
  assert.equal(store.packs.length, 2, "storage 原数据必须原样保留（不删用户数据）");
});

test("N11：popup 对孤儿包出可见警告（不伪装成正常 Pack）", async () => {
  const LEGACY = { pack_id: "legacy-2", pack_name: "旧格式包" };
  const NORMAL = {
    metadata: { pack_id: "wiring-ok2", pack_name: "正常包" },
    workflow: { steps: [] },
  };
  const dom = await loadPopupWithPacks([LEGACY, NORMAL]);
  const list = dom.window.document.getElementById("packList");
  const items = [...list.querySelectorAll(".pack-item")];
  assert.equal(items.length, 2, "两条都渲染（数据保留，不静默删）");

  const legacyRow = items.find((li) => li.dataset.unrecognized === "true");
  assert.ok(legacyRow, "孤儿行必须带 data-unrecognized 标");
  assert.match(
    legacyRow.textContent,
    /无法识别/,
    `警告必须可见：${legacyRow.textContent}`,
  );

  const normalRow = items.find((li) => li.dataset.id === "wiring-ok2");
  assert.ok(normalRow, "正常行照常渲染");
  assert.equal(normalRow.dataset.unrecognized, undefined, "正常行不许带警告标");
  assert.equal(normalRow.querySelector(".pack-warn"), null, "正常行不许有警告元素");
});
