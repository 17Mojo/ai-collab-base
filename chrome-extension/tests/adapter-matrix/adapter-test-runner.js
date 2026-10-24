/**
 * Adapter Test Runner（ESM）
 *
 * 与历史版本的根本差别：**直接跑生产 adapter 源码**。
 *
 * 历史版本在 runner 里手抄了一份 SELECTORS 表、并自实现了一套查找逻辑，
 * 那份副本与生产代码没有任何联动——生产选择器漂移了矩阵照样全绿。
 * 真机实测已经证明过这一点：Gemini 的发送按钮选择器在真实站点
 * （zh-CN / en-US 两种语言）一个都命中不了，而矩阵长期 120/120 全绿。
 *
 * 现在矩阵只做三件事：
 *   1. 把 fixture 装进 jsdom 并接好全局；
 *   2. 调用**生产 adapter 实例**的方法；
 *   3. 把结果与 fixture 里用 data-role 标注的「真实 DOM 契约」对账。
 *
 * fixture 的角色因此变了：它不再是一份「恰好能让选择器命中」的假 DOM，
 * 而是**真实站点 DOM 的快照**——生产选择器一改，快照就对不上，矩阵立刻报红。
 *
 * 用法：
 *   node tests/adapter-matrix/adapter-test-runner.js
 *   node tests/adapter-matrix/adapter-test-runner.js --platform=gemini
 *   node tests/adapter-matrix/adapter-test-runner.js --list
 */

import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  loadFixture,
  listProductionAdapterModules,
  getRoleElements,
  isWithin,
  runTest,
  formatResults,
  PLATFORMS_DIR,
} from "./adapter-test-utils.js";

// ============================================================================
// 平台清单（只登记「平台 ↔ 域名 ↔ fixture ↔ 生产模块」的对应关系；
// 选择器一律从生产模块读取，这里不重复维护）
// ============================================================================

const PLATFORMS = [
  { id: "chatgpt", name: "ChatGPT", hostnames: ["chat.openai.com", "chatgpt.com"], fixture: "chatgpt", module: "chatgpt-adapter.js" },
  { id: "claude", name: "Claude.ai", hostnames: ["claude.ai"], fixture: "claude", module: "claude-adapter.js" },
  { id: "gemini", name: "Gemini", hostnames: ["gemini.google.com"], fixture: "gemini", module: "gemini-adapter.js" },
  { id: "deepseek", name: "DeepSeek", hostnames: ["chat.deepseek.com"], fixture: "deepseek", module: "deepseek-adapter.js" },
  { id: "kimi", name: "Kimi AI", hostnames: ["kimi.com", "kimi.moonshot.cn"], fixture: "kimi", module: "kimi-adapter.js" },
  { id: "longcat", name: "LongCat AI", hostnames: ["longcat.chat"], fixture: "longcat", module: "longcat-adapter.js" },
  { id: "qianwen", name: "Qianwen (千问)", hostnames: ["qianwen.com", "tongyi.aliyun.com"], fixture: "qianwen", module: "qianwen-adapter.js" },
  { id: "yiyan", name: "Yiyan (文心一言)", hostnames: ["yiyan.baidu.com", "wenxin.baidu.com"], fixture: "yiyan", module: "yiyan-adapter.js" },
  { id: "yuanbao", name: "Yuanbao (腾讯元宝)", hostnames: ["yuanbao.tencent.com"], fixture: "yuanbao", module: "yuanbao-adapter.js" },
  { id: "chatglm", name: "ChatGLM (智谱清言)", hostnames: ["chatglm.cn"], fixture: "chatglm", module: "chatglm-adapter.js" },
];

const TEST_TEXT = "Hello from adapter test!";

/**
 * 载入生产 adapter 模块。
 * @param {object} spec
 * @returns {Promise<object>} 模块命名空间（含 SELECTORS 与 default 适配器类）
 */
function importAdapter(spec) {
  const href = pathToFileURL(path.join(PLATFORMS_DIR, spec.module)).href;
  return import(href);
}

