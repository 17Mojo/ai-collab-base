/**
 * 正文长度对账探针（回答 N57：视口外的正文到底在不在 DOM 里）
 *
 * ## 要回答的问题
 *
 * 2026-11-18 用户现场指出：DeepSeek 长回答的右下角、压在最后一行、紧贴输入框上沿，
 * 会出现一个**白底圆形 + 下尖角**的小按钮；「长文输出时会出现，生成文字内容无法直接
 * 识别，需点击后才能识别全部生成内容」。
 *
 * 这句话有两种完全不同的含义，对 pipeline 的影响也相反：
 *
 *   A. **视图层折叠/滚动**：全文早就在 DOM 里，只是视口没滚到底。
 *      ⇒ `_extractContent` 走 `el.textContent`，不依赖滚动位置、对 CSS 裁切免疫 ⇒ **无影响**。
 *   B. **DOM 缺段（懒渲染）**：只有可见段落挂进了 DOM。
 *      ⇒ `textContent` 同样拿不到，而 50 字闸门照常放行 ⇒ **静默交付半截内容**（N14 同类）。
 *
 * 已知的间接证据只够支持 A（fix1 回执 1049 字 vs 截图止于第 878 字，多出的 171 字在 DOM 里），
 * 但**没有反证 B**——所以要一次能证伪的实测。
 *
 * ## 判据（先写死，避免看到数字再解释）
 *
 * 对同一个会话，取每条 AI 回复的 `[class*="ds-assistant-message-main-content"]`：
 *
 *   - `clicked=false` 与 `clicked=true` 两轮的 `textContent.length` 与 `childElementCount`
 *     **都不变** ⇒ 判据 A 成立（视口外文字在 DOM 里，点击只是滚动/展开视图）；
 *   - 点击后**变多** ⇒ 判据 B 成立，必须加「先展开再取」，且这是 P1。
 *
 * 另外把每条回复的末 40 字一起写进回执：可以直接与 L2 回执里的 `final_content` 尾部对账，
 * 看抽取有没有少一截。
 *
 * ## 硬红线
 *
 * 只读会话内容：**不发消息、不导入 Pack、不触发发送/生成控件**。
 * `CLICK_CONV` 是导航型点击（点侧栏历史条目进会话页）；`EXPAND_CLICK=1` 是唯一的
 * 非导航点击，只允许点在「视口右下、尺寸 20–48px、含 svg、且在输入区上方」的元素上——
 * 逐条闸门见 `pickChevron`，任何一条不满足就拒绝点击并如实报告 `clicked:false`。
 *
 * 冻结站（deepseek / longcat）跑本脚本**需要用户明确放行**：输出里的
 * `policy.unfrozenBy` 必须写清是谁在哪天放行的，便于从磁盘复核。
 *
 * ## 用法
 *
 *   URL='https://chat.deepseek.com/' \
 *   CLICK_CONV='text=最贵AI协作工具链子' \
 *   EXPAND_CLICK=1 \
 *   OUT=.../evidence/deepseek-text-length-2026-11-18.json \
 *   node tests/real-machine/text-length-probe.mjs
 *
 * 环境变量：
 *   URL          目标页（默认 https://chat.deepseek.com/）
 *   CLICK_CONV   可选，导航型点击（进会话），Playwright selector
 *   MEASURE_SEL  测量选择器，默认 `[class*="ds-assistant-message-main-content"]`
 *   EXPAND_CLICK =1 时尝试点击右下角圆形 chevron 并二次测量
 *   OUT / SHOT   回执与截图路径
 *   PROFILE      持久 profile（默认与 l2-platform-auto.mjs 一致）
 *   WAIT         页面加载后等待毫秒（默认 6000）
 *   UNFROZEN_BY  放行留痕（默认 "user-approved-2026-11-18-chevron-probe"）
 */

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const PROFILE =
  process.env.PROFILE || `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const URL_ARG = process.env.URL || "https://chat.deepseek.com/";
const CLICK_CONV = process.env.CLICK_CONV || "";
const MEASURE_SEL = process.env.MEASURE_SEL || '[class*="ds-assistant-message-main-content"]';
const EXPAND_CLICK = process.env.EXPAND_CLICK === "1";
const SCROLL_TO_TOP = process.env.SCROLL_TO_TOP === "1";
const WAIT = Number(process.env.WAIT || 6000);
const UNFROZEN_BY = process.env.UNFROZEN_BY || "user-approved-2026-11-18-chevron-probe";
const STAMP = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const OUT = process.env.OUT || `${EVIDENCE_DIR}/text-length-probe-${STAMP}.json`;
const SHOT = process.env.SHOT || OUT.replace(/\.json$/, ".png");

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

/**
 * 在页面里测量所有命中元素。返回长度、子节点数、末 40 字与容器几何。
 * @param {import("playwright").Page} page
 */
async function measure(page) {
  return page.evaluate((sel) => {
    const els = [...document.querySelectorAll(sel)];
    return {
      count: els.length,
      items: els.map((el) => {
        const text = el.textContent || "";
        const rect = el.getBoundingClientRect();
        return {
          textLength: text.length,
          innerTextLength: (el.innerText || "").length,
          childElementCount: el.childElementCount,
          paragraphCount: el.querySelectorAll("p").length,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          rect: {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            w: Math.round(rect.width),
            h: Math.round(rect.height),
          },
          tail: text.trim().slice(-40),
          head: text.trim().slice(0, 30),
        };
      }),
      // 输入区上沿：点击闸门要用它判断「别点到输入框」
      composerTop: (() => {
        const c = document.querySelector("textarea");
        return c ? Math.round(c.getBoundingClientRect().top) : null;
      })(),
      viewport: { w: window.innerWidth, h: window.innerHeight },
    };
  }, MEASURE_SEL);
}

/**
 * 找「视口右下角的圆形 chevron 按钮」候选，并逐条过闸。
 *
 * 闸门（少一条都不点）：
 *   1. 尺寸 20–48px 的近方形；
 *   2. 含 svg（图标按钮，不是文字块）；
 *   3. 落在视口右下象限（right 的 70% 之后、bottom 的 50% 之后）；
 *   4. 整个盒子在输入区上沿之上（防止点到发送/输入区）；
 *   5. 圆角 ≥ 尺寸的 40%（圆形，而不是方形卡片）。
 */
async function pickChevron(page) {
  return page.evaluate(() => {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const ta = document.querySelector("textarea");
    const composerTop = ta ? ta.getBoundingClientRect().top : vh;
    const out = [];
    for (const el of document.querySelectorAll("div,button,[role=button]")) {
      const r = el.getBoundingClientRect();
      if (r.width < 20 || r.width > 48 || r.height < 20 || r.height > 48) continue;
      if (Math.abs(r.width - r.height) > 6) continue;
      if (!el.querySelector("svg")) continue;
      if (r.left < vw * 0.7 || r.top < vh * 0.5) continue;
      if (r.bottom > composerTop) continue;
      const cs = getComputedStyle(el);
      const radius = parseFloat(cs.borderRadius) || 0;
      const round = radius >= r.width * 0.4 || cs.borderRadius.includes("50%");
      if (!round) continue;
      out.push({
        x: Math.round(r.x + r.width / 2),
        y: Math.round(r.y + r.height / 2),
        w: Math.round(r.width),
        h: Math.round(r.height),
        radius,
        cls: (el.className || "").toString().slice(0, 120),
        aria: el.getAttribute("aria-label") || "",
        tag: el.tagName,
        svgPaths: el.querySelectorAll("svg path, svg use").length,
        html: el.outerHTML.slice(0, 300),
        composerTop: Math.round(composerTop),
      });
    }
    // 越靠右下越像「回到底部」按钮
    out.sort((a, b) => b.y + b.x - (a.y + a.x));
    return out;
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  mkdirSync(dirname(OUT), { recursive: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: null,
    args: ["--no-first-run", "--no-default-browser-check"],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const receipt = {
    probe: "text-length-probe",
    purpose: "N57：长回答视口外的正文是否在 DOM 里（证伪 A/B）",
    startedAt: new Date().toISOString(),
    policy: { frozenPlatform: true, unfrozenBy: UNFROZEN_BY },
    config: { url: URL_ARG, clickConv: CLICK_CONV || null, measureSel: MEASURE_SEL, expandClick: EXPAND_CLICK },
  };

  try {
    await page.goto(URL_ARG, { waitUntil: "domcontentloaded", timeout: 60000 });
    await sleep(WAIT);

    if (CLICK_CONV) {
      log("导航型点击进会话:", CLICK_CONV);
      await page.click(CLICK_CONV, { timeout: 15000 });
      await sleep(WAIT);
    }

    receipt.before = await measure(page);
    log(`点前：命中 ${receipt.before.count} 条，长度 ${receipt.before.items.map((i) => i.textLength).join(" / ")}`);
    await page.screenshot({ path: SHOT.replace(/\.png$/, ".before.png"), fullPage: false });

    // 那个圆形 chevron 的语义还没定：若它是「回到底部」，就得先把滚动位置挪开它才会出现。
    // 滚到顶不改 DOM 文本，改的只是视口 —— 正好用来区分「视图层」与「DOM 缺段」。
    if (SCROLL_TO_TOP) {
      const scrolled = await page.evaluate(() => {
        const el = [...document.querySelectorAll("div")]
          .filter((d) => d.scrollHeight - d.clientHeight > 200 && d.clientHeight > 300)
          .sort((a, b) => b.clientHeight - a.clientHeight)[0];
        if (!el) return null;
        const before = el.scrollTop;
        el.scrollTop = 0;
        return { cls: (el.className || "").toString().slice(0, 80), before, after: el.scrollTop, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight };
      });
      receipt.scrollToTop = scrolled;
      log("滚到顶:", JSON.stringify(scrolled));
      await sleep(1200);
      receipt.afterScroll = await measure(page);
      log(`滚动后长度 ${receipt.afterScroll.items.map((i) => i.textLength).join(" / ")}（应与点前相同）`);
      await page.screenshot({ path: SHOT.replace(/\.png$/, ".scrolled-top.png"), fullPage: false });
    }

    const cands = await pickChevron(page);
    receipt.chevronCandidates = cands;
    log(`右下角圆形候选 ${cands.length} 个`);

    if (EXPAND_CLICK && cands.length > 0) {
      const t = cands[0];
      log(`点击候选：(${t.x},${t.y}) ${t.w}×${t.h} radius=${t.radius} aria=${t.aria || "-"}`);
      await page.mouse.click(t.x, t.y);
      await sleep(1500);
      receipt.clicked = true;
      receipt.clickedTarget = t;
      receipt.after = await measure(page);
      log(`点后：长度 ${receipt.after.items.map((i) => i.textLength).join(" / ")}`);
      await page.screenshot({ path: SHOT.replace(/\.png$/, ".after.png"), fullPage: false });
    } else {
      receipt.clicked = false;
      receipt.after = null;
      if (EXPAND_CLICK && cands.length === 0) receipt.note = "要点击但没找到过闸的圆形候选，未点击";
    }

    // 判据落地：只比「计数与长度」，不比肉眼
    if (receipt.after) {
      const b = receipt.before.items.map((i) => [i.textLength, i.childElementCount]);
      const a = receipt.after.items.map((i) => [i.textLength, i.childElementCount]);
      receipt.verdict = {
        unchanged: JSON.stringify(b) === JSON.stringify(a),
        beforePairs: b,
        afterPairs: a,
        conclusion: JSON.stringify(b) === JSON.stringify(a)
          ? "A：视口外正文在 DOM 里，点击只影响视图（textContent 取数不受影响）"
          : "B：点击后 DOM 变多 ⇒ 存在懒渲染缺段，抽取必须「先展开再取」",
      };
    }
  } catch (e) {
    receipt.error = String(e && e.message ? e.message : e);
    log("FAIL:", receipt.error);
  } finally {
    receipt.finishedAt = new Date().toISOString();
    writeFileSync(OUT, JSON.stringify(receipt, null, 2));
    log("回执已写:", OUT);
    await ctx.close();
  }
}

main().catch((e) => {
  console.error("FATAL:", e);
  process.exit(1);
});
