/**
 * 「会话边界能不能解掉长会话撞墙」—— A/B 对照**方案**（不是执行器）。
 *
 * ## 为什么这个文件只出计划、不跑真机
 *
 * 用户 2026-11-11 红线：deepseek / longcat 等冻结平台「不去碰」。
 * 而这两个恰好是**当初真正撞墙的站**——RESULT §9.4 把 step_8 失败
 * 从「平台慢」改判成「Pack 尾部撞墙」，就是在它们身上观察到的。
 * 现在活跃 5 站验到的只是「重置真的做到了」（N23），
 * **不是**「重置解掉了撞墙」。后者仍欠一次解冻后的 A/B 对照。
 *
 * 所以本脚本：
 *   - 产出一份机器可读的计划 JSON（判据、变体、命令、归因边界）；
 *   - **纯本地**生成两个待用变体 Pack（A 去掉 fresh_session / B 原样）；
 *   - **不启动浏览器、不导入 Pack、不发任何消息**；
 *   - 不生成「看起来像回执」的文件，避免被误读成已经跑过。
 *
 * 2026-11-11 修订：第一版 `plan.commands` 里写的是
 * `PACK_PATH=<variant-pack.json>` —— 一个**占位符**，两个变体文件从未落盘，
 * 于是「4 条命令已备好」是不成立的（命令根本不能原样执行）。
 * 现在改为真实绝对路径 + 实际生成文件，并加测试守护不许退回占位符。
 *
 * 解冻后由人拿着 `plan.commands` **串行**逐条跑（见 executionOrder），
 * 跑完的产物才是证据。
 *
 * 用法（只写本地计划与变体文件，安全）：
 *   node tests/real-machine/session-wall-ab.mjs
 *   OUT=... node tests/real-machine/session-wall-ab.mjs
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  ACTIVE_PLATFORM_IDS,
  FROZEN_AB_PLATFORMS,
  evaluatePlatformPolicy,
} from "./platform-freeze.mjs";
import { precheckOutputPath } from "./evidence-paths.mjs";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const PACKS_DIR = `${REPO_ROOT}packs/examples`;
const FACTORY_PACK = `${PACKS_DIR}/xiaohongshu_knowledge_creator.json`;
const TODAY = new Date().toISOString().slice(0, 10);

/**
 * 变体 Pack 的**绝对路径**（不是占位符）。
 * 命名带日期与变体名，A/B 互不覆盖；测试会盯着这里不许退回 `<...>`。
 * @param {"no-boundary"|"with-boundary"} variant
 */
export function variantPackPath(variant, outDir = EVIDENCE_DIR, date = TODAY) {
  return resolve(outDir, `ab-pack-${date}.${variant}.json`);
}

/**
 * 派生 A/B 变体（**纯函数**，只变换内存里的 Pack 对象，不写盘、不导入）。
 *
 * - `no-boundary`：删掉所有步骤的 fresh_session —— 对照组，复现「同一个长会话
 *   连问 8 步」的原始形态；
 * - `with-boundary`：保留出厂 Pack 的 `fresh_session: prefer` —— 实验组。
 *
 * 刻意不改动 prompt / 步骤顺序 / 其他字段：A/B 只能差一个变量，
 * 否则「B 比 A 好」无法归因给会话边界。
 *
 * 出厂 Pack 的声明实际在 `workflow.steps[7]`（不是顶层 `steps`），
 * 所以这里递归删键而不是写死容器路径——写死过一次就漂移过一次。
 * @param {object} pack
 * @param {"no-boundary"|"with-boundary"} variant
 */
export function derivePackVariant(pack, variant) {
  if (variant !== "no-boundary" && variant !== "with-boundary") {
    throw new Error(`未知变体 ${variant}`);
  }
  const clone = JSON.parse(JSON.stringify(pack));
  if (variant === "no-boundary") {
    const strip = (o) => {
      if (Array.isArray(o)) {
        for (const v of o) strip(v);
      } else if (o && typeof o === "object") {
        delete o.fresh_session;
        for (const v of Object.values(o)) strip(v);
      }
    };
    strip(clone);
  }
  return clone;
}

/**
 * 纯本地生成两个待用变体 Pack，**不导入、不执行、不碰任何网站**。
 *
 * 自检是硬性的：pack_id 必须与出厂一致（EXECUTE_PACK 用的是固定 PACK_ID），
 * 步数必须是 8，A 必须删干净 fresh_session、B 必须原样保留，
 * 两者除 fresh_session 外逐字节一致。任何一条不满足就直接抛错，不写文件。
 *
 * @param {{outDir?: string, packPath?: string, date?: string}} [opts]
 * @returns {{files: Array<{variant:string, path:string, sha256:string, bytes:number}>, checks: object}}
 */
