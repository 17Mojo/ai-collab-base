/**
 * CI 接线守护
 *
 * ## 为什么要有这个
 *
 * 本仓吃过一次很具体的亏：`test.yml` 里的扩展测试步骤写的是
 *
 *   node tests/test-adapters.js 2>/dev/null || echo "adapter tests skipped"
 *
 * 而那两个文件早被归档到 `tests/_archive/` —— 命令**必然失败**，
 * 于是**必然**走进 `|| echo` 分支。CI 长期绿灯，
 * 实际**一个扩展测试都没跑过**。
 *
 * 这类失败的特点是：**不会有人发现**。门禁显示通过，正是它坏的信号。
 *
 * 所以这里把「CI 确实在跑扩展测试」变成机检：
 *   - 步骤必须存在；
 *   - 命令后面**不许**跟吞掉失败的 `|| echo` / `|| true`；
 *   - 那个已经失效的旧命令不许复活。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(EXT_ROOT, "..");
const WORKFLOW = join(REPO_ROOT, ".github", "workflows", "test.yml");

const yaml = readFileSync(WORKFLOW, "utf-8");

/**
 * 只看**会真正执行**的行。
 *
 * YAML 里 `#` 开头的行是注释，YAML 解析器会丢掉它们；
 * 而 test.yml 里偏偏**把那个早就失效的旧命令写在注释里**（作为「曾经错在哪」的说明），
 * 所以直接对整份文件做字符串匹配会误报。
 * 真正的命令出现在 `run: |` 块的**内容**里——那些行不以 `#` 开头。
 */
const commandLines = yaml
  .split("\n")
  .filter((line) => !line.trim().startsWith("#"))
  .map((line) => line.trim());

/** 去掉 YAML 注释后的正文——「步骤存在吗」这类判断必须看这份，不能看注释。 */
const yamlNoComments = yaml
  .split("\n")
  .filter((line) => !line.trim().startsWith("#"))
  .join("\n");

test("CI 存在扩展测试作业", () => {
  assert.ok(yaml.includes("chrome-extension-tests:"), "test.yml 里没有 chrome-extension-tests 作业");
});

test("CI 跑扩展单测入口（node tests/run-tests.mjs）", () => {
  assert.ok(
    yamlNoComments.includes("node tests/run-tests.mjs"),
    "扩展单测入口没接进 CI——新加的测试不会在门禁里跑",
  );
});

test("CI 跑 adapter 矩阵", () => {
  assert.ok(
    yamlNoComments.includes("node tests/adapter-matrix/adapter-test-runner.js"),
    "adapter 矩阵没接进 CI",
  );
});

test("扩展测试命令后面不许吞掉失败", () => {
  // 逐行看真正会执行的命令行：任何 `|| echo` / `|| true` / `2>/dev/null` 都是吞失败的信号
  const offenders = commandLines.filter(
    (t) =>
      t.startsWith("node ") &&
      (t.includes("|| echo") || t.includes("|| true") || t.includes("2>/dev/null")),
  );
  assert.deepEqual(
    offenders,
    [],
    `这些命令会吞掉失败，让门禁形同虚设：\n${offenders.join("\n")}`,
  );
});

test("那个早就失效的旧测试命令不许复活", () => {
  // tests/test-adapters.js 早已归档，它必然失败，配上 || echo 就是长绿的来源
  assert.ok(
    !commandLines.some((t) => t.includes("tests/test-adapters.js")),
    "test.yml 又写回了 tests/test-adapters.js——那个文件早归档了，命令必然失败",
  );
});

test("CI 用的 Node 版本够跑测试入口", () => {
  const m = yamlNoComments.match(/node-version:\s*"?(\d+)/);
  assert.ok(m, "test.yml 里找不到 node-version");
  const major = Number(m[1]);
  // tests/run-tests.mjs 只用 node:fs / node:path / node:child_process，18+ 即可；
  // 但 node:test 的 assert/strict 断言在 18 上行为略有差异，统一要求 20+
  assert.ok(major >= 20, `CI 的 Node 版本 ${major} 低于 20，应升到 20 或更高`);
});

test("单测入口存在且会跳过 node_modules", () => {
  const runner = join(EXT_ROOT, "tests", "run-tests.mjs");
  assert.ok(existsSync(runner), "缺少 tests/run-tests.mjs 单测入口");
  const src = readFileSync(runner, "utf-8");
  assert.ok(
    src.includes('entry === "node_modules"'),
    "单测入口必须跳过 node_modules——自动发现会把 tests/playwright/node_modules 扫进去，直接卡死",
  );
});

test("变异检查存在且不污染工作区", () => {
  const m = join(EXT_ROOT, "tests", "real-machine", "mutation-check.mjs");
  assert.ok(existsSync(m), "缺少变异检查脚本");
  const src = readFileSync(m, "utf-8");
  assert.ok(
    src.includes(".mutation-tmp"),
    "变异检查必须在临时副本上跑——就地改坏工作区的话，中途崩了就留下半个坏文件",
  );
});
