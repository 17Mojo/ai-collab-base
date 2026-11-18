/**
 * 扩展单测入口
 *
 * ## 为什么不直接用 `node --test`
 *
 * 三种写法各有各的坑：
 *   - `node --test`（自动发现）：会把仓库里**所有**符合命名规则的目录都扫一遍。
 *     本仓 `tests/playwright/node_modules` 下面有大量第三方测试文件，
 *     扫进去要跑十几分钟甚至挂住——实测在本机就是直接卡死。
 *   - `node --test tests/real-machine/`（目录形式）：Node 23 上直接报
 *     `Cannot find module '.../tests'`，因为它把参数当模块解析。
 *   - `node --test "tests/<双星号>/<任意目录>/x.test.mjs"`（glob 形式）：Node 21+ 才支持，
 *     而 CI 现在钉的是 Node 20。
 *
 * 所以这里自己枚举文件、显式传路径——**Node 18+ 都能跑**，
 * CI 与本地用同一条命令，不会出现「本地绿、CI 跑不到」的经典假绿。
 *
 * 用法：node tests/run-tests.mjs
 * 退出码：0 = 全过；非 0 = 有失败（沿用 node --test 的退出码语义）
 *
 * ## 为什么要打印「受跟踪 / 本次运行」两个数（台账 N39）
 *
 * 收集器是 `readdirSync` 扫目录，不看 git 跟踪状态。于是**结论是工作区属性，不是 commit 属性**：
 * 2026-11-18 实测同一 commit，干净工作区 318 条全绿，本工作区 334 条里 4 条失败，
 * 而失败的四条测的是一个只在那片磁盘上存在、从未提交的特性。
 *
 * 所以每次运行都会：
 *   1. 首行给出「受跟踪 N / 本次运行 M / 未跟踪 K」；
 *   2. 未跟踪文件在清单里带 `[未跟踪]` 标记，并单独警告；
 *   3. 结尾再打一行 `[test-inventory]`，把「跑的是什么范围」和 pass/fail 钉在一起。
 *
 * **为什么不阻断**：本地「先写测试再 add」是正常节奏，阻断会逼人去绕。
 * **为什么报文件数而不是用例数**：用例数只能靠解析 TAP 或正则数 `test(`
 * ——前者要么改掉即时输出、要么依赖 Node 20.10+ 的多 reporter；后者会数错，
 * 而**数错的不变量比没有更糟**（会天天假警报，然后被忽略）。N39 的实际故障形态
 * 本来就是文件级差异，文件数足以让它现形。
 */

import { readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const TESTS_ROOT = resolve(HERE, "..");

/**
 * 递归收集测试文件。
 * @param {string} dir
 * @param {string[]} out
 * @returns {string[]}
 */
function collectTestFiles(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      collectTestFiles(full, out);
    } else if (entry.endsWith(".test.mjs")) {
      out.push(full);
    }
  }
  return out;
}

/**
 * 列出**被 git 跟踪**的测试文件（绝对路径）。
 *
 * 存在的理由（台账 N39）：收集器是 `readdirSync` 扫目录，不查跟踪状态，
 * 于是在工作区里放一个未提交的 `xxx.test.mjs`，用例数就会变、结论也会变。
 * 2026-11-18 实测过代价：同一 commit，干净工作区 318 条全绿，本工作区 334 条里 4 条失败，
 * 而失败的四条测的是一个**只在那片磁盘上存在、从未提交**的特性。
 * 「重跑一遍」对这种问题无效——它读的还是同一片磁盘。
 *
 * @returns {Set<string>|null} null 表示无法判定（git 不可用/不在仓库里），
 *   不假装知道——「不知道」和「都跟踪了」必须能区分。
 */
function trackedTestFiles() {
  const res = spawnSync("git", ["ls-files", "--", "*.test.mjs"], {
    cwd: TESTS_ROOT,
    encoding: "utf-8",
  });
  if (res.status !== 0 || res.error) return null;
  const set = new Set();
  for (const line of String(res.stdout || "").split("\n")) {
    const rel = line.trim();
    if (rel) set.add(resolve(TESTS_ROOT, rel));
  }
  return set;
}

const files = collectTestFiles(TESTS_ROOT).sort();

if (files.length === 0) {
  console.error("没有找到任何 *.test.mjs——这本身就是个问题：门禁会空跑。");
  process.exit(1);
}

const tracked = trackedTestFiles();
const runAbsolute = files.map((f) => resolve(f));
const untrackedFiles = tracked
  ? runAbsolute.filter((f) => !tracked.has(f))
  : [];

const inventoryLine = tracked
  ? `受跟踪 ${tracked.size} 个 / 本次运行 ${files.length} 个 / 未跟踪 ${untrackedFiles.length} 个`
  : `本次运行 ${files.length} 个 / 跟踪状态无法判定（git 不可用）`;

console.log(`发现 ${files.length} 个测试文件（${inventoryLine}）：`);
for (const f of files) {
  const mark = untrackedFiles.includes(resolve(f)) ? "  [未跟踪]" : "";
  console.log(`  - ${relative(TESTS_ROOT, f)}${mark}`);
}
console.log("");

if (untrackedFiles.length > 0) {
  // 不阻断：本地开发时「先写测试再 add」是正常节奏。但必须让人看见，
  // 否则「测试绿/红」会被当成本 commit 的属性，而它其实是工作区属性。
  console.warn("⚠️ 本次包含未跟踪的测试文件——干净检出下不会运行，结论不可复现：");
  for (const f of untrackedFiles) {
    console.warn(`  - ${relative(TESTS_ROOT, f)}`);
  }
  console.warn("  要么 git add 它，要么先挪走再跑；否则本结论只在这片磁盘上成立。");
  console.warn("");
}

const res = spawnSync(process.execPath, ["--test", ...files], {
  stdio: "inherit",
  cwd: TESTS_ROOT,
});

// 结论行放在最后：把「这次跑了什么范围的用例」和用例结果钉在一起，
// 避免只记住 pass/fail 数字却不知道自己跑的不是同一个集合（N39）。
console.log("");
console.log(`[test-inventory] ${inventoryLine}`);
if (untrackedFiles.length > 0) {
  console.log("[test-inventory] 注意：结论含未提交用例，不可作为 commit 级结论引用。");
}

process.exit(res.status ?? 1);