export function emitVariantPacks(opts = {}) {
  const outDir = opts.outDir || EVIDENCE_DIR;
  const date = opts.date || TODAY;
  const factory = JSON.parse(readFileSync(opts.packPath || FACTORY_PACK, "utf-8"));
  const factoryId = factory.metadata?.pack_id;
  const stepCount = factory.workflow?.steps?.length;

  const a = derivePackVariant(factory, "no-boundary");
  const b = derivePackVariant(factory, "with-boundary");
  // 缺步时给空对象而不是 undefined：否则 `'fresh_session' in undefined`
  // 会抛 TypeError，把「步数不对」这个真因盖成一个看不懂的类型错误。
  const stepOf = (p) => p.workflow.steps.find((s) => s.id === "step_8_output") || {};
  const strip = (o) => {
    if (Array.isArray(o)) return o.map(strip);
    if (o && typeof o === "object") {
      const c = {};
      for (const [k, v] of Object.entries(o)) if (k !== "fresh_session") c[k] = strip(v);
      return c;
    }
    return o;
  };
  // 每行写清**期望值**：A 组「没有 fresh_session」才是正确状态，
  // 笼统地要求「所有布尔值为真」会把正确实现判成失败（第一版就踩了）。
  const expected = {
    factoryPackId: [factoryId, "xiaohongshu-knowledge-creator"],
    stepCount: [stepCount, 8],
    aHasNoFreshSession: [!("fresh_session" in stepOf(a)), true],
    bKeepsPrefer: [stepOf(b).fresh_session, "prefer"],
    samePackId: [a.metadata.pack_id === factoryId && b.metadata.pack_id === factoryId, true],
    onlyDiffersByFreshSession: [
      JSON.stringify(strip(a)) === JSON.stringify(strip(b)) &&
        JSON.stringify(b) === JSON.stringify(factory),
      true,
    ],
  };
  const checks = Object.fromEntries(Object.entries(expected).map(([k, [v]]) => [k, v]));
  for (const [k, [actual, want]] of Object.entries(expected)) {
    if (actual !== want) throw new Error(`变体自检失败：${k} = ${actual}，期望 ${want}`);
  }

  mkdirSync(outDir, { recursive: true });
  const files = [];
  for (const [variant, pack] of [["no-boundary", a], ["with-boundary", b]]) {
    const path = variantPackPath(variant, outDir, date);
    const text = JSON.stringify(pack, null, 2) + "\n";
    writeFileSync(path, text);
    files.push({
      variant,
      path,
      sha256: createHash("sha256").update(text).digest("hex"),
      bytes: Buffer.byteLength(text),
    });
  }
  return { files, checks };
}

/**
 * 产出计划。纯函数，便于单测与变异锚直接咬判据。
 * @param {{variantFiles?: Array, outDir?: string, date?: string}} [opts]
 * @returns {object}
 */
