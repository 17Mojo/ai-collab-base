/**
 * 选择器侦察器
 *
 * ## 它解决什么问题
 *
 * B-3（定千问的消息选择器）卡住的原因是：**没有证据**。
 * 千问的 `messageList` 三条选择器在落地页上全部命中 0 个——
 * 落地页上没有会话，所以既证不了「选择器对」，也证不了「选择器错」。
 *
 * 与其猜，不如**量**。这个工具把真机页面的 DOM 结构扫一遍，
 * 回答三个问题：
 *   1. 页面上到底有没有「像消息气泡」的容器？（有 → 候选；没有 → 落地页证不了）
 *   2. 有的话，它们长什么样（类名、层级、文本长度、兄弟数）？
 *   3. 现有的宽松选择器（如 `[class*="message"]`）会误命中什么？
 *
 * 第 3 问是关键：它能**当场证伪**一条宽松选择器，
 * 而不用等到有人真的发一条消息才发现计数被撑大。
 *
 * ## 硬红线
 *
 * 只读。不注入文本、不点发送、不改页面结构。
 *
 * ## 用法
 *
 *   node tests/real-machine/selector-scout.mjs --platform=qianwen
 *   node tests/real-machine/selector-scout.mjs --platform=qianwen --locale=en-US
 *   node tests/real-machine/selector-scout.mjs --all
 *
 *   # 顺带把某个容器（按类名子串找）的子树打出来，看它内部结构
 *   node tests/real-machine/selector-scout.mjs --platform=qianwen --root=chatRoom
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import { PLATFORMS, getPlatform } from "../platforms.mjs";
import { injectAdapter } from "./_bundle.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 页面里做一次结构扫描。
 *
 * 扫的判据刻意不依赖「类名里有没有 message」——
 * 那正是我们要检验的东西，不能拿它当前提。
 *
 * 「像气泡」的判据是**结构**上的：
 *   - 有非空文本（气泡必有内容）
 *   - 不是 body/html（那是壳）
 *   - 不是输入框的祖先链上的东西（那是输入区）
 *   - 有兄弟（气泡是列表里的一项）
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId
 * @param {string|null} rootQuery 类名子串；给定则额外抓该容器的子树
 */
async function scoutPage(page, platformId, rootQuery = null) {
  return page.evaluate(({ adapterId, rootQuery }) => {
    const registry = window.__PROBE_ADAPTERS__ || {};
    const mod = registry[adapterId];
    if (!mod || !mod.default) return { error: "adapter bundle 未注入页面" };

    let adapter;
    try {
      adapter = new mod.default();
    } catch (e) {
      return { error: `adapter 实例化失败：${e.message}` };
    }

    // 输入区：输入框及其祖先链——这些不算「气泡」
    const composerZone = new Set();
    let input = null;
    try {
      input = adapter.getChatInput();
    } catch (e) {
      input = null;
    }
    if (input) {
      let el = input;
      for (let i = 0; i < 6 && el; i += 1) {
        composerZone.add(el);
        el = el.parentElement;
      }
    }

    const all = Array.from(document.querySelectorAll("*"));
    const candidates = [];

    for (const el of all) {
      const tag = el.tagName.toLowerCase();
      if (tag === "html" || tag === "body" || tag === "head") continue;
      if (composerZone.has(el)) continue;

      const text = (el.innerText || el.textContent || "").trim();
      const textLength = text.length;
      const childCount = el.children.length;
      const className = typeof el.className === "string" ? el.className : "";
      const id = el.id || "";

      // 「像气泡」的结构判据
      const looksLikeBubble =
        textLength > 0 &&
        textLength < 4000 &&
        childCount > 0 &&
        el.parentElement !== null &&
        el.parentElement.children.length > 1;

      candidates.push({
        tag,
        id,
        className,
        textLength,
        text: text.slice(0, 160),
        childCount,
        siblingCount: el.parentElement ? el.parentElement.children.length : 0,
        depth: (() => {
          let d = 0;
          let p = el;
          while (p && p !== document.body) {
            d += 1;
            p = p.parentElement;
          }
          return d;
        })(),
        looksLikeBubble,
        parentClass:
          el.parentElement && typeof el.parentElement.className === "string"
            ? el.parentElement.className
            : "",
        outerHTML: (el.outerHTML || "").slice(0, 600),
      });
    }

    // 现有的宽松选择器会命中什么
    const looseChecks = {};
    for (const sel of ['[class*="message"]', '[class*="chat"]', '[class*="content"]', '[class*="item"]', '[class*="role"]']) {
      let hits = [];
      try {
        hits = Array.from(document.querySelectorAll(sel));
      } catch (e) {
        looseChecks[sel] = { error: e.message };
        continue;
      }
      looseChecks[sel] = {
        count: hits.length,
        samples: hits.slice(0, 6).map((el) => ({
          tag: el.tagName.toLowerCase(),
          className: typeof el.className === "string" ? el.className : "",
          textLength: (el.innerText || el.textContent || "").trim().length,
          childCount: el.children.length,
        })),
      };
    }

    const bubbles = candidates.filter((c) => c.looksLikeBubble);

    // 指定容器子树：看它内部结构（对话区 / 消息区长什么样）
    let subtree = null;
    if (rootQuery) {
      const rootEl = Array.from(document.querySelectorAll("*")).find((el) => {
        const cn = typeof el.className === "string" ? el.className : "";
        return cn.split(/\s+/).some((c) => c.includes(rootQuery));
      });
      if (!rootEl) {
        subtree = { error: `没找到类名含 "${rootQuery}" 的元素` };
      } else {
        const walk = (el, depth) => {
          if (depth > 6) return [];
          const cn = typeof el.className === "string" ? el.className : "";
          const text = (el.innerText || el.textContent || "").trim();
          const node = {
            tag: el.tagName.toLowerCase(),
            className: cn,
            id: el.id || "",
            depth,
            textLength: text.length,
            childCount: el.children.length,
            children: [],
          };
          for (const c of el.children) {
            node.children.push(...walk(c, depth + 1));
          }
          return [node];
        };
        subtree = {
          error: null,
          rootClass: typeof rootEl.className === "string" ? rootEl.className : "",
          rootTextLength: (rootEl.innerText || "").trim().length,
          tree: walk(rootEl, 0),
        };
      }
    }

    return {
      error: null,
      totalElements: all.length,
      bubbleCandidates: bubbles.slice(0, 40),
      bubbleCandidateCount: bubbles.length,
      subtree,
      // 父容器里「有一堆结构相似的孩子」的容器——对话区通常长这样
      repeatedChildren: (() => {
        const groups = new Map();
        for (const el of all) {
          if (el.children.length < 2) continue;
          const childClasses = Array.from(el.children).map(
            (c) => (typeof c.className === "string" ? c.className : "").split(/\s+/)[0],
          );
          const uniq = new Set(childClasses.filter(Boolean));
          if (uniq.size !== 1 || childClasses.length < 2) continue;
          const key = `${el.tagName.toLowerCase()}.${childClasses[0]}`;
          const g = groups.get(key) || { key, count: 0, parentClass: "", sample: "" };
          g.count += 1;
          g.parentClass = typeof el.className === "string" ? el.className : "";
          if (!g.sample) g.sample = (el.outerHTML || "").slice(0, 400);
          groups.set(key, g);
        }
        return Array.from(groups.values()).sort((a, b) => b.count - a.count).slice(0, 15);
      })(),
      looseChecks,
    };
  }, { adapterId: platformId, rootQuery });
}

