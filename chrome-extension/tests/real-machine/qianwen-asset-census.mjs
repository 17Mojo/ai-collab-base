/**
 * 千问站点资产普查（asset census）
 *
 * ## 它解决什么问题
 *
 * B-3（定千问的消息选择器）卡住的原因是**没有证据**：
 *
 *   - 落地页上没有会话 ⇒ 没有消息气泡 ⇒ 落地页快照既证不了选择器对，
 *     也证不了选择器错；
 *   - 而千问自己的选择器（.response-content / .prose / [class*="chat-item"]
 *     / .typing-indicator）**在千问自己的静态资源里一次都没出现过**——
 *     也就是说它们是照着别的站点抄来的，在千问上永远命中 0 个。
 *
 * 这个工具把「站点到底有哪些类名」变成**可复算的事实**：
 * 抓站点自己的 JS+CSS，做全量字符串普查，产出两份清单：
 *
 *   1. **站点自己声明的**类名（CSS 规则里的选择器 + JS 里的 className 字面量）
 *      —— 这是「真实结构」的事实来源；
 *   2. **生产 adapter 用到的**类名在站点产物里的出现次数
 *      —— 这是「生产选择器是不是抄来的」的事实来源。
 *
 * ## 为什么用「产出清单」而不是「采集快照」
 *
 * 采集真会话需要已登录的浏览器 profile（那是 L2 真机会话的事）。
 * 而站点的**产物本身**就是权威的结构说明：站点自己的 CSS 用后代选择器
 * 写死了 DOM 层级，自己的 React 代码给出确切的 class 字符串，
 * 自己的文本选择功能还直接声明了「哪张卡是答案、哪张卡是问题」。
 *
 * ## 硬红线
 *
 * 只读。只 GET 页面自己的静态资源，**不注入、不点击、不发送**。
 *
 * ## 用法
 *
 *   node tests/real-machine/qianwen-asset-census.mjs
 *   node tests/real-machine/qianwen-asset-census.mjs --out=evidence/qianwen-census.json
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import { getPlatform } from "../platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 生产 adapter 的六组选择器里，**类名/属性值**部分。
 *
 * 这里刻意写死字面量，而不是 import 生产 adapter：
 * 普查的用途正是回答「生产选择器在站点上存不存在」，
 * 如果直接 import 生产代码，生产选择器一改这份清单就跟着变，
 * 普查就变成了自说自话。
 */
const PRODUCTION_TOKENS = [
  // 旧的 messageList
  "response-content",
  "chat-item",
  "message",
  // 旧的 messageContent
  "prose",
  "message-content",
  "content",
  // 旧的 typingIndicator
  "loading",
  "generating",
  "typing-indicator",
  // 新的（2026-10-25 B-3 引入）
  "answer-text",
  "md-text-card",
  "answer-common-card",
  "answer-receiving-card",
  "qk-markdown",
  "qk-md-text",
  "markdown-content",
  "data-chat-answers-wrap",
  "data-chat-question-wrap",
  "data-session-switch-target",
  "stopAnswer",
  "sendMessage",
];

/**
 * 抓取站点页面，把所有 JS/CSS 资源拉下来。
 *
 * **只扫 <script src> / <link href> 是不够的**：千问的会话渲染代码
 * （web/js/async/6605.js）不是以标签形式出现的，是 webpack 运行时
 * 动态加载的 chunk。2026-10-25 第一次跑这个普查时只扫标签，
 * 结果「answer-text」「md-text-card」「answer-receiving-card」
 * 全部显示 0 次——那不是它们不存在，是**根本没被抓到**。
 * 所以这里同时监听网络响应，把动态 chunk 一并收进来。
 *
 * @param {import('playwright').BrowserContext} ctx
 * @param {import('playwright').Page} page
 * @returns {Promise<{urls: string[], texts: Map<string, string>}>}
 */
async function collectAssets(ctx, page) {
  const seen = new Set();

  page.on("response", (res) => {
    const url = res.url();
    if (/\.m?js(\?|$)|\.css(\?|$)/.test(url)) seen.add(url);
  });

  await page.goto("https://www.qianwen.com/", { waitUntil: "domcontentloaded", timeout: 30000 });
  // 等动态 chunk 加载完（会话渲染代码是懒加载的）
  await page.waitForTimeout(8000);

  const tagged = await page.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll("script[src]")).map((s) => s.src);
    const links = Array.from(document.querySelectorAll("link[href]")).map((l) => l.href);
    return [...scripts, ...links].filter((u) => /\.m?js(\?|$)|\.css(\?|$)/.test(u));
  });
  for (const u of tagged) seen.add(u);

  const texts = new Map();
  for (const url of seen) {
    try {
      const res = await ctx.request.get(url, { timeout: 20000 });
      if (!res.ok()) continue;
      texts.set(url, await res.text());
    } catch {
      /* 单个资源抓不到不影响普查结论 */
    }
  }
  return { urls: [...seen], texts };
}

