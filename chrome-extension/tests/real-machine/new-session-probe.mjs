/**
 * 「新对话」入口的**只读** DOM 结构探针。
 *
 * 背景：2026-11-11 第一版按 `button / a / [role=button]` 找入口，chatglm 上
 * 恒 0 命中（真身是 `div.new-session`）；随后一轮又发现千问的入口藏在
 * `opacity-0 / pointer-events-none` 的 hover-reveal 层里，元宝 / Kimi 干脆
 * 不用「新对话」这个措辞。⇒ 每加一个站之前，必须先看**真实结构**，不再猜。
 *
 * ## 红线（脚本级保证，不靠人记）
 *
 * - 只 `page.goto` + `page.evaluate` **读** DOM；不 click、不 type、不 send、
 *   不 hover、不绕过任何验证码 / 滑块 / 登录墙。
 * - 遇到登录墙 / 滑块只是如实记下来并跳过该站的结构推断，不做任何规避。
 * - 不导入 Pack、不连后台、不发 EXECUTE_PACK。
 *
 * ## 用法
 *
 *   CANDIDATES=kimi node tests/real-machine/new-session-probe.mjs
 *   CANDIDATES=qianwen,yuanbao,kimi,chatglm,yiyan \
 *     node tests/real-machine/new-session-probe.mjs
 *
 * 环境变量：CANDIDATES（逗号分隔，默认 5 个活跃站）、PROFILE、OUT。
 * 输出：`evidence/new-session-probe-<date>.<候选集 slug>.json`，
 * 覆盖已存在文件时会打印一行提示（复用 evidence-paths.mjs 的同一套口径）。
 */

import { chromium } from "playwright";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";

