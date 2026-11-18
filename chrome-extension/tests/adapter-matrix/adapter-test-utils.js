/**
 * Adapter Matrix 测试工具（ESM）
 *
 * 设计原则：**工具只负责搭建环境，不复制生产逻辑**。
 *
 * 历史版本在这里自实现了 findElement / findElements / extractMessageContent，
 * 注释写着「Mirrors the adapter-utils ... behavior」但实际并不一致——例如生产的
 * findElements 在全都不匹配时回退到「页面上的全部 div」，而这里的实现返回空数组。
 * 矩阵因此测的是一个「平行宇宙」：生产选择器漂移了矩阵照样全绿。
 * 真机实测已经证明过这一点（Gemini 的发送按钮选择器在真实站点一个都命中不了，
 * 矩阵长期 120/120 全绿）。
 *
 * 现在这里只做两件事：把 fixture 装进 jsdom、把全局对象接好。
 * 其余判定全部由生产 adapter 代码本身给出。
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";
import { installSlateSiteIfNeeded } from "../helpers/slate-site.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const FIXTURES_DIR = path.join(__dirname, "fixtures");
export const PLATFORMS_DIR = path.resolve(__dirname, "..", "..", "src", "platforms");

/**
 * 真实 DOM 快照目录（B-2 采集器产出）。
 *
 * 与 `fixtures/mock-dom-*.html`（手写假 DOM）的区别：
 *   - mock 是**手写**的，天然「让选择器能命中」；
 *   - real 是**从真机上采下来**的，标注由生产 adapter 的实际命中结果给出。
 */
export const REAL_FIXTURES_DIR = path.resolve(__dirname, "..", "real-machine", "fixtures", "real");

/**
 * 列出生产 adapter 源文件（用于「矩阵必须覆盖全部平台」的守护）。
 * @returns {string[]}
 */
export function listProductionAdapterModules() {
  return readdirSync(PLATFORMS_DIR)
    .filter((f) => f.endsWith("-adapter.js"))
    .sort();
}

/**
 * 载入 fixture 到 jsdom，并把 jsdom 的全局对象接到 globalThis 上。
 * 生产 adapter 直接使用裸 document / window，不接上就跑不起来。
 *
 * @param {string} fixtureId - fixture 标识（如 'gemini'）
 * @param {string} hostname - 模拟的站点域名（决定 detect() 的结果）
 * @returns {JSDOM}
 */
export function loadFixture(fixtureId, hostname) {
  const fixturePath = path.join(FIXTURES_DIR, `mock-dom-${fixtureId}.html`);
  const html = readFileSync(fixturePath, "utf-8");
  const dom = new JSDOM(html, {
    url: `https://${hostname}/`,
    pretendToBeVisual: true,
  });
  installGlobals(dom.window);
  installSiteBehavior(dom.window);
  return dom;
}

/**
 * 给 fixture 里的站点补上「行为」。
 *
 * 静态 fixture 只有结构没有行为，而 Slate 编辑器的关键语义是行为
 * （模型只认 beforeinput、选区靠 selectionchange 同步）。
 * 少了这一步，矩阵里的注入用例会看到一个**永远不收文本**的假站点，
 * 测的就不是生产代码的真实行为了。详见 tests/helpers/slate-site.mjs。
 *
 * @param {Window} window
 */
function installSiteBehavior(window) {
  const editor = window.document.querySelector("[data-slate-editor]");
  if (!editor) return;
  const sendButton = window.document.querySelector(
    "[data-probe-role='send-button'], [data-role='send-button']",
  );
  installSlateSiteIfNeeded(window, editor, { sendButton });
}

/**
 * 载入**真实 DOM 快照**（B-2 采集器产出）到 jsdom。
 *
 * 与 `loadFixture` 的区别：
 *   - 快照文件可能**不存在**（该平台没采到）——此时返回 null，由调用方
 *     **如实跳过**，不能当成通过；
 *   - 快照存在但 outcome 不是 captured（登录墙 / 人机校验）——同样跳过，
 *     原因从 sidecar 元数据里读出来一并报出来。
 *
 * @param {string} fixtureId - 平台标识（如 'gemini'）
 * @param {string} hostname - 模拟的站点域名
 * @returns {{dom: JSDOM, meta: object}|null}
 */
