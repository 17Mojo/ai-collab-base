/**
 * send-button 对账的守护（N59）—— 假绿是怎么被消掉的，就怎么防止它长回来。
 *
 * ## 缺陷形状
 *
 * 矩阵的「getSendButton() 命中 fixture 标注的发送按钮」这条，此前只用 mock。
 * 而 mock 是**照着 adapter 的选择器写的**（`mock-dom-deepseek.html` 里那个
 * `<button data-testid="send-button" aria-label="发送" class="send-button">`
 * 在真机落地页上根本不存在）——于是「选择器能命中」在自己身上闭环了。
 *
 * 与此同时，真机快照 `fixtures/real/deepseek.json` 自己写着 `sendButtonFound: false`：
 * 采集器在真实 DOM 上调的也是**同一个** `adapter.getSendButton()`。
 * 同一函数、两种 DOM、结论相反，两份证据从来没对过账。
 *
 * ## 这份测试守什么
 *
 *   1. 判据本身：5 种状态（no-snapshot / unusable / contradiction / pass / fail）各自返回什么（纯函数，不碰 DOM）；
 *   2. 事实地图：当前 11 站里谁的 send-button 结论是「一致」、谁是「假绿降级」、
 *      谁是「快照不可用」——这条一变就必须有人来解释；
 *   3. 接线：runner 真的调了这个判据、真读了真机快照、真有 STRICT 开关；
 *   4. 行为：默认模式 deepseek 判 SKIP 且退出码 0；`STRICT_SENDBUTTON=1` 判 FAIL 且退出码 1。
 *
 * 对应变异锚见 tests/real-machine/mutation-check.mjs 的三条「send-button 对账…」（外加一条 STRICT 锚）。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

import {
  judgeSendButtonCrossCheck,
  readRealSnapshotMeta,
} from "./adapter-matrix/adapter-test-utils.js";
import { PLATFORMS } from "./platforms.mjs";

const RUNNER = fileURLToPath(new URL("./adapter-matrix/adapter-test-runner.js", import.meta.url));
const MOCK_DIR = fileURLToPath(new URL("./adapter-matrix/fixtures", import.meta.url));

/** 真机快照可用（outcome=captured 且采到了输入框）——只有这种快照能当证据。 */
const usable = (over = {}) => ({ outcome: "captured", composerFound: true, sendButtonFound: false, ...over });

// ─────────────────────────────────────────────────────────────────────
// 1 · 判据分支
// ─────────────────────────────────────────────────────────────────────

test("对账判据：没快照 ⇒ no-snapshot，不冒充已验证", () => {
  const v = judgeSendButtonCrossCheck({ realMeta: null, mockHit: true, id: "x" });
  assert.equal(v.status, "no-snapshot");
  assert.match(v.reason, /未与真机对账/);
});

test("对账判据：快照不可用（登录墙）⇒ unusable，不说「没有发送按钮」", () => {
  const v = judgeSendButtonCrossCheck({
    realMeta: { outcome: "unverified", composerFound: false, sendButtonFound: false },
    mockHit: true,
    id: "chatgpt",
  });
  assert.equal(v.status, "unusable");
  assert.match(v.reason, /不能作为「没有发送按钮」的证据/);
});

test("对账判据：采集成功但没找着输入框（composer 选择器漂移）⇒ 同样 unusable", () => {
  // 为什么需要这一条：真机 11 站里 `outcome` 与 `composerFound` **恰好同真同假**
  // （只有 captured+true 与 unverified+false 两种组合）⇒ 上一条用例无法证明
  // `composerFound === true` 这半句是载重的，把它删掉照样全绿（变异锚实测存活过一次）。
  // 而「页面打开了、但 composer 选择器漂移」是最可能的下一种故障：采到了页面却采错地方，
  // 这时 sendButtonFound=false 同样不能当「没有按钮」的证据。
  const v = judgeSendButtonCrossCheck({
    realMeta: { outcome: "captured", composerFound: false, sendButtonFound: false },
    mockHit: true,
    id: "future-drift",
  });
  assert.equal(v.status, "unusable");
  assert.match(v.reason, /composerFound=false/);
});

test("对账判据：真机 false + mock 命中 ⇒ contradiction（这就是假绿）", () => {
  const v = judgeSendButtonCrossCheck({ realMeta: usable(), mockHit: true, id: "deepseek" });
  assert.equal(v.status, "contradiction");
  assert.match(v.reason, /不构成真机证据/);
  assert.match(v.reason, /N59/);
});

test("对账判据：真机 true + mock 命中 ⇒ pass（一致）", () => {
  const v = judgeSendButtonCrossCheck({
    realMeta: usable({ sendButtonFound: true }),
    mockHit: true,
    id: "stepfun",
  });
  assert.equal(v.status, "pass");
});

