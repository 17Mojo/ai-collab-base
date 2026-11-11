/**
 * L2 真机执行驱动（平台参数化版）
 *
 * 由 l2-qianwen-auto.mjs 泛化而来，供「真机 3 平台回归」补齐千问之外的平台。
 * 平台定义唯一事实源：tests/platforms.mjs（hostnames / url），不在此处硬编码域名。
 *
 * 两种模式：
 *   PRECHECK=1  只做勘察：加载 dist 扩展 → SW 自检 → 逐个打开候选平台 →
 *               判断输入框是否可见、是否被重定向到登录页。**不导入 Pack、不发消息**。
 *   默认       对 PLATFORM 指定的单个平台跑完整 L2（IMPORT_PACKS → EXECUTE_PACK）。
 *
 * 硬红线与 l2-qianwen-auto.mjs 相同：本脚本会真实发送消息、消耗账号额度，
 * 只允许在真机回归时跑，不进 CI、不进 npm test。
 *
 * 用法：
 *   PRECHECK=1 node tests/real-machine/l2-platform-auto.mjs
 *   PLATFORM=gemini OUT=... SHOT=... node tests/real-machine/l2-platform-auto.mjs
 *
 * 环境变量：
 *   PLATFORM   平台 id（默认 qianwen）
 *   CANDIDATES PRECHECK 模式下的候选 id，逗号分隔（默认 5 个活跃站）
 *   PROFILE    持久 profile 目录
 *   OUT / SHOT 回执与截图路径
 *   TOPIC / LEVEL   Pack 输入
 *   LOGIN_WAIT 等登录分钟数（默认 15）
 *   ALLOW_FROZEN=1  仅在用户明确解冻后允许跑冻结平台（见 platform-freeze.mjs）
 *   PACK_PATH  覆盖出厂 Pack 路径；A/B 对照时指向生成的变体（默认仍是出厂 Pack）
 *   PACK_VARIANT 只写进回执的标签，便于区分 A/B 两轮，不改变执行逻辑
 *
 * ## 平台冻结守卫（2026-11-11）
 *
 * 用户红线「仅保留 qianwen、yuanbao、chatglm、yiyan、kimi，其他冻结不去碰」
 * 由 `platform-freeze.mjs` 在 `launch()` 之前硬拦截：冻结站连浏览器都不启动。
 * 预检虽然不发包，但会打开页面，所以 `CANDIDATES` 同样过闸。
 * 守卫的放行结果写进回执 `platformPolicy`，便于从磁盘复核「谁解冻过」。
 */

import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { clearSwCaches } from "./clear-sw-cache.mjs";
import { overwriteNotice, precheckOutputPath } from "./evidence-paths.mjs";
import { PLATFORMS, getPlatform } from "../platforms.mjs";
import {
  ACTIVE_PLATFORM_IDS,
  assertCandidatesAllowed,
  assertPlatformAllowed,
  evaluatePlatformPolicy,
} from "./platform-freeze.mjs";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EXT = fileURLToPath(new URL("../../dist", import.meta.url));
const PACK_PATH =
  process.env.PACK_PATH || `${REPO_ROOT}packs/examples/xiaohongshu_knowledge_creator.json`;
const PACK_VARIANT = process.env.PACK_VARIANT || "as-is";
const ALLOW_FROZEN = process.env.ALLOW_FROZEN === "1";
const PROFILE =
  process.env.PROFILE ||
  // 🔧 2026-11-11：原默认值 `rm-l2-multi-profile` 从未被创建（磁盘上不存在），
  // 导致不带 PROFILE 直接跑时 clearSwCaches 以「不是 Chrome profile」秒退。
  // 统一到与 clear-sw-cache.mjs / l2-qianwen-auto.mjs 相同的真机 profile（多站共用一份登录态）。
  `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const TODAY = new Date().toISOString().slice(0, 10);
const PLATFORM = process.env.PLATFORM || "qianwen";
const PRECHECK = process.env.PRECHECK === "1";
// 默认候选集直接由白名单派生，不在这里再抄一份平台清单——
// 否则「白名单加了新站、这里漏了」又是一处静默漂移。
const CANDIDATES = (process.env.CANDIDATES || ACTIVE_PLATFORM_IDS.join(","))
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const OUT =
  process.env.OUT || `${EVIDENCE_DIR}/L2-${PLATFORM}-auto-${TODAY}.json`;
const SHOT = process.env.SHOT || OUT.replace(/\.json$/, ".png");
const TOPIC = process.env.TOPIC || "AI 智能体（Agent）到底是什么";
const LEVEL = process.env.LEVEL || "普通上班族";
const LOGIN_WAIT = Number(process.env.LOGIN_WAIT || 15);
const PACK_ID = "xiaohongshu-knowledge-creator";

const COMPOSER =
  'textarea, div[contenteditable="true"], div[data-slate-editor="true"], [role="textbox"], [contenteditable="true"]';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

function tabPatterns(spec) {
  return spec.hostnames.map((h) => `*://${h}/*`).concat(
    spec.hostnames.map((h) => `*://*.${h}/*`),
  );
}

