/**
 * 平台冻结守卫的守护测试。
 *
 * 用户 2026-11-11 红线：仅保留 qianwen / yuanbao / chatglm / yiyan / kimi，
 * 其他冻结不去碰。上一轮的教训是「只读探针」——红线写在注释里，
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
} from "./real-machine/platform-freeze.mjs";

const L2_DRIVER = fileURLToPath(
  new URL("./real-machine/l2-platform-auto.mjs", import.meta.url),
);

test("白名单恰好是 5 个活跃站，不含 deepseek / longcat", () => {
  assert.deepEqual(
    [...ACTIVE_PLATFORM_IDS].sort(),
    ["chatglm", "kimi", "qianwen", "yiyan", "yuanbao"],
  );
  for (const id of FROZEN_AB_PLATFORMS) {
    assert.equal(isPlatformActive(id), false, `${id} 必须处于冻结状态`);
  }
});

test("冻结平台默认被硬闸门拒绝（deepseek / longcat 都拦）", () => {
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

test("活跃 5 站默认放行，且不留解冻痕迹", () => {
  for (const id of ACTIVE_PLATFORM_IDS) {
    const p = assertPlatformAllowed(id);
    assert.equal(p.allowed, true);
    assert.equal(p.active, true);
    assert.equal(p.unfrozenBy, null);
  }
});

test("只有 ALLOW_FROZEN=1 才放行冻结平台，并在回执里留痕", () => {
  assert.equal(evaluatePlatformPolicy("deepseek").allowed, false);
  const p = evaluatePlatformPolicy("deepseek", { allowFrozen: true });
  assert.equal(p.allowed, true);
  assert.equal(p.active, false, "解冻不改变它「本质是冻结平台」这一事实");
  assert.equal(p.unfrozenBy, "ALLOW_FROZEN=1", "谁解冻的必须可复核");
});

test("候选集里混进一个冻结站，整个预检都拒绝，不许跳过继续", () => {
  assert.throws(
    () => assertCandidatesAllowed(["qianwen", "chatglm", "longcat"]),
    /候选集含冻结平台 \[longcat\]/,
  );
});

test("候选集全活跃时放行，逐个可用的策略都写清楚", () => {
  const rows = assertCandidatesAllowed(["qianwen", "kimi"]);
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
