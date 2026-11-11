/**
 * 「会话边界能不能解掉长会话撞墙」A/B 方案的守护测试。
 *
 * 守的不是「代码跑得通」，而是**判据没被悄悄稀释**：
 * 一旦有人把「B 组必须真的开了新会话」或「不能归因给重置」这些
 * 边界删掉，方案就会退化成「跑一轮 B 成功就宣布有效」——
 * 那正是本轮要防的归因错误。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { buildAbPlan, derivePackVariant } from "./real-machine/session-wall-ab.mjs";
import { FROZEN_AB_PLATFORMS } from "./real-machine/platform-freeze.mjs";

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

test("方案默认标注「未执行」，不冒充真机回执", () => {
  const plan = buildAbPlan();
  assert.match(plan.status, /NOT-EXECUTED/);
  assert.equal(plan.frozenPlatforms.length, 2);
});

test("冻结的两个站恰好是当初真正撞墙的 deepseek / longcat", () => {
  const plan = buildAbPlan();
  assert.deepEqual(plan.frozenPlatforms, ["deepseek", "longcat"]);
  assert.deepEqual(FROZEN_AB_PLATFORMS, ["deepseek", "longcat"]);
  for (const p of plan.platformPolicy) {
    assert.equal(p.allowed, false, `${p.id} 在本方案里必须是被闸门拒绝的状态`);
  }
});

test("变体是 A/B 两组，且只差 fresh_session 一个变量", () => {
  const plan = buildAbPlan();
  assert.equal(plan.variants.length, 2);
  assert.equal(plan.variants[0].packVariant, "no-boundary");
  assert.equal(plan.variants[1].packVariant, "with-boundary");
  assert.equal(plan.runMatrix.length, 4, "2 站 × 2 变体");
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
  const src = readFileSync(PLAN_SRC, "utf-8");
  for (const forbidden of [
    "chromium.launch",
    "EXECUTE_PACK",
    "IMPORT_PACKS",
    "SEND_TO_AI",
    "chrome.runtime.sendMessage",
  ]) {
    assert.ok(!src.includes(forbidden), `方案脚本不得出现 ${forbidden}`);
  }
  assert.match(src, /本脚本未启动浏览器、未导入 Pack、未发送任何消息/);
});

test("解冻前置条件写全：用户授权 / 登录态 / dist 一致 / 额度", () => {
  const c = buildAbPlan().unfreezeConditions.join("\n");
  assert.match(c, /明确的解冻指令/);
  assert.match(c, /登录态/);
  assert.match(c, /dist/);
  assert.match(c, /32 步/);
});