/**
 * 跑一个可能异步的用例。
 * @param {string} name
 * @param {Function} fn
 * @returns {Promise<{name: string, pass: boolean, error: string|null}>}
 */
async function runTestAsync(name, fn) {
  try {
    const result = await fn();
    if (result === "SKIP") {
      return { name, pass: true, skipped: true, error: null };
    }
    if (result === false) {
      return { name, pass: false, skipped: false, error: "Test returned false" };
    }
    return { name, pass: true, skipped: false, error: null };
  } catch (e) {
    return { name, pass: false, skipped: false, error: e.message };
  }
}

/**
 * 描述一个元素，便于失败信息定位。
 * @param {Element|null} el
 * @returns {string}
 */
function describe(el) {
  if (!el) return "null";
  const cls = typeof el.className === "string" ? el.className : "";
  return `<${el.tagName.toLowerCase()}${cls ? ` class="${cls}"` : ""}>`;
}

/**
 * 为一个平台构造全部用例。
 * 每个用例都**重新载入 fixture**，避免前一个用例的 DOM 改动污染后一个。
 *
 * @param {object} spec
 * @param {object} mod - 生产 adapter 模块
 * @returns {Array<{name: string, fn: Function}>}
 */
function buildCases(spec, mod) {
  const AdapterClass = mod.default;
  const hostname = spec.hostnames[0];

  /** 载入 fixture 并新建生产 adapter 实例 */
  const setup = () => {
    const dom = loadFixture(spec.fixture, hostname);
    return { dom, doc: dom.window.document, adapter: new AdapterClass() };
  };

  return [
    {
      name: `detect() 在 ${hostname} 上返回 true`,
      fn: () => {
        const { adapter } = setup();
        const actual = adapter.detect();
        if (actual !== true) throw new Error(`detect() 返回 ${actual}，期望 true`);
      },
    },
    {
      name: "detect() 在其他站点上返回 false",
      fn: () => {
        loadFixture(spec.fixture, "example.com");
        const adapter = new AdapterClass();
        const actual = adapter.detect();
        if (actual !== false) throw new Error(`detect() 返回 ${actual}，期望 false`);
      },
    },
    {
      name: "getChatInput() 命中 fixture 标注的输入框",
      fn: () => {
        const { doc, adapter } = setup();
        const expected = getRoleElements(doc, "chat-input");
        if (expected.length !== 1) {
          throw new Error(`fixture 应当标注 1 个 chat-input，实际 ${expected.length} 个`);
        }
        const el = adapter.getChatInput();
        if (!el) throw new Error("getChatInput() 返回 null");
        if (el !== expected[0]) {
          throw new Error(`getChatInput() 返回 ${describe(el)}，不是标注的 ${describe(expected[0])}`);
        }
      },
    },
    {
      name: "getSendButton() 命中 fixture 标注的发送按钮",
      fn: () => {
        const { doc, adapter } = setup();
        const expected = getRoleElements(doc, "send-button");
        if (expected.length !== 1) {
          throw new Error(`fixture 应当标注 1 个 send-button，实际 ${expected.length} 个`);
        }
        const el = adapter.getSendButton();
        if (!el) throw new Error("getSendButton() 返回 null");
        if (el !== expected[0]) {
          throw new Error(`getSendButton() 返回 ${describe(el)}，不是标注的 ${describe(expected[0])}`);
        }
      },
    },
    {
      name: "getMessageList() 覆盖 fixture 标注的全部消息",
      fn: () => {
        // 「覆盖」= 每个标注的消息容器内部至少有一个元素被返回。
        // 不要求「容器本身」被返回：像千问这种宽松选择器
        // （[class*="message"] 同时命中容器和内容包装层）会返回容器内部的元素，
        // 那属于选择器偏松、留待真机复核，不属于「矩阵与快照对不上」。
        const { doc, adapter } = setup();
        const annotated = getRoleElements(doc, "message");
        if (annotated.length === 0) throw new Error("fixture 没有标注任何 message");
        const returned = Array.from(adapter.getMessageList() || []);
        for (const m of annotated) {
          if (!returned.some((el) => m === el || m.contains(el))) {
            throw new Error(`标注的消息 ${describe(m)} 没有被 getMessageList() 覆盖`);
          }
        }
      },
    },
    {
      name: "getMessageList() 第 3 个及以后的选择器也能生效",
      fn: () => {
        // 守护「messageList 里的第 3、4 个选择器从不生效」这类缺陷：
        // 历史实现只取 messageList[0] / messageList[1]，其余选择器形同虚设。
        // 这里移除前两组选择器命中的元素（模拟站点改版），断言 adapter 仍能
        // 靠第 3 个及以后的选择器找到消息。
        // 只有 2 个选择器的平台没有这条路径，如实标记为跳过。
        const { doc, adapter } = setup();
        const selectors = adapter.selectors.messageList;
        if (selectors.length < 3) return "SKIP";
        for (const sel of selectors.slice(0, 2)) {
          for (const el of Array.from(doc.querySelectorAll(sel))) el.remove();
        }
        const deeper = selectors.slice(2);
        if (!deeper.some((sel) => doc.querySelector(sel) !== null)) return "SKIP";
        const found = Array.from(adapter.getMessageList() || []);
        if (found.length === 0) {
          throw new Error(
            `移除前两组选择器命中的元素后 getMessageList() 返回空——` +
              `第 3 个及以后的选择器（${deeper.join(" / ")}）没有生效`,
          );
        }
      },
    },
    {
      name: "getMessageList() 不返回标注范围之外的元素",
      fn: () => {
        // 这条守护的是历史上的「全都不匹配就回退到页面全部 div」缺陷：
        // 回退会让 getMessageList() 返回上百个与消息无关的 div，
        // 并连带把基于计数的响应等待逻辑带偏。
        const { doc, adapter } = setup();
        const annotated = getRoleElements(doc, "message");
        const returned = Array.from(adapter.getMessageList() || []);
        for (const el of returned) {
          if (!isWithin(el, annotated)) {
            throw new Error(
              `getMessageList() 返回了标注范围之外的元素 ${describe(el)}` +
                "——这正是「回退到页面全部 div」的旧缺陷",
            );
          }
        }
      },
    },
    {
      name: "getLatestMessage() 返回最后一条标注消息",
      fn: () => {
        const { doc, adapter } = setup();
        const annotated = getRoleElements(doc, "message");
        const latest = adapter.getLatestMessage();
        if (!latest) throw new Error("getLatestMessage() 返回 null");
        if (!isWithin(latest, [annotated[annotated.length - 1]])) {
          throw new Error(
            `getLatestMessage() 返回 ${describe(latest)}，不在最后一条标注消息 ${describe(annotated[annotated.length - 1])} 之内`,
          );
        }
      },
    },
    {
      name: "isTyping() 在空闲 fixture 上为 false",
      fn: () => {
        // 守护可见性判定：真实站点空闲态会把打字指示器留在 DOM 里
        // （display:none）。按「存在即命中」判定会让 isTyping() 恒为 true，
        // 于是响应等待永远超时。
        const { adapter } = setup();
        const actual = adapter.isTyping();
        if (actual !== false) throw new Error(`isTyping() 返回 ${actual}，期望 false`);
      },
    },
    {
      name: "adapter.selectors 与模块导出的 SELECTORS 是同一份",
      fn: () => {
        const { adapter } = setup();
        if (adapter.selectors !== mod.SELECTORS) {
          throw new Error("adapter.selectors 与模块导出的 SELECTORS 不是同一份对象");
        }
      },
    },
    {
      name: "injectText() 把文本写进输入框",
      fn: async () => {
        const { doc, adapter } = setup();
        await adapter.injectText(TEST_TEXT);
        const input = adapter.getChatInput();
        if (!input) throw new Error("注入后取不到输入框");
        const text = input.textContent || "";
        const value = typeof input.value === "string" ? input.value : "";
        if (!text.includes(TEST_TEXT) && !value.includes(TEST_TEXT)) {
          throw new Error(`注入后输入框里找不到 ${JSON.stringify(TEST_TEXT)}（textContent=${JSON.stringify(text)} value=${JSON.stringify(value)}）`);
        }
      },
    },
  ];
}