test("对账判据：真机 true 但 mock 取不到 ⇒ fail（fixture 与真机脱节）", () => {
  const v = judgeSendButtonCrossCheck({
    realMeta: usable({ sendButtonFound: true }),
    mockHit: false,
    id: "qianwen",
  });
  assert.equal(v.status, "fail");
  assert.match(v.reason, /fixture 与真机脱节/);
});

test("对账判据：两边都没有 ⇒ pass（都空的也算一致）", () => {
  const v = judgeSendButtonCrossCheck({ realMeta: usable(), mockHit: false, id: "x" });
  assert.equal(v.status, "pass");
});

// ─────────────────────────────────────────────────────────────────────
// 2 · 事实地图（改了就要来解释）
// ─────────────────────────────────────────────────────────────────────

test("当前 11 站的 send-button 事实地图：只有 qianwen / stepfun 两边一致", () => {
  const judged = {};
  for (const p of PLATFORMS) {
    const mockHtml = readFileSync(`${MOCK_DIR}/mock-dom-${p.id}.html`, "utf-8");
    // mock 里标注了几个 send-button —— 这一步不用 jsdom，只数标注，够用
    const annotated = (mockHtml.match(/data-role="send-button"/g) || []).length;
    judged[p.id] = judgeSendButtonCrossCheck({
      realMeta: readRealSnapshotMeta(p.id),
      mockHit: annotated > 0,
      id: p.id,
    }).status;
  }

  const byStatus = (s) => Object.entries(judged).filter(([, v]) => v === s).map(([k]) => k).sort();

  assert.deepEqual(byStatus("pass"), ["qianwen", "stepfun"], "两边一致的只剩这两家");
  assert.deepEqual(
    byStatus("unusable"),
    ["chatgpt", "claude"],
    "这两家快照是登录墙，sendButtonFound=false 不能当证据",
  );
  assert.deepEqual(
    byStatus("contradiction"),
    ["chatglm", "deepseek", "gemini", "kimi", "longcat", "yiyan", "yuanbao"],
    "这 7 家的 send-button 从未被真机验证过（N59）。" +
      "如果这里变了：要么真机补采了快照、要么 fixture 被按真机重写了——" +
      "两种情况都要同步更新本断言并在 N59 里写清依据，别直接删。",
  );
  assert.deepEqual(byStatus("fail"), [], "不该有「真机有、mock 没有」的站");
});

// ─────────────────────────────────────────────────────────────────────
// 3 · 接线（判据存在但不被调用 = 等于没有）
// ─────────────────────────────────────────────────────────────────────

test("runner 真的调了对账判据，并且真的读了真机快照", () => {
  const src = readFileSync(RUNNER, "utf-8");
  assert.match(src, /judgeSendButtonCrossCheck\(\{/, "send-button 断言必须走对账判据");
  assert.match(src, /readRealSnapshotMeta\(spec\.id\)/, "对账必须基于本平台的真机快照");
  assert.match(src, /STRICT_SENDBUTTON/, "严格模式开关必须存在（解冻验收要用）");
});

test("SKIP 必须带原因：runTestAsync 认 {skip} 形状，formatResults 会打印", () => {
  const runnerSrc = readFileSync(RUNNER, "utf-8");
  assert.match(runnerSrc, /typeof result\.skip === "string"/, "runTestAsync 要认 { skip: reason }");
  const utilsSrc = readFileSync(
    fileURLToPath(new URL("./adapter-matrix/adapter-test-utils.js", import.meta.url)),
    "utf-8",
  );
  assert.match(utilsSrc, /r\.reason/, "formatResults 要把 SKIP 原因打印出来");
});

// ─────────────────────────────────────────────────────────────────────
// 4 · 行为：默认 SKIP、严格 FAIL
// ─────────────────────────────────────────────────────────────────────

test("默认模式：deepseek 的 send-button 判 SKIP（带原因），整体退出码 0", () => {
  const out = execFileSync("node", [RUNNER, "--platform=deepseek"], { encoding: "utf-8" });
  assert.match(out, /N59/, "SKIP 原因里要指回台账编号");
  assert.match(out, /\[SKIP\] getSendButton\(\)/, "这条应当降级为 SKIP 而不是继续 PASS");
  assert.ok(!/\[FAIL\] getSendButton\(\)/.test(out), "默认模式不该把「未验证」判成「坏了」");
});

test("STRICT_SENDBUTTON=1：同一个平台判 FAIL，退出码 1（解冻验收必须用它）", () => {
  let exitCode = 0;
  let out = "";
  try {
    out = execFileSync("node", [RUNNER, "--platform=deepseek"], {
      encoding: "utf-8",
      env: { ...process.env, STRICT_SENDBUTTON: "1" },
    });
  } catch (e) {
    exitCode = e.status ?? 1;
    out = String(e.stdout || "");
  }
  assert.equal(exitCode, 1, "严格模式必须让门禁变红，否则解冻验收拦不住");
  assert.match(out, /STRICT_SENDBUTTON=1/, "失败信息要说明是严格模式触发的");
});
