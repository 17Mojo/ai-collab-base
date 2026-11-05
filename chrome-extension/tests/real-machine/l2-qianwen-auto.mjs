/**
 * L2 真机全自动执行驱动（xiaohongshu_knowledge_creator × 千问）
 *
 * ## 它解决什么问题
 *
 * L1 探针只读；`l2-send-observer.mjs` 半自动（人点发送）。本驱动是 L2 的
 * **全自动**一档：挂载 `dist/` 扩展 → 导入 Pack → EXECUTE_PACK 精确投递 →
 * 收完整回执 → 会话截图。产出可机检 JSON（对齐 RMR 的 --evidence-file）。
 *
 * 2026-11-04 用它跑出了本 Pack 真机上的第一次 7/7 真产出（RMR-2026-11-04-01，
 * L2/qianwen/zh-CN = pass），三轮弧线与语义裁决见
 * `collaboration/results/RESULT-L2-SEMANTIC-VERDICT-2026-11-04.md`。
 *
 * ## 硬红线（与探针相反，这里必须读清）
 *
 * 1. **本脚本会真实发送消息**（EXECUTE_PACK 全链路，消耗账号额度）——
 *    这就是 L2 的定义。只允许在真机回归时跑，不允许当 CI 测试跑。
 * 2. CI **不跑**本脚本（无登录态）；它不进 `npm test`，也不是变异锚的对象
 *    （非生产代码路径）。生产闸门的变异判定权威在 CI。
 * 3. 需要人工登录：脚本打开千问后最多等 15 分钟，期间扫码/登录。
 *
 * ## 跑前必读：SW ScriptCache 粘连协议（台账 N15，2026-11-04 实锤踩过）
 *
 * 持久 profile 的 `Default/Service Worker/ScriptCache/` 会**按 URL** 把旧 SW
 * 粘住：`dist/` 重建后 SW 仍跑旧代码（内容脚本每次注入读盘是新的）——
 * 闸门静默失效，跑出来的是一份看似成功的污染回执（17 字 ack 过 20 字闸）。
 *
 * 复跑前**必须**清缓存：
 *   rm -rf "<PROFILE>/Default/Service Worker" \
 *          "<PROFILE>/Default/Code Cache" \
 *          "<PROFILE>/Default/Extension Scripts"
 *
 * 脚本内置 SW 自检探针（hasGate / hasStatusSelector / hasMin50 三个标记物），
 * 任一 false 直接中止。标记物随构建演进——改了 wait-policy 常量名/闸门名，
 * 同步改探针里的 includes() 字面量。
 *
 * ## 用法
 *
 *   cd chrome-extension && node tests/real-machine/l2-qianwen-auto.mjs
 *
 * 环境变量（都有默认值）：
 *   TOPIC   跑题（默认「AI 智能体（Agent）到底是什么」）
 *   LEVEL   受众层级（默认「普通上班族」）
 *   OUT     回执 JSON 路径（默认 evidence/L2-qianwen-auto-<今天>.json）
 *   SHOT    会话截图路径（默认与 OUT 同名 .png）
 *   PROFILE 持久 profile 目录（默认 ~/Library/Application Support/rm-qianwen-l2-profile；勿指回 /tmp——会被系统清）
 *
 * 同日重跑默认覆盖同名回执——要留档先改名（`.roundN` / `.stale-sw-*` 后缀惯例）
 * 或显式设 OUT/SHOT。
 */