async function launch() {
  const cleared = clearSwCaches(PROFILE);
  if (!cleared.ok) throw new Error("清缓存计划被拒: " + cleared.reason);
  log("已清 SW 缓存:", cleared.removed.length, "项");

  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: null,
    args: [
      `--disable-extensions-except=${EXT}`,
      `--load-extension=${EXT}`,
      "--no-first-run",
      "--no-default-browser-check",
    ],
  });

  let extId = null;
  for (let i = 0; i < 30 && !extId; i++) {
    for (const w of context.serviceWorkers()) {
      const m = w.url().match(/^chrome-extension:\/\/([^/]+)\//);
      if (m) extId = m[1];
    }
    if (!extId) await new Promise((r) => setTimeout(r, 500));
  }
  if (!extId) throw new Error("没等到扩展 service worker");
  log("extension id:", extId);

  const sw = context.serviceWorkers().find((w) => w.url().includes(extId));
  const probe = sw
    ? await sw
        .evaluate(async () => {
          const t = await fetch("/service-worker.js").then((r) => r.text());
          return {
            hasGate: t.includes("assertUsableAIContent"),
            hasStatusSelector: t.includes("data-status"),
            hasMin50: t.includes("MIN_AI_CONTENT_LENGTH_DEFAULT = 50"),
            size: t.length,
          };
        })
        .catch(() => null)
    : null;
  log("SW 自检:", JSON.stringify(probe ?? "探测失败"));
  if (probe && (!probe.hasGate || !probe.hasStatusSelector || !probe.hasMin50)) {
    throw new Error("SW 加载的不是带闸门的构建 —— 先 npm run build 并清缓存");
  }
  return { context, extId, probe };
}

async function precheck(context) {
  const results = [];
  for (const id of CANDIDATES) {
    const spec = getPlatform(id);
    if (!spec) {
      results.push({ platform: id, error: "平台未在 platforms.mjs 登记" });
      continue;
    }
    const page = await context.newPage();
    let row = { platform: id, url: spec.url };
    try {
      await page.goto(spec.url, { waitUntil: "domcontentloaded", timeout: 45000 });
      await page.waitForTimeout(4000);
      row.finalUrl = page.url();
      row.title = await page.title().catch(() => "");
      const composer = page.locator(COMPOSER).first();
      row.composerVisible = await composer.isVisible({ timeout: 2000 }).catch(() => false);
      row.composerCount = await page.locator(COMPOSER).count().catch(() => 0);
      // 🔧 2026-11-11 修正：原正则写的是 `signin`，匹配不上 deepseek 的 `/sign_in`
      // （带下划线）⇒ 该站明明是登录墙却报 looksLikeLogin=false，与
      // composerVisible=false 自相矛盾。认证路径的分隔符各站不同（sign_in /
      // sign-in / signin / log_in / login），一律用 `[_-]?` 吃掉。
      row.looksLikeLogin = /log[_-]?in|sign[_-]?in|passport|auth|登录|扫码/i.test(
        row.finalUrl + " " + row.title,
      );
      // 刻意**不**把 `composerVisible === false` 并进 looksLikeLogin：
      // 两者含义不同（「页面没渲染完」vs「需要登录」），合并会制造假信号。
      // 读者同时看两列即可——deepseek 那种 `composerVisible:false` +
      // `finalUrl:/sign_in` 的双信号才是有力证据。
      // 顺带采一份「消息容器选择器命中数」——handleWaitForResponse 的
      // countGrew 判据依赖它增长；0 命中或恒定命中都会导致永远超时。
      row.dom = await page
        .evaluate(() => {
          const sels = [
            '[class*="message"]',
            '[class*="response"]',
            ".message-item",
            '[class*="chat"]',
            '[data-conv-speaker]',
            '[data-message-id]',
            '[role="article"]',
          ];
          const counts = Object.fromEntries(
            sels.map((s) => [s, document.querySelectorAll(s).length]),
          );
          const cands = [...document.querySelectorAll("div,article,section")]
            .filter((e) => {
              const t = e.textContent.trim();
              return t.length > 40 && t.length < 500 && e.children.length < 12;
            })
            .slice(0, 8)
            .map((e) => ({
              cls: String(e.className || "").slice(0, 100),
              len: e.textContent.trim().length,
              attrs: [...e.attributes]
                .slice(0, 5)
                .map((a) => `${a.name}=${String(a.value).slice(0, 40)}`),
            }));
          return { counts, cands };
        })
        .catch((e) => ({ error: e.message.slice(0, 120) }));
    } catch (e) {
      row.error = e.message.slice(0, 160);
    }
    log(id, JSON.stringify(row));
    results.push(row);
    await page.close().catch(() => {});
  }
  // N22：文件名必须带候选集，否则「同日跑第二遍」会把上一次的预检证据
  // 静默覆盖掉（2026-11-11 13:32 就这么把 5 站记录写成了单站）。
  const outPath = precheckOutputPath({
    evidenceDir: EVIDENCE_DIR,
    date: TODAY,
    candidates: CANDIDATES,
    override: process.env.OUT,
  });
  mkdirSync(dirname(outPath), { recursive: true });
  const notice = overwriteNotice(outPath);
  if (notice) log("⚠️", notice, "—— 旧文件将被写入覆盖，若要保留请改用 OUT=...");
  writeFileSync(
    outPath,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        mode: "precheck",
        candidates: CANDIDATES,
        platformPolicy: CANDIDATES.map((id) => ({
          id,
          ...evaluatePlatformPolicy(id, { allowFrozen: ALLOW_FROZEN }),
        })),
        results,
      },
      null,
      2,
    ),
  );
  log("预检结果已写:", outPath);
  return results;
}

