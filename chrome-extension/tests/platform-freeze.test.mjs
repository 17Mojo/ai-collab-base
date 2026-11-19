/**
 * 平台冻结守卫的守护测试。
 *
 * 用户 2026-11-11 红线：仅保留 5 个活跃站，其他冻结不去碰。
 * 2026-11-18 用户改判：千问有反自动化机制，活跃位由 stepfun 接替；
 * qianwen 不再出现在活跃白名单里（生产 adapter 仍保留）。
 * 2026-11-19 用户再次改判：授权解冻 deepseek（P1→P4，含真机验收）⇒ 活跃 6 站，
 * 冻结样本集只剩 longcat。原先用 deepseek 当「冻结站样例」的断言全部换成 longcat，
 * **不是删掉**；另补一条正向断言钉住「deepseek 真活跃且 unfrozenBy=null」。
 * 上一轮的教训是「只读探针」——红线写在注释里，
 * 谁加一行 click 也不会红。这里把红线变成会红的测试。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import {
  ACTIVE_PLATFORM_IDS,
  FROZEN_AB_PLATFORMS,
  assertCandidatesAllowed,
  assertPlatformAllowed,
  evaluatePlatformPolicy,
  isPlatformActive,
  shouldAnnounceUnfreeze,
} from "./real-machine/platform-freeze.mjs";

const L2_DRIVER = fileURLToPath(
  new URL("./real-machine/l2-platform-auto.mjs", import.meta.url),
);

test("白名单恰好是 6 个活跃站：deepseek 已解冻，longcat / qianwen 仍不碰", () => {
  assert.deepEqual(
    [...ACTIVE_PLATFORM_IDS].sort(),
    ["chatglm", "deepseek", "kimi", "stepfun", "yiyan", "yuanbao"],
  );
  for (const id of [...FROZEN_AB_PLATFORMS, "qianwen"]) {
    assert.equal(isPlatformActive(id), false, `${id} 必须处于冻结/不碰状态`);
  }
  assert.equal(
    isPlatformActive("deepseek"),
    true,
    "2026-11-19 授权解冻后 deepseek 必须真的活跃——不是 ALLOW_FROZEN 假放行",
  );
});

test("当前冻结平台默认被硬闸门拒绝（deepseek 已解冻，longcat 仍拦）", () => {
  for (const id of FROZEN_AB_PLATFORMS) {
    assert.throws(
      () => assertPlatformAllowed(id),
      /已冻结/,
      `${id} 不该被放行——放行就等于替用户解冻了`,
    );
  }
});

test("不认识的平台 id 也一律视为冻结，不搞默认放行", () => {
  assert.throws(() => assertPlatformAllowed("gemini"), /已冻结/);
  assert.throws(() => assertPlatformAllowed("some-new-site"), /已冻结/);
});

test("活跃 6 站默认放行，且不留解冻痕迹", () => {
  for (const id of ACTIVE_PLATFORM_IDS) {
    const p = assertPlatformAllowed(id);
    assert.equal(p.allowed, true);
    assert.equal(p.active, true);
    assert.equal(p.unfrozenBy, null);
  }
});

test("只有 ALLOW_FROZEN=1 才放行仍冻结的平台，并在回执里留痕", () => {
  // 样例换成 longcat：deepseek 已于 2026-11-19 被授权解冻，不再是冻结站。
  // 改样例而不是删断言——这道门守的是「例外开关必须留痕」，与具体站点无关。
  assert.equal(evaluatePlatformPolicy("longcat").allowed, false);
  const p = evaluatePlatformPolicy("longcat", { allowFrozen: true });
  assert.equal(p.allowed, true);
  assert.equal(p.active, false, "解冻不改变它「本质是冻结平台」这一事实");
  assert.equal(p.unfrozenBy, "ALLOW_FROZEN=1", "谁解冻的必须可复核");
});

test("解冻后的 deepseek 默认放行且不留例外痕迹（不是 ALLOW_FROZEN 假放行）", () => {
  const p = assertPlatformAllowed("deepseek");
  assert.equal(p.allowed, true);
  assert.equal(p.active, true, "它现在是真活跃站，active 必须是 true");
  assert.equal(p.unfrozenBy, null, "不许带 ALLOW_FROZEN 留痕——那是冻结站才有的标记");
  assert.equal(p.reason, "active", "回执理由必须是 active，不是例外开关");
});

test("候选集里混进一个冻结站，整个预检都拒绝，不许跳过继续", () => {
  assert.throws(
    () => assertCandidatesAllowed(["stepfun", "chatglm", "longcat"]),
    /候选集含冻结平台 \[longcat\]/,
  );
});

test("候选集全活跃时放行，逐个可用的策略都写清楚", () => {
  const rows = assertCandidatesAllowed(["stepfun", "kimi"]);
  assert.equal(rows.length, 2);
  assert.ok(rows.every((r) => r.allowed === true && r.unfrozenBy === null));
});

test("L2 真机驱动在 launch() 之前调用了冻结闸门（接线不能断）", () => {
  const src = readFileSync(L2_DRIVER, "utf-8");
  const gateAt = src.indexOf("assertPlatformAllowed(PLATFORM");
  const candidatesGateAt = src.indexOf("assertCandidatesAllowed(CANDIDATES");
  const launchAt = src.indexOf("await launch()");
  assert.ok(gateAt > -1, "L2 模式必须调用 assertPlatformAllowed");
  assert.ok(candidatesGateAt > -1, "PRECHECK 模式必须调用 assertCandidatesAllowed");
  assert.ok(launchAt > -1, "找不到 launch() 调用点");
  assert.ok(
    gateAt < launchAt && candidatesGateAt < launchAt,
    "闸门必须在 launch() 之前——冻结站连浏览器都不该启动",
  );
});

test("L2 驱动把放行策略与 Pack 变体写进回执", () => {
  const src = readFileSync(L2_DRIVER, "utf-8");
  // 必须绑**运行时的策略变量**，不能是一个写死的 null。
  // 只断言 `platformPolicy:` 存在是不够的——预检回执里也有同名字段，
  // 于是「把 L2 回执的策略改成常量」这种改坏根本咬不到（变异实测存活过一次）。
  assert.match(
    src,
    /platformPolicy: platformPolicy \|\| null/,
    "L2 回执要绑定运行时平台策略，不能是写死的常量",
  );
  assert.match(src, /packVariant:/, "A/B 轮次标签要能区分");
  assert.match(src, /packPath:/, "变体 Pack 路径要可复核");
  assert.match(src, /platformPolicy: CANDIDATES\.map/, "预检回执也要留逐站策略");
});


// ─────────────────────────────────────────────────────────────────────
// N35 解冻留痕判据
//
// 这条日志是「谁在什么时候解冻过」的唯一运行时线索。旧实现用
// `!policy.active` 当代理，在 PRECHECK 下对已移出白名单的默认 PLATFORM
// 打出「已按 ALLOW_FROZEN=1 放行」——事实相反，且没人解冻过。
// ─────────────────────────────────────────────────────────────────────

test("N35 回归：预检模式下不得打出解冻留痕（预检不碰 PLATFORM）", () => {
  const frozen = evaluatePlatformPolicy("qianwen", { allowFrozen: false });
  assert.equal(frozen.active, false, "前提：qianwen 已冻结");
  assert.equal(frozen.unfrozenBy, null);
  assert.equal(
    shouldAnnounceUnfreeze(frozen, { precheck: true }),
    false,
    "预检只开 CANDIDATES，对 PLATFORM 断言无依据 ⇒ 不许打",
  );
});

test("N35 回归：预检 + 真的解冻过，仍不许打（这条才守住 precheck 分支）", () => {
  // 关键用例：设了 ALLOW_FROZEN=1 时 unfrozenBy 有值，第二个条件（非空字符串）会满足，
  // 此时**只有 precheck 守卫能拦住**。预检只打开 CANDIDATES，从不打开 PLATFORM，
  // 所以对 PLATFORM 打「已放行」依旧是无依据的假日志。
  // 若有人删掉 `if (opts.precheck === true) return false;`，这条必须变红。
  const unfrozen = evaluatePlatformPolicy("longcat", { allowFrozen: true });
  assert.equal(unfrozen.unfrozenBy, "ALLOW_FROZEN=1", "前提：确实处于解冻态");
  assert.equal(shouldAnnounceUnfreeze(unfrozen, { precheck: false }), true, "非预检时该打");
  assert.equal(
    shouldAnnounceUnfreeze(unfrozen, { precheck: true }),
    false,
    "预检下即便解冻过也不打——预检压根没碰这个平台",
  );
});

test("N35 回归：冻结但未解冻 ⇒ 不打（旧实现会在这里误报）", () => {
  const frozen = evaluatePlatformPolicy("qianwen", { allowFrozen: false });
  assert.equal(shouldAnnounceUnfreeze(frozen, { precheck: false }), false);
});

test("真正解冻过 ⇒ 打，且靠 unfrozenBy 而非 active 判定", () => {
  const unfrozen = evaluatePlatformPolicy("longcat", { allowFrozen: true });
  assert.equal(unfrozen.active, false, "解冻不等于变成活跃站");
  assert.equal(shouldAnnounceUnfreeze(unfrozen, { precheck: false }), true);
});

test("活跃站不需要解冻留痕（它压根没被冻过）", () => {
  const active = evaluatePlatformPolicy("stepfun", { allowFrozen: false });
  assert.equal(shouldAnnounceUnfreeze(active, { precheck: false }), false);
});

test("字段缺失不得被当成「已解冻」（undefined !== null 的坑）", () => {
  assert.equal(shouldAnnounceUnfreeze({}, { precheck: false }), false);
  assert.equal(shouldAnnounceUnfreeze(null, { precheck: false }), false);
  assert.equal(shouldAnnounceUnfreeze(undefined, { precheck: false }), false);
  assert.equal(shouldAnnounceUnfreeze({ unfrozenBy: "" }, { precheck: false }), false);
});
