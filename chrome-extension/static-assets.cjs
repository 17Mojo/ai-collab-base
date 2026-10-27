/**
 * 静态资源复制 — 构建产物里 public/ 的布局
 *
 * ## 为什么单独抽出来
 *
 * 复制逻辑此前有**两份**：`build.js` 里一份，`vite.config.js` 里一份
 * （后者还被 `export` 出去，却**没有任何地方调用**）。两份各写各的文件清单，
 * 于是「装好的扩展里到底有哪些页面」这件事没有唯一答案——
 * 2026-10-25 就是这么翻车的：
 *
 *   - `popup.js` / `settings.js` 打开 Pack 编辑器用的是
 *     `chrome.runtime.getURL('public/pack-editor.html')`
 *   - 而构建产物里 Pack 编辑器只被复制成**扁平**的 `dist/pack-editor.html`
 *   - ⇒ 那个 URL 在装好的扩展里 404 ⇒ 外部用户卡在「导入 Pack」这一步
 *
 * 现在复制只有这一份实现、这一个文件清单。
 *
 * ## 两种布局都保留
 *
 *   - `<dest>/<file>`          扁平（构建产物的 manifest 指向的就是这一份）
 *   - `<dest>/public/<file>`   嵌套（代码里 `getURL('public/...')` 用的就是这一份）
 *
 * 两种 URL 因此都打得开，代码里引用哪种都不会 404。
 *
 * @file
 */

const { copyFileSync, mkdirSync, existsSync, writeFileSync } = require("fs");
const { resolve } = require("path");

/** 需要复制到构建产物的 HTML 与 JS */
const STATIC_FILES = [
  "popup.html",
  "settings.html",
  "pack-editor.html",
  "style-editor.html",
  "popup.js",
  "settings.js",
  "pack-editor.js",
  "style-editor.js",
];

/** 需要复制到构建产物的图标 */
const ICON_SIZES = ["16", "48", "128"];

/**
 * 把 public/ 下的静态资源复制到构建产物目录。
 *
 * @param {Object} options
 * @param {string} options.rootDir - 扩展根目录（含 public/）
 * @param {string} options.destDir - 构建产物目录
 * @returns {{files: string[], icons: string[]}} 实际复制过去的文件（相对 destDir）
 */
function copyStaticAssets({ rootDir, destDir }) {
  const publicDir = resolve(rootDir, "public");
  const files = [];
  const icons = [];

  // HTML 与 JS：扁平 + public/ 嵌套各一份
  const nestedDir = resolve(destDir, "public");
  if (!existsSync(nestedDir)) mkdirSync(nestedDir, { recursive: true });
  for (const file of STATIC_FILES) {
    const src = resolve(publicDir, file);
    if (!existsSync(src)) continue;
    copyFileSync(src, resolve(destDir, file));
    copyFileSync(src, resolve(nestedDir, file));
    files.push(file);
    files.push(`public/${file}`);
  }

  // 图标：只在扁平布局下放一份（manifest 指向 icons/iconN.png）
  const iconsDir = resolve(destDir, "icons");
  if (!existsSync(iconsDir)) mkdirSync(iconsDir, { recursive: true });
  for (const size of ICON_SIZES) {
    const src = resolve(publicDir, "icons", `icon${size}.png`);
    if (!existsSync(src)) continue;
    copyFileSync(src, resolve(iconsDir, `icon${size}.png`));
    icons.push(`icons/icon${size}.png`);
  }

  return { files, icons };
}

/**
 * 由 `manifest.json` **生成**构建产物用的 manifest。
 *
 * ## 为什么不再手写 `manifest.dist.json`
 *
 * 此前仓库里有**三份**平台清单：`manifest.json`、`manifest.dist.json`、
 * 以及 `tests/platforms.mjs`。而 `build.js` / `vite.config.js` 复制的是
 * **`manifest.dist.json`**（存在就用它）——于是改 `manifest.json` 根本不生效，
 * 而且两份清单会各自漂移：
 *
 *   - 2026-10-26 实测：`manifest.json` 里有 `wenxin.baidu.com`，
 *     `manifest.dist.json` 里**没有**；描述里一个写 10 个适配器、一个写 11 个。
 *   - 更要命的是**站点覆盖**：两份都只写了 `https://qianwen.com/*`，
 *     而千问的真站是 `https://www.qianwen.com/` ⇒ 内容脚本根本没注入。
 *
 * 现在：**`manifest.json` 是唯一的事实源**，产物里的 manifest 由它生成，
 * 路径按产物的扁平布局改写。改一处就够，不会再有「改了不生效」。
 *
 * 改写规则（与产物布局一一对应）：
 *   - `background.service_worker` → 文件名（产物里是扁平的 `service-worker.js`）
 *   - `content_scripts[].js`     → 文件名（`content-script.js`）
 *   - `action.default_popup`     → 文件名（`popup.html`）
 *   - `action.default_icon`      → 去掉 `public/` 前缀（`icons/icon16.png`）
 *
 * @param {Object} manifest - `manifest.json` 的内容
 * @returns {Object} 产物用的 manifest（深拷贝，不改原对象）
 */
function buildDistManifest(manifest) {
  const dist = JSON.parse(JSON.stringify(manifest));

  if (dist.background && dist.background.service_worker) {
    const p = dist.background.service_worker;
    dist.background.service_worker = p.slice(p.lastIndexOf("/") + 1);
  }

  for (const cs of dist.content_scripts || []) {
    cs.js = (cs.js || []).map((p) => p.slice(p.lastIndexOf("/") + 1));
  }

  if (dist.action && dist.action.default_popup) {
    const p = dist.action.default_popup;
    dist.action.default_popup = p.slice(p.lastIndexOf("/") + 1);
  }

  if (dist.action && dist.action.default_icon) {
    dist.action.default_icon = Object.fromEntries(
      Object.entries(dist.action.default_icon).map(([size, p]) => [
        size,
        p.replace(/^public\//, ""),
      ]),
    );
  }

  return dist;
}

/**
 * 把 `manifest.json` 写进构建产物目录（内容由 buildDistManifest 生成）。
 *
 * @param {Object} options
 * @param {string} options.rootDir - 扩展根目录
 * @param {string} options.destDir - 构建产物目录
 * @returns {Object} 写进去的 manifest
 */
function writeDistManifest({ rootDir, destDir }) {
  const src = resolve(rootDir, "manifest.json");
  const manifest = JSON.parse(require("fs").readFileSync(src, "utf-8"));
  const dist = buildDistManifest(manifest);
  writeFileSync(resolve(destDir, "manifest.json"), `${JSON.stringify(dist, null, 2)}\n`, "utf-8");
  return dist;
}

module.exports = {
  copyStaticAssets,
  buildDistManifest,
  writeDistManifest,
  STATIC_FILES,
  ICON_SIZES,
};
