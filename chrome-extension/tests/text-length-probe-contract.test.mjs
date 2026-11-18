/**
 * `text-length-probe.mjs` 的「点击纪律」契约 —— 它比别的探针多一次点击，就得单独守。
 *
 * ## 为什么不能复用 probe-readonly.test.mjs
 *
 * 那份契约守的是 `new-session-probe.mjs`，判据是「**任何** .click / .mouse. 都不许出现」。
 * 本探针天生要多点一下右下角那个圆形按钮（N57 要靠点击前后对比才能证伪），
 * 所以它套不进「零点击」的模子；但如果因此就不守，等于给这个目录开了一个口子：
 * 以后谁往这里加一行 `page.click(发送按钮)` 也不会有任何东西变红。
 *
 * 于是把纪律写细，只允许两件事：
 *
 *   1. **导航型点击**：`page.click(CLICK_CONV)`，且必须挂在 `if (CLICK_CONV)` 后面——
 *      只用来点侧栏历史条目进会话；
 *   2. **一次几何受控的点击**：`page.mouse.click(x, y)`，且必须挂在
 *      `if (EXPAND_CLICK && cands.length > 0)` 后面，坐标只能来自 `pickChevron`，
 *      而 `pickChevron` 的 5 条闸门一条都不能少（少一条就可能点到输入框/发送键）。
 *
 * 另守：不许有 .fill / .type / .press / keyboard.（打字即可能触发发送），
 * 不许出现 EXECUTE_PACK / SEND_TO_AI / IMPORT_PACKS / chrome.*.sendMessage。
 *
 * 对应变异锚见 tests/real-machine/mutation-check.mjs 的两条「text-length-probe ...」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// 相对**自身**：变异检查会把 tests/ 复制到 .mutation-tmp/tests/，从副本读副本的探针。
const PROBE = fileURLToPath(new URL("./real-machine/text-length-probe.mjs", import.meta.url));

/** 剥掉块注释与整行注释，只留可执行代码——注释里写「不要点击」不算调用。 */
function code() {
  return readFileSync(PROBE, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

test("探针里没有任何打字类调用（打字即可能触发发送）", () => {
  const src = code();
  for (const re of [/\.fill\s*\(/, /\.type\s*\(/, /\.press\s*\(/, /keyboard\s*\./]) {
    assert.ok(!re.test(src), `不许出现 ${re}：探针只读，打字等于半次发送`);
  }
});

test("探针不碰 Pack / 扩展消息通道", () => {
  const src = code();
  for (const token of ["EXECUTE_PACK", "SEND_TO_AI", "IMPORT_PACKS", "sendMessage"]) {
    assert.ok(!src.includes(token), `不许出现 ${token}`);
  }
});

test("唯一的导航型点击必须挂在 CLICK_CONV 开关后面", () => {
  const src = code();
  const lines = src.split("\n");
  const clickLine = lines.findIndex((l) => /page\.click\s*\(/.test(l));
  assert.ok(clickLine >= 0, "找不到 page.click(CLICK_CONV)，探针就进不了会话页");
  const guardLine = lines.findIndex((l) => /if\s*\(CLICK_CONV\)/.test(l));
  assert.ok(guardLine >= 0, "导航型点击没有 if (CLICK_CONV) 闸门 ⇒ 无条件点侧栏第一项");
  assert.ok(guardLine < clickLine, "闸门必须在点击之前");
});

test("非导航点击必须挂在 EXPAND_CLICK 开关后面，且坐标只来自 pickChevron", () => {
  const src = code();
  const lines = src.split("\n");
  const mouseLine = lines.findIndex((l) => /mouse\.click\s*\(/.test(l));
  assert.ok(mouseLine >= 0, "找不到 mouse.click —— 那 N57 的证伪就没做");
  const guardLine = lines.findIndex((l) => /if\s*\(EXPAND_CLICK\s*&&\s*cands\.length\s*>\s*0\)/.test(l));
  assert.ok(guardLine >= 0, "点击没有 EXPAND_CLICK + 候选非空的双闸门");
  assert.ok(guardLine < mouseLine, "闸门必须在点击之前");
  // 坐标来源必须是 pickChevron 的结果，不许在这里临时算
  assert.ok(/const t = cands\[0\]/.test(src), "点击坐标必须取自 cands[0]（pickChevron 过闸后的结果）");
});

test("探针里 5 条几何闸门一条都不能少", () => {
  const src = code();
  const gates = [
    [/r\.width < 20 \|\| r\.width > 48/, "尺寸下界/上界（20–48px）"],
    [/el\.querySelector\("svg"\)/, "必须是图标按钮"],
    [/r\.left < vw \* 0\.7/, "必须在视口右侧 30% 内"],
    [/r\.bottom > composerTop/, "必须整体在输入区上沿之上"],
    [/radius >= r\.width \* 0\.4/, "必须是圆形"],
  ];
  for (const [re, why] of gates) {
    assert.ok(re.test(src), `缺了这条闸门：${why}——少一条就可能点到输入框或发送键`);
  }
});
