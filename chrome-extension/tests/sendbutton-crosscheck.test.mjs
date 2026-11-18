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
 *   1. 对账判据：5 种状态（no-snapshot / unusable / contradiction / pass / fail）各自返回什么（纯函数，不碰 DOM）；
 *   2. 声明判据：`data-expect-send-button="none"` 的 7 种结局（A2 新增）；
 *   3. 事实地图：当前 11 站里谁「一致」、谁「假绿降级」、谁「快照不可用」、谁「显式声明无按钮」——
 *      这条一变就必须有人来解释；
 *   4. 接线：runner 真的调了两个判据、真读了真机快照、真有 STRICT 开关、声明真从 body 读；
 *   5. 行为：仍有假 button 的站（gemini）默认 SKIP / 严格 FAIL；
 *      声明站（deepseek）两种模式都 PASS。
 *
 * 变异锚共 6 条，见 tests/real-machine/mutation-check.mjs 的「send-button 对账…」与「声明判据…」两组。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { JSDOM } from "jsdom";

import {
  judgeSendButtonCrossCheck,
  judgeSendButtonDeclaration,
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
// 2 · 声明判据（A2：`data-expect-send-button="none"`）
// ─────────────────────────────────────────────────────────────────────

const witness = (over = {}) => ({ outcome: "captured", composerFound: true, sendButtonFound: false, ...over });

test("声明判据：没声明 ⇒ no-declaration（调用方走原对账路径）", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: null, annotated: 1, hit: true, realMeta: witness() });
  assert.equal(v.status, "no-declaration");
});

test("声明判据：不认识的取值 ⇒ unknown（不许静默放过）", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: "maybe", annotated: 0, hit: false, realMeta: witness() });
  assert.equal(v.status, "unknown");
  assert.match(v.reason, /只认 "none"/);
});

test("声明判据：声明 none 却还标注了 send-button ⇒ self-contradictory", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: "none", annotated: 1, hit: true, realMeta: witness() });
  assert.equal(v.status, "self-contradictory");
});

test("声明判据：没有真机快照 ⇒ no-witness（声明无人作证，降级不算 PASS）", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: "none", annotated: 0, hit: false, realMeta: null, id: "x" });
  assert.equal(v.status, "no-witness");
});

test("声明判据：真机快照不可用（登录墙）⇒ 也算 no-witness", () => {
  const v = judgeSendButtonDeclaration({
    expectDecl: "none",
    annotated: 0,
    hit: false,
    realMeta: witness({ outcome: "unverified", composerFound: false }),
    id: "chatgpt",
  });
  assert.equal(v.status, "no-witness");
});

test("声明判据：真机说 sendButtonFound=true ⇒ contradicts-real（声明与真机相反）", () => {
  const v = judgeSendButtonDeclaration({
    expectDecl: "none",
    annotated: 0,
    hit: false,
    realMeta: witness({ sendButtonFound: true }),
  });
  assert.equal(v.status, "contradicts-real");
});

test("声明判据：声明 none 但 adapter 仍然命中 ⇒ still-matches（硬红）", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: "none", annotated: 0, hit: true, realMeta: witness() });
  assert.equal(v.status, "still-matches");
});

test("声明判据：三方一致 ⇒ pass", () => {
  const v = judgeSendButtonDeclaration({ expectDecl: "none", annotated: 0, hit: false, realMeta: witness() });
  assert.equal(v.status, "pass");
});

// ─────────────────────────────────────────────────────────────────────
// 3 · 事实地图（改了就要来解释）
// ─────────────────────────────────────────────────────────────────────

/**
 * 把 mock 装进 jsdom 取 document。
 *
 * **不用正则数 `data-role="send-button"`**：2026-11-19 踩过——fixture 的注释里
 * 引用了被删掉的那段标记原文（为了说清「删了什么、为什么删」），正则把它当成了 DOM，
 * 于是「deepseek 已经没有发送按钮」这条断言被自己的注释弄红了。
 * 注释不是 DOM，只有解析器分得清。
 */
const mockDocument = (id) =>
  new JSDOM(readFileSync(`${MOCK_DIR}/mock-dom-${id}.html`, "utf-8")).window.document;

test("当前 11 站的事实地图：deepseek 已改成「显式声明无按钮」，只剩 6 站仍是假绿", () => {
  const judged = {};
  const declared = {};
  for (const p of PLATFORMS) {
    const doc = mockDocument(p.id);
    const annotated = doc.querySelectorAll('[data-role="send-button"]').length;
    declared[p.id] = doc.body.dataset.expectSendButton || null;
    judged[p.id] = judgeSendButtonCrossCheck({
      realMeta: readRealSnapshotMeta(p.id),
      mockHit: annotated > 0,
      id: p.id,
    }).status;
  }

  const byStatus = (s) => Object.entries(judged).filter(([, v]) => v === s).map(([k]) => k).sort();

  // A2（2026-11-19）之后 deepseek 的 mock 里不再有那个假按钮，也不再标注 send-button，
  // 于是它在**对账判据**看来是「两边都没有」的 pass；真正的断言在声明判据那一层。
  assert.deepEqual(byStatus("pass"), ["deepseek", "qianwen", "stepfun"], "两边一致的只剩这三家");
  assert.deepEqual(
    byStatus("unusable"),
    ["chatgpt", "claude"],
    "这两家快照是登录墙，sendButtonFound=false 不能当证据",
  );
  assert.deepEqual(
    byStatus("contradiction"),
    ["chatglm", "gemini", "kimi", "longcat", "yiyan", "yuanbao"],
    "这 6 家的 send-button 从未被真机验证过（N59），假 button 还在 fixture 里。" +
      "如果这里变了：要么真机补采了快照、要么 fixture 被按真机重写了——" +
      "两种情况都要同步更新本断言并在台账里写清依据，别直接删。",
  );
  assert.deepEqual(byStatus("fail"), [], "不该有「真机有、mock 没有」的站");

  // 声明这一列：目前只有 deepseek 敢声明，且只有它一个。
  assert.deepEqual(
    Object.entries(declared).filter(([, v]) => v !== null),
    [["deepseek", "none"]],
    "声明必须逐站显式表态，不许靠默认值悄悄成立",
  );
});