/**
 * 工具层守护：直接打生产 adapter-utils 的两条查找函数。
 *
 * 平台级用例只经由 adapter 的公开方法间接触发这两条规则，**覆盖不到**
 * 「查找不到时的回退行为」这类分支——而那正是历史缺陷所在：
 *   - findElements 全不匹配时回退到「页面全部 div」（注释却写着 empty NodeList）；
 *   - findElement 会把 <body> 当作合法命中（Gemini 的 body class 常驻
 *     enable-lm-loading-animation，宽松的 [class*="loading"] 必然命中它）。
 * 用例用 Gemini 真实快照（body class 与真机一致）来复现这两条路径。
 *
 * @returns {Promise<Array>} 用例结果
 */
async function testUtilGuards() {
  const utils = await import(
    pathToFileURL(path.join(PLATFORMS_DIR, "adapter-utils.js")).href,
  );
  const cases = [];

  cases.push(
    runTest("findElement() 不会把 <body> 当作匹配结果", () => {
      loadFixture("gemini", "gemini.google.com");
      const el = utils.findElement(['[class*="loading"]']);
      if (!el) return true;
      if (el.tagName === "BODY" || el.tagName === "HTML") {
        throw new Error(`findElement() 返回了页面根节点 <${el.tagName.toLowerCase()}>`);
      }
    }),
  );

  cases.push(
    runTest("findElements() 不会把 <body> 计入结果", () => {
      loadFixture("gemini", "gemini.google.com");
      for (const el of Array.from(utils.findElements(['[class*="loading"]']))) {
        if (el.tagName === "BODY" || el.tagName === "HTML") {
          throw new Error(`findElements() 把页面根节点 <${el.tagName.toLowerCase()}> 计入了结果`);
        }
      }
    }),
  );

  cases.push(
    runTest("findElements() 全不匹配时返回空集合（不回退到页面全部 div）", () => {
      loadFixture("gemini", "gemini.google.com");
      const els = Array.from(utils.findElements(['[data-role="no-such-element-here"]']));
      if (els.length !== 0) {
        throw new Error(`期望空集合，实际返回 ${els.length} 个元素（历史缺陷：回退到全部 div）`);
      }
    }),
  );

  return cases;
}

