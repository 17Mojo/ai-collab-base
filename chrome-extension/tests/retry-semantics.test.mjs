/**
 * 超时不许重发 —— 台账 N21 的根治守护
 *
 * ## 缺陷长什么样
 *
 * `_executeStep` 的 catch 里原本是一段**不看错误语义**的重试：
 * 失败了就再跑一遍这一步。对 AI 步骤来说「再跑一遍」= 把同一句提示词
 * **再发一次**。
 *
 * 而 `Response timeout` 的语义是「**已经发出去了**，只是没等到回复」。
 * 于是重试把它放大成：会话里多一条**重复提问**、AI 再答一遍、烧双倍额度。
 * 用户看到的是「AI 怎么回了我两遍」。
 *
 * 证据长这样（2026-11-11 chatglm，RMR-2026-11-11-03）：
 *   step_2 用了 170.7s ≈ 60 + 60 + 50.7
 *   step_7 用了 151.3s ≈ 60 + 60 + 31.3
 *   errors 却是空的 ⇒ 中途至少重发过一次，只是重发后碰巧等到了回复。
 * 也就是说：**它一直没报错，所以一直没人发现**。
 *
 * ## 这份测试钉什么
 *
 * 三条，缺一条修法就是假的：
 *   1. 超时后 `SEND_TO_AI` **只出现一次**，后面跟的是 `WAIT_FOR_RESPONSE`；
 *   2. 续等必须带上**发送前**的 `baselineCount`（不带就是重新数，
 *      而重新数会让 `countGrew` 恒 false —— 白等满一个超时窗口）；
 *   3. 别的失败（输入框没找到之类）**照样重试** —— 别为了修超时把重试一起废了。
 *
 * 另外钉一条边界：广播投递（不知道目标标签页）时宁可失败也不重发，
 * 因为重发是**确定的**副作用，等不到只是慢。
 *
 * 用法：node --test tests/retry-semantics.test.mjs（run-tests.mjs 会自动收）
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  FAILURE_STRATEGY,
  failureStrategy,
  resolveInitialCount,
} from "../src/utils/retry-policy.js";
import {
  ECHO_CONTENT,
  loadServiceWorker,
} from "./helpers/service-worker-harness.mjs";

/**
 * 只跑一个 AI 步骤的 Pack。
 *
 * `retries: 1` 而不是默认 3：每条断言都要等一次 retryDelay（1 秒），
 * 3 次就是 3 秒，而这里要验的是**重试干了什么**，不是重试了几次。
 */
const AI_PACK = {
  metadata: { pack_id: "retry-semantics", pack_name: "超时语义分流" },
  workflow: {
    steps: [
      {
        id: "step_ai",
        type: "ai",
        prompt_template: "你好",
        retries: 1,
      },
    ],
  },
};

/** 内容脚本报超时时会回的信封（见 content-script.js 的 failureEnvelope） */
const TIMEOUT_ENVELOPE = {
  success: false,
  error: "Response timeout",
  code: "RESPONSE_TIMEOUT",
  baselineCount: 4,
};

const kindsOf = (tabMessages) => tabMessages.map((m) => m.msg.type);

// ─────────────────────────────────────────────────────────────────────
// 一、分流规则本身（纯函数，不起浏览器环境）
// ─────────────────────────────────────────────────────────────────────

test("错误码是 RESPONSE_TIMEOUT ⇒ 只能续等，不能重发", () => {
  const error = new Error("标签页 42 没能完成这次发送：Response timeout。");
  error.code = "RESPONSE_TIMEOUT";
  assert.equal(failureStrategy(error), FAILURE_STRATEGY.RESUME_WAIT);
});

test("老路径没有错误码时，按整串文案兜底认超时", () => {
  // adapter-utils.js 的超时是 `label ? `${label}: Response timeout` : "Response timeout"`
  assert.equal(
    failureStrategy(new Error("千问: Response timeout")),
    FAILURE_STRATEGY.RESUME_WAIT,
  );
  assert.equal(
    failureStrategy(new Error("Response timeout")),
    FAILURE_STRATEGY.RESUME_WAIT,
  );
});

test("文案里只是**提到**超时，不算超时（不许用子串包含误判）", () => {
  // 兜底写成 includes("Response timeout") 的话，下面这句会被判成超时 ⇒
  // 一个「输入框没找到」的失败不去重试，反而傻等一整个窗口。
  assert.equal(
    failureStrategy(new Error("Response timeout 之后我换了选择器，仍找不到输入框")),
    FAILURE_STRATEGY.RETRY,
  );
  assert.equal(
    failureStrategy(new Error("Chat input not found")),
    FAILURE_STRATEGY.RETRY,
  );
});

