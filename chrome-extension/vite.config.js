/**
 * Vite 构建配置 — Chrome Extension (Manifest V3)
 *
 * 构建策略：
 * - 使用两次独立构建，避免多入口代码拆分问题
 * - Service Worker: ESM 打包为单文件（Manifest V3 支持 type:module）
 * - Content Script: ESM 打包为 IIFE（Manifest V3 content_scripts 不支持 type:module）
 * - Popup/Settings: 直接复制（不参与构建）
 * - manifest.json: 复制到 dist，路径指向构建产物
 *
 * 选择器自动同步：
 * Content Script 通过 ESM import 从适配器文件导入 SELECTORS 常量，
 * Vite 构建时自动将选择器配置内联到产物中，无需手动维护两份配置。
 */

import { defineConfig } from "vite";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { copyFileSync, mkdirSync, existsSync, readdirSync, rmSync } from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const rootDir = resolve(__dirname);
const srcDir = resolve(rootDir, "src");
const publicDir = resolve(rootDir, "public");
const distDir = resolve(rootDir, "dist");

/**
 * 复制静态资源到 dist 目录
 */
function copyStaticAssets() {
  // 1. 复制 manifest.json
  const manifestSrc = resolve(rootDir, "manifest.dist.json");
  const manifestDst = resolve(distDir, "manifest.json");
  if (existsSync(manifestSrc)) {
    copyFileSync(manifestSrc, manifestDst);
  } else {
    copyFileSync(resolve(rootDir, "manifest.json"), manifestDst);
  }

  // 2. 复制 public 目录下的 HTML 和 JS
  const files = [
    "popup.html", "settings.html", "pack-editor.html", "style-editor.html",
    "popup.js", "settings.js", "pack-editor.js", "style-editor.js",
  ];
  for (const file of files) {
    const src = resolve(publicDir, file);
    const dst = resolve(distDir, file);
    if (existsSync(src)) copyFileSync(src, dst);
  }

  // 3. 复制图标
  const iconsDir = resolve(distDir, "icons");
  if (!existsSync(iconsDir)) mkdirSync(iconsDir, { recursive: true });
  for (const size of ["16", "48", "128"]) {
    const src = resolve(publicDir, "icons", `icon${size}.png`);
    const dst = resolve(iconsDir, `icon${size}.png`);
    if (existsSync(src)) copyFileSync(src, dst);
  }

  console.log("[vite] Static assets copied to dist/");
}

// 根据环境变量决定构建哪个入口
const buildTarget = process.env.BUILD_TARGET || "all";

const configs = {
  // Service Worker 构建（ESM 单文件）
  "service-worker": defineConfig({
    root: rootDir,
    publicDir: false,
    build: {
      outDir: resolve(rootDir, ".vite-tmp/sw"),
      emptyDirFirst: true,
      minify: false,
      sourcemap: true,
      lib: {
        entry: resolve(srcDir, "background/service-worker.js"),
        formats: ["es"],
        fileName: () => "service-worker.js",
      },
      rollupOptions: {
        external: [],
      },
    },
    resolve: {
      alias: { "@": srcDir },
    },
  }),

  // Content Script 构建（IIFE 单文件）
  "content-script": defineConfig({
    root: rootDir,
    publicDir: false,
    build: {
      outDir: resolve(rootDir, ".vite-tmp/cs"),
      emptyDirFirst: true,
      minify: false,
      sourcemap: true,
      lib: {
        entry: resolve(srcDir, "content/content-script.js"),
        formats: ["iife"],
        fileName: () => "content-script.js",
        name: "PromptPackCS",
      },
      rollupOptions: {
        external: [],
      },
    },
    resolve: {
      alias: { "@": srcDir },
    },
  }),
};

// 默认导出：根据 BUILD_TARGET 选择配置
// 如果 BUILD_TARGET=all，则导出 service-worker 配置（第一个构建）
// 完整构建需要运行: npm run build（内部执行两次 vite build）
export default configs[buildTarget] || configs["service-worker"];

// 导出复制静态资源的函数供构建脚本使用
export { copyStaticAssets };
