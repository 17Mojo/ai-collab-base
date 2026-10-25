/**
 * 消息计数模型判定的单测
 *
 * 这个判定守着两条不变量：
 *   1. 落地页（无会话）上，messageList 命中的元素必须都是**空的**；
 *   2. 空闲落地页上 isTyping() 必须是 false。
 *
 * 两条都是 2026-10-25 真机实测抓出来的——违反它们的直接后果是
 * waitForResponse 要么返回导航元素当回复，要么每次都必然超时。
 *
 * 下面每个用例都用**真机上抓到的真实数据**改写，
 * 不是凭空编的形状——改写时保留了实测到的类名与计数。
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { assessMessageCountModel } from "./message-model.mjs";

/** 2026-10-25 实测：Yiyan 落地页上 `[class*="chat"]` 命中的东西。 */
const YIYAN_SHELL = {
  selector: '[class*="chat"]',
  matched: true,
  count: 37,
  samples: [
    {
      tag: "body",
      className: "cos-chat cos-pc font-size-1",
      text: "新对话 新工作任务 定时任务…",
      textLength: 120,
      childCount: 40,
    },
    {
      tag: "div",
      className: "_chat-container_10y6s_1",
      text: "新对话 技能广场 知识库…",
      textLength: 88,
      childCount: 12,
    },
  ],
};

/** 2026-10-25 实测：Yuanbao 落地页上 `[class*="chat"]` 命中的东西。 */
const YUANBAO_BUTTON = {
  selector: '[class*="chat"]',
  matched: true,
  count: 8,
  samples: [
    {
      tag: "div",
      className: "yb-new-chat-entry",
      text: "新建对话",
      textLength: 4,
      childCount: 1,
    },
  ],
};

/** 2026-10-25 实测：Kimi 落地页上 `[class*="message"]` 命中的空容器。 */
const KIMI_EMPTY_CONTAINER = {
  selector: '[class*="message"]',
  matched: true,
  count: 2,
  samples: [
    {
      tag: "div",
      className: "message-list-container",
      text: "",
      textLength: 0,
      childCount: 1,
    },
    {
      tag: "div",
      className: "message-list",
      text: "",
      textLength: 0,
      childCount: 0,
    },
  ],
};

test("落地页上消息数为 0、isTyping 为 false —— 通过", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [],
    messageList: { count: 0 },
    isTyping: false,
  });
  assert.equal(verdict.ok, true);
  assert.deepEqual(verdict.falsePositiveSelectors, []);
});

test("命中界面外壳（Yiyan 的 _chat-container_）—— 判为硬伤", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [YIYAN_SHELL],
    messageList: { count: 37 },
    isTyping: false,
  });
  assert.equal(verdict.ok, false, "命中应用外壳必须判为硬伤");
  assert.deepEqual(verdict.falsePositiveSelectors, ['[class*="chat"]']);
  assert.ok(verdict.reason.includes("有内容的界面元素"), verdict.reason);
  assert.ok(verdict.reason.includes("_chat-container_10y6s_1"), verdict.reason);
});

test("命中界面按钮（Yuanbao 的 yb-new-chat-entry）—— 判为硬伤", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [YUANBAO_BUTTON],
    messageList: { count: 8 },
    isTyping: false,
  });
  assert.equal(verdict.ok, false);
  assert.ok(verdict.reason.includes("yb-new-chat-entry"), verdict.reason);
});

test("命中空容器（Kimi 的 message-list-container）—— 不算硬伤，但要留痕", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [KIMI_EMPTY_CONTAINER],
    messageList: { count: 2 },
    isTyping: false,
  });
  assert.equal(verdict.ok, true, "空容器不影响增长检测，不该判硬伤");
  assert.equal(verdict.count, 2);
  assert.ok(verdict.reason.includes("空容器"), verdict.reason);
  assert.ok(verdict.reason.includes("已登录会话"), "必须写明还差什么");
  assert.deepEqual(verdict.falsePositiveSelectors, []);
});

test("空闲页上 isTyping 为 true —— 判为硬伤（必然超时）", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [],
    messageList: { count: 0 },
    isTyping: true,
    typingIndicatorSelectors: [
      {
        selector: '[class*="loading"]',
        matched: true,
        count: 9,
        samples: [
          {
            tag: "div",
            className: "next-sidebar__history-loading",
            text: " ",
            textLength: 1,
            childCount: 0,
          },
        ],
      },
    ],
  });
  assert.equal(verdict.ok, false);
  assert.ok(verdict.reason.includes("空闲即不忙"), verdict.reason);
  assert.ok(verdict.reason.includes("next-sidebar__history-loading"), verdict.reason);
});

test("两处硬伤同时出现时，两条都写进 reason", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [YIYAN_SHELL],
    messageList: { count: 37 },
    isTyping: true,
  });
  assert.equal(verdict.ok, false);
  assert.ok(verdict.reason.includes("有内容的界面元素"));
  assert.ok(verdict.reason.includes("空闲即不忙"));
});

test("isTyping 为 null（未采到）不算硬伤", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [],
    messageList: { count: 0 },
    isTyping: null,
  });
  assert.equal(verdict.ok, true);
});

test("选择器非法（matched=false）不算命中", () => {
  const verdict = assessMessageCountModel({
    messageListSelectors: [
      { selector: "[", matched: false, count: 0, error: "选择器非法" },
    ],
    messageList: { count: 0 },
    isTyping: false,
  });
  assert.equal(verdict.ok, true);
});

test("缺字段的输入不会崩", () => {
  assert.equal(assessMessageCountModel({}).ok, true);
  assert.equal(assessMessageCountModel(undefined).ok, true);
});