import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EXT = fileURLToPath(new URL("../../dist", import.meta.url));
const PACK_PATH = `${REPO_ROOT}packs/examples/xiaohongshu_knowledge_creator.json`;
// 登录态存盘不能放 /tmp（macOS 会定期清，QR 重登成本高）也不能进仓库树（含 cookie），
// 落 ~/Library/Application Support/ 下的固定目录（2026-11-05 工程债收口）。
const PROFILE = process.env.PROFILE || `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const TODAY = new Date().toISOString().slice(0, 10);
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const OUT = process.env.OUT || `${EVIDENCE_DIR}/L2-qianwen-auto-${TODAY}.json`;
const SHOT = process.env.SHOT || OUT.replace(/\.json$/, ".png");
const TOPIC = process.env.TOPIC || "AI 智能体（Agent）到底是什么";
const LEVEL = process.env.LEVEL || "普通上班族";
const PACK_ID = "xiaohongshu-knowledge-creator";

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

async function main() {
  log("启动自动化 Chromium（挂载 dist 扩展）…");
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

  // MV3 service worker 注册后才能拿到 extension id
  let extId = null;
  for (let i = 0; i < 30 && !extId; i++) {
    for (const w of context.serviceWorkers()) {
      const m = w.url().match(/^chrome-extension:\/\/([^/]+)\//);
      if (m) extId = m[1];
    }
    if (!extId) await new Promise((r) => setTimeout(r, 500));
  }
  if (!extId) throw new Error("没等到扩展 service worker —— --load-extension 未生效");
  log("extension id:", extId);

  // SW 自检：确认运行中的 SW 加载的是**带闸门**的构建（N15 协议，见头注释）。
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
    throw new Error("SW 加载的不是带闸门的构建（ScriptCache 粘连？）—— 先按头注释清缓存再跑");
  }

  const page = await context.newPage();
  await page.goto("https://www.qianwen.com/chat/workbench", {
    waitUntil: "domcontentloaded",
    timeout: 90000,
  });
  log("千问已打开。未登录请在弹出的窗口里扫码/登录 —— 脚本等你，最多 15 分钟");

  const composer = page
    .locator('div[data-slate-editor="true"], textarea, div[contenteditable="true"]')
    .first();
  let loggedIn = false;
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    try {
      if (await composer.isVisible({ timeout: 1500 })) {
        loggedIn = true;
        break;
      }
    } catch {}
    await new Promise((r) => setTimeout(r, 5000));
  }
  if (!loggedIn) throw new Error("15 分钟未出现输入框 —— 登录未完成");
  log("✅ 检测到输入框，视为已登录");

  const extPage = await context.newPage();
  await extPage.goto(`chrome-extension://${extId}/pack-editor.html`, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });

  const packJson = readFileSync(PACK_PATH, "utf8");
  const importRes = await extPage.evaluate(
    (json) =>
      chrome.runtime.sendMessage({
        type: "IMPORT_PACKS",
        jsonData: json,
        mergeStrategy: "overwrite",
      }),
    packJson,
  );
  log("导入结果:", JSON.stringify(importRes));
  if (!importRes?.imported?.length) {
    throw new Error("导入失败: " + JSON.stringify(importRes));
  }

  const tabId = await extPage.evaluate(async () => {
    try {
      const tabs = await chrome.tabs.query({ url: "*://*.qianwen.com/*" });
      return tabs[0]?.id ?? null;
    } catch {
      return null;
    }
  });
  log(
    "目标 tabId:",
    tabId,
    tabId === null ? "（广播路径；自动化浏览器内仅此一个 AI 标签页）" : "（精确投递）",
  );

  log("▶ 触发 Pack，topic =", TOPIC, "| 预计 5–15 分钟，期间别关窗口");
  const execRes = await extPage.evaluate(
    ({ packId, input, tabId }) =>
      chrome.runtime.sendMessage({ type: "EXECUTE_PACK", packId, input, tabId }),
    { packId: PACK_ID, input: { topic: TOPIC, target_audience_level: LEVEL }, tabId },
  );

  const out = {
    generatedAt: new Date().toISOString(),
    platform: "qianwen",
    packId: PACK_ID,
    input: { topic: TOPIC, target_audience_level: LEVEL },
    tabIdUsed: tabId,
    delivery: tabId === null ? "broadcast" : "precise",
    exec: execRes,
  };
  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  log("回执已写:", OUT);
  const outputs = execRes?.result?.output || {};
  log("产出字段:", Object.keys(outputs).join(", ") || "(空)");
  for (const [k, v] of Object.entries(outputs)) {
    if (typeof v === "string") log(`  ${k}: len=${v.length}`);
  }
  log("success:", execRes?.success, "| status:", execRes?.result?.status ?? execRes?.result?.errors?.[0]?.message);

  await page.screenshot({ path: SHOT }).catch(() => {});
  log("会话截图:", SHOT);
  await context.close();
  log("DONE");
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