async function runOne(context, extId, spec, platformPolicy) {
  const page = await context.newPage();
  await page.goto(spec.url, { waitUntil: "domcontentloaded", timeout: 90000 });
  log(`${spec.name} 已打开；未登录请在窗口里扫码，最多等 ${LOGIN_WAIT} 分钟`);

  const composer = page.locator(COMPOSER).first();
  let loggedIn = false;
  const deadline = Date.now() + LOGIN_WAIT * 60 * 1000;
  while (Date.now() < deadline) {
    try {
      if (await composer.isVisible({ timeout: 1500 })) {
        loggedIn = true;
        break;
      }
    } catch {}
    await new Promise((r) => setTimeout(r, 5000));
  }
  if (!loggedIn) throw new Error(`${LOGIN_WAIT} 分钟未出现输入框 —— ${spec.name} 登录未完成`);
  log("✅ 检测到输入框，视为已登录");

  const extPage = await context.newPage();
  await extPage.goto(`chrome-extension://${extId}/pack-editor.html`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  const importRes = await extPage.evaluate(
    (json) =>
      chrome.runtime.sendMessage({
        type: "IMPORT_PACKS",
        jsonData: json,
        mergeStrategy: "overwrite",
      }),
    readFileSync(PACK_PATH, "utf8"),
  );
  log("导入结果:", JSON.stringify(importRes));
  if (!importRes?.imported?.length) throw new Error("导入失败: " + JSON.stringify(importRes));

  const patterns = tabPatterns(spec);
  const tabId = await extPage.evaluate(async (ps) => {
    for (const p of ps) {
      try {
        const tabs = await chrome.tabs.query({ url: p });
        if (tabs[0]?.id != null) return tabs[0].id;
      } catch {}
    }
    return null;
  }, patterns);
  log("目标 tabId:", tabId, tabId === null ? "（广播）" : "（精确投递）");

  log("▶ 触发 Pack，topic =", TOPIC);
  // 不 await：PROBE_DURING 模式下要在 EXECUTE_PACK 进行中采真实消息 DOM。
  // 历史会话点开的探针拿不到「发送瞬间」的气泡（虚拟列表/游客态不持久），
  // 这是 11-10 首轮探针没做到位的地方。
  const execPromise = extPage.evaluate(
    ({ packId, input, tabId }) =>
      chrome.runtime.sendMessage({ type: "EXECUTE_PACK", packId, input, tabId }),
    { packId: PACK_ID, input: { topic: TOPIC, target_audience_level: LEVEL }, tabId },
  );

  if (process.env.PROBE_DURING === "1") {
    const samples = [];
    const t0 = Date.now();
    while (Date.now() - t0 < 90000) {
      const s = await page
        .evaluate(() => {
          const sels = [
            '[data-conv-speaker]',
            ".hyc-content-md-done",
            ".answer-content-wrap",
            ".conversation-item",
            ".conversation",
            ".chat-message",
            '[class*="message"]',
            '[class*="answer"]',
          ];
          const counts = Object.fromEntries(
            sels.map((s) => [s, document.querySelectorAll(s).length]),
          );
          const leaves = [...document.querySelectorAll("*")].filter(
            (e) =>
              e.textContent?.includes("你要写一条小红书") && e.children.length === 0,
          );
          const chains = leaves.slice(0, 1).map((e) => {
            const ch = [];
            let p = e;
            for (let i = 0; i < 7 && p; i++, p = p.parentElement) {
              ch.push(String(p.className || "").slice(0, 100));
            }
            return ch;
          });
          return { counts, chains, url: location.href };
        })
        .catch((e) => ({ error: e.message.slice(0, 120) }));
      samples.push({ t: Date.now() - t0, ...s });
      if (samples.length % 8 === 0) {
        log("  DOM 采样", samples.length, JSON.stringify(s.counts ?? s.error));
      }
      await page.waitForTimeout(2000);
    }
    const probePath = OUT.replace(/\.json$/, ".dom-samples.json");
    writeFileSync(probePath, JSON.stringify({ platform: spec.id, samples }, null, 2));
    log("发送期间 DOM 采样已写:", probePath);
  }

  const execRes = await execPromise;

  const out = {
    generatedAt: new Date().toISOString(),
    platform: spec.id,
    platformUrl: spec.url,
    packId: PACK_ID,
    packPath: PACK_PATH,
    packVariant: PACK_VARIANT,
    platformPolicy: platformPolicy || null,
    input: { topic: TOPIC, target_audience_level: LEVEL },
    tabIdUsed: tabId,
    delivery: tabId === null ? "broadcast" : "precise",
    exec: execRes,
  };
  mkdirSync(dirname(OUT), { recursive: true });
  // L2 回执的默认名仍是 `L2-<platform>-auto-<date>.json`（同一天同一站
  // 复跑会覆盖上一次）。既有的复盘习惯是用 OUT 显式加后缀（.fix1 / .full5），
  // 所以这里不改命名，但**覆盖必须出声**——不然又是「静默丢证据」。
  const l2Notice = overwriteNotice(OUT);
  if (l2Notice) log("⚠️", l2Notice, "—— 同一站同日复跑请用 OUT=... 另存");
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  log("回执已写:", OUT);
  const outputs = execRes?.result?.output || {};
  for (const [k, v] of Object.entries(outputs)) {
    if (typeof v === "string") log(`  ${k}: len=${v.length}`);
  }
  log("success:", execRes?.success, "| status:", execRes?.result?.status);
  await page.screenshot({ path: SHOT }).catch(() => {});
  log("会话截图:", SHOT);
  return out;
}

async function main() {
  // 冻结闸门必须在 launch() 之前：冻结站连浏览器都不启动，更不打开页面。
  // 预检的 CANDIDATES 也过同一道闸（打开页面就算「碰」）。
  if (PRECHECK) {
    assertCandidatesAllowed(CANDIDATES, { allowFrozen: ALLOW_FROZEN });
  } else {
    assertPlatformAllowed(PLATFORM, { allowFrozen: ALLOW_FROZEN });
  }

  const spec = getPlatform(PLATFORM);
  if (!spec) throw new Error(`未知平台 ${PLATFORM}；可选: ${PLATFORMS.map((p) => p.id).join(",")}`);
  const policy = evaluatePlatformPolicy(PLATFORM, { allowFrozen: ALLOW_FROZEN });
  if (!policy.active) {
    log("⚠️ 冻结平台已按 ALLOW_FROZEN=1 放行:", PLATFORM, "—— 请确认用户已明确解冻");
  }
  const { context, extId, probe } = await launch();
  try {
    if (PRECHECK) {
      await precheck(context);
    } else {
      await runOne(context, extId, spec, policy);
    }
  } finally {
    await context.close();
  }
  log("DONE");
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
