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
 *
 * 覆盖行为（B3 2026-11-19）：目标路径已有**内容不同**的工件时默认拒绝，
 * 一个文件都不写，退出码 2。要覆盖必须显式 `FORCE_OVERWRITE=1`——
 * 因为那些工件是现场记录，不是草稿。只想验证脚本能跑就用 `OUT=/tmp/...`。
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  AB_PLATFORMS,
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
 * 计划写盘前的**留档判据**（纯函数，B3 2026-11-19）。
 *
 * ## 为什么需要这道门
 *
 * `main()` 原来无条件 `writeFileSync(out, ...)`，而计划文件名只带**日期**。
 * 「同一天重跑一次」就等于覆盖同名工件——而那件工件可能已经是一份
 * 不可复现的现场记录（N25 的 4 命令计划就是这种）。
 *
 * 这不是假想。2026-11-19 为验证脚本能跑，我直接执行了 `--plan`，
 * 把 `evidence/session-wall-ab-plan-2026-11-18.json` 覆盖成了「1 站 2 命令」
 * 的版本（原文件是 2026-11-18 02:49 的现场计划，还被 `.vscode/ai-collab.local.json`
 * 的 watchPaths 监视着），靠 `git checkout` 才还原。**能靠 git 还原是运气**：
 * 没提交过的工件覆盖了就没了。
 *
 * ## 三种结局，默认是拒绝而不是覆盖
 *
 *   create     目标不存在 → 正常落盘
 *   identical  与已有文件逐字节相同 → 不重写（顺便避免 mtime 漂移，
 *              把一份旧工件伪装成「刚生成的产物」）
 *   refuse     内容不同且没有显式放行 → 拒绝，一个文件都不写
 *
 * 放行办法只有一个：`FORCE_OVERWRITE=1`（或 `opts.force`）。
 * 之所以要「显式」，是因为覆盖历史证据这件事不该由「我刚好又跑了一次」
 * 顺带完成——它应该是一次有人负责的决定。
 *
 * @param {{existing?: string|null, next: string, force?: boolean}} input
 * @returns {{action: "create"|"identical"|"refuse", reason: string}}
 */
export function decidePlanWrite({ existing, next, force = false }) {
  if (existing === null || existing === undefined) {
    return { action: "create", reason: "目标文件不存在，首次落盘" };
  }
  if (existing === next) {
    return {
      action: "identical",
      reason: "内容与已有文件逐字节相同，不重写（避免 mtime 漂移把旧工件伪装成新产物）",
    };
  }
  if (force) {
    return { action: "create", reason: "FORCE_OVERWRITE=1 显式放行覆盖" };
  }
  return {
    action: "refuse",
    reason:
      "目标处已有一份内容不同的工件，默认拒绝覆盖（历史证据不是草稿纸）。" +
      "确认要覆盖时加 FORCE_OVERWRITE=1，或改 OUT 写到别的路径。",
  };
}

/**
 * 纯本地生成两个待用变体 Pack，**不导入、不执行、不碰任何网站**。
 *
 * 自检是硬性的：pack_id 必须与出厂一致（EXECUTE_PACK 用的是固定 PACK_ID），
 * 步数必须是 8，A 必须删干净 fresh_session、B 必须原样保留，
 * 两者除 fresh_session 外逐字节一致。任何一条不满足就直接抛错，不写文件。
 *
 * B3（2026-11-19）把「算」与「写」拆开：`deriveVariantFiles` 只算不写，
 * 让 `main()` 能在**任何文件落盘之前**统一过 `decidePlanWrite`——
 * 否则会出现「变体包已写、计划被拒」的半新半旧状态。
 *
 * @param {{outDir?: string, packPath?: string, date?: string}} [opts]
 * @returns {{files: Array<{variant:string, path:string, text:string, sha256:string, bytes:number}>, checks: object}}
 */
export function deriveVariantFiles(opts = {}) {
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

  const files = [];
  for (const [variant, pack] of [["no-boundary", a], ["with-boundary", b]]) {
    const path = variantPackPath(variant, outDir, date);
    const text = JSON.stringify(pack, null, 2) + "\n";
    files.push({
      variant,
      path,
      text,
      sha256: createHash("sha256").update(text).digest("hex"),
      bytes: Buffer.byteLength(text),
    });
  }
  return { files, checks };
}

/**
 * 生成并落盘两个变体 Pack。保留「算了就写」的旧语义（测试与一次性脚本用它），
 * 跳过覆盖判据的调用方请改用 `deriveVariantFiles` 自己决定写不写。
 * @param {{outDir?: string, packPath?: string, date?: string}} [opts]
 * @returns {{files: Array<{variant:string, path:string, sha256:string, bytes:number}>, checks: object}}
 */
export function emitVariantPacks(opts = {}) {
  const { files, checks } = deriveVariantFiles(opts);
  mkdirSync(dirname(files[0].path), { recursive: true });
  for (const f of files) writeFileSync(f.path, f.text);
  return { files: files.map(({ text: _text, ...rest }) => rest), checks };
}

/**
 * 产出计划。纯函数，便于单测与变异锚直接咬判据。
 * @param {{variantFiles?: Array, outDir?: string, date?: string}} [opts]
 * @returns {object}
 */
