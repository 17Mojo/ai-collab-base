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

const files = collectTestFiles(TESTS_ROOT).sort();

if (files.length === 0) {
  console.error("没有找到任何 *.test.mjs——这本身就是个问题：门禁会空跑。");
  process.exit(1);
}

console.log(`发现 ${files.length} 个测试文件：`);
for (const f of files) {
  console.log(`  - ${relative(TESTS_ROOT, f)}`);
}
console.log("");

const res = spawnSync(process.execPath, ["--test", ...files], {
  stdio: "inherit",
  cwd: TESTS_ROOT,
});

process.exit(res.status ?? 1);
