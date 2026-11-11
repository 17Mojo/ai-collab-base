/**
 * Pack 的「会话边界」（`fresh_session`）契约
 *
 * ## 为什么需要这个能力
 *
 * deepseek 与 longcat 都在 step_8（fusion）挂掉，但**不是同一个错**：
 * deepseek 是答案超出 4×180s 窗口，longcat 是平台直接报「服务出错啦」。
 * 两个平台无关，却在同一位置撞墙 ⇒ 要找共同变量。
 *
 * 隔离实验给出来了：把 longcat 那条 **2437 字**的 fusion 提示词原样发进
 * **全新会话** —— **21 秒答完，产出 1481 字正文**。
 * ⇒ 提示词本身不被任何一方拒绝，**「单会话串行跑完 8 步」才是变量**。
 *
 * 所以 Pack 需要一个显式声明：这一步是自足的（所需字段全在提示词里内联），
 * 不该继续背着前面 7 轮的上下文。
 *
 * ## 这份测试钉什么
 *
 * 1. 声明了 `fresh_session` 的步骤，**必须先在同一个标签页开新会话，再发**；
 * 2. 没声明就**不许**多这一步——共用会话对某些 Pack 是有意义的；
 * 3. 开新会话失败时**一条提示词都不许发**。这是最要紧的一条：发进旧会话的
 *    后果是静默的——答案照样生成，只是又撞墙，而现象仍像「平台慢」；
 * 4. 广播投递声明 fresh_session ⇒ 明确失败（不知道该操作哪个页面）；
 * 5. 真实 Pack 里声明了 fresh_session 的步骤，其提示词引用的变量必须
 *    **全部来自上游**——自足是 fresh_session 成立的前提。
 *
 * 用法：node --test tests/session-boundary.test.mjs（run-tests.mjs 会自动收）
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { loadServiceWorker } from "./helpers/service-worker-harness.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 从本文件所在目录往上找交付的 Pack。
 *
 * **不能写死 `../../packs`**：变异检查会把整个 `tests/` 复制到
 * `<扩展根>/.mutation-tmp/tests/` 下，深度比原地多一层，于是 `../../packs`
 * 落到 `<扩展根>/packs`（不存在）——2026-11-11 全量变异跑到最后一条时
 * 就是这么发现「真实 Pack 的 step_8_output 声明了 fresh_session=prefer」
 * 与「…变量必须全部来自上游」两条**在副本里恒红**的（ENOENT），
 * 也就是说这两条守护此前从未被变异检查真正判定过。
 *
 * @param {string} rel 相对路径（如 `packs/examples/xxx.json`）
 * @returns {string} 绝对路径
 */
function findUpwards(rel) {
  let dir = HERE;
  for (let i = 0; i < 6; i += 1) {
    const candidate = resolve(dir, rel);
    if (existsSync(candidate)) return candidate;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  throw new Error(`找不到 ${rel}：从 ${HERE} 往上找了 6 层都没有`);
}

const PACK_PATH = findUpwards("packs/examples/xiaohongshu_knowledge_creator.json");

/** 单步 AI Pack；`fresh` 决定是否声明会话边界（`true`/`"strict"`/`"prefer"`） */
const makePack = (fresh) => ({
  metadata: { pack_id: "session-boundary", pack_name: "会话边界" },
  workflow: {
    steps: [
      {
        id: "step_ai",
        type: "ai",
        prompt_template: "你好",
        retries: 1,
        ...(fresh ? { fresh_session: fresh } : {}),
      },
    ],
  },
});

const kindsOf = (tabMessages) => tabMessages.map((m) => m.msg.type);

// ─────────────────────────────────────────────────────────────────────
// 一、执行顺序
// ─────────────────────────────────────────────────────────────────────

test("声明 fresh_session ⇒ 先开新会话，再发提示词（同一标签页）", async () => {
  const { send, tabMessages } = await loadServiceWorker([makePack(true)]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });

  assert.deepEqual(
    kindsOf(tabMessages),
    ["NEW_SESSION", "SEND_TO_AI"],
    `顺序必须是「先开新会话再发」。实际：${JSON.stringify(kindsOf(tabMessages))}`,
  );
  assert.equal(
    tabMessages[0].tabId,
    42,
    "开新会话与发送必须落在**同一个**标签页——换页面等于换了会话",
  );
  assert.equal(response?.success, true, `正常路径必须成功：${response?.error}`);
});