export function loadRealFixture(fixtureId, hostname) {
  const htmlPath = path.join(REAL_FIXTURES_DIR, `${fixtureId}.html`);
  const metaPath = path.join(REAL_FIXTURES_DIR, `${fixtureId}.json`);
  if (!existsSync(htmlPath) || !existsSync(metaPath)) return null;

  const meta = JSON.parse(readFileSync(metaPath, "utf-8"));
  if (meta.outcome !== "captured") return null;

  const html = readFileSync(htmlPath, "utf-8");
  const dom = new JSDOM(html, {
    url: `https://${hostname}/`,
    pretendToBeVisual: true,
  });
  installGlobals(dom.window);
  installSiteBehavior(dom.window);
  return { dom, meta };
}

/**
 * 读取**真实快照**里的探针标注。
 *
 * 用的是 `data-probe-role` 而不是 `data-role`：
 * 真实站点自己也会用 data-role（实测千问有 data-role="icon"），
 * 共用命名空间会把站点自己的元素误读成「消息气泡」。
 *
 * @param {Document} document
 * @param {string} role
 * @returns {Element[]}
 */
export function getProbeRoleElements(document, role) {
  return Array.from(document.querySelectorAll(`[data-probe-role="${role}"]`));
}

/**
 * 把 jsdom 的 window / document 接到 globalThis。
 * 生产代码用的是裸 `document` / `window`，不是 import 进来的对象。
 *
 * @param {Window} window
 */export function installGlobals(window) {
  globalThis.window = window;
  globalThis.document = window.document;
  globalThis.location = window.location;
  globalThis.Event = window.Event;
  globalThis.KeyboardEvent = window.KeyboardEvent;
  globalThis.MouseEvent = window.MouseEvent;
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.HTMLTextAreaElement = window.HTMLTextAreaElement;
  globalThis.HTMLInputElement = window.HTMLInputElement;
  globalThis.MutationObserver = window.MutationObserver;
  globalThis.getComputedStyle = window.getComputedStyle.bind(window);
  installExecCommandShim(window);
  installContentEditableShim(window);
}

/**
 * jsdom 没有实现 document.execCommand（直接调用会抛 TypeError），
 * 而生产注入路径依赖它。这里补一个最小可用实现：
 * 记录最后一次 focus 的元素，insertText 把文本写进去。
 *
 * 不补这个垫片的话，矩阵只能像历史版本那样**绕过**生产注入代码
 * 自己改 DOM——那样就测不到生产注入路径了。
 *
 * @param {Window} window
 */
function installExecCommandShim(window) {
  const doc = window.document;
  if (typeof doc.execCommand === "function") return;

  let focused = null;
  const originalFocus = window.HTMLElement.prototype.focus;
  window.HTMLElement.prototype.focus = function focus() {
    focused = this;
    try {
      originalFocus.call(this);
    } catch {
      // jsdom 对不可聚焦元素可能抛错——生产代码不关心，忽略即可
    }
  };

  doc.execCommand = function execCommand(command, _showUi, value) {
    const target = focused || doc.activeElement;
    if (!target) return false;
    if (command === "selectAll") return true;
    if (command === "delete") {
      target.textContent = "";
      return true;
    }
    if (command === "insertText") {
      target.textContent = (target.textContent || "") + (value || "");
      target.dispatchEvent(new window.Event("input", { bubbles: true }));
      return true;
    }
    return false;
  };
}

/**
 * jsdom 的 element.isContentEditable 是 undefined（真实浏览器是 boolean）。
 * 生产 injectTextSmart 靠它区分 contenteditable div，补上以便走到
 * 真正的生产分支（injectIntoContentEditable）而不是兜底分支。
 *
 * @param {Window} window
 */
function installContentEditableShim(window) {
  const proto = window.HTMLElement.prototype;
  if (Object.prototype.hasOwnProperty.call(proto, "isContentEditable")) return;
  Object.defineProperty(proto, "isContentEditable", {
    configurable: true,
    get() {
      const attr = this.getAttribute && this.getAttribute("contenteditable");
      return attr !== null && attr !== "false";
    },
  });
}

/**
 * 取出 fixture 里用 data-role 标注的元素（真实 DOM 契约）。
 * @param {Document} document
 * @param {string} role
 * @returns {Element[]}
 */
export function getRoleElements(document, role) {
  return Array.from(document.querySelectorAll(`[data-role="${role}"]`));
}

/**
 * 判断元素是否落在某个标注元素内部（含自身）。
 * @param {Element} el
 * @param {Element[]} containers
 * @returns {boolean}
 */
