/**
 * 「探针永不发送」—— 从**声明**变成有门禁守护的事实。
 *
 * 之前 `new-session-probe.mjs` 头部的红线只写在注释和回执字段里：
 * 靠人记、靠人复核注释。谁后来加一行 `await page.locator(...).click()`，
 * 注释不会变、单测不会红，而「只读」就已经不成立了。
 *
 * 这份测试扫描**剥离注释后的实际代码**：
 *   - 不许出现任何交互 / 发送 / 注入调用；
 *   - 不许出现 EXECUTE_PACK / SEND_TO_AI / IMPORT_PACKS / chrome.*.sendMessage；
 *   - 允许调用只能是导航 + 读 DOM + 等待 + 本地写文件那一小撮；
 *   - 回执必须明写 readonly mode 与 redlines 全 false。
 *
 * 对应变异锚：「往探测器插一次真实 click，这份测试必须变红」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// 相对**自身**：变异检查会把 tests/ 复制到 .mutation-tmp/tests/，
// 从副本读副本的探测器，锚才咬得到行为。
const PROBE = fileURLToPath(
  new URL("./real-machine/new-session-probe.mjs", import.meta.url),
);

/** 剥掉块注释与整行注释，只留可执行代码。行内注释的关键字不算「调用」。 */
function executableSource() {
  const raw = readFileSync(PROBE, "utf-8");
  return raw
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

test("探测器里没有任何点击 / 输入 / 悬停 / 键盘调用", () => {
  const code = executableSource();
  const forbidden = [
    /\.click\s*\(/,
    /\.dblclick\s*\(/,
    /\.type\s*\(/,
    /\.fill\s*\(/,
    /\.press\s*\(/,
    /\.hover\s*\(/,
    /\.focus\s*\(/,
    /\.check\s*\(/,
    /\.selectOption\s*\(/,
    /keyboard\s*\./,
    /mouse\s*\./,
  ];
  for (const re of forbidden) {
    assert.doesNotMatch(code, re, `探针必须只读，发现被禁止的交互调用：${re}`);
  }
});

test("探测器不导入 Pack、不发任何消息类型", () => {
  const code = executableSource();
  for (const keyword of [
    "EXECUTE_PACK",
    "SEND_TO_AI",
    "WAIT_FOR_RESPONSE",
    "IMPORT_PACKS",
    "NEW_SESSION",
    "runtime.sendMessage",
    "tabs.sendMessage",
  ]) {
    assert.ok(!code.includes(keyword), `探针不得出现 ${keyword}`);
  }
});

test("Playwright 侧只调用「导航 / 读 DOM / 等待」，没有别的", () => {
  const code = executableSource();
  // 只管 page.* / context.* —— 纯 JS 方法（toISOString / JSON.stringify 等）
  // 不是浏览器交互，列白名单反而会把门禁写成一个不停误报的清单。
  const found = [
    ...code.matchAll(/\b(?:page|context)\.([A-Za-z]+)\s*\(/g),
  ].map((m) => m[1]);
  const allowed = new Set([
    "goto", "evaluate", "waitForTimeout", "title", "isVisible", "count",
    "newPage", "close", "url", "locator",
  ]);
  assert.ok(found.length > 0, "没扫到任何 page/context 调用，正则可能失效");
  for (const name of found) {
    assert.ok(
      allowed.has(name),
      `Playwright 侧出现未在白名单里的调用 .${name}() —— 请人工确认它是只读的`,
    );
  }
});

test("回执明写 readonly mode 与 redlines 全 false（降级可见）", () => {
  const code = executableSource();
  assert.match(code, /mode:\s*"readonly-dom-probe"/);
  for (const flag of ["clicks", "typing", "sending", "hover", "captchaBypass", "packImported"]) {
    assert.match(code, new RegExp(`${flag}:\\s*false`), `${flag} 必须明确写 false`);
  }
});