test("没声明 fresh_session ⇒ 不许凭空开新会话", async () => {
  const { send, tabMessages } = await loadServiceWorker([makePack(false)]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });

  assert.deepEqual(
    kindsOf(tabMessages),
    ["SEND_TO_AI"],
    "会话是否共用应该由 Pack 说了算，执行器不许自己加戏",
  );
  assert.equal(response?.success, true);
});

// ─────────────────────────────────────────────────────────────────────
// 二、失败时必须「不发」，而不是「回退到旧会话继续发」
// ─────────────────────────────────────────────────────────────────────

test("strict：开新会话失败 ⇒ 一条提示词都不许发，Pack 必须失败", async () => {
  const { send, tabMessages } = await loadServiceWorker([makePack(true)], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type === "NEW_SESSION") {
        return {
          success: false,
          error: "找不到「新对话」入口",
          code: "NEW_SESSION_CONTROL_NOT_FOUND",
        };
      }
      // 万一真的发了，就给一个正常回复——让「发了」这件事暴露成断言失败
      return undefined;
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });

  assert.equal(
    kindsOf(tabMessages).filter((k) => k === "SEND_TO_AI").length,
    0,
    "开新会话失败后仍然发了提示词 ⇒ 它进了旧会话，这个缺陷是**静默的**，" +
      "现象只会表现成「平台又慢了」",
  );
  assert.equal(response?.success, false, "开不了新会话时这一步必须失败");
  assert.match(
    response?.error || "",
    /新会话|旧会话/,
    `错误信息要说明是「会话没开成」，实际：${response?.error}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 二之二、prefer：开不成就降级，但降级必须**可见**
// ─────────────────────────────────────────────────────────────────────

test("prefer：开不成也照常发送，但回执里必须留下 available:false", async () => {
  const { send, tabMessages } = await loadServiceWorker([
    makePack("prefer"),
  ], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type === "NEW_SESSION") {
        return {
          success: true,
          result: {
            available: false,
            strategy: "none",
            reason: "找不到「新对话」入口",
          },
        };
      }
      return undefined;
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });

  assert.deepEqual(
    kindsOf(tabMessages),
    ["NEW_SESSION", "SEND_TO_AI"],
    "prefer 的语义是「尽力而为」：开不成就继续发，不能把站点打成失败",
  );
  assert.equal(response?.success, true, "prefer 模式下这一步必须仍然成功");

  const resets = response?.result?.sessionResets;
  assert.ok(Array.isArray(resets) && resets.length === 1, "回执里必须有会话边界的记录");
  assert.equal(
    resets[0].available,
    false,
    "降级必须如实记录成 available:false——否则「开了新会话」与「没开成」" +
      "在证据上长得一模一样，那就又变成一句无法核验的声明",
  );
  assert.equal(resets[0].mode, "prefer");
  assert.equal(resets[0].stepId, "step_ai");
});

test("NEW_SESSION 上报的 durationMs 原样进回执（重置开销可复核）", async () => {
  const { send } = await loadServiceWorker([makePack("prefer")], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type === "NEW_SESSION") {
        return {
          success: true,
          result: {
            available: true,
            strategy: "adapter-selector",
            messageCountBefore: 12,
            messageCountAfter: 0,
            durationMs: 1234,
          },
        };
      }
      return undefined;
    },
  });
  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });
  assert.equal(
    response?.result?.sessionResets?.[0]?.durationMs,
    1234,
    "重置耗时必须能从内容脚本一路透到 EXECUTE_PACK 回执——否则整包变快/变慢永远只能猜",
  );
});

test("prefer：开成功时回执记录 available:true 与所用策略", async () => {
  const { send, tabMessages } = await loadServiceWorker([
    makePack("prefer"),
  ], {
    tabsSendMessageResponse: (tabId, msg) => {
      if (msg.type === "NEW_SESSION") {
        return {
          success: true,
          result: {
            available: true,
            strategy: "adapter-selector",
            messageCountBefore: 16,
            messageCountAfter: 0,
          },
        };
      }
      return undefined;
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    tabId: 42,
  });

  assert.deepEqual(kindsOf(tabMessages), ["NEW_SESSION", "SEND_TO_AI"]);
  assert.equal(response?.success, true);

  const [record] = response.result.sessionResets;
  assert.equal(record.available, true);
  assert.equal(record.strategy, "adapter-selector");
  assert.equal(record.messageCountBefore, 16, "前后的消息数是「真的重置了」的物证");
  assert.equal(record.messageCountAfter, 0);
});

// ─────────────────────────────────────────────────────────────────────
// 三、广播投递：不知道该操作哪个页面
// ─────────────────────────────────────────────────────────────────────

test("广播投递声明 fresh_session ⇒ 明确失败，且不发提示词", async () => {
  const { send, tabMessages, runtimeMessages } = await loadServiceWorker([
    makePack(true),
  ]);

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "session-boundary",
    input: {},
    // 不给 tabId ⇒ 走 chrome.runtime 广播
  });

  assert.equal(
    tabMessages.length,
    0,
    `广播时不应向任何具体标签页发消息，实际：${JSON.stringify(kindsOf(tabMessages))}`,
  );
  assert.equal(
    runtimeMessages.filter((m) => m.type === "SEND_TO_AI").length,
    0,
    "不知道该让哪个页面开新会话时，不许广播出去碰运气",
  );
  assert.equal(response?.success, false);
  assert.match(
    response?.error || "",
    /广播|精确投递/,
    `错误信息要指出「广播投递做不到」，实际：${response?.error}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// 四、真实 Pack 的声明必须站得住
// ─────────────────────────────────────────────────────────────────────

/** 从 `{{var}}` 里取出变量名（去重） */
function templateVars(template) {
  return [...new Set([...String(template || "").matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]))];
}