export function buildAbPlan(opts = {}) {
  const platforms = [...FROZEN_AB_PLATFORMS];
  const variants = [
    {
      id: "A-control",
      packVariant: "no-boundary",
      freshSession: "removed",
      role: "对照组：复现 step_8 长会话撞墙",
    },
    {
      id: "B-boundary",
      packVariant: "with-boundary",
      freshSession: "prefer",
      role: "实验组：出厂 Pack，step_8_output 声明 fresh_session=prefer",
    },
  ];

  const runMatrix = platforms.flatMap((platform) =>
    variants.map((v) => ({
      platform,
      variant: v.packVariant,
      // 路径只是**计划**，本脚本不写这些文件。
      out: `L2-${platform}-auto-${TODAY}.ab-${v.packVariant}.json`,
    })),
  );

  return {
    status: "plan-only / NOT-EXECUTED",
    proposition:
      "fresh_session 会话边界能解掉 deepseek / longcat 的 step_8 长会话撞墙",
    generatedAt: new Date().toISOString(),
    whyNotRunNow: [
      "用户 2026-11-11 红线：仅保留 qianwen / yuanbao / chatglm / yiyan / kimi，其他冻结不去碰。",
      "platform-freeze.mjs 已把这条红线落成代码级闸门；ALLOW_FROZEN=1 只有用户明确解冻后才可以加。",
      "本轮活跃 5 站只验到「重置真的做到了」（N23），没有碰过真正撞墙的两个站。",
    ],
    unfreezeConditions: [
      "用户给出明确的解冻指令（点名平台 + 允许范围）。**当前未满足**：用户只授权了本地准备与 push，没有解冻。",
      "两站登录态可用：PRECHECK=1 且 ALLOW_FROZEN=1、显式 CANDIDATES=deepseek,longcat；deepseek 此前从未被预检过，longcat 只有 2026-11-10 的旧快照，都不是当前态。**当前未满足**。",
      "dist 产物与源码一致（npm run build 后比对 hash 与关键字，G1–G10 口径）。本轮本地准备会核，结果写进 RESULT。",
      "确认账号额度：2 站 × 2 变体 × 8 步 = 32 步真实发送 + 1 轮预检。**当前未满足/未核**：账号侧信息，我无法核，需用户确认。",
    ],
    activePlatforms: [...ACTIVE_PLATFORM_IDS],
    frozenPlatforms: platforms,
    platformPolicy: platforms.map((id) => ({
      id,
      ...evaluatePlatformPolicy(id, { allowFrozen: false }),
    })),
    variants,
    runMatrix,
    // 变体 Pack 是**本地准备产物**，不是回执；路径为真实绝对路径，命令可原样执行。
    variantPacks: (opts.variantFiles || ["no-boundary", "with-boundary"].map((v) => ({
      variant: v,
      path: variantPackPath(v, opts.outDir || EVIDENCE_DIR, opts.date || TODAY),
    }))).map((f) => ({
      variant: f.variant,
      path: f.path,
      sha256: f.sha256 || null,
      imported: false,
      executed: false,
    })),
    executionOrder: [
      "4 条命令必须**串行**，禁止并行：两轮都用 mergeStrategy=overwrite 导入同一个 pack_id，并行会互相覆盖 storage 里的 Pack。",
      "每轮结束后先核回执（8/8 + sessionResets），再跑下一轮；B 组若 available:false 这轮作废，不要直接拿去判定。",
      "预检登录态也要显式解冻：PRECHECK=1 会打开冻结站页面，本身受 assertCandidatesAllowed 拦截，必须带 ALLOW_FROZEN=1 与显式 CANDIDATES。",
    ],
    commands: [
      "# 解冻后由人逐条执行（本脚本不代跑）；先预检，再串行跑 4 轮：",
      `CANDIDATES=deepseek,longcat PRECHECK=1 ALLOW_FROZEN=1 ` +
        `OUT=${EVIDENCE_DIR}/${precheckOutputPath({ evidenceDir: EVIDENCE_DIR, date: TODAY, candidates: platforms }).split("/").pop()} ` +
        `node tests/real-machine/l2-platform-auto.mjs`,
      ...runMatrix.map(
        (r) =>
          `PLATFORM=${r.platform} ALLOW_FROZEN=1 PACK_VARIANT=${r.variant} ` +
          `PACK_PATH=${variantPackPath(r.variant, opts.outDir || EVIDENCE_DIR, opts.date || TODAY)} ` +
          `OUT=${EVIDENCE_DIR}/${r.out} ` +
          `node tests/real-machine/l2-platform-auto.mjs`,
      ),
    ],
    acceptance: {
      packCompleted: "exec.success === true && exec.result.status === completed && 8/8 steps success",
      resetActuallyHappened:
        "B 组回执 sessionResets[0].available === true && messageCountAfter < messageCountBefore —— 否则 B 不能算「开了新会话」，这轮对照作废",
      noDuplicateSend: "截图里每个 step 只有一条提问气泡；N21 的续等只发 WAIT_FOR_RESPONSE，不重发",
      likeForLike:
        "同站、同账号态、同 prompt、相邻时间窗；A 与 B 只允许差 fresh_session 一个变量",
      verdictRule:
        "只有 A 撞墙且 B 通过才支持命题；A/B 都通过 ⇒ 本轮墙不存在，不能归功边界；A/B 都撞墙 ⇒ 边界无效，另找根因",
    },
    attributionBoundaries: [
      "不能把整包耗时差异归因给会话重置——RESULT §14.1/§14.2 已判否（重置只在 step_8，step_1~7 的差值与它无关）。",
      "也不能说「重置免费」——durationMs 非零，4 站实测 304–319ms，代码上界 8s。",
      "B 单轮通过 ≠ 边界有效：N21 续等修复、N24 文心假基准修复是同期混杂变量，必须在 A/B 两轮里同时固定。",
      "chatglm 那轮 419.6s vs 349.8s 的差异主要在 step_2 抖动（28.7→70.2s），既不能归因给重置，也不能反过来当「重置无代价」的证据。",
    ],
    precheckPath: precheckOutputPath({
      evidenceDir: EVIDENCE_DIR,
      date: TODAY,
      candidates: platforms,
    }),
  };
}

function main() {
  // 纯本地准备：生成两个待用变体 Pack。不是导入、不是执行、不碰网站。
  const { files, checks } = emitVariantPacks({
    packPath: process.env.PACK_PATH || FACTORY_PACK,
  });
  for (const f of files) {
    console.log("变体 Pack 已生成（未导入/未执行）:", f.path, "sha256=" + f.sha256.slice(0, 12) + "…");
  }

  const plan = buildAbPlan({ variantFiles: files });
  const out =
    process.env.OUT || `${EVIDENCE_DIR}/session-wall-ab-plan-${TODAY}.json`;
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, JSON.stringify(plan, null, 2));
  console.log("A/B 计划已写（**未执行、无真机回执**）:", out);
  console.log("status:", plan.status);
  console.log("冻结平台:", plan.frozenPlatforms.join(", "));
  console.log("变体自检:", JSON.stringify(checks));
  console.log("命令:", plan.commands.length - 1, "条 + 注释；判据:", Object.keys(plan.acceptance).length, "条");
  console.log("本脚本未启动浏览器、未导入 Pack、未发送任何消息。");
}

// 只在被直接执行时写计划；被 import（单测 / 变异）时不产生副作用。
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