export function buildAbPlan(opts = {}) {
  // B1（2026-11-19）：实验对象读 AB_PLATFORMS，不再读冻结名单。
  // 读冻结名单的后果是「解冻一个站 = 悄悄改掉实验设计」，见 platform-freeze.mjs 的注释。
  const platforms = [...AB_PLATFORMS];
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
      `本站登录态可用：PRECHECK=1 且 ALLOW_FROZEN=1、显式 CANDIDATES=${platforms.join(",")}。` +
        `2026-11-18 那次只读预检里 ${platforms.join(" / ")} 是 composerVisible=true、looksLikeLogin=false、未发包` +
        `（collaboration/results/real-machine-runs/evidence/L2-precheck-2026-11-18.deepseek-longcat.json），所以这条**当时是满足的**；` +
        `但那是 1 天前的快照，正式跑前必须重跑一次预检确认当前态。**当前未重跑**。`,
      "dist 产物与源码一致（npm run build 后比对 hash 与关键字，G1–G10 口径）。本轮本地准备会核，结果写进 RESULT。",
      `确认账号额度：${platforms.length} 站 × ${variants.length} 变体 × 8 步 = ` +
        `${platforms.length * variants.length * 8} 步真实发送 + 1 轮预检。**当前未满足/未核**：账号侧信息，我无法核，需用户确认。`,
    ],
    activePlatforms: [...ACTIVE_PLATFORM_IDS],
    // 实验对象（读 AB_PLATFORMS）——**这份计划要跑哪些站**
    abPlatforms: platforms,
    // 冻结样本集（读 FROZEN_AB_PLATFORMS）——**治理事实**，仅供对账；它不再决定实验对象
    frozenPlatforms: [...FROZEN_AB_PLATFORMS],
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
      `${runMatrix.length} 条命令必须**串行**，禁止并行：两轮都用 mergeStrategy=overwrite 导入同一个 pack_id，并行会互相覆盖 storage 里的 Pack。`,
      "每轮结束后先核回执（8/8 + sessionResets），再跑下一轮；B 组若 available:false 这轮作废，不要直接拿去判定。",
      "预检登录态也要显式解冻：PRECHECK=1 会打开冻结站页面，本身受 assertCandidatesAllowed 拦截，必须带 ALLOW_FROZEN=1 与显式 CANDIDATES。",
    ],
    commands: [
      `# 解冻后由人逐条执行（本脚本不代跑）；先预检，再串行跑 ${runMatrix.length} 轮：`,
      `CANDIDATES=${platforms.join(",")} PRECHECK=1 ALLOW_FROZEN=1 ` +
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
  // PLAN_OUT_DIR 只影响「写到哪」，默认仍是 evidence/。存在的意义是让
  // 端到端测试能在临时目录里验证覆盖判据，而不去碰真实工件（B3）。
  const outDir = process.env.PLAN_OUT_DIR || EVIDENCE_DIR;

  // 纯本地准备：算出两个待用变体 Pack（此时**还没写盘**）。不是导入、不是执行、不碰网站。
  const { files: derived, checks } = deriveVariantFiles({
    outDir,
    packPath: process.env.PACK_PATH || FACTORY_PACK,
  });

  // buildAbPlan 只需要 path / sha256，别把整段包文本塞进计划 JSON。
  const files = derived.map(({ text: _text, ...rest }) => rest);
  const plan = buildAbPlan({ variantFiles: files });
  const out = process.env.OUT || `${outDir}/session-wall-ab-plan-${TODAY}.json`;
  const planText = JSON.stringify(plan, null, 2);

  // B3（2026-11-19）：**先对全部目标做覆盖判定，再决定写不写**。
  // 逐个「检查即写」会出现「变体包已落盘、计划被拒」的半新半旧状态。
  const force = process.env.FORCE_OVERWRITE === "1";
  const targets = [
    ...derived.map((f) => ({ what: `变体包 ${f.variant}`, path: f.path, text: f.text })),
    { what: "A/B 计划", path: out, text: planText },
  ].map((t) => ({
    ...t,
    ...decidePlanWrite({
      existing: existsSync(t.path) ? readFileSync(t.path, "utf-8") : null,
      next: t.text,
      force,
    }),
  }));

  const refused = targets.filter((t) => t.action === "refuse");
  if (refused.length > 0) {
    console.error("拒绝写入——目标处已有内容不同的工件，一个文件都没写：");
    for (const t of refused) console.error(`  · ${t.what}: ${t.path}\n    ${t.reason}`);
    console.error("确认要覆盖就加 FORCE_OVERWRITE=1；只想验证脚本能跑，请用 OUT=/tmp/... 指到别处。");
    process.exitCode = 2;
    return;
  }

  for (const t of targets) {
    if (t.action === "identical") {
      console.log(`未改写（内容相同）: ${t.what}`, t.path);
      continue;
    }
    mkdirSync(dirname(t.path), { recursive: true });
    writeFileSync(t.path, t.text);
    console.log(`已写入: ${t.what}`, t.path);
  }

  console.log("A/B 计划（**未执行、无真机回执**）:", out);
  console.log("status:", plan.status);
  console.log("实验对象:", plan.abPlatforms.join(", "), "| 冻结样本集:", plan.frozenPlatforms.join(", "));
  console.log("变体自检:", JSON.stringify(checks));
  console.log("命令:", plan.commands.length - 1, "条 + 注释；判据:", Object.keys(plan.acceptance).length, "条");
  console.log("本脚本未启动浏览器、未导入 Pack、未发送任何消息。");
}

// 只在被直接执行时写计划；被 import（单测 / 变异）时不产生副作用。
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