/**
 * 跑单个平台的全部用例。
 * @param {object} spec
 * @returns {Promise<{pass: number, fail: number, total: number}>}
 */
async function testAdapter(spec) {
  const mod = await importAdapter(spec);
  const results = [];
  for (const c of buildCases(spec, mod)) {
    results.push(await runTestAsync(c.name, c.fn));
  }
  return formatResults(spec.name, results);
}

/**
 * 矩阵级守护：生产 adapter 模块必须全部被矩阵覆盖。
 * @returns {Array} 用例结果
 */
function testMatrixCoverage() {
  const production = listProductionAdapterModules();
  const covered = PLATFORMS.map((p) => p.module);
  const missing = production.filter((m) => !covered.includes(m));
  const extra = covered.filter((m) => !production.includes(m));

  return [
    runTest("矩阵覆盖了 src/platforms 下的全部生产 adapter", () => {
      if (missing.length > 0) {
        throw new Error(`生产新增了 adapter 但矩阵没覆盖：${missing.join(", ")}`);
      }
      if (extra.length > 0) {
        throw new Error(`矩阵登记了不存在的生产 adapter：${extra.join(", ")}`);
      }
    }),
  ];
}

/**
 * 跑整个矩阵。
 * @param {string|null} filterPlatform
 * @returns {Promise<{totalPass: number, totalFail: number, totalTests: number}>}
 */
