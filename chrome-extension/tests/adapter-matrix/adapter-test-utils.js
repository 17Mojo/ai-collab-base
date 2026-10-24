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

import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const FIXTURES_DIR = path.join(__dirname, "fixtures");
export const PLATFORMS_DIR = path.resolve(__dirname, "..", "..", "src", "platforms");

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
  return dom;
}

/**
 * 把 jsdom 的 window / document 接到 globalThis。
 * 生产代码用的是裸 `document` / `window`，不是 import 进来的对象。
 *
 * @param {Window} window
 */
export function installGlobals(window) {
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
    const detail = r.error ? ` (${r.error})` : "";
    console.log(`    [${icon}] ${r.name}${detail}`);
  }

  const skipNote = skipped > 0 ? `, ${skipped} skipped` : "";
  console.log(`  Result: ${pass}/${total} passed${skipNote}`);
  return { pass, fail, skipped, total };
}
