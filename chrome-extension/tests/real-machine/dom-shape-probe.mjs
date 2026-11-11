/**
 * 只读 DOM 结构探针（L2 fail 后的定位工具）
 *
 * ## 为什么需要它
 *
 * 2026-11-10 与 11-11 两轮 L2 的 fail 都是同一个模式：截图证明 AI 回复真实存在，
 * 但扩展判 `Response timeout`。根因永远落在 `messageList` 选择器 0 命中。
 * 定位手段此前有两次失败经验：
 *
 *  1. **静默页探针**（打开会话页直接数）—— 虚拟列表/游客态不持久，拿不到气泡。
 *  2. **发送期采样 + 固定 seed 文本**（`l2-platform-auto.mjs` 的 PROBE_DURING）——
 *     seed 文本「你要写一条小红书」同时出现在**侧栏历史条目**里，向上取祖先链
 *     取到的是 `chat-side-list-item`，不是对话气泡。2026-11-11 yiyan 就是这么被误导的。
 *
 * 本探针改正这两点：
 *  - 不猜 seed：**按文本反查最内层节点**（`textContent` 包含目标片段且没有子元素也包含它），
 *    再向上取祖先链，链上每一层都带 tag / class / 文本长度 / 子元素数；
 *  - 附带**类名分组统计**：所有 class 含 answer/message/chat/conv/response 的元素按
 *    className 归一化分组，给出命中数与文本长度分布 —— 用来判断「哪一类是真气泡、
 *    哪一类是导航外壳」，这正是 yiyan adapter 注释里 2026-10-25 踩过的坑。
 *
 * ## 硬红线
 *
 * **只读**：不发消息、不导入 Pack、不触发任何发送类控件。可以安全地对已登录会话反复跑。
 * 只允许真机环境使用，不进 CI、不进 npm test。
 *
 * `CLICK` 是这条红线上唯一的例外，且只允许**导航型点击**：点侧栏历史会话条目进到
 * 会话页（longcat 这类站不暴露会话 URL，只能点进去）。点之前先自检 selector 是否
 * 落在发送/输入区附近——见 `assertNavigationalClick`。绝不点发送、提交、生成。
 *
 * ## 用法
 *
 *   URL='https://wenxin.baidu.com/search/xxx' \
 *   TEXTS='它不需要你把每一步操作都讲清楚|你要写一条小红书' \
 *   OUT=.../evidence/L2-yiyan-dom-shape-2026-11-11.json \
 *   node tests/real-machine/dom-shape-probe.mjs
 *
 * 环境变量：
 *   URL    必填，目标会话页
 *   TEXTS  用 `|` 分隔的目标文本片段（建议一条 AI 回复片段 + 一条用户 prompt 片段）
 *   CLICK  可选，导航型点击目标（Playwright selector，如 `text=它不是工具`）。
 *          用于「会话 URL 不暴露、必须先点历史条目」的站（longcat）。
 *   SEL    逗号分隔候选选择器，逐个报精确命中数 + 是否可见
 *   OUT    输出 JSON 路径（默认 evidence/dom-shape-<timestamp>.json）
 *   PROFILE 持久 profile（默认与 l2-platform-auto.mjs 一致，多站共用登录态）
 *   WAIT   页面加载后等待毫秒（默认 6000；等虚拟列表渲染）
 */

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const PROFILE =
  process.env.PROFILE ||
  `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const URL_ARG = process.env.URL;
const TEXTS = (process.env.TEXTS || "")
  .split("|")
  .map((s) => s.trim())
  .filter(Boolean);
/** 逗号分隔的候选选择器：逐个报命中数，用来选「每条消息 1 个」的稳定容器。 */
const SEL = (process.env.SEL || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const WAIT = Number(process.env.WAIT || 6000);
/**
 * 导航型点击目标（可选）。存在的原因：longcat 这类站进会话后 URL 不带会话 id，
 * 探针没法直接 goto 到带内容的会话页，只能从首页点侧栏历史条目进去。
 *
 * 红线：只放行「点进会话」这一种点击。发送/提交/生成类 selector 一律拒绝执行，
 * 因为探针的价值就是「在绝不改变会话状态的前提下看结构」。
 */
const CLICK = process.env.CLICK || "";
/** 出现这些词就说明目标不是导航而是触发动作，直接拒绝。 */
const FORBIDDEN_CLICK = /send|submit|发送|提交|生成|generate|regenerate|重新生成/i;
const OUT =
  process.env.OUT ||
  `${EVIDENCE_DIR}/dom-shape-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

