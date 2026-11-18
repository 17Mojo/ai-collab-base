/**
 * 「会话边界能不能解掉长会话撞墙」A/B 方案的守护测试。
 *
 * 守的不是「代码跑得通」，而是**判据没被悄悄稀释**：
 * 一旦有人把「B 组必须真的开了新会话」或「不能归因给重置」这些
 * 边界删掉，方案就会退化成「跑一轮 B 成功就宣布有效」——
 * 那正是本轮要防的归因错误。
 */

import { test, after } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

import {
  buildAbPlan,
  derivePackVariant,
  emitVariantPacks,
  variantPackPath,
} from "./real-machine/session-wall-ab.mjs";
import { AB_PLATFORMS, ACTIVE_PLATFORM_IDS, FROZEN_AB_PLATFORMS } from "./real-machine/platform-freeze.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 从本文件所在目录往上找出厂 Pack。
 * 不能写死 `../../packs`：变异检查把 tests/ 复制到
 * `<扩展根>/.mutation-tmp/tests/`，深度多一层，写死会 ENOENT 假红
 * （session-boundary.test.mjs 的 findUpwards 注释记着这个教训）。
 */
function findUpwards(rel) {
  let dir = HERE;
  for (let i = 0; i < 6; i += 1) {
    const candidate = resolve(dir, rel);
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(`找不到 ${rel}`);
}

const PACK_PATH = findUpwards("packs/examples/xiaohongshu_knowledge_creator.json");
const PLAN_SRC = fileURLToPath(
  new URL("./real-machine/session-wall-ab.mjs", import.meta.url),
);
// 落盘自检用系统临时目录，不污染 evidence（变异副本也安全）。
const EVIDENCE_DIR = mkdtempSync(join(tmpdir(), "ab-pack-test-"));
after(() => rmSync(EVIDENCE_DIR, { recursive: true, force: true }));

test("方案默认标注「未执行」，不冒充真机回执", () => {
  const plan = buildAbPlan();
  assert.match(plan.status, /NOT-EXECUTED/);
  assert.equal(
    plan.frozenPlatforms.length,
    FROZEN_AB_PLATFORMS.length,
    "冻结样本集长度跟随常量；写死 2 的话解冻 deepseek 就会红，而那不是 A/B 设计的问题",
  );
});

// ── B1/B2（2026-11-19）：实验对象与冻结样本集解耦 ──────────────────────
// 之前 session-wall-ab 直接读 FROZEN_AB_PLATFORMS，于是「解冻 deepseek」会
// **静默**把 A/B 的实验对象从 2 站改成 1 站——计划少了两轮命令，而没有任何东西
// 说清这是治理状态变了还是实验设计变了。现在两者分开，红线用断言守着。

test("A/B 实验对象必须是冻结样本的子集（不许拿活跃站做实验）", () => {
  const notFrozen = AB_PLATFORMS.filter((id) => !FROZEN_AB_PLATFORMS.includes(id));
  assert.deepEqual(
    notFrozen,
    [],
    "AB_PLATFORMS 里出现了冻结样本集之外的站。解冻某站时要先把它从 AB_PLATFORMS 移出，" +
      "再改 FROZEN_AB_PLATFORMS 与 ACTIVE_PLATFORM_IDS——顺序反了就该在这里红，不许静默通过。",
  );

  const activeSubjects = AB_PLATFORMS.filter((id) => ACTIVE_PLATFORM_IDS.includes(id));
  assert.deepEqual(
    activeSubjects,
    [],
    "红线直说：活跃站是交付源，不许当 A/B 实验对象（实验会扰动它）。",
  );
});

test("计划只跑 AB 实验对象，不跑冻结名单里的其他站", () => {
  const plan = buildAbPlan();
  assert.deepEqual(plan.abPlatforms, [...AB_PLATFORMS], "计划对象必须等于 AB_PLATFORMS");
  assert.deepEqual(
    plan.frozenPlatforms,
    [...FROZEN_AB_PLATFORMS],
    "frozenPlatforms 是治理事实（冻结样本集），不该被实验设计改写",
  );
  assert.deepEqual(
    [...new Set(plan.runMatrix.map((r) => r.platform))],
    [...AB_PLATFORMS],
    "runMatrix 的平台集合必须恰好是实验对象——不许偷偷带上冻结名单里的其它站",
  );
});

/**
 * 当初真正撞墙、被立为 A/B 样本的站——**历史事实**，不随解冻变化。
 * 冻结样本集与实验对象都只能是它的子集：不许把没撞过墙的站当成 A/B 样本。
 */
const WALL_HIT_PLATFORMS = ["deepseek", "longcat"];

test("冻结样本集与实验对象都取自「当初撞墙的两站」，且当前都被闸门拒绝", () => {
  const plan = buildAbPlan();

  // 这里判**子集**而不是相等：解冻 deepseek 后 frozenPlatforms 只剩 longcat。
  // 写成相等就等于把「治理状态」抄成常量，解冻时必红，而红的原因与 A/B 设计无关。
  for (const id of [...FROZEN_AB_PLATFORMS, ...AB_PLATFORMS]) {
    assert.ok(
      WALL_HIT_PLATFORMS.includes(id),
      `${id} 不在「当初撞墙的两站」里，不许被当成 A/B 样本`,
    );
  }
  assert.deepEqual(
    plan.frozenPlatforms,
    [...FROZEN_AB_PLATFORMS],
    "plan 里的冻结集必须就是常量本身，不许二次加工",
  );
  for (const p of plan.platformPolicy) {
    assert.equal(p.allowed, false, `${p.id} 在本方案里必须是被闸门拒绝的状态`);
  }
});

test("变体是 A/B 两组，且只差 fresh_session 一个变量", () => {
  const plan = buildAbPlan();
  assert.equal(plan.variants.length, 2);
  assert.equal(plan.variants[0].packVariant, "no-boundary");
  assert.equal(plan.variants[1].packVariant, "with-boundary");
  assert.equal(
    plan.runMatrix.length,
    AB_PLATFORMS.length * plan.variants.length,
    "站数 × 变体数（从 AB_PLATFORMS 推导，别再写死 4）",
  );
});

test("A 组真的删掉了出厂 Pack 的 fresh_session，B 组原样保留", () => {
  const pack = JSON.parse(readFileSync(PACK_PATH, "utf-8"));
  const stepPath = (p) => p.workflow.steps.find((s) => s.id === "step_8_output");
  assert.equal(stepPath(pack).fresh_session, "prefer", "出厂 Pack 必须有声明，否则这组测试失去前提");

  const a = derivePackVariant(pack, "no-boundary");
  const b = derivePackVariant(pack, "with-boundary");
  assert.equal(stepPath(a).fresh_session, undefined, "A 组必须删干净");
  assert.equal(stepPath(b).fresh_session, "prefer");

  // 除 fresh_session 外，两边必须与出厂 Pack 逐字节一致（只差一个变量）。
  const stripped = (o) => {
    if (Array.isArray(o)) return o.map(stripped);
    if (o && typeof o === "object") {
      const c = {};
      for (const [k, v] of Object.entries(o)) {
        if (k !== "fresh_session") c[k] = stripped(v);
      }
      return c;
    }
    return o;
  };
  assert.deepEqual(stripped(a), stripped(pack), "A 组不许顺手改别的字段");
  assert.deepEqual(b, pack, "B 组就是出厂 Pack 本身");
  assert.deepEqual(stripped(a), stripped(b), "A/B 只允许差 fresh_session");
});

test("derivePackVariant 拒绝未知变体，不静默回退", () => {
  assert.throws(() => derivePackVariant({}, "whatever"), /未知变体/);
});

test("验收判据含「B 组必须真的重置成功」，否则对照作废", () => {
  const a = buildAbPlan().acceptance;
  assert.match(a.resetActuallyHappened, /available === true/);
  assert.match(a.resetActuallyHappened, /messageCountAfter < messageCountBefore/);
  assert.match(a.verdictRule, /A 撞墙且 B 通过/);
  assert.match(a.likeForLike, /只允许差 fresh_session 一个变量/);
  assert.match(a.noDuplicateSend, /续等只发 WAIT_FOR_RESPONSE/);
});

test("归因边界明写「不能归因给重置」，也明写「不能说重置免费」", () => {
  const lines = buildAbPlan().attributionBoundaries.join("\n");
  assert.match(lines, /不能把整包耗时差异归因给会话重置/);
  assert.match(lines, /也不能说「重置免费」/);
  assert.match(lines, /durationMs 非零/);
  assert.match(lines, /混杂变量/);
  assert.match(lines, /step_2 抖动/);
});

test("脚本不启动浏览器、不导入 Pack、不发消息（红线仍是事实）", () => {
  // 只扫**剥离注释后的可执行代码**：注释里讨论 PACK_ID / IMPORT_PACKS 的
  // 契约是必要的说明，不是调用；笼统全文匹配会把文档性文字误判成越线。
  const src = readFileSync(PLAN_SRC, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  for (const forbidden of [
    "chromium.launch",
    "EXECUTE_PACK",
    "IMPORT_PACKS",
    "SEND_TO_AI",
    "chrome.runtime.sendMessage",
  ]) {
    assert.ok(!src.includes(forbidden), `方案脚本的可执行代码不得出现 ${forbidden}`);
  }
  const raw = readFileSync(PLAN_SRC, "utf-8");
  assert.match(raw, /本脚本未启动浏览器、未导入 Pack、未发送任何消息/);
});

test("解冻前置条件写全：用户授权 / 登录态 / dist 一致 / 额度", () => {
  const c = buildAbPlan().unfreezeConditions.join("\n");
  assert.match(c, /明确的解冻指令/);
  assert.match(c, /登录态/);
  assert.match(c, /dist/);
  assert.match(c, new RegExp(`${AB_PLATFORMS.length * 2 * 8} 步`), "额度按实验对象算，不写死 32");
});

// ── 「命令可原样执行」：修的是第一版 PACK_PATH=<variant-pack.json> 占位符 ──

test("计划命令里不许再出现 <...> 占位符", () => {
  const cmds = buildAbPlan().commands;
  assert.equal(
    cmds.length,
    2 + AB_PLATFORMS.length * 2,
    "1 条注释 + 1 条预检 + 每站 2 轮 L2（从 AB_PLATFORMS 推导）",
  );
  for (const c of cmds) {
    assert.ok(!c.includes("<variant-pack.json>"), "占位符会让命令无法原样执行");
    assert.ok(!/<[a-z-]+\.json>/i.test(c), "任何 <...> 形式的路径占位符都不许出现");
  }
});

test("每条 L2 命令的 PACK_PATH 指向真实绝对路径，且 A/B 各用各的文件", () => {
  const cmds = buildAbPlan().commands.filter((c) => c.startsWith("PLATFORM="));
  assert.equal(cmds.length, AB_PLATFORMS.length * 2, "每站 2 轮（2 变体）");
  const byVariant = {};
  for (const c of cmds) {
    const m = c.match(/PACK_PATH=(\S+)/);
    assert.ok(m, "命令必须显式给出 PACK_PATH");
    assert.ok(m[1].startsWith("/"), "必须是绝对路径（cwd 相对路径会随执行目录漂移）");
    assert.match(m[1], /ab-pack-\d{4}-\d{2}-\d{2}\.(no-boundary|with-boundary)\.json$/);
    const variant = c.match(/PACK_VARIANT=(\S+)/)[1];
    assert.ok(m[1].includes(variant), `${variant} 必须用对应变体的 Pack`);
    byVariant[variant] = m[1];
  }
  assert.notEqual(byVariant["no-boundary"], byVariant["with-boundary"], "A/B 不许共用一个文件");
  assert.equal(variantPackPath("no-boundary"), byVariant["no-boundary"]);
  assert.equal(variantPackPath("with-boundary"), byVariant["with-boundary"]);
});

test("预检命令也要显式解冻（打开冻结站页面本身受守卫拦截）", () => {
  const c = buildAbPlan().commands.find((x) => x.includes("PRECHECK=1"));
  assert.ok(c);
  assert.match(c, /ALLOW_FROZEN=1/);
  assert.match(
    c,
    new RegExp(`CANDIDATES=${AB_PLATFORMS.join(",")}`),
    "预检名单必须与实验对象一致，不写死 deepseek,longcat",
  );
});

test("执行顺序写明每轮必须串行（共享同一个 pack_id），且 B 组降级要作废", () => {
  const o = buildAbPlan().executionOrder.join("\n");
  assert.match(o, /串行/);
  assert.match(o, /并行会互相覆盖/);
  assert.match(o, /available:false 这轮作废/);
});

test("emitVariantPacks 纯本地生成两个文件，自检通过且标注未导入未执行", () => {
  const { files, checks } = emitVariantPacks({
    outDir: EVIDENCE_DIR,
    packPath: PACK_PATH,
  });
  assert.equal(files.length, 2);
  assert.equal(checks.aHasNoFreshSession, true);
  assert.equal(checks.bKeepsPrefer, "prefer");
  assert.equal(checks.samePackId, true);
  assert.equal(checks.onlyDiffersByFreshSession, true);
  for (const f of files) {
    assert.ok(existsSync(f.path), `${f.variant} 变体文件必须真的落盘`);
    assert.match(f.sha256, /^[0-9a-f]{64}$/);
    assert.ok(f.bytes > 0);
  }
  // 计划里的 sha256 与实际文件一致，且明确不是回执
  const plan = buildAbPlan({ variantFiles: files });
  for (const v of plan.variantPacks) {
    assert.equal(v.imported, false);
    assert.equal(v.executed, false);
  }
  assert.equal(plan.variantPacks[0].sha256, files[0].sha256);
});

test("emitVariantPacks 遇到出厂 Pack 契约变化必须拒绝，不静默生成坏变体", () => {
  // 必须是**合法 JSON 但契约被改坏**的 Pack：喂一个 .mjs 只会在 JSON.parse
  // 阶段就炸，根本走不到自检，于是「把自检整个删掉」的变异能存活
  // （2026-11-11 局部变异实测存活过一次）。
  const factory = JSON.parse(readFileSync(PACK_PATH, "utf-8"));
  const badId = { ...factory, metadata: { ...factory.metadata, pack_id: "renamed-pack" } };
  const badSteps = { ...factory, workflow: { ...factory.workflow, steps: factory.workflow.steps.slice(0, 7) } };
  for (const [name, bad] of [["pack_id 被改", badId], ["只剩 7 步", badSteps]]) {
    const p = join(EVIDENCE_DIR, `bad-${name.replace(/\W/g, "_")}.json`);
    writeFileSync(p, JSON.stringify(bad));
    assert.throws(
      () => emitVariantPacks({ outDir: EVIDENCE_DIR, packPath: p }),
      /变体自检失败|出厂 Pack 契约变了/,
      `${name} 必须被自检拦下，否则 A/B 两轮会导入一个 EXECUTE_PACK 找不到的包`,
    );
  }
});