test("deepseek 的发送区：DOM 里没有 button 形态的发送控件，也没有能命中 send 选择器的元素", () => {
  const doc = mockDocument("deepseek");
  assert.equal(
    doc.querySelectorAll('[data-role="send-button"]').length,
    0,
    "不许再标注一个真机上不存在的发送按钮",
  );
  assert.equal(
    doc.body.dataset.expectSendButton,
    "none",
    "必须显式声明「本站没有 button 形态的发送控件」",
  );

  // 关键一击：拿**生产 adapter 自己的四条选择器**去问这个 DOM。
  // 这比正则强——它问的是「选择器会不会命中」，而不是「文件里有没有这几个字」。
  return import("../src/platforms/deepseek-adapter.js").then(({ SELECTORS }) => {
    const hits = SELECTORS.sendButton
      .map((sel) => ({ sel, n: doc.querySelectorAll(sel).length }))
      .filter((x) => x.n > 0);
    assert.deepEqual(hits, [], "fixture 里不许有能命中 adapter send 选择器的元素");
  });
});

// ─────────────────────────────────────────────────────────────────────
// 4 · 接线（判据存在但不被调用 = 等于没有）
// ─────────────────────────────────────────────────────────────────────

test("runner 真的调了两个判据，并且真的读了真机快照", () => {
  const src = readFileSync(RUNNER, "utf-8");
  assert.match(src, /judgeSendButtonCrossCheck\(\{/, "send-button 断言必须走对账判据");
  assert.match(src, /judgeSendButtonDeclaration\(\{/, "声明必须走声明判据，不许内联在 runner 里");
  assert.match(src, /readRealSnapshotMeta\(spec\.id\)/, "对账必须基于本平台的真机快照");
  assert.match(src, /STRICT_SENDBUTTON/, "严格模式开关必须存在（解冻验收要用）");
  assert.match(
    src,
    /doc\.body\.dataset\.expectSendButton/,
    "声明从 body 的 data-expect-send-button 读，不能靠 fixture 里的注释",
  );
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
// 5 · 行为：假绿站默认 SKIP / 严格 FAIL；声明站两种模式都 PASS
// ─────────────────────────────────────────────────────────────────────

const runMatrix = (platform, env = {}) => {
  let exitCode = 0;
  let out = "";
  try {
    out = execFileSync("node", [RUNNER, `--platform=${platform}`], {
      encoding: "utf-8",
      env: { ...process.env, ...env },
    });
  } catch (e) {
    exitCode = e.status ?? 1;
    out = String(e.stdout || "");
  }
  return { exitCode, out };
};

test("默认模式：仍有假 button 的站（gemini）判 SKIP 且带原因，退出码 0", () => {
  // 换成 gemini 而不是 deepseek：A2 之后 deepseek 已经没有假 button 了，
  // 它不再是这条行为的载体——拿它当载体等于测了个空。
  const { exitCode, out } = runMatrix("gemini");
  assert.equal(exitCode, 0, "默认模式不该把「未验证」判成「坏了」");
  assert.match(out, /N59/, "SKIP 原因里要指回台账编号");
  assert.match(out, /\[SKIP\] getSendButton\(\)/, "这条应当降级为 SKIP 而不是继续 PASS");
  assert.ok(!/\[FAIL\] getSendButton\(\)/.test(out), "默认模式不该判 FAIL");
});

test("STRICT_SENDBUTTON=1：同一个站判 FAIL，退出码 1（解冻验收必须用它）", () => {
  const { exitCode, out } = runMatrix("gemini", { STRICT_SENDBUTTON: "1" });
  assert.equal(exitCode, 1, "严格模式必须让门禁变红，否则解冻验收拦不住");
  assert.match(out, /STRICT_SENDBUTTON=1/, "失败信息要说明是严格模式触发的");
});

test("声明站（deepseek）：两种模式都 PASS，且打印的用例名不含「命中」二字", () => {
  for (const env of [{}, { STRICT_SENDBUTTON: "1" }]) {
    const { exitCode, out } = runMatrix("deepseek", env);
    assert.equal(exitCode, 0, `deepseek 不该在 ${JSON.stringify(env)} 下报红`);
    assert.ok(
      !/\[(SKIP|FAIL)\] getSendButton\(\)/.test(out),
      "声明站的三方一致是**验过的 PASS**，不该显示成 SKIP 或 FAIL",
    );
    assert.match(out, /\[PASS\] getSendButton\(\) 与 fixture 的 send-button 契约一致/);
  }
});