function parseArgs(argv) {
  const args = { platform: null, all: false, locale: "zh-CN", channel: "chrome", out: null, root: null };
  for (const raw of argv) {
    if (raw.startsWith("--platform=")) args.platform = raw.slice("--platform=".length).trim();
    else if (raw.startsWith("--locale=")) args.locale = raw.slice("--locale=".length);
    else if (raw.startsWith("--channel=")) args.channel = raw.slice("--channel=".length);
    else if (raw.startsWith("--out=")) args.out = raw.slice("--out=".length);
    else if (raw.startsWith("--root=")) args.root = raw.slice("--root=".length).trim();
    else if (raw === "--all") args.all = true;
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targets = args.all ? PLATFORMS : [getPlatform(args.platform)];
  if (!targets[0]) {
    console.error(`未知平台 ${args.platform}。可选：${PLATFORMS.map((p) => p.id).join(", ")}`);
    return 2;
  }

  const browser = await chromium.launch({ channel: args.channel, headless: true });
  const report = [];

  for (const p of targets) {
    const context = await browser.newContext({ locale: args.locale, viewport: { width: 1440, height: 900 } });
    try {
      await injectAdapter(context, `src/platforms/${p.module}`, p.id);
      const page = await context.newPage();
      await page.goto(p.url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(3000);
      try {
        await page.waitForLoadState("networkidle", { timeout: 8000 });
      } catch {
        /* networkidle 超时不算失败 */
      }
      await page.waitForTimeout(2000);

      const r = await scoutPage(page, p.id, args.root);
      r.platform = p.id;
      r.platformName = p.name;
      r.url = p.url;
      r.locale = args.locale;
      report.push(r);

      console.log(`\n=== ${p.name}（${p.id}）===`);
      if (r.error) {
        console.log(`  错误：${r.error}`);
        continue;
      }
      console.log(`  页面元素总数：${r.totalElements}`);
      console.log(`  「像气泡」的候选数：${r.bubbleCandidateCount}`);
      console.log(`  「结构重复的孩子」容器（前 5）：`);
      for (const g of r.repeatedChildren.slice(0, 5)) {
        console.log(`    - ${g.key} × ${g.count}  父类名="${g.parentClass.slice(0, 60)}"`);
      }
      console.log(`  宽松选择器实测：`);
      for (const [sel, v] of Object.entries(r.looseChecks)) {
        if (v.error) {
          console.log(`    - ${sel} → 选择器非法`);
          continue;
        }
        const withText = (v.samples || []).filter((s) => s.textLength > 0).length;
        console.log(
          `    - ${sel.padEnd(22)} 命中 ${String(v.count).padStart(4)} 个` +
            `（前 ${(v.samples || []).length} 个里有 ${withText} 个带文本）`,
        );
      }
      if (r.subtree) {
        console.log(`  子树（root=${args.root}）：`);
        if (r.subtree.error) {
          console.log(`    - ${r.subtree.error}`);
        } else {
          const print = (nodes) => {
            for (const n of nodes) {
              const cn = (n.className || "(无类)").slice(0, 58);
              console.log(
                `    ${"  ".repeat(n.depth)}${n.tag}.${cn} ` +
                  `[txt=${n.textLength} kid=${n.childCount}]`,
              );
              print(n.children);
            }
          };
          print(r.subtree.tree);
        }
      }
    } finally {
      await context.close();
    }
  }

  await browser.close();

  const outPath = args.out ? resolve(args.out) : join(HERE, "evidence", `scout-${Date.now()}.json`);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, "utf-8");
  console.log(`\n完整报告：${outPath}`);
  return 0;
}

main()
  .then((c) => process.exit(c))
  .catch((e) => {
    console.error("[ERROR] 侦察器自身异常：", e);
    process.exit(2);
  });
