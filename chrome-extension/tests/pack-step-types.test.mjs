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
