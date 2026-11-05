import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const PACK_PATH = fileURLToPath(new URL("../../packs/examples/xiaohongshu_knowledge_creator.json", import.meta.url));

const AI_STEP_TYPES = ["analysis", "generation", "validation", "fusion", "tracking", "ai"];

test("PackExecutor 把语义步骤类型统一走 _executeAIStep", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  for (const type of AI_STEP_TYPES) {
    const executor = new PackExecutor({ maxRetries: 0 });
    let received = null;
    executor._executeAIStep = async (step, execution) => {
      received = { type: step.type, execution };
      return `ai-output:${step.type}`;
    };
    const result = await executor._executeStep({ id: "s", name: type, type, retry: false }, {});
    assert.equal(result.success, true, `${type} 应成功`);
    assert.equal(result.error, null, `${type} 不应有错误`);
    assert.equal(result.output, `ai-output:${type}`);
    assert.equal(received?.type, type);
  }
});

test("PackExecutor._executeStepByType 也把语义步骤类型统一走 _executeAIStep", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  for (const type of AI_STEP_TYPES) {
    const executor = new PackExecutor({ maxRetries: 0 });
    let received = null;
    executor._executeAIStep = async (step, execution) => {
      received = { type: step.type, execution };
      return `ai-output:${step.type}`;
    };
    const output = await executor._executeStepByType({ id: "s", name: type, type }, {});
    assert.equal(output, `ai-output:${type}`);
    assert.equal(received?.type, type);
  }
});

test("PackExecutor 仍拒绝未收编的步骤类型", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const executor = new PackExecutor({ maxRetries: 0 });
  const result = await executor._executeStep({ id: "s", name: "bogus", type: "bogus", retry: false }, {});
  assert.equal(result.success, false);
  assert.match(result.error || "", /Unknown step type: bogus/);
});

test("_buildPrompt 用上游 output 替换占位符", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const executor = new PackExecutor();
  const step = { prompt_template: "主题:{{topic}} 开头:{{hook_statement}} 无:{{missing}}" };
  const prompt = executor._buildPrompt(step, {
    input: { topic: "AI写作工具" },
    output: { hook_statement: "90%的人用错了" },
  });
  assert.equal(prompt, "主题:AI写作工具 开头:90%的人用错了 无:{{missing}}");
});

test("execute 顺序路径回写 output 且提示词无残留", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const fs = await import("node:fs/promises");
  const pack = JSON.parse(await fs.readFile(PACK_PATH, "utf-8"));
  const executor = new PackExecutor({ maxRetries: 0 });
  executor.packs.set("xiaohongshu-knowledge-creator", pack);
  const prompts = [];
  executor._executeAIStep = async (step, execution) => {
    const prompt = executor._buildPrompt(step, execution);
    prompts.push({ id: step.id, prompt });
    return prompt;
  };
  const result = await executor.execute(
    "xiaohongshu-knowledge-creator",
    { topic: "AI写作工具", target_audience_level: "运营新手" },
    { tabId: null },
  );
  assert.equal(result.status, "completed");
  assert.ok(result.output.hook_statement);
  assert.ok(result.output.explanation_text);
  assert.ok(result.output.boundary_notes);
  for (const { id, prompt } of prompts) {
    assert.equal(prompt.match(/{{[^}]+}}/g), null, `${id} 不应残留占位符`);
  }
});

test("_executeAIStep 解包回复内容，output 全为文本且无 [object Object]", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const fs = await import("node:fs/promises");
  const pack = JSON.parse(await fs.readFile(PACK_PATH, "utf-8"));
  const sentPrompts = [];
  globalThis.chrome = {
    tabs: {
      sendMessage: async (_tabId, msg) => {
        sentPrompts.push(msg.prompt);
        return { success: true, result: { content: msg.prompt, messageCount: 1, duration: 0 } };
      },
    },
  };
  try {
    const executor = new PackExecutor({ maxRetries: 0 });
    executor.packs.set("xiaohongshu-knowledge-creator", pack);
    const result = await executor.execute(
      "xiaohongshu-knowledge-creator",
      { topic: "AI写作工具", target_audience_level: "运营新手" },
      { tabId: 1 },
    );
    assert.equal(result.status, "completed");
    const AI_OUTPUT_FIELDS = ["hook_statement", "explanation_text", "use_cases", "boundary_notes", "takeaway_content", "visual_content", "final_content"];
    for (const key of AI_OUTPUT_FIELDS) {
      assert.equal(typeof result.output[key], "string", `output.${key} 应为文本`);
      assert.equal(String(result.output[key]).includes("[object Object]"), false, `output.${key} 不应含 [object Object]`);
    }
    for (const prompt of sentPrompts) {
      assert.equal(String(prompt).includes("[object Object]"), false, "投递的提示词不应含 [object Object]");
    }
    assert.equal(typeof result.output.final_content, "string");
    assert.ok(result.output.final_content.length > 0);
  } finally {
    delete globalThis.chrome;
  }
});

// ─────────────────────────────────────────────────────────────────────
// N3：required_fields 守卫（空串也算缺——残句提示词的源头）
// ─────────────────────────────────────────────────────────────────────

test("_executeStep 拒绝 required_fields 缺失（含空串/纯空白）的步骤", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const step = {
    id: "s1",
    name: "收集",
    type: "local",
    input_fields: ["topic"],
    config: { required_fields: ["topic"] },
    retry: false,
  };
  for (const input of [{}, { topic: "" }, { topic: "   " }, { topic: null }]) {
    const executor = new PackExecutor({ maxRetries: 3 });
    const result = await executor._executeStep(step, { input, output: {} });
    assert.equal(result.success, false, `input=${JSON.stringify(input)} 应失败`);
    assert.match(result.error || "", /缺少必填输入: topic/);
    assert.equal(result.output, null);
  }
});