/**
 * 从 CSS 文本里抽出类选择器里的类名。
 * @param {string} css
 * @returns {Set<string>}
 */
function classNamesFromCss(css) {
  const out = new Set();
  for (const m of css.matchAll(/\.(-?[_A-Za-z][\w-]*)/g)) out.add(m[1]);
  return out;
}

/**
 * 从 JS 文本里抽出 className 字面量。
 * @param {string} js
 * @returns {Set<string>}
 */
function classNamesFromJs(js) {
  const out = new Set();
  // className: "a b c" / className: `a b ${x}` / "a b c"
  for (const m of js.matchAll(/className\s*:\s*"([^"]{1,200})"/g)) {
    for (const c of m[1].split(/\s+/)) if (c && !c.includes("$")) out.add(c);
  }
  // CSS Modules 的本地名映射：{"localName":"localName-hash"}
  for (const m of js.matchAll(/"([A-Za-z_][\w-]{1,60})"\s*:\s*"([A-Za-z_][\w-]{1,80})"/g)) {
    if (m[2].startsWith(m[1]) && m[2].length > m[1].length) out.add(m[1]);
  }
  return out;
}

function parseArgs(argv) {
  const args = { out: null, locale: "zh-CN", channel: "chrome" };
  for (const raw of argv) {
    if (raw.startsWith("--out=")) args.out = raw.slice("--out=".length).trim();
    else if (raw.startsWith("--locale=")) args.locale = raw.slice("--locale=".length);
    else if (raw.startsWith("--channel=")) args.channel = raw.slice("--channel=".length);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const platform = getPlatform("qianwen");
  if (!platform) {
    console.error("平台登记表里没有 qianwen");
    return 2;
  }

  const browser = await chromium.launch({ channel: args.channel, headless: true });
  const context = await browser.newContext({ locale: args.locale, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const { urls, texts } = await collectAssets(context, page);

  // 站点自己的类名清单
  const siteClassNames = new Set();
  let totalBytes = 0;
  for (const text of texts.values()) {
    totalBytes += text.length;
    for (const c of classNamesFromCss(text)) siteClassNames.add(c);
    for (const c of classNamesFromJs(text)) siteClassNames.add(c);
  }

  // 生产 adapter 的每个 token 在站点产物里出现多少次
  //
  // **两个数都要看**：
  //   - rawStringCount：字符串层面出现几次。它会被无关上下文污染——
  //     'response-content' 出现 2 次，但那是下载 URL 的查询参数
  //     '?response-content-disposition='；'prose' 出现 5 次，但那是
  //     Tailwind 的 'max-w: prose' 与 prosemirror-* 库。
  //   - isClassName：它**是不是站点真的用的类名**。这才是选择器能不能
  //     命中的判据。
  const tokenCounts = {};
  for (const token of PRODUCTION_TOKENS) {
    let count = 0;
    const perAsset = {};
    for (const [url, text] of texts) {
      let c = 0;
      let i = -1;
      while ((i = text.indexOf(token, i + 1)) !== -1) c += 1;
      if (c > 0) {
        perAsset[url.split("/").pop()] = c;
        count += c;
      }
    }
    tokenCounts[token] = {
      rawStringCount: count,
      isClassName: siteClassNames.has(token),
      perAsset,
    };
  }

  await browser.close();
  await context.close().catch(() => {});

  const report = {
    platform: "qianwen",
    url: platform.url,
    capturedAt: new Date().toISOString(),
    method: "read-only fetch of the site's own JS/CSS assets; no input, no click, no message sent",
    assetCount: texts.size,
    assetUrls: urls,
    totalBytes,
    siteClassNameCount: siteClassNames.size,
    siteClassNames: [...siteClassNames].sort(),
    productionTokenCounts: tokenCounts,
  };

  const outPath = args.out ? resolve(args.out) : join(HERE, "evidence", "qianwen-asset-census.json");
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, "utf-8");

  console.log(`资源 ${texts.size} 个 / ${totalBytes} 字节；站点类名 ${siteClassNames.size} 个`);
  console.log(`\n生产 adapter 的 token：`);
  console.log(`  ${"token".padEnd(26)} 字符串次数  是站点类名?`);
  for (const [token, info] of Object.entries(tokenCounts)) {
    console.log(
      `  ${token.padEnd(26)} ${String(info.rawStringCount).padStart(6)}    ` +
        (info.isClassName ? "✓ 是" : "✗ 不是"),
    );
  }
  console.log(`\n清单：${outPath}`);
  return 0;
}

main()
  .then((c) => process.exit(c))
  .catch((e) => {
    console.error("[ERROR] 普查自身异常：", e);
    process.exit(2);
  });
