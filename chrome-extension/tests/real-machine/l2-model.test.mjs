/**
 * L2 观测器判定逻辑的单测
 *
 * 观测器本体要真浏览器 + 真人点击，进不了 CI。但**判定口径**决定了
 * 「这次真机验证算不算通过」，必须能离线钉住。
 *
 * 下面的时间线是照着真机上会出现的形态写的，不是随手编的：
 *   - 「计数涨了但 isTyping 恒为 true」＝ Kimi/ChatGLM 打字指示器选错的那类缺陷
 *   - 「等待成功但正文是空的」＝ adapter 取不到回复正文的缺陷
 *   - 「基准必须取生产启动那一刻」＝ 否则中间落进一条消息就误判为没增长
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { parseArgs, buildVerdict, buildEvidence, SAMPLE_INTERVAL } from "./l2-model.mjs";

/**
 * 造一条采样时间线。
 * @param {Array<[number, boolean|null, string]>} rows - [messageCount, isTyping, lastContent]
 * @returns {Array<object>}
 */
function timeline(rows) {
  return rows.map(([messageCount, isTyping, lastContent], i) => ({
    t: 1000 + i * SAMPLE_INTERVAL,
    messageCount,
    isTyping,
    lastContent,
  }));
}

test("采样间隔与生产轮询一致（500ms）", () => {
  assert.equal(SAMPLE_INTERVAL, 500);
});

test("默认参数不含 --i-will-send（必须显式确认才会发消息）", () => {
  const args = parseArgs([]);
  assert.equal(args.iWillSend, false);
});

test("--i-will-send 会打开发送闸门", () => {
  const args = parseArgs(["--i-will-send", "--platform=gemini"]);
  assert.equal(args.iWillSend, true);
  assert.equal(args.platform, "gemini");
});

test("--profile-dir / --locale / --timeout 都被解析", () => {
  const args = parseArgs([
    "--profile-dir=/tmp/rm-profile",
    "--locale=en-US",
    "--timeout=90000",
    "--i-will-send",
  ]);
  assert.equal(args.profileDir, "/tmp/rm-profile");
  assert.equal(args.locale, "en-US");
  assert.equal(args.timeout, 90000);
  assert.equal(args.iWillSend, true);
});

test("--headless 会关掉有头模式", () => {
  assert.equal(parseArgs(["--headless"]).headed, false);
  assert.equal(parseArgs([]).headed, true);
});

test("计数增长且生成中解除 —— 会成功", () => {
  const samples = timeline([
    [0, false, ""],
    [0, true, ""],
    [1, true, "…"],
    [1, false, "答案是 2"],
  ]);
  const v = buildVerdict(samples, { settled: true, result: { messageCount: 1, content: "答案是 2", duration: 1500 } });
  assert.equal(v.wouldResolve, true);
  assert.equal(v.countGrew, true);
  assert.equal(v.typingCleared, true);
  assert.equal(v.contentNonEmpty, true);
  assert.equal(v.productionContentNonEmpty, true);
  assert.equal(v.resolveAtSampleIndex, 3);
  assert.equal(v.consistent, true);
});

test("计数涨了但 isTyping 恒为 true —— 不会成功（Kimi/ChatGLM 那类缺陷）", () => {
  const samples = timeline([
    [0, false, ""],
    [1, true, "…"],
    [1, true, "…"],
  ]);
  const v = buildVerdict(samples, { settled: true, result: null, error: "Kimi: Response timeout" });
  assert.equal(v.countGrew, true, "计数确实涨了");
  assert.equal(v.typingCleared, true, "有一帧是 false（起点那帧），但没能同时满足");
  assert.equal(v.wouldResolve, false, "生产口径要求两者同时成立");
  assert.equal(v.resolveAtSampleIndex, null);
  assert.equal(v.productionWaitError, "Kimi: Response timeout");
  assert.equal(v.productionWaitSettled, true);
});

test("生成中解除但计数没涨 —— 不会成功（取消息列表选错）", () => {
  const samples = timeline([
    [37, false, ""],
    [37, false, ""],
  ]);
  const v = buildVerdict(samples, { settled: true, result: null, error: "Response timeout" });
  assert.equal(v.countGrew, false);
  assert.equal(v.wouldResolve, false);
  assert.equal(v.initialMessageCount, 37);
});

