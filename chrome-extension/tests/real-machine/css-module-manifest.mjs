/**
 * CSS Module 类名清单提取器
 *
 * ## 它解决什么问题
 *
 * 千问（qianwen.com）用的是 **CSS Modules**。它生成的类名长这样：
 *
 *     chatRoom-rNZG_v
 *     newChatReveal-OikAdB
 *     surfaceSwitchReveal-_L0G1n
 *
 * 其中：
 *   - `chatRoom` 是**作者在源码里写的本地名** —— 每次重新构建**都不变**；
 *   - `-rNZG_v` 是**内容哈希** —— 站点每次发版都可能变。
 *
 * 这件事对写 adapter 有直接后果：
 *
 *   ✗ `div.chatRoom-rNZG_v`  → 站点下次发版就废了
 *   ✓ `div[class*="chatRoom"]` → 只依赖稳定的那一半
 *
 * 但**哪些本地名跟消息气泡有关**，光看落地页是不知道的
 * （落地页没有会话 ⇒ 没有气泡元素）。
 * 所以这个工具去翻 JS bundle —— CSS Modules 的「本地名 → 哈希」映射表
 * 就编译在打包产物里。翻出来就能回答：
 * 「这个站点到底有没有叫 `messageItem` / `chatBubble` 之类的类？」
 *
 * ## 硬红线
 *
 * 只读。只 GET 页面自己的静态资源，不注入、不点击、不发送。
 *
 * ## 用法
 *
 *   node tests/real-machine/css-module-manifest.mjs --platform=qianwen
 *   node tests/real-machine/css-module-manifest.mjs --platform=qianwen --grep=message
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import { PLATFORMS, getPlatform } from "../platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 一次抓取：页面里所有 <script src> 与 <link href>。
 * @param {import('playwright').Page} page
 */
async function collectAssets(page) {
  return page.evaluate(() => ({
    scripts: Array.from(document.querySelectorAll("script[src]")).map((s) => s.src),
    links: Array.from(document.querySelectorAll("link[href]")).map((l) => l.href),
  }));
}

/**
 * 从一段 JS/CSS 文本里抽出 CSS Modules 的类名映射。
 *
 * 打包产物里的典型形态（webpack / vite / rsbuild 都差不多）：
 *
 *     {"chatRoom":"chatRoom-rNZG_v","newChatReveal":"newChatReveal-OikAdB"}
 *
 * 也可能是压缩过的数字键：
 *
 *     {".V7x1":".V7x1",...}   ← 这个抓不到，本工具会明确报告
 *
 * @param {string} text
 * @returns {Map<string, string>} 本地名 → 完整类名
 */
export function extractLocalNames(text) {
  const found = new Map();
  // 形如 "localName":"localName-hash" 或 'localName':'localName-hash'
  const re = /["']([A-Za-z_][A-Za-z0-9_-]{1,60})["']\s*:\s*["']([A-Za-z_][A-Za-z0-9_-]{1,80})["']/g;
  let m = re.exec(text);
  while (m !== null) {
    const local = m[1];
    const full = m[2];
    // 只收「哈希后缀」形态：full 必须是 local 加一段后缀
    if (full.startsWith(local) && full.length > local.length) {
      found.set(local, full);
    }
    m = re.exec(text);
  }
  return found;
}

function parseArgs(argv) {
  const args = { platform: null, locale: "zh-CN", channel: "chrome", out: null, grep: null, maxAssets: 60 };
  for (const raw of argv) {
    if (raw.startsWith("--platform=")) args.platform = raw.slice("--platform=".length).trim();
    else if (raw.startsWith("--locale=")) args.locale = raw.slice("--locale=".length);
    else if (raw.startsWith("--channel=")) args.channel = raw.slice("--channel=".length);
    else if (raw.startsWith("--out=")) args.out = raw.slice("--out=".length);
    else if (raw.startsWith("--grep=")) args.grep = raw.slice("--grep=".length).trim();
    else if (raw.startsWith("--max-assets=")) args.maxAssets = Number(raw.slice("--max-assets=".length));
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const platform = getPlatform(args.platform);
  if (!platform) {
    console.error(`未知平台 ${args.platform}。可选：${PLATFORMS.map((p) => p.id).join(", ")}`);
    return 2;
  }

  const browser = await chromium.launch({ channel: args.channel, headless: true });
  const context = await browser.newContext({ locale: args.locale, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto(platform.url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(3000);

  const assets = await collectAssets(page);
  // CSS 也要看：类名映射有时以 .css 资源里的注释形式出现
  const urls = [...assets.scripts, ...assets.links].filter((u) => /\.m?js(\?|$)|\.css(\?|$)/.test(u));
  console.log(`页面资源：${assets.scripts.length} 个 script + ${assets.links.length} 个 link；`);
  console.log(`其中 JS/CSS 候选 ${urls.length} 个，逐个抓取（上限 ${args.maxAssets}）…`);

  const manifest = new Map();
  const perAsset = [];
  let fetched = 0;
  let failed = 0;

  for (const url of urls.slice(0, args.maxAssets)) {
    try {
      const res = await context.request.get(url, { timeout: 20000 });
      if (!res.ok()) {
        failed += 1;
        continue;
      }
      const text = await res.text();
      const names = extractLocalNames(text);
      if (names.size > 0) {
        perAsset.push({ url, localNames: names.size });
        for (const [local, full] of names) {
          if (!manifest.has(local)) manifest.set(local, full);
        }
      }
      fetched += 1;
    } catch (e) {
      failed += 1;
    }
  }

  await browser.close();
  await context.close().catch(() => {});

  const all = Array.from(manifest.entries()).map(([local, full]) => ({ local, full })).sort((a, b) => a.local.localeCompare(b.local));

  let filtered = all;
  if (args.grep) {
    const needle = args.grep.toLowerCase();
    filtered = all.filter((e) => e.local.toLowerCase().includes(needle) || e.full.toLowerCase().includes(needle));
  }

  console.log(`\n抓取成功 ${fetched} 个，失败 ${failed} 个；`);
  console.log(`共提取到 ${all.length} 个 CSS Module 本地名。`);
  if (args.grep) {
    console.log(`含 "${args.grep}" 的：${filtered.length} 个`);
    for (const e of filtered) console.log(`  ${e.local.padEnd(38)} → ${e.full}`);
  } else {
    for (const e of all.slice(0, 60)) console.log(`  ${e.local.padEnd(38)} → ${e.full}`);
    if (all.length > 60) console.log(`  …（还有 ${all.length - 60} 个，见 JSON）`);
  }

  const outPath = args.out ? resolve(args.out) : join(HERE, "evidence", `cssmod-${platform.id}-${Date.now()}.json`);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(
    outPath,
    `${JSON.stringify({ platform: platform.id, url: platform.url, fetched, failed, localNames: all, perAsset }, null, 2)}\n`,
    "utf-8",
  );
  console.log(`\n完整清单：${outPath}`);
  return 0;
}

main()
  .then((c) => process.exit(c))
  .catch((e) => {
    console.error("[ERROR] 提取器自身异常：", e);
    process.exit(2);
  });