export function isWithin(el, containers) {
  return containers.some((c) => c === el || c.contains(el));
}

/**
 * 执行单个用例，失败时捕获错误信息。
 * @param {string} name
 * @param {Function} fn - 抛异常即视为失败
 * @returns {{ name: string, pass: boolean, error: string|null }}
 */
/**
 * fixture 声明的判据（纯函数）：`data-expect-send-button="none"` 该不该放行（N59 ② / A2）。
 *
 * ## 为什么要有「声明」这层
 *
 * 删掉 deepseek mock 里那个假按钮之后，矩阵会遇到一个新问题：
 * `[data-role="send-button"]` 一个都没有，这条断言该算什么？
 * 「什么都不算」是最坏的选择——它把「没想过」伪装成「没有」。
 * 所以要求 fixture 显式表态：
 *
 *   - 有按钮：标注恰好 1 个 `[data-role="send-button"]`（原有契约，走对账判据）；
 *   - 没按钮：在 `<body>` 上写 `data-expect-send-button="none"`，
 *     断言改为「`getSendButton()` 必须返回 null」。
 *
 * 声明本身不是证据——它是**待证主张**。所以这里要求一个独立见证人：
 * 同站的真机快照必须采成功（`outcome=captured` 且 `composerFound=true`），
 * 且其 `sendButtonFound` 必须与声明同向。否则只能算「没有见证人」，降级 SKIP。
 *
 * 状态：
 *   no-declaration     没声明 ⇒ 调用方走原对账路径
 *   pass               声明「无按钮」，且 fixture / adapter / 真机三方一致
 *   unknown            声明了不认识的取值（目前只认 none）
 *   self-contradictory 声明「无按钮」却又标注了 send-button
 *   no-witness         没有可用的真机快照 ⇒ 声明无人作证
 *   contradicts-real   声明「无按钮」但真机快照说 sendButtonFound=true
 *   still-matches      声明「无按钮」但 getSendButton() 仍然返回了元素
 *
 * @param {{expectDecl: string|null, annotated: number, hit: boolean, realMeta: object|null, id?: string}} arg
 * @returns {{status: string, reason: string}}
 */
export function judgeSendButtonDeclaration({ expectDecl, annotated, hit, realMeta, id = "?" }) {
  if (expectDecl === null || expectDecl === undefined) {
    return { status: "no-declaration", reason: "" };
  }
  if (expectDecl !== "none") {
    return {
      status: "unknown",
      reason: `未知的 data-expect-send-button="${expectDecl}"——目前只认 "none"；新增取值请同时改矩阵与 N59 的记录`,
    };
  }
  if (annotated !== 0) {
    return {
      status: "self-contradictory",
      reason:
        `fixture 声明 data-expect-send-button="none"，却仍标注了 ${annotated} 个 ` +
        `[data-role="send-button"]——声明与 DOM 自相矛盾`,
    };
  }
  if (!realMeta) {
    return {
      status: "no-witness",
      reason: `fixture 声明无发送按钮，但没有真机快照可印证（fixtures/real/${id}.json）`,
    };
  }
  if (realMeta.outcome !== "captured" || realMeta.composerFound !== true) {
    return {
      status: "no-witness",
      reason:
        `fixture 声明无发送按钮，但真机快照不可用（outcome=${realMeta.outcome}, ` +
        `composerFound=${realMeta.composerFound}）——声明没有独立见证人`,
    };
  }
  if (realMeta.sendButtonFound === true) {
    return {
      status: "contradicts-real",
      reason:
        "fixture 声明无发送按钮，但真机快照 sendButtonFound=true——" +
        "声明与真机相反，先确认哪个错了（不许两边都留着）",
    };
  }
  if (hit) {
    return {
      status: "still-matches",
      reason:
        "fixture 声明无发送按钮，但 getSendButton() 仍然命中了元素——" +
        "要么选择器靠猜命中了不相干的东西，要么 fixture 里混进了控件",
    };
  }
  return { status: "pass", reason: "声明无按钮，且 fixture / adapter / 真机三方一致" };
}

export function runTest(name, fn) {
  try {
    const result = fn();
    if (result === false) {
      return { name, pass: false, error: "Test returned false" };
    }
    return { name, pass: true, error: null };
  } catch (e) {
    return { name, pass: false, error: e.message };
  }
}

