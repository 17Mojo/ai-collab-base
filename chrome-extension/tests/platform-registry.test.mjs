/**
 * 平台登记表跨文件一致性守护
 *
 * 背景（2026-10-25）：平台清单曾经分散在**四份**拷贝里——
 *   1. `tests/adapter-matrix/adapter-test-runner.js` 的 PLATFORMS（模拟层）
 *   2. `tests/real-machine/dom-contract-probe.mjs` 的 PLATFORMS（真机层，**只 3 家**）
 *   3. `src/content/content-script.js` 的 PLATFORM_CONFIGS（生产层，16 个 hostname）
 *   4. `src/background/multi-platform-executor.js` 的 platformUrls（生产层，10 个）
 *
 * 四份拷贝之间会漂移，而且**漂移是静默的**：真机探针那份只登记 3 家，
 * 于是 deepseek / kimi / longcat / qianwen / yiyan / yuanbao / chatglm
 * 这 7 家**从未进入过真机回归**——而模拟层矩阵长期 110/114 全绿，
 * 看上去一切正常。矩阵绿 ≠ 真机覆盖到了。
 *
 * 现在：
 *   - 模拟层与真机层都从 `tests/platforms.mjs` 派生（本守护的 6 号检查项）；
 *   - 生产层的两处**不改**（超出工单范围），改由本文件做**双向对账**，
 *     一旦生产层新增/删除了平台而登记表没跟上，测试立刻报红。
 *
 * 这不是形式主义：2026-10-25 的 Gemini 缺陷之所以能潜伏，
 * 正是因为「模拟层全绿」被当成了「真机也覆盖了」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

import { PLATFORMS, allHostnames, getPlatform } from "./platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "..");
const PLATFORMS_DIR = join(EXT_ROOT, "src", "platforms");
const FIXTURES_DIR = join(HERE, "adapter-matrix", "fixtures");

/**
 * 从 `src/content/content-script.js` 里解析 PLATFORM_CONFIGS 的键（hostname）。
 * 用正则而不是 import——该文件是 content script，import 会拖进浏览器 API。
 * @param {string} source
 * @returns {string[]}
 */
function parseContentScriptHostnames(source) {
  const block = source.match(/const PLATFORM_CONFIGS\s*=\s*\{([\s\S]*?)\n\};/);
  assert.ok(block, "content-script.js 里应能找到 PLATFORM_CONFIGS");
  return [...block[1].matchAll(/"([^"]+)"\s*:/g)].map((m) => m[1]);
}

/**
 * 从 `src/background/multi-platform-executor.js` 里解析 platformUrls 的键。
 * @param {string} source
 * @returns {string[]}
 */
function parseExecutorHostnames(source) {
  const block = source.match(/const platformUrls\s*=\s*\{([\s\S]*?)\n\s*\};/);
  assert.ok(block, "multi-platform-executor.js 里应能找到 platformUrls");
  return [...block[1].matchAll(/'([^']+)'\s*:/g)].map((m) => m[1]);
}

/**
 * 从 manifest 的 matches / host_permissions 里抽出 hostname。
 * @param {string[]} patterns
 * @returns {string[]}
 */
function hostnamesFromPatterns(patterns) {
  return patterns
    .map((p) => p.match(/^https?:\/\/([^/]+)/))
    .filter(Boolean)
    .map((m) => m[1]);
}

// ---------------------------------------------------------------------------
// 1. 登记表 ↔ 生产 adapter 文件
// ---------------------------------------------------------------------------

test("登记表里的每个平台都有对应的生产 adapter 文件", () => {
  for (const p of PLATFORMS) {
    const file = join(PLATFORMS_DIR, p.module);
    assert.ok(existsSync(file), `平台 ${p.id} 登记的 module 不存在：${p.module}`);
  }
});

test("生产目录下的每个 adapter 都已在登记表里（没有漏登记的平台）", () => {
  const files = readdirSync(PLATFORMS_DIR).filter((f) => f.endsWith("-adapter.js"));
  const registered = new Set(PLATFORMS.map((p) => p.module));
  const orphans = files.filter((f) => !registered.has(f));
  assert.deepEqual(
    orphans,
    [],
    `这些生产 adapter 没有登记进 tests/platforms.mjs：${orphans.join(", ")}` +
      "——真机探针会漏掉它们（这正是 2026-10-25 那 7 家平台漏检的成因）",
  );
});

test("每个平台的 module 字段与 id 对得上（<id>-adapter.js 约定）", () => {
  for (const p of PLATFORMS) {
    assert.equal(p.module, `${p.id}-adapter.js`, `平台 ${p.id} 的 module 命名与 id 不一致`);
  }
});

// ---------------------------------------------------------------------------
// 2. 登记表 ↔ 生产层 hostname 清单（双向对账）
// ---------------------------------------------------------------------------

test("登记表 hostname 与 content-script 的 PLATFORM_CONFIGS 完全一致", () => {
  const source = readFileSync(join(EXT_ROOT, "src", "content", "content-script.js"), "utf-8");
  const actual = new Set(parseContentScriptHostnames(source));
  const expected = new Set(allHostnames());

  const missing = [...expected].filter((h) => !actual.has(h));
  const extra = [...actual].filter((h) => !expected.has(h));

  assert.deepEqual(missing, [], `content-script.js 缺少这些 hostname：${missing.join(", ")}`);
  assert.deepEqual(extra, [], `content-script.js 多出这些 hostname：${extra.join(", ")}`);
});