test("_executeStep 必填校验是确定性失败，不进重试", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const executor = new PackExecutor({ maxRetries: 3, retryDelay: 50 });
  let delayCalls = 0;
  executor._delay = async () => {
    delayCalls += 1;
  };
  const result = await executor._executeStep(
    {
      id: "s1",
      name: "收集",
      type: "local",
      input_fields: ["topic"],
      config: { required_fields: ["topic"] },
    },
    { input: { topic: "" }, output: {} },
  );
  assert.equal(result.success, false);
  assert.equal(delayCalls, 0, "必填缺失是确定性失败——一次重试都不该有");
});

test("_executeStep 必填可由上游 output 满足；齐备时 local 步骤照常产出", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const executor = new PackExecutor({ maxRetries: 0 });
  const step = {
    id: "s1",
    name: "收集",
    type: "local",
    input_fields: ["topic"],
    output_field: "topic_info",
    config: { required_fields: ["topic"] },
    retry: false,
  };
  // input 缺、上游 output 有 ⇒ 满足
  const fromOutput = await executor._executeStep(step, {
    input: {},
    output: { topic: "上游题" },
  });
  assert.equal(fromOutput.success, true);

  // input 有 ⇒ 满足，产出形状（input 字段名建键）保持不变
  const fromInput = await executor._executeStep(step, {
    input: { topic: "用户题" },
    output: {},
  });
  assert.equal(fromInput.success, true);
  assert.equal(fromInput.output.topic, "用户题");
});

test("必填失败会中止整个执行（status=failed，不再有残句提示词出城）", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const pack = {
    metadata: { pack_id: "n3-pack", pack_name: "N3", version: "1.0.0" },
    workflow: {
      steps: [
        {
          id: "step_1",
          name: "收集",
          type: "local",
          input_fields: ["topic"],
          output_field: "topic_info",
          config: { required_fields: ["topic"] },
        },
        {
          id: "step_2",
          name: "生成",
          type: "generation",
          prompt_template: "主题：{{topic}}。",
          output_field: "text",
        },
      ],
    },
  };
  const executor = new PackExecutor({ maxRetries: 0 });
  executor.packs.set("n3-pack", pack);
  let aiCalled = false;
  executor._executeAIStep = async () => {
    aiCalled = true;
    return "不该走到这里";
  };
  const result = await executor.execute("n3-pack", { topic: "" }, { tabId: null });
  assert.equal(result.status, "failed");
  assert.match(result.errors?.[0]?.message || "", /Step step_1 failed: 缺少必填输入: topic/);
  assert.equal(aiCalled, false, "step_1 失败后不许再发提示词");
});

// ─────────────────────────────────────────────────────────────────────
// N4：对象产出序列化（[object Object] 不许进提示词）
// ─────────────────────────────────────────────────────────────────────

test("_buildPrompt 对对象值 JSON 序列化，不产生 [object Object]", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const executor = new PackExecutor();
  const warns = [];
  const origWarn = console.warn;
  console.warn = (...a) => warns.push(a.join(" "));
  try {
    const step = { prompt_template: "信息:{{topic_info}} 数:{{count}} 标:{{flag}}" };
    const prompt = executor._buildPrompt(step, {
      input: {},
      output: {
        topic_info: { topic: "AI写作", style: "口语" },
        count: 3,
        flag: true,
      },
    });
    assert.equal(prompt.includes("[object Object]"), false, "对象必须被序列化");
    assert.match(prompt, /"topic":"AI写作"/, "对象应以 JSON 形式出现");
    assert.match(prompt, /数:3/, "数字走 String()");
    assert.match(prompt, /标:true/, "布尔走 String()");
    assert.ok(warns.length >= 3, `非字符串替换必须告警，实际 ${warns.length} 条`);
    assert.ok(warns.some((w) => w.includes("topic_info")));
  } finally {
    console.warn = origWarn;
  }
});

test("local 步骤对象产出经 {{output_field}} 消费时不出现 [object Object]", async () => {
  const { default: PackExecutor } = await import("../src/background/pack-executor.js");
  const pack = {
    metadata: { pack_id: "n4-pack", pack_name: "N4", version: "1.0.0" },
    workflow: {
      steps: [
        {
          id: "step_1",
          name: "收集",
          type: "local",
          input_fields: ["topic", "style"],
          output_field: "topic_info",
          config: { operation: "merge" },
        },
        {
          id: "step_2",
          name: "生成",
          type: "generation",
          input_fields: ["topic_info"],
          prompt_template: "背景:{{topic_info}}",
          output_field: "text",
        },
      ],
    },
  };
  const sent = [];
  globalThis.chrome = {
    tabs: {
      sendMessage: async (_tabId, msg) => {
        sent.push(msg.prompt);
        return {
          success: true,
          result: {
            // 回复要过 assertUsableAIContent 的最小长度闸（默认 50 字）
            content: msg.prompt + "（这里是足够长的模拟回复正文，越过最小长度闸，仅供本用例验证序列化。）",
            messageCount: 1,
            duration: 0,
          },
        };
      },
    },
  };
  try {
    const executor = new PackExecutor({ maxRetries: 0 });
    executor.packs.set("n4-pack", pack);
    const result = await executor.execute(
      "n4-pack",
      { topic: "AI写作", style: "口语" },
      { tabId: 1 },
    );
    assert.equal(result.status, "completed");
    for (const prompt of sent) {
      assert.equal(prompt.includes("[object Object]"), false, "提示词不许含 [object Object]");
    }
    assert.ok(
      sent.some((p) => p.includes('"topic":"AI写作"')),
      "topic_info 对象应以 JSON 进提示词",
    );
  } finally {
    delete globalThis.chrome;
  }
});