/**
 * 读同站真实快照的元数据（`fixtures/real/<id>.json`），拿不到返回 null。
 *
 * 为什么要单独给一个读入口：矩阵的 send-button 断言此前只用 mock——而 mock 是
 * **照着 adapter 的选择器写的**，于是「选择器命中」这件事在自己身上闭环了。
 * 真机快照里 `sendButtonFound` 是采集器用**同一个** `adapter.getSendButton()`
 * 在真实 DOM 上跑出来的结论，把它拉进来才有对账可言。见 N59。
 *
 * @param {string} fixtureId
 * @returns {object|null}
 */
export function readRealSnapshotMeta(fixtureId) {
  const metaPath = path.join(REAL_FIXTURES_DIR, `${fixtureId}.json`);
  if (!existsSync(metaPath)) return null;
  try {
    return JSON.parse(readFileSync(metaPath, "utf-8"));
  } catch {
    return null;
  }
}

/**
 * send-button 断言与真机快照的对账判据（纯函数，不碰 DOM，便于单测）。
 *
 * 状态与含义：
 *   pass          两边一致（都命中 / 都没有），断言照常走
 *   contradiction 真机 `sendButtonFound=false`，但 mock 上命中了
 *                 ⇒ mock 的命中**不构成真机证据**（N59 的假绿），默认降级为 SKIP
 *   unusable      快照没采成（outcome≠captured 或 composerFound=false，登录墙）
 *                 ⇒ 它的 false 不能当「没有按钮」的证据（别把环境限制当事实）
 *   no-snapshot   没有真机快照，未对账
 *   fail          真机 `sendButtonFound=true` 但 mock 上取不到 ⇒ fixture 与真机脱节
 *
 * @param {{realMeta: object|null, mockHit: boolean, id?: string}} arg
 * @returns {{status: "pass"|"contradiction"|"unusable"|"no-snapshot"|"fail", reason: string}}
 */
export function judgeSendButtonCrossCheck({ realMeta, mockHit, id = "?" }) {
  if (!realMeta) {
    return { status: "no-snapshot", reason: `无真机快照（fixtures/real/${id}.json），未与真机对账` };
  }
  const usable = realMeta.outcome === "captured" && realMeta.composerFound === true;
  if (!usable) {
    return {
      status: "unusable",
      reason:
        `真机快照不可用（outcome=${realMeta.outcome}, composerFound=${realMeta.composerFound}）` +
        `——它的 sendButtonFound=${realMeta.sendButtonFound} 不能作为「没有发送按钮」的证据`,
    };
  }
  const realFound = realMeta.sendButtonFound === true;
  if (realFound && mockHit) return { status: "pass", reason: "真机命中、mock 也命中（一致）" };
  if (!realFound && !mockHit) return { status: "pass", reason: "真机未命中、mock 也未命中（一致）" };
  if (realFound && !mockHit) {
    return {
      status: "fail",
      reason:
        `真机快照 sendButtonFound=true，但 getSendButton() 在 mock 上返回 null` +
        `——fixture 与真机脱节（fixtures/real/${id}.json vs fixtures/mock-dom-${id}.html）`,
    };
  }
  return {
    status: "contradiction",
    reason:
      `真机快照 sendButtonFound=false（采集器用的是同一个 adapter.getSendButton()），` +
      `mock 却命中——那命中不构成真机证据（N59 假绿），本条降级为未验证`,
  };
}

/**
 * 打印一个平台的用例结果。
 * @param {string} platformName
 * @param {Array} results
 * @returns {{ pass: number, fail: number, skipped: number, total: number }}
 */
export function formatResults(platformName, results) {
  const pass = results.filter((r) => r.pass && !r.skipped).length;
  const skipped = results.filter((r) => r.skipped).length;
  const fail = results.filter((r) => !r.pass).length;
  const total = results.length;

  console.log(`\n  ${platformName}`);
  console.log(`  ${"─".repeat(50)}`);

  for (const r of results) {
    const icon = r.skipped ? "SKIP" : r.pass ? "PASS" : "FAIL";
    // SKIP 必须带上「为什么没验」：无声跳过去等于把「没验」记成「验过了」，
    // deepseek 的 send-button 假绿就是这么长出来的（N59）。
    const detail = r.error ? ` (${r.error})` : r.reason ? ` — ${r.reason}` : "";
    console.log(`    [${icon}] ${r.name}${detail}`);
  }

  const skipNote = skipped > 0 ? `, ${skipped} skipped` : "";
  console.log(`  Result: ${pass}/${total} passed${skipNote}`);
  return { pass, fail, skipped, total };
}