test("multi-platform-executor 的 platformUrls 不含登记表之外的域名", () => {
  const source = readFileSync(join(EXT_ROOT, "src", "background", "multi-platform-executor.js"), "utf-8");
  const actual = new Set(parseExecutorHostnames(source));
  const expected = new Set(allHostnames());

  const extra = [...actual].filter((h) => !expected.has(h));
  assert.deepEqual(extra, [], `multi-platform-executor.js 出现登记表之外的域名：${extra.join(", ")}`);
});

test("multi-platform-executor 的 platformUrls 未覆盖全部平台——如实记账，不假装齐全", () => {
  // 该文件目前是**死代码**（无人 import），只覆盖 10/16 个 hostname。
  // 本断言把这条既成事实钉住：如果将来有人补齐了它，本测试会提醒更新这条记账。
  const source = readFileSync(join(EXT_ROOT, "src", "background", "multi-platform-executor.js"), "utf-8");
  const actual = new Set(parseExecutorHostnames(source));
  const missing = allHostnames().filter((h) => !actual.has(h));
  assert.ok(
    missing.length > 0,
    "multi-platform-executor.js 现在覆盖了全部 hostname——请更新本测试的记账与相关文档",
  );
});

// ---------------------------------------------------------------------------
// 3. 登记表 ↔ manifest
// ---------------------------------------------------------------------------

test("manifest 的 content_scripts matches 覆盖登记表全部 hostname", () => {
  const manifest = JSON.parse(readFileSync(join(EXT_ROOT, "manifest.json"), "utf-8"));
  const patterns = manifest.content_scripts.flatMap((cs) => cs.matches);
  const covered = new Set(hostnamesFromPatterns(patterns));

  const missing = allHostnames().filter((h) => !covered.has(h));
  assert.deepEqual(missing, [], `manifest 的 content_scripts 没覆盖：${missing.join(", ")}`);
});

test("manifest 的 host_permissions 覆盖登记表全部 hostname", () => {
  const manifest = JSON.parse(readFileSync(join(EXT_ROOT, "manifest.json"), "utf-8"));
  const covered = new Set(hostnamesFromPatterns(manifest.host_permissions));

  const missing = allHostnames().filter((h) => !covered.has(h));
  assert.deepEqual(missing, [], `manifest 的 host_permissions 没覆盖：${missing.join(", ")}`);
});

// ---------------------------------------------------------------------------
// 4. 登记表 ↔ 模拟层 fixture
// ---------------------------------------------------------------------------

test("每个平台都有对应的模拟层 fixture 文件", () => {
  for (const p of PLATFORMS) {
    const file = join(FIXTURES_DIR, `mock-dom-${p.fixture}.html`);
    assert.ok(existsSync(file), `平台 ${p.id} 缺少 fixture：mock-dom-${p.fixture}.html`);
  }
});

test("fixture 标识与平台 id 一致（避免同一份 fixture 被两个平台共用）", () => {
  for (const p of PLATFORMS) {
    assert.equal(p.fixture, p.id, `平台 ${p.id} 的 fixture 标识与 id 不一致`);
  }
});

// ---------------------------------------------------------------------------
// 5. 登记表自身的完整性
// ---------------------------------------------------------------------------

test("平台 id 与 hostname 都不得重复", () => {
  const ids = PLATFORMS.map((p) => p.id);
  assert.deepEqual(ids, [...new Set(ids)], "平台 id 有重复");

  const hosts = allHostnames();
  assert.deepEqual(hosts, [...new Set(hosts)], "hostname 有重复");
});

test("getPlatform() 能按 id 查到平台，查不到返回 undefined", () => {
  assert.equal(getPlatform("gemini")?.id, "gemini");
  assert.equal(getPlatform("no-such-platform"), undefined);
});

test("登记表覆盖 10 个平台（2026-10-25 基线）", () => {
  // 平台数量变化时这条会提醒同步文档与矩阵基线，而不是静默漂移。
  assert.equal(PLATFORMS.length, 10);
});

// ---------------------------------------------------------------------------
// 6. 禁止再出现手抄的平台清单
// ---------------------------------------------------------------------------

const NO_HARDCODED_LIST = [
  { file: "adapter-matrix/adapter-test-runner.js", label: "模拟层 runner" },
  { file: "real-machine/dom-contract-probe.mjs", label: "真机探针" },
];

test("模拟层与真机层都从唯一事实源导入平台清单（不再手抄）", () => {
  for (const { file, label } of NO_HARDCODED_LIST) {
    const source = readFileSync(join(HERE, file), "utf-8");
    assert.match(
      source,
      /from\s+["'][^"']*platforms\.mjs["']/,
      `${label} 必须从 tests/platforms.mjs 导入平台清单`,
    );
  }
});

test("模拟层与真机层里不出现手写的平台条目", () => {
  // 命中形如 `id: "chatgpt"` 的字面量 = 又抄了一份清单。
  for (const { file, label } of NO_HARDCODED_LIST) {
    const source = readFileSync(join(HERE, file), "utf-8");
    for (const p of PLATFORMS) {
      assert.doesNotMatch(
        source,
        new RegExp(`id\\s*:\\s*["']${p.id}["']`),
        `${label} 里出现了手写的平台条目（id: "${p.id}"）——请改从 tests/platforms.mjs 派生`,
      );
    }
  }
});