test("真实 Pack 的 step_8_output 声明了 fresh_session=prefer", () => {
  const pack = JSON.parse(readFileSync(PACK_PATH, "utf-8"));
  const step = pack.workflow.steps.find((s) => s.id === "step_8_output");
  assert.ok(step, "找不到 step_8_output");
  assert.equal(
    step.fresh_session,
    "prefer",
    "step_8 是撞墙那一步：提示词把 6 个上游字段全内联了，却还要背着前 7 轮" +
      "上下文——这正是隔离实验证伪的那个假设。用 prefer 而不是 strict，" +
      "是因为实测只有 chatglm / 文心有可识别的「新对话」入口；" +
      "strict 会把这几个本来跑得通的站点直接打成 7/8",
  );
});

test("声明 fresh_session 的步骤，提示词引用的变量必须全部来自上游", () => {
  const pack = JSON.parse(readFileSync(PACK_PATH, "utf-8"));
  // 运行输入（不进对话历史，所以总是可用）
  const inputs = new Set();
  for (const step of pack.workflow.steps) {
    for (const f of (step.config || {}).required_fields || []) inputs.add(f);
    for (const f of (step.config || {}).optional_fields || []) inputs.add(f);
  }

  const produced = new Set(inputs);
  const problems = [];

  for (const step of pack.workflow.steps) {
    // 判「有没有声明」而不是判「等于 true」：
    // `"prefer"` 与 `"strict"` 在支持新会话的站点上一样会把历史清空——
    // 2026-11-11 这条原本写的是 `=== true`，而出厂 Pack 声明的正是
    // `"prefer"`，于是**这条自足性检查对交付的那个 Pack 从来没执行过**
    // （变异检查跑到最后才暴露：锚点挂在一条永远进不去分支的测试上）。
    if (step.fresh_session) {
      // 开新会话 ⇒ 对话历史一片空白，只能靠提示词自己带齐
      const need = templateVars(step.prompt_template);
      const missing = need.filter((v) => !produced.has(v));
      if (missing.length) {
        problems.push(
          `${step.id} 声明了 fresh_session="${step.fresh_session}"，但提示词引用的 ` +
            `${missing.join(", ")} 不在任何上游产出里——开新会话后这些变量会是空的`,
        );
      }
    }
    if (step.output_field) produced.add(step.output_field);
  }

  assert.deepEqual(
    problems,
    [],
    `fresh_session 的前提是「提示词自足」。不满足时开了新会话反而更糟：\n${problems.join("\n")}`,
  );
});
