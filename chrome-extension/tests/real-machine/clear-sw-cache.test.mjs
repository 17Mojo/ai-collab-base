/**
 * SW ScriptCache 清理器守卫测试（台账 N15）
 *
 * 这个清理器要删的东西在用户机器的持久 profile 里——删错范围的代价是
 * 丢登录态/丢浏览器数据。所以这里最要紧的两条不变量：
 *   1. 只删 Default/{Service Worker, Code Cache, Extension Scripts} 三个缓存目录；
 *   2. 路径不长得像 Chrome profile 就拒绝执行。
 *
 * 用例全部跑临时目录 fixture，不碰任何真实 profile。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { CACHE_DIRS, clearSwCaches, planCleanup } from "./clear-sw-cache.mjs";

/** 搭一个假 Chrome profile：三个缓存目录 + 两个必须存活的邻居 */
function makeFakeProfile() {
  const root = mkdtempSync(join(tmpdir(), "sw-cache-test-"));
  const def = join(root, "Default");
  for (const d of [...CACHE_DIRS, "Preferences", "Local Storage"]) {
    mkdirSync(join(def, d), { recursive: true });
    writeFileSync(join(def, d, "dummy.bin"), "x".repeat(64));
  }
  // 缓存目录里再埋一层子文件，确保递归删除与计数路径都有覆盖
  mkdirSync(join(def, "Service Worker", "ScriptCache"), { recursive: true });
  writeFileSync(join(def, "Service Worker", "ScriptCache", "hash_0"), "old-build");
  return { root, def };
}

test("planCleanup 拒绝空路径", () => {
  const plan = planCleanup("");
  assert.equal(plan.ok, false);
  assert.equal(plan.targets.length, 0);
});

test("planCleanup 拒绝非 Chrome profile（缺 Default/）", () => {
  const root = mkdtempSync(join(tmpdir(), "sw-cache-notprofile-"));
  const plan = planCleanup(root);
  assert.equal(plan.ok, false);
  assert.match(plan.reason, /不是 Chrome profile/);
});

test("planCleanup 只认三个缓存子目录", () => {
  const { root } = makeFakeProfile();
  const plan = planCleanup(root);
  assert.equal(plan.ok, true);
  assert.equal(plan.targets.length, 3);
  for (const t of plan.targets) {
    assert.ok(CACHE_DIRS.some((d) => t.endsWith(`Default/${d}`)), t);
  }
  // 变异锚：绝不能包含 Cookies / Local Storage / Preferences 之类
  for (const forbidden of ["Cookies", "Local Storage", "Preferences", "History"]) {
    assert.ok(!plan.targets.some((t) => t.includes(forbidden)), forbidden);
  }
});

test("clearSwCaches 删三缓存、留邻居（防过删锚）", () => {
  const { root, def } = makeFakeProfile();
  const result = clearSwCaches(root);

  assert.equal(result.ok, true);
  assert.equal(result.removed.length, 3);
  for (const d of CACHE_DIRS) {
    assert.equal(existsSync(join(def, d)), false, `${d} 应被删除`);
  }
  // 变异锚：这两个目录掉一个就是删过界
  assert.ok(existsSync(join(def, "Preferences")), "Preferences 必须存活");
  assert.ok(existsSync(join(def, "Local Storage")), "Local Storage 必须存活");
  // 删除计数应统计到嵌套文件
  const sw = result.removed.find((r) => r.path.endsWith("Service Worker"));
  assert.ok(sw.files >= 2, `Service Worker 应统计到嵌套文件，实际 ${sw.files}`);
});

test("clearSwCaches dry-run 不实际删除", () => {
  const { root, def } = makeFakeProfile();
  const result = clearSwCaches(root, { dryRun: true });

  assert.equal(result.ok, true);
  assert.equal(result.dryRun, true);
  assert.equal(result.removed.length, 3); // 计划里有三项
  for (const d of CACHE_DIRS) {
    assert.ok(existsSync(join(def, d)), `${d} dry-run 后应仍在`);
  }
});

test("clearSwCaches 对缺目录不炸，记 skipped", () => {
  const root = mkdtempSync(join(tmpdir(), "sw-cache-empty-"));
  mkdirSync(join(root, "Default"), { recursive: true });
  const result = clearSwCaches(root);

  assert.equal(result.ok, true);
  assert.equal(result.removed.length, 0);
  assert.equal(result.skipped.length, 3);
});

test("clearSwCaches 对非 profile 返回 ok:false 而非抛错", () => {
  const root = mkdtempSync(join(tmpdir(), "sw-cache-bad-"));
  const result = clearSwCaches(root);
  assert.equal(result.ok, false);
  assert.match(result.reason, /不是 Chrome profile/);
});
