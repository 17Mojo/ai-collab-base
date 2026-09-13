#!/usr/bin/env node
/**
 * Chrome Extension 构建脚本
 *
 * 执行两次 Vite 构建（输出到临时目录），然后合并到 dist 目录
 */

const { execSync } = require("child_process");
const { rmSync, existsSync, copyFileSync, mkdirSync, readdirSync } = require("fs");
const { resolve } = require("path");

const rootDir = __dirname;
const distDir = resolve(rootDir, "dist");
const publicDir = resolve(rootDir, "public");
const tmpDir = resolve(rootDir, ".vite-tmp");

console.log("=== Chrome Extension Build ===\n");

// 清空临时和输出目录
for (const dir of [tmpDir, distDir]) {
  if (existsSync(dir)) rmSync(dir, { recursive: true });
}
console.log("[1/5] Cleaned output directories");

// 构建 Content Script（IIFE 格式）
console.log("\n[2/5] Building Content Script (IIFE)...");
try {
  execSync("npx vite build --config vite.config.js", {
    env: { ...process.env, BUILD_TARGET: "content-script" },
    stdio: "inherit",
    cwd: rootDir,
  });
  console.log("  ✅ Content Script built");
} catch (e) {
  console.error("  ❌ Content Script build failed");
  process.exit(1);
}

// 构建 Service Worker（ESM 格式）
console.log("\n[3/5] Building Service Worker (ESM)...");
try {
  execSync("npx vite build --config vite.config.js", {
    env: { ...process.env, BUILD_TARGET: "service-worker" },
    stdio: "inherit",
    cwd: rootDir,
  });
  console.log("  ✅ Service Worker built");
} catch (e) {
  console.error("  ❌ Service Worker build failed");
  process.exit(1);
}

// 合并构建产物到 dist
console.log("\n[4/5] Merging build outputs...");
mkdirSync(distDir, { recursive: true });

// 复制 CS 产物
const csDir = resolve(tmpDir, "cs");
if (existsSync(csDir)) {
  for (const file of readdirSync(csDir)) {
    copyFileSync(resolve(csDir, file), resolve(distDir, file));
  }
  console.log("  ✅ Content Script merged");
}

// 复制 SW 产物
const swDir = resolve(tmpDir, "sw");
if (existsSync(swDir)) {
  for (const file of readdirSync(swDir)) {
    copyFileSync(resolve(swDir, file), resolve(distDir, file));
  }
  console.log("  ✅ Service Worker merged");
}

// 复制静态资源
console.log("\n[5/5] Copying static assets...");

// manifest.json
const manifestSrc = resolve(rootDir, "manifest.dist.json");
if (existsSync(manifestSrc)) {
  copyFileSync(manifestSrc, resolve(distDir, "manifest.json"));
} else {
  copyFileSync(resolve(rootDir, "manifest.json"), resolve(distDir, "manifest.json"));
}

// HTML 和 JS
const staticFiles = [
  "popup.html", "settings.html", "pack-editor.html", "style-editor.html",
  "popup.js", "settings.js", "pack-editor.js", "style-editor.js",
];
for (const file of staticFiles) {
  const src = resolve(publicDir, file);
  if (existsSync(src)) copyFileSync(src, resolve(distDir, file));
}

// 图标
const iconsDir = resolve(distDir, "icons");
mkdirSync(iconsDir, { recursive: true });
for (const size of ["16", "48", "128"]) {
  const src = resolve(publicDir, "icons", `icon${size}.png`);
  if (existsSync(src)) copyFileSync(src, resolve(iconsDir, `icon${size}.png`));
}

// 清理临时目录
rmSync(tmpDir, { recursive: true });

console.log("  ✅ Static assets copied");
console.log("\n=== Build Complete ===");
console.log("Output directory: dist/");
console.log("Load in Chrome: chrome://extensions → Developer mode → Load unpacked → select dist/");