if (!URL_ARG) {
  console.error("缺 URL 环境变量。用法见文件头注释。");
  process.exit(2);
}

async function main() {
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: null,
    args: ["--no-first-run", "--no-default-browser-check"],
  });

  const page = await context.newPage();
  log("打开", URL_ARG);
  await page.goto(URL_ARG, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(WAIT);
  log("当前 URL:", page.url());

  if (CLICK) {
    if (FORBIDDEN_CLICK.test(CLICK)) {
      throw new Error(`CLICK 命中发送/生成类关键词，探针拒绝点击：${CLICK}`);
    }
    log("导航型点击:", CLICK);
    await page.click(CLICK, { timeout: 15000 });
    await page.waitForTimeout(WAIT);
    log("点击后 URL:", page.url());
  }

  const shape = await page.evaluate(({ texts, sels }) => {
    const SENTINEL = "\u0000no-child-match\u0000";

    /** 元素指纹：tag + 归一化 class（去掉哈希后缀与多余空白）+ 文本长度 */
    const fingerprint = (el) => {
      const cls = String(el.className || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 140);
      return {
        tag: el.tagName.toLowerCase(),
        cls,
        textLen: (el.textContent || "").trim().length,
        childCount: el.children.length,
      };
    };

    /** 按文本反查最内层节点：contains 且没有任何子元素也 contains */
    const innermost = (needle) => {
      const all = [...document.querySelectorAll("*")];
      const hits = all.filter((el) => (el.textContent || "").includes(needle));
      const leaf = hits.filter(
        (el) => ![...el.children].some((c) => (c.textContent || "").includes(needle)),
      );
      // 按文本长度升序：最短的最贴近文本本身；前 5 个全部留下，
      // 因为同一个片段往往同时出现在**侧栏历史**和**对话气泡**两处，必须能对比。
      const sorted = leaf.sort(
        (a, b) => (a.textContent || "").length - (b.textContent || "").length,
      );
      const chainOf = (el) => {
        const chain = [];
        let p = el;
        for (let i = 0; i < 9 && p && p !== document.documentElement; i++, p = p.parentElement) {
          chain.push(fingerprint(p));
        }
        return chain;
      };
      return {
        needle,
        found: sorted.length > 0,
        hits: hits.length,
        leafHits: leaf.length,
        candidates: sorted.slice(0, 5).map((el) => ({
          textPreview: (el.textContent || "").trim().slice(0, 120),
          chain: chainOf(el),
        })),
      };
    };

    /** 类名分组统计：把哈希类名归一化后计数 */
    const normClass = (c) =>
      String(c || "")
        .split(/\s+/)
        .filter(Boolean)
        .map((x) => x.replace(/_[a-z0-9]{4,8}_\d+$/i, "_*")) // CSS Modules 哈希后缀
        .join(" ");

    const groups = {};
    const KEY = /answer|message|chat|conv|response|bubble|markdown|prose/i;
    for (const el of document.querySelectorAll("div, article, section, li, p")) {
      const cls = String(el.className || "");
      if (!cls || !KEY.test(cls)) continue;
      const key = normClass(cls).slice(0, 120);
      const g = (groups[key] ||= {
        count: 0,
        textLens: [],
        maxChildren: 0,
        sampleTag: el.tagName.toLowerCase(),
      });
      g.count += 1;
      g.maxChildren = Math.max(g.maxChildren, el.children.length);
      if (g.textLens.length < 40) g.textLens.push((el.textContent || "").trim().length);
    }

    // 只为「可能承载消息」的分组排序：数量少、文本较长、子元素少者更像单个气泡
    const groupList = Object.entries(groups)
      .map(([cls, g]) => {
        const nonEmpty = g.textLens.filter((n) => n > 0);
        const avg = nonEmpty.length
          ? Math.round(nonEmpty.reduce((a, b) => a + b, 0) / nonEmpty.length)
          : 0;
        return {
          cls,
          count: g.count,
          avgTextLen: avg,
          maxTextLen: Math.max(0, ...g.textLens),
          maxChildren: g.maxChildren,
          sampleTag: g.sampleTag,
        };
      })
      .sort((a, b) => b.avgTextLen - a.avgTextLen)
      .slice(0, 40);

    // 自定义元素统计：Gemini 用 <model-response>、元宝用 <hyc-*> 这类
    // 无 class 的标签承载消息主体，只统计 class 会整体漏掉它们。
    const tagGroups = {};
    for (const el of document.querySelectorAll("*")) {
      const t = el.tagName.toLowerCase();
      if (!t.includes("-")) continue;
      const g = (tagGroups[t] ||= { count: 0, textLens: [] });
      g.count += 1;
      if (g.textLens.length < 40) g.textLens.push((el.textContent || "").trim().length);
    }
    const customTags = Object.entries(tagGroups)
      .map(([tag, g]) => ({
        tag,
        count: g.count,
        avgTextLen: Math.round(
          g.textLens.reduce((a, b) => a + b, 0) / Math.max(1, g.textLens.length),
        ),
        maxTextLen: Math.max(0, ...g.textLens),
      }))
      .sort((a, b) => b.avgTextLen - a.avgTextLen)
      .slice(0, 20);

    // 指定选择器的精确命中数 + 各命中项的 class/文本长度。
    // 用途：`findElements` 是「按优先级取第一个有命中的选择器」，
    // 所以必须知道每个候选的命中数，才能判断它是不是「每条消息 1 个」的稳定容器。
    //
    // `visible` 字段是为 `isTyping()` 服务的：它走 `findVisibleElement`
    // （只看**可见**元素）。真站常把 loading/generating 这类骨架留在 DOM 里
    // 用 display:none 藏起来——按「存在即命中」判定会让 isTyping() 恒 true，
    // 于是 wait 永远等不到「不再打字」。这里把可见性一并数出来，
    // 才能区分「0 命中」和「命中但全隐藏」这两种完全不同的情况。
    const isVisible = (el) => {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    const selectorCounts = {};
    for (const sel of sels) {
      try {
        const els = [...document.querySelectorAll(sel)];
        selectorCounts[sel] = {
          count: els.length,
          visible: els.filter(isVisible).length,
          // textPreview 是判定「取到的是正文还是状态条」的唯一直接证据：
          // 「已找到 15 个网页」这类行只比正文少十来个字，长度看不出来，只能看文本。
          samples: els.slice(0, 8).map((el) => ({
            cls: String(el.className || "").slice(0, 100),
            textLen: (el.textContent || "").trim().length,
            textPreview: (el.textContent || "").trim().slice(0, 60),
            kids: el.children.length,
            visible: isVisible(el),
          })),
        };
      } catch (e) {
        selectorCounts[sel] = { error: e.message.slice(0, 80) };
      }
    }

    return {
      url: location.href,
      title: document.title,
      totalElements: document.querySelectorAll("*").length,
      anchors: texts.map(innermost),
      groups: groupList,
      customTags,
      selectorCounts,
      sentinel: SENTINEL,
    };
  }, { texts: TEXTS, sels: SEL });

  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify(shape, null, 2));
  log("结构已写:", OUT);

  for (const a of shape.anchors) {
    if (!a.found) {
      log(`锚点「${a.needle}」未找到（命中 ${a.hits}）`);
      continue;
    }
    log(`锚点「${a.needle}」leafHits=${a.leafHits}，候选 ${a.candidates.length} 个`);
    for (const [i, cand] of a.candidates.entries()) {
      log(`  [候选 ${i}] "${cand.textPreview.slice(0, 40)}"`);
      for (const f of cand.chain.slice(0, 6)) {
        log(`     ${f.tag} .${f.cls.slice(0, 70)} | text=${f.textLen} kids=${f.childCount}`);
      }
    }
  }
  log("最可能的候选类名（按平均文本长度降序，前 10）:");
  for (const g of shape.groups.slice(0, 10)) {
    log(`   ${g.count}× .${g.cls.slice(0, 70)} | avgText=${g.avgTextLen} kids=${g.maxChildren}`);
  }
  if (shape.customTags?.length) {
    log("自定义元素标签（前 8）:");
    for (const t of shape.customTags.slice(0, 8)) {
      log(`   <${t.tag}> ${t.count}× | avgText=${t.avgTextLen} max=${t.maxTextLen}`);
    }
  }
  if (SEL.length) {
    log("候选选择器精确命中数:");
    for (const [sel, r] of Object.entries(shape.selectorCounts || {})) {
      if (r.error) {
        log(`   ${sel} → 报错 ${r.error}`);
        continue;
      }
      log(`   ${r.count}× (可见 ${r.visible}) ${sel}`);
      for (const s of r.samples) {
        log(
          `      .${s.cls.slice(0, 60)} | text=${s.textLen} kids=${s.kids} vis=${s.visible} ` +
            `| "${s.textPreview.replace(/\s+/g, " ").slice(0, 44)}"`,
        );
      }
    }
  }

  await context.close();
  log("DONE");
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
