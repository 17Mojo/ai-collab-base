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
 *   - `<dest>/<file>`          扁平（`manifest.dist.json` 指向的就是这一份）
 *   - `<dest>/public/<file>`   嵌套（代码里 `getURL('public/...')` 用的就是这一份）
 *
 * 两种 URL 因此都打得开，代码里引用哪种都不会 404。
 *
 * @file
 */

const { copyFileSync, mkdirSync, existsSync } = require("fs");
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

module.exports = { copyStaticAssets, STATIC_FILES, ICON_SIZES };
