/**
 * 平台等待上限覆盖表（PLATFORM_RESPONSE_TIMEOUT）的一致性契约
 *
 * ## 为什么需要这组测试（2026-11-11）
 *
 * 这张表的查找方式是 `PLATFORM_RESPONSE_TIMEOUT[currentPlatformId]`，
 * 而 `currentPlatformId` 来自 background 回的 **adapterId**，取值就是 hostname
 * （能对上 `PLATFORM_CONFIGS[response.adapterId]` 才算命中）。
 *
 * 于是有一个**静默失效**的失败模式：键写错一个字符（比如 `www.chatglm.cn`、
 * `chatglm.com`），查表得到 `undefined`，`?? ...` 直接回落到 60s 默认值 ——
 * **不报错、不告警、日志里也看不出来**，只表现为「配了没用」。
 *
 * 2026-11-11 就踩过相邻的坑：`adapter.getConfig().timeouts.response` 从来没被接进内容脚本，
 * 于是所有平台恒 60s，直到用耗时指纹 `244s = 4×60 + 4` 才反推出来。
 * 那次是「表不存在」，这次加表之后必须防「表存在但键对不上」。
 *
 * 所以本测试钉两件事：
 *   1. 表里每个 key 必须是 PLATFORM_CONFIGS 里真实存在的 hostname（防拼错即失效）
 *   2. 每个 value 必须是 >= 60s 的数字（低于默认值等于反向配置，没有意义）
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SRC_PATH = fileURLToPath(new URL("../../src/content/content-script.js", import.meta.url));
const SRC = readFileSync(SRC_PATH, "utf8");

/** 去掉行注释，避免注释里的引号被当成键 */
function stripLineComments(s) {
  return s
    .split("\n")
    .map((line) => line.replace(/\/\/.*$/, ""))
    .join("\n");
}

/** 从源码里截出 `const NAME = { ... \n};` 这一段 */
function sliceObjectLiteral(src, name) {
  const start = src.indexOf(`const ${name} = {`);
  assert.ok(start >= 0, `源码里找不到 ${name}`);
  const end = src.indexOf("\n};", start);
  assert.ok(end > start, `${name} 没找到收尾的 };`);
  return src.slice(start, end);
}

/** 取出对象字面量里的字符串键 */
function quotedKeys(block) {
  return [...stripLineComments(block).matchAll(/"([^"]+)"\s*:/g)].map((m) => m[1]);
}

/** 取出 `"key": value` 的键值对（value 为纯数字） */
function numericEntries(block) {
  return [...stripLineComments(block).matchAll(/"([^"]+)"\s*:\s*(\d+)/g)].map((m) => ({
    key: m[1],
    value: Number(m[2]),
  }));
}

test("等待上限表的每个 key 都是真实存在的平台 hostname", () => {
  const configKeys = quotedKeys(sliceObjectLiteral(SRC, "PLATFORM_CONFIGS"));
  const timeoutKeys = quotedKeys(sliceObjectLiteral(SRC, "PLATFORM_RESPONSE_TIMEOUT"));

  assert.ok(configKeys.length > 0, "PLATFORM_CONFIGS 没解析出任何键，解析逻辑要修");
  assert.ok(timeoutKeys.length > 0, "PLATFORM_RESPONSE_TIMEOUT 没解析出任何键，解析逻辑要修");

  const unknown = timeoutKeys.filter((k) => !configKeys.includes(k));
  assert.deepEqual(
    unknown,
    [],
    `这些 key 不在 PLATFORM_CONFIGS 里，查表会得到 undefined 并静默回落到 60s：${unknown.join(", ")}`,
  );
});

test("等待上限表的每个值都是 >= 60s 的数字", () => {
  const entries = numericEntries(sliceObjectLiteral(SRC, "PLATFORM_RESPONSE_TIMEOUT"));
  assert.ok(entries.length > 0, "没解析出任何数值项");
  for (const { key, value } of entries) {
    assert.ok(Number.isFinite(value), `${key} 的值不是数字`);
    assert.ok(value >= 60000, `${key} = ${value}ms 低于 60s 默认值，等于把超时调短，不符合本表用途`);
  }
});

test("已知慢站确实被登记（deepseek / longcat / chatglm）", () => {
  const keys = quotedKeys(sliceObjectLiteral(SRC, "PLATFORM_RESPONSE_TIMEOUT"));
  // chatglm 是 2026-11-11 12:41 回归发现的：默认 60s 下 step_2 用了 170.7s 且 errors 为空
  for (const required of ["chat.deepseek.com", "longcat.chat", "chatglm.cn"]) {
    assert.ok(keys.includes(required), `${required} 应在本表内（有实测证据支持其答案会超过 60s）`);
  }
});