async function runTestMatrix(filterPlatform) {
  console.log("╔══════════════════════════════════════════════════════════════╗");
  console.log("║         Chrome Extension Adapter Test Matrix                ║");
  console.log("╚══════════════════════════════════════════════════════════════╝");
  console.log(`  Platforms: ${PLATFORMS.length}`);
  console.log("  判定对象: 生产 adapter 源码（src/platforms/*.js）");
  console.log("  契约来源: fixture 内 data-role 标注的真实 DOM 快照");
  console.log("");

  const platformIds = filterPlatform ? [filterPlatform] : PLATFORMS.map((p) => p.id);

  let totalPass = 0;
  let totalFail = 0;
  let totalSkipped = 0;
  let totalTests = 0;
  const platformResults = [];

  for (const id of platformIds) {
    const spec = PLATFORMS.find((p) => p.id === id);
    const result = await testAdapter(spec);
    totalPass += result.pass;
    totalFail += result.fail;
    totalSkipped += result.skipped;
    totalTests += result.total;
    platformResults.push({ id, ...result });
  }

  const coverage = testMatrixCoverage();
  if (!filterPlatform) {
    const covResult = formatResults("矩阵覆盖守护", coverage);
    totalPass += covResult.pass;
    totalFail += covResult.fail;
    totalSkipped += covResult.skipped;
    totalTests += covResult.total;

    const utilResult = formatResults("工具层守护", await testUtilGuards());
    totalPass += utilResult.pass;
    totalFail += utilResult.fail;
    totalSkipped += utilResult.skipped;
    totalTests += utilResult.total;
  }

  console.log("\n╔══════════════════════════════════════════════════════════════╗");
  console.log("║                        Summary                              ║");
  console.log("╚══════════════════════════════════════════════════════════════╝\n");

  for (const r of platformResults) {
    const icon = r.fail === 0 ? "ALL PASS" : `${r.fail} FAIL`;
    const name = PLATFORMS.find((p) => p.id === r.id).name;
    console.log(`  ${name.padEnd(25)} ${r.pass}/${r.total} (${icon})`);
  }

  console.log(
    `\n  Total: ${totalPass}/${totalTests} passed, ${totalFail} failed, ${totalSkipped} skipped`,
  );
  console.log("");

  return { totalPass, totalFail, totalTests };
}

// ============================================================================
// CLI 入口
// ============================================================================

async function main() {
  const args = process.argv.slice(2);
  let filterPlatform = null;

  for (const arg of args) {
    if (arg.startsWith("--platform=")) {
      filterPlatform = arg.split("=")[1];
    }
    if (arg === "--help" || arg === "-h") {
      console.log("Usage: node tests/adapter-matrix/adapter-test-runner.js [options]");
      console.log("");
      console.log("Options:");
      console.log("  --platform=<id>   只测某个平台");
      console.log("  --list            列出全部平台");
      console.log("  --help, -h        显示本帮助");
      console.log("");
      console.log("Platforms:");
      for (const p of PLATFORMS) {
        console.log(`  ${p.id.padEnd(12)} ${p.name} (${p.hostnames.join(", ")})`);
      }
      process.exit(0);
    }
    if (arg === "--list") {
      console.log("Available platforms:");
      for (const p of PLATFORMS) {
        console.log(`  ${p.id.padEnd(12)} ${p.name}`);
        console.log(`               Hostnames: ${p.hostnames.join(", ")}`);
        console.log(`               Fixture:   mock-dom-${p.fixture}.html`);
        console.log(`               Module:    ${p.module}`);
        console.log("");
      }
      process.exit(0);
    }
  }

  if (filterPlatform && !PLATFORMS.some((p) => p.id === filterPlatform)) {
    console.error(`Error: Unknown platform "${filterPlatform}"`);
    console.error(`Available: ${PLATFORMS.map((p) => p.id).join(", ")}`);
    process.exit(1);
  }

  const { totalFail } = await runTestMatrix(filterPlatform);
  process.exit(totalFail > 0 ? 1 : 0);
}

await main();