test("续等要用发送前的基准条数，不许重新数", () => {
  // 页面判完成是 currentCount > initialCount。
  // 回复若在「超时」与「续等开始」之间落地，重新数会把它算进基准 ⇒
  // countGrew 恒 false ⇒ 白等满一个超时窗口。
  assert.equal(resolveInitialCount(9, 4), 4, "给了基准就必须用基准");
  assert.equal(resolveInitialCount(9, undefined), 9, "没给基准只能就地数");
  assert.equal(resolveInitialCount(9, null), 9);
  assert.equal(resolveInitialCount(9, -1), 9, "负数不是合法条数");
  assert.equal(resolveInitialCount(9, 4.5), 9, "小数不是合法条数");
  assert.equal(resolveInitialCount(9, 0), 0, "0 是合法基准（空会话）");
});

// ─────────────────────────────────────────────────────────────────────
// 二、执行器真的这么做（起生产 service-worker）
// ─────────────────────────────────────────────────────────────────────

test("超时后 SEND_TO_AI 只发一次，随后是带 baselineCount 的续等", async () => {
  const { send, tabMessages } = await loadServiceWorker([AI_PACK], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type === "SEND_TO_AI") return TIMEOUT_ENVELOPE;
      if (msg.type === "WAIT_FOR_RESPONSE") {
        return { success: true, result: { content: ECHO_CONTENT } };
      }
      return undefined;
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "retry-semantics",
    input: {},
    tabId: 42,
  });

  const kinds = kindsOf(tabMessages);
  assert.deepEqual(
    kinds,
    ["SEND_TO_AI", "WAIT_FOR_RESPONSE"],
    `超时后只许续等，不许重发。实际发出的消息：${JSON.stringify(kinds)}`,
  );
  assert.equal(
    kinds.filter((k) => k === "SEND_TO_AI").length,
    1,
    "同一句提示词只许发一次——多发一次就是会话里多一条重复提问",
  );

  const resume = tabMessages.find((m) => m.msg.type === "WAIT_FOR_RESPONSE");
  assert.equal(
    resume.msg.baselineCount,
    4,
    "续等必须带回发送前的基准条数，否则页面会重新数 ⇒ countGrew 恒 false",
  );
  assert.equal(
    resume.tabId,
    42,
    "续等要回到**同一个**标签页——换一个页面等于换了一个会话",
  );

  assert.equal(
    response?.success,
    true,
    `续等拿到回复时 Pack 必须成功，实际：${JSON.stringify(response?.error || response)}`,
  );
});

test("非超时的失败照样重试（别为了修超时把重试一起废了）", async () => {
  let attempts = 0;
  const { send, tabMessages } = await loadServiceWorker([AI_PACK], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type !== "SEND_TO_AI") return undefined;
      attempts += 1;
      // 第一次说「没找到输入框」（没送出去，重试是安全的），第二次成功
      if (attempts === 1) {
        return { success: false, error: "Chat input not found" };
      }
      return { success: true, result: { content: ECHO_CONTENT } };
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "retry-semantics",
    input: {},
    tabId: 42,
  });

  assert.equal(attempts, 2, "输入框没找到属于「没送出去」，必须重试");
  assert.deepEqual(
    kindsOf(tabMessages),
    ["SEND_TO_AI", "SEND_TO_AI"],
    "重试就是把这一步再跑一遍（对没送出去的失败这是对的）",
  );
  assert.equal(
    response?.success,
    true,
    `第二次成功时 Pack 必须成功，实际：${JSON.stringify(response?.error || response)}`,
  );
});

test("广播投递遇到超时：宁可失败也不重发", async () => {
  // 没有 tabId ⇒ 走 chrome.runtime.sendMessage 广播。
  // 这时后台不知道该让哪一个页面续等；重发是**确定的**副作用，
  // 等不到只是慢 ⇒ 选失败。
  const { send, runtimeMessages } = await loadServiceWorker([AI_PACK], {
    runtimeSendMessageResponse: TIMEOUT_ENVELOPE,
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "retry-semantics",
    input: {},
  });

  const broadcasts = runtimeMessages.filter((m) => m.type === "SEND_TO_AI");
  assert.equal(
    broadcasts.length,
    1,
    `广播超时后不许再发一遍，实际发了 ${broadcasts.length} 次——每多一次就是多一条重复提问`,
  );
  assert.equal(
    response?.success,
    false,
    "广播投递超时无法续等，必须如实失败，不能假装成功",
  );
  assert.match(
    response?.error || "",
    /不重发|重复提问/,
    "失败信息里要说清「为什么不重发」，否则用户只看到一句莫名的失败",
  );
});