import { candidatesSlug, overwriteNotice } from "./evidence-paths.mjs";
import { getPlatform } from "../platforms.mjs";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const PROFILE =
  process.env.PROFILE ||
  `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const TODAY = new Date().toISOString().slice(0, 10);
const CANDIDATES = (
  process.env.CANDIDATES || "qianwen,yuanbao,chatglm,yiyan,kimi"
)
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const OUT =
  process.env.OUT ||
  `${EVIDENCE_DIR}/new-session-probe-${TODAY}.${candidatesSlug(CANDIDATES)}.json`;

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

/** 文案 / 语义类名候选。宁可多列，也不要凭印象写一个。 */
const NEEDLES = [
  "新对话", "新建对话", "新的对话", "开始新对话", "发起新对话", "开启新对话",
  "新建聊天", "新建会话", "新会话", "新建", "清空上下文", "清空会话",
  "New chat", "New Chat", "New conversation",
];
const CLASS_RE = /new[-_]?chat|new[-_]?session|new[-_]?dialog|newChat|create[-_]?conv|sidebar-new/i;
const COMPOSER =
  'textarea, div[contenteditable="true"], div[data-slate-editor="true"], [role="textbox"], [contenteditable="true"]';

/**
 * 在页面里跑的纯读取函数。写到字符串里交给 page.evaluate，
 * 避免闭包变量跨进程传递。
 */
function domScan({ needles, classReSource, messageSelectors = [], answerText = "" }) {
  const classRe = new RegExp(classReSource, "i");
  const short = (s, n = 160) => String(s || "").replace(/\s+/g, " ").slice(0, n);
  const ownText = (el) =>
    [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent)
      .join("")
      .trim();

  // 与生产 adapter-utils.js:96 的 isElementRendered 保持同一判据，
  // 否则「探到了」和「生产能点到」会对不上。
  const rendered = (el) => {
    if (!el || el === document.documentElement || el === document.body) return false;
    let node = el;
    while (node && node.nodeType === 1) {
      const st = window.getComputedStyle(node);
      if (st.display === "none") return false;
      if (st.visibility === "hidden" || st.visibility === "collapse") return false;
      if (st.opacity === "0") return false;
      node = node.parentElement;
    }
    return true;
  };

  const describe = (el) => {
    const r = el.getBoundingClientRect();
    const st = window.getComputedStyle(el);
    const chain = [];
    let p = el.parentElement;
    for (let i = 0; i < 6 && p; i += 1, p = p.parentElement) {
      chain.push({
        tag: p.tagName.toLowerCase(),
        cls: short(String(p.className || ""), 180),
        textLen: (p.textContent || "").trim().length,
      });
    }
    // 点谁最合理：最近的 button / [role=button] / a，或自身
    const clickable = el.closest('button, [role="button"], a');
    return {
      tag: el.tagName.toLowerCase(),
      cls: short(String(el.className || ""), 220),
      id: short(el.id || "", 80),
      ariaLabel: short(el.getAttribute("aria-label") || "", 80),
      title: short(el.getAttribute("title") || "", 80),
      testid: short(el.getAttribute("data-testid") || "", 80),
      role: short(el.getAttribute("role") || "", 40),
      ownText: short(ownText(el), 80),
      innerText: short(el.textContent, 80),
      rendered: rendered(el),
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      css: {
        display: st.display,
        visibility: st.visibility,
        opacity: st.opacity,
        pointerEvents: st.pointerEvents,
        cursor: st.cursor,
      },
      clickableAncestor: clickable
        ? { tag: clickable.tagName.toLowerCase(), cls: short(String(clickable.className || ""), 160), rendered: rendered(clickable) }
        : null,
      ancestors: chain,
      outerHTML: short(el.outerHTML, 400),
    };
  };

  const all = [...document.querySelectorAll("*")];
  const wanted = new Set(needles);

  // 1) 文案命中：自身文本或 aria/title/testid 精确等于/包含候选文案
  const textHits = [];
  for (const el of all) {
    const ot = ownText(el);
    const fields = [ot, el.getAttribute("aria-label") || "", el.getAttribute("title") || "", el.getAttribute("data-testid") || ""];
    const hit = fields.find((f) => f && (wanted.has(f.trim()) || ([...wanted].some((n) => f.trim() === n))));
    if (!hit) continue;
    // 只收「短文本」节点，避免把整页容器算成命中
    if ((el.textContent || "").trim().length > 40) continue;
    textHits.push({ needle: hit.trim(), ...describe(el) });
    if (textHits.length >= 40) break;
  }

  // 2) 语义类名命中：即使没有文案，也要看到结构（图标按钮常见）
  const classHits = [];
  for (const el of all) {
    const marker = `${el.className || ""} ${el.id || ""} ${el.getAttribute("data-testid") || ""}`;
    if (!classRe.test(marker)) continue;
    if ((el.textContent || "").trim().length > 3000) continue;
    classHits.push(describe(el));
    if (classHits.length >= 40) break;
  }

  // 3) 带标签的控件（button / [role=button] / a）
  const labeledControls = [];
  for (const el of document.querySelectorAll('button, [role="button"], a')) {
    const label = `${el.getAttribute("aria-label") || ""} ${el.getAttribute("title") || ""} ${ownText(el)}`;
    if (!classRe.test(label) && ![...wanted].some((n) => label.includes(n))) continue;
    labeledControls.push(describe(el));
    if (labeledControls.length >= 30) break;
  }

  // 消息容器契约：adapter 的 messageList 在真机上到底命中几个。
  // 2026-11-11 文心 L2 第 2 步超时 243.6s，但截图里 AI 明明答了 ——
  // 就是这里该给出的证据：哪个选择器 0 命中、真答案挂在什么容器里。
  const messageListHits = (messageSelectors || []).map((sel) => {
    const els = [...document.querySelectorAll(sel)];
    return {
      sel,
      count: els.length,
      samples: els.slice(0, 2).map((e) => short(e.outerHTML, 260)),
    };
  });

  // 顺着已知答案文本往上找祖先链，直接给出「新容器长什么样」。
  const answerChain = answerText
    ? (() => {
        const leaf = all.find(
          (el) => el.children.length === 0 && (el.textContent || "").includes(answerText),
        );
        if (!leaf) return null;
        const chain = [];
        let n = leaf;
        for (let i = 0; i < 7 && n; i += 1, n = n.parentElement) {
          chain.push({
            tag: n.tagName.toLowerCase(),
            cls: short(String(n.className || ""), 200),
            textLen: (n.textContent || "").trim().length,
          });
        }
        return chain;
      })()
    : null;

  return {
    bodyTextLen: (document.body?.innerText || "").length,
    messageListHits,
    answerChain,
    textHits,
    classHits,
    labeledControls,
    // 供人工核验：页面上所有短文本里带「新」字的，用来发现我们没列进 NEEDLES 的措辞
    novelPhrases: [...new Set(
      all.filter((el) => el.children.length === 0)
        .map((el) => ownText(el).trim())
        .filter((t) => t && t.length <= 12 && /新|对话|会话|chat/i.test(t)),
    )].slice(0, 40),
  };
}

async function main() {
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: null,
    args: ["--disable-blink-features=AutomationControlled"],
  });
  const report = {
    generatedAt: new Date().toISOString(),
    mode: "readonly-dom-probe",
    redlines: {
      clicks: false, typing: false, sending: false, hover: false,
      captchaBypass: false, packImported: false,
    },
    needles: NEEDLES,
    classRe: CLASS_RE.source,
    platforms: [],
  };

  try {
    for (const id of CANDIDATES) {
      const spec = getPlatform(id);
      if (!spec) {
        report.platforms.push({ platform: id, error: "未在 platforms.mjs 登记" });
        continue;
      }
      const page = await context.newPage();
      const row = { platform: id, url: spec.url };
      try {
        await page.goto(spec.url, { waitUntil: "domcontentloaded", timeout: 45000 });
        await page.waitForTimeout(4000);
        row.finalUrl = page.url();
        row.title = await page.title().catch(() => "");
        row.composerVisible = await page.locator(COMPOSER).first().isVisible({ timeout: 2000 }).catch(() => false);
        row.looksLikeLogin = /log[_-]?in|sign[_-]?in|passport|auth|登录|扫码|verify|滑块|captcha/i.test(
          `${row.finalUrl} ${row.title}`,
        );
        const adapter = await import(`../../src/platforms/${spec.module}`)
          .then((m) => m.SELECTORS)
          .catch(() => ({}));
        row.adapterNewChat = adapter?.newChat ?? null;
        row.adapterMessageList = adapter?.messageList ?? [];
        Object.assign(row, await page.evaluate(domScan, {
          needles: NEEDLES,
          classReSource: CLASS_RE.source,
          messageSelectors: row.adapterMessageList,
          // 上一轮 L2 在文心留下的回答开头，用来定位新的答案容器；
          // 别的站没有这句也不会报错（answerChain 为 null）。
          answerText: process.env.ANSWER_TEXT || "",
        }));
        log(
          id,
          `textHits=${row.textHits?.length} classHits=${row.classHits?.length} ` +
            `labeled=${row.labeledControls?.length} composer=${row.composerVisible} login=${row.looksLikeLogin}`,
        );
      } catch (e) {
        row.error = e.message.slice(0, 200);
        log(id, "ERROR", row.error);
      } finally {
        await page.close().catch(() => {});
      }
      report.platforms.push(row);
    }
  } finally {
    await context.close().catch(() => {});
  }

  mkdirSync(dirname(OUT), { recursive: true });
  const notice = overwriteNotice(OUT);
  if (notice) log("⚠️", notice, "—— 旧文件将被覆盖，若要保留请改用 OUT=...");
  writeFileSync(OUT, JSON.stringify(report, null, 2));
  log("只读探测结果已写:", OUT);
  log("DONE（全程未点击、未发送、未绕验证码）");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
