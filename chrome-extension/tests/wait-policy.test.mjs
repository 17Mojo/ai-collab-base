import { test } from "node:test";
import assert from "node:assert/strict";

import {
  STABLE_MS_DEFAULT,
  MIN_AI_CONTENT_LENGTH_DEFAULT,
  sampleWaitState,
  isUsableAIContent,
} from "../src/utils/wait-policy.js";

// ─────────────────────────────────────────────────────────────────────
// ① 内容稳定性判据（防「太早成功」）
//
// 2026-11-04 千问真机实锤：旧判据「消息数增加 且 不在生成中」在流式
// 开口瞬间就放行，7 个产出全是 '收到，' 之类碎片。这里逐条钉死新判据。
// ─────────────────────────────────────────────────────────────────────

test("空内容永不判完成（防把流式开头当回复）", () => {
  // 消息气泡已经出现（countGrew=true），但正文还没开始流：
  // 8 秒里反复采样空串，任何一刻都不许 ready。
  let lastContent = null;
  let lastChangeAt = null;
  for (let t = 0; t <= 8000; t += 500) {
    const s = sampleWaitState({
      countGrew: true,
      content: t < 4000 ? "" : "   ",
      now: t,
      lastContent,
      lastChangeAt,
    });
    lastContent = s.lastContent;
    lastChangeAt = s.lastChangeAt;
    assert.equal(s.ready, false, `t=${t} 空内容不许判完成`);
  }
});

test("内容还在变化时不判完成", () => {
  // 流式生成：正文每个采样都在长。即使消息数早已增长，也不许提前放行。
  const growing = ["收", "收到，", "收到，我", "收到，我已", "收到，我已理解", "收到，我已理解你的需求"];
  let lastContent = null;
  let lastChangeAt = null;
  growing.forEach((content, i) => {
    const s = sampleWaitState({
      countGrew: true,
      content,
      now: i * 500,
      lastContent,
      lastChangeAt,
    });
    lastContent = s.lastContent;
    lastChangeAt = s.lastChangeAt;
    assert.equal(s.ready, false, `第 ${i} 个采样内容仍在变化，不许判完成`);
  });
});

test("内容连续稳定满窗口才算完成", () => {
  // 正文在 t=1000 定格；t=1000+STABLE_MS 之前不算完成，到点才算。
  let s = sampleWaitState({
    countGrew: true,
    content: "这是一段已经生成完毕的完整回复正文。",
    now: 1000,
    lastContent: null,
    lastChangeAt: null,
  });
  assert.equal(s.ready, false, "刚定格就放行 = 太早成功");

  s = sampleWaitState({
    countGrew: true,
    content: "这是一段已经生成完毕的完整回复正文。",
    now: 1000 + STABLE_MS_DEFAULT - 1,
    lastContent: s.lastContent,
    lastChangeAt: s.lastChangeAt,
  });
  assert.equal(s.ready, false, "窗口没满不许放行");

  s = sampleWaitState({
    countGrew: true,
    content: "这是一段已经生成完毕的完整回复正文。",
    now: 1000 + STABLE_MS_DEFAULT,
    lastContent: s.lastContent,
    lastChangeAt: s.lastChangeAt,
  });
  assert.equal(s.ready, true, "窗口满了才放行");
});

test("计数没涨不判完成（别把静止的旧消息当新回复）", () => {
  // 反向测试：内容再稳定，没有新消息就不许算「回复到了」。
  const s = sampleWaitState({
    countGrew: false,
    content: "上一轮就存在的旧消息正文，一直稳定不变。",
    now: 99_000,
    lastContent: "上一轮就存在的旧消息正文，一直稳定不变。",
    lastChangeAt: 0,
  });
  assert.equal(s.ready, false);
});

// ─────────────────────────────────────────────────────────────────────
// ③ 碎片/空内容判失败
// ─────────────────────────────────────────────────────────────────────

test("isUsableAIContent：空串/碎片/非字符串不可用，长文可用；minLen 可覆盖", () => {
  assert.equal(isUsableAIContent(""), false, "空串不可用");
  assert.equal(isUsableAIContent("   "), false, "纯空白不可用");
  assert.equal(isUsableAIContent("收到，"), false, "流式开头碎片不可用");
  assert.equal(isUsableAIContent({ toString: () => "x" }), false, "非字符串不可用");
  assert.equal(isUsableAIContent(null), false, "null 不可用");
  assert.equal(
    isUsableAIContent("这是一段长度超过二十个字符的完整回复正文，应当可用。"),
    true,
    "长文可用",
  );
  assert.equal(
    isUsableAIContent("收到，", 3),
    true,
    "step.config.min_output_length 放宽阈值后短回复可用",
  );
  assert.equal(MIN_AI_CONTENT_LENGTH_DEFAULT, 20, "默认阈值是 20 字符");
});