test("等待成功但正文是空的 —— 等待过了但回复取不到", () => {
  const samples = timeline([
    [0, false, ""],
    [1, false, ""],
  ]);
  const v = buildVerdict(samples, { settled: true, result: { messageCount: 1, content: "  ", duration: 800 } });
  assert.equal(v.wouldResolve, true, "等待条件确实满足了");
  assert.equal(v.contentNonEmpty, false, "但页面上取到的正文是空的");
  assert.equal(v.productionContentNonEmpty, false, "生产代码取到的也是空的");
  assert.equal(v.consistent, true, "等待逻辑本身没矛盾");
});

test("生产结果与时间线重放不一致时，consistent 为 false", () => {
  // 生产说成功了，但按生产口径重放时间线找不到满足条件的帧
  const samples = timeline([
    [0, false, ""],
    [1, true, "…"],
  ]);
  const v = buildVerdict(samples, { settled: true, result: { messageCount: 1, content: "x", duration: 600 } });
  assert.equal(v.wouldResolve, false);
  assert.equal(v.productionWaitSettled, true);
  assert.equal(v.consistent, false);
});

test("基准取生产启动那一刻的计数，而不是第一个采样", () => {
  // 场景：生产等待启动后、第一次采样前，恰好落进一条消息。
  // 若用第一个采样（count=1）当基准，就会得出「没增长」的假结论。
  const samples = timeline([
    [1, false, ""],
    [2, false, "回复"],
  ]);
  const v = buildVerdict(samples, { settled: true, result: { messageCount: 2, content: "回复", duration: 500 } }, 0);
  assert.equal(v.initialMessageCount, 0);
  assert.equal(v.baselineFromProduction, true);
  assert.equal(v.countGrew, true);
  assert.equal(v.wouldResolve, true);
});

test("没有生产基准时，退回第一个采样的计数", () => {
  const samples = timeline([
    [3, false, ""],
    [4, false, "回复"],
  ]);
  const v = buildVerdict(samples, { settled: true, result: null, error: "x" }, null);
  assert.equal(v.initialMessageCount, 3);
  assert.equal(v.baselineFromProduction, false);
  assert.equal(v.countGrew, true);
});

test("空采样不崩", () => {
  const v = buildVerdict([], { settled: false, result: null, error: null });
  assert.equal(v.wouldResolve, false);
  assert.equal(v.initialMessageCount, null);
  assert.equal(v.productionWaitSettled, false);
});

test("waitResult 缺失不崩", () => {
  const v = buildVerdict(timeline([[0, false, ""]]), undefined);
  assert.equal(v.productionWaitSettled, false);
  assert.equal(v.productionWaitError, null);
});

test("证据文件里正文被脱敏，但结构保留", () => {
  const ev = buildEvidence({
    platform: "gemini",
    platformName: "Gemini",
    url: "https://gemini.google.com/app",
    locale: "zh-CN",
    prompt: "问",
    startedAt: "2026-10-25T00:00:00.000Z",
    samples: timeline([
      [0, false, ""],
      [1, false, "联系 zhang.san@example.com 或 13812345678"],
    ]),
    waitResult: { settled: true, result: { messageCount: 1, content: "ok", duration: 500 } },
    baselineCount: 0,
  });

  assert.equal(ev.layer, "L2-send-observer");
  assert.equal(ev.sendsMessages, false, "证据文件必须自证「脚本没发消息」");
  assert.equal(ev.sentBy, "human-in-browser");
  assert.equal(ev.sanitized, true);
  assert.equal(ev.sampleCount, 2);

  const last = ev.samples[1].lastContent;
  assert.ok(!last.includes("@example.com"), `邮箱不该留下：${last}`);
  assert.ok(!last.includes("13812345678"), `手机号不该留下：${last}`);
  assert.ok(last.includes("[EMAIL]"), `应留下脱敏标记：${last}`);
  assert.ok(last.includes("[PHONE]"), `应留下脱敏标记：${last}`);
});

test("证据文件里没有样本时也能组装", () => {
  const ev = buildEvidence({ platform: "x", samples: [], waitResult: null });
  assert.equal(ev.sampleCount, 0);
  assert.equal(ev.verdict.wouldResolve, false);
});
