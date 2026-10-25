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
  const input = dom.window.document.querySelector("[data-probe-role='chat-input']");
  if (input) {
    Object.defineProperty(input, "isContentEditable", {
      value: true,
      configurable: true,
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
      },
    ],
  },
};

/**
 * 起一个假的 chrome 环境，把**生产 service-worker** 跑起来。
 *
 * @param {Object[]} packs - 放进 chrome.storage.local["packs"] 的 Pack
 * @returns {Promise<{listener: Function, send: Function}>}
 */
async function loadServiceWorker(packs) {
  const store = { packs };
  const listeners = [];
  const tabMessages = [];

  globalThis.chrome = {
    runtime: {
      sendMessage: async () => undefined,
      onInstalled: { addListener: () => {} },
      onMessage: {
        addListener: (fn) => listeners.push(fn),
      },
    },
    storage: {
      local: {
        get: async (key) => (key === "packs" ? { packs: store.packs } : {}),
        set: async (obj) => {
          Object.assign(store, obj);
        },
      },
      onChanged: { addListener: () => {} },
    },
    tabs: {
      onUpdated: { addListener: () => {} },
      sendMessage: async (tabId, msg) => {
        tabMessages.push({ tabId, msg });
        return { success: true, result: { content: "回声" } };
      },
    },
  };

  swImportCounter += 1;
  await import(`../src/background/service-worker.js?bust=${swImportCounter}`);
  await new Promise((r) => setTimeout(r, 0));

  const listener = listeners[0];
  assert.ok(listener, "service-worker 必须注册 onMessage 监听器");

  /**
   * 给后台发一条消息并等它回话。
   * @param {Object} message
   * @returns {Promise<any>}
   */
  const send = (message) =>
    new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error(`${message.type} 没有响应`)),
        5000,
      );
      const keepAlive = listener(message, {}, (r) => {
        clearTimeout(timer);
        resolve(r);
      });
      assert.equal(keepAlive, true, `${message.type} 的监听器必须返回 true`);
    });

  return { listener, send, store, tabMessages };
}

let swImportCounter = 0;

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

  const exec = sent.find((m) => m?.type === "EXECUTE_PACK");
  assert.ok(exec, "点 Pack 必须发出 EXECUTE_PACK");
  assert.equal(
    exec.tabId,
    7,
    "必须带上用户当前所在的标签页 id：后台据此精确投递，" +
      "不带就只能广播给每一个打开的 AI 页面",
  );
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
 * 在假 chrome 里跑**生产执行器**。
 *
 * @param {Object} [options] - 假 chrome 的行为开关
 * @returns {Promise<{executor: Object, calls: Object}>}
 */
async function loadExecutor(options = {}) {
  const calls = { tabs: [], runtime: [] };
  globalThis.chrome = {
    runtime: {
      sendMessage: async (msg) => {
        calls.runtime.push(msg);
        return { success: true, result: { content: "回声" } };
      },
    },
    tabs: {
      sendMessage: async (tabId, msg) => {
        calls.tabs.push({ tabId, msg });
        if (options.tabsSendThrows) {
          throw new Error("Could not establish connection.");
        }
        return { success: true, result: { content: "回声" } };
      },
    },
  };

  executorImportCounter += 1;
  const mod = await import(
    `../src/background/pack-executor.js?bust=${executorImportCounter}`
  );
  const executor = new mod.default();
  executor.loadPack(AI_PACK);
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
    result.steps[0].output.broadcast,
    true,
    "广播的结果要标明是广播（否则用户以为自己只发了一次）",
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
