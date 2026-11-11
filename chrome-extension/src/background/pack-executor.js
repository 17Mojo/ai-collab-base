/**
 * Pack Executor
 * Pack 执行引擎，负责执行 Prompt Pack 的 workflow
 */

import {
  MIN_AI_CONTENT_LENGTH_DEFAULT,
  isUsableAIContent,
} from "../utils/wait-policy.js";
import {
  FAILURE_STRATEGY,
  failureStrategy,
} from "../utils/retry-policy.js";

/**
 * Runtime Override 白名单 (prompt-pack-runtime-style Requirement 2)
 */
const ALLOWED_OVERRIDE_KEYS = [
  "user_query",
  "context_injection",
  "platform_selection",
  "model_preference",
];

/**
 * 执行状态枚举
 */
const ExecutionStatus = {
  IDLE: "idle",
  RUNNING: "running",
  PAUSED: "paused",
  COMPLETED: "completed",
  FAILED: "failed",
};

/**
 * 检查内容脚本对 SEND_TO_AI 的回话，失败就抛。
 *
 * ## 为什么必须有这一步
 *
 * 内容脚本是**如实**报告失败的：`sendResponse({success:false, error})`
 * （见 content-script.js 的 SEND_TO_AI 分支）。但执行器此前把回话
 * **原样返回**，`_executeStep` 紧接着无条件 `stepResult.success = true`
 * ⇒ 内容脚本说的失败被吞掉 ⇒ popup 显示「执行成功」。
 *
 * 2026-10-26 排演实测（第二十二步）：修好前三处断点后，排演在
 * **匿名会话**下拿到了 popup 的「状态: 执行成功」，但页面上
 * **提示词还留在输入框里**（压根没发出去），且页面上有「登录」。
 * 那正是这条缺陷在真实世界的样子——
 * 「成功」两个字是假的，外部用户会以为链路通了。
 *
 * 守护：tests/external-user-path.test.mjs 的
 * 「内容脚本报告失败时，整个 Pack 必须失败」。
 *
 * @param {any} response - 内容脚本的回话
 * @param {number|null} targetTabId - 目标标签页（null = 广播）
 * @throws {Error} 内容脚本报告失败时抛出
 */
function assertAIStepSucceeded(response, targetTabId) {
  if (!response || response.success !== false) return;

  const where =
    targetTabId === null || targetTabId === undefined
      ? "页面"
      : `标签页 ${targetTabId}`;
  const error = new Error(
    `${where}没能完成这次发送：${response.error || "未知原因"}。` +
      "如果那个网站要求先登录，请先在页面上登录再重试。",
  );
  // 把失败语义随错误一起带上去。文案只是给人看的，**分流要看 code**
  // （N21）：超时若被当成「可重试」，重试就会把同一句话再发一遍。
  if (response.code) error.code = response.code;
  if (Number.isInteger(response.baselineCount)) {
    error.baselineCount = response.baselineCount;
  }
  throw error;
}

/**
 * 校验 AI 步骤取回的正文是**可用的完整回复**，不是流式开头碎片。
 *
 * ## 为什么必须有这一步（2026-11-04 千问真机实锤）
 *
 * `assertAIStepSucceeded` 只看回话信封上的 success 位——而内容脚本
 * 在「太早成功」缺陷下会把流式开头碎片（'收到，'）如实当作 content
 * 交上来，信封照样是 success。于是 8 步 Pack 全部「成功」，
 * 产物却是 7 段碎片 + 1 个空串（空串那个连 output 字段都没进）。
 *
 * 这一步把「内容可用」变成硬闸门：空串 / 纯空白 / 短于阈值
 * （默认 20 字符，`step.config.min_output_length` 可按步骤覆盖）
 * 一律判失败——碎片冒充回复到此为止。
 *
 * 守护：tests/external-user-path.test.mjs 的
 * 「AI 步骤取回流式开头碎片时，整个 Pack 必须失败」。
 *
 * @param {string} content - 内容脚本交上来的正文
 * @param {Object} step - 步骤定义（读 `config.min_output_length`）
 * @param {number|null} targetTabId - 目标标签页（null = 广播）
 * @throws {Error} 内容为空或短于阈值时抛出
 */
function assertUsableAIContent(content, step, targetTabId) {
  const minLen = step?.config?.min_output_length ?? MIN_AI_CONTENT_LENGTH_DEFAULT;
  if (isUsableAIContent(content, minLen)) return;

  const text = typeof content === "string" ? content.trim() : "";
  const where =
    targetTabId === null || targetTabId === undefined
      ? "页面"
      : `标签页 ${targetTabId}`;
  throw new Error(
    `${where}取回的 AI 回复不可用（长度 ${text.length} < ${minLen}）：` +
      "回复多半还没生成完就被取走（流式开头碎片）。" +
      "请重试；若反复出现，说明该站点的「生成中」信号没被认出来。",
  );
}

/**
 * 正则匹配器
 */
class RegexMatcher {
  /**
   * 单次匹配
   * @param {string} pattern - 正则模式
   * @param {string} text - 待匹配文本
   * @param {string} flags - 正则标志 (i, m, g)
   * @returns {Object} { matched, extracts, fullMatch }
   */
  static match(pattern, text, flags = "") {
    try {
      // 处理命名捕获组
      const regex = new RegExp(pattern, flags);
      const match = text.match(regex);

      if (!match) {
        return { matched: false, extracts: {}, fullMatch: null };
      }

      // 提取捕获组
      const extracts = match.groups || {};

      return {
        matched: true,
        extracts,
        fullMatch: match[0],
        index: match.index,
      };
    } catch (error) {
      console.error("RegexMatcher.match error:", error);
      return {
        matched: false,
        extracts: {},
        fullMatch: null,
        error: error.message,
      };
    }
  }

  /**
   * 全部匹配
   * @param {string} pattern - 正则模式
   * @param {string} text - 待匹配文本
   * @param {string} flags - 正则标志 (默认包含 g)
   * @returns {Array<Object>} 匹配结果数组
   */
  static matchAll(pattern, text, flags = "g") {
    try {
      const regex = new RegExp(pattern, flags);
      const matches = [...text.matchAll(regex)];

      return matches.map((match) => ({
        matched: true,
        extracts: match.groups || {},
        fullMatch: match[0],
        index: match.index,
      }));
    } catch (error) {
      console.error("RegexMatcher.matchAll error:", error);
      return [];
    }
  }
}

/**
 * 分支评估器
 */
class BranchEvaluator {
  /**
   * 评估分支条件
   * @param {Object} branch - 分支条件定义
   * @param {Object} execution - 执行上下文
   * @returns {Object} { matched, targetStep, extracts }
   */
  static evaluate(branch, execution) {
    const targetValue = this._getTargetValue(branch.target_field, execution);

    let matched = false;
    let extracts = {};

    switch (branch.condition_type) {
      case "regex_match":
        if (branch.regex_config) {
          const result = RegexMatcher.match(
            branch.regex_config.pattern,
            String(targetValue),
            branch.regex_config.flags || "",
          );
          matched = result.matched;
          extracts = result.extracts;
        }
        break;

      case "contains":
        matched = String(targetValue).includes(branch.condition_value);
        break;

      case "equals":
        matched = String(targetValue) === branch.condition_value;
        break;

      case "exists":
        matched =
          targetValue !== null &&
          targetValue !== undefined &&
          String(targetValue) !== "";
        break;

      case "threshold":
        const numValue = parseFloat(targetValue);
        const threshold = branch.threshold_value || 0;
        matched = !isNaN(numValue) && numValue >= threshold;
        break;

      default:
        console.warn("Unknown condition_type:", branch.condition_type);
        matched = false;
    }

    // 处理否定条件
    if (branch.negate) {
      matched = !matched;
    }

    return {
      matched,
      targetStep: matched ? branch.target_step : null,
      extracts,
    };
  }

  /**
   * 获取目标字段值
   * @param {string} targetField - 目标字段名
   * @param {Object} execution - 执行上下文
   * @returns {any}
   */
  static _getTargetValue(targetField, execution) {
    switch (targetField) {
      case "output":
        return execution.output || {};
      case "input":
        return execution.input || {};
      case "context":
        return execution.context || {};
      case "last_step_output":
        const lastStep = execution.steps[execution.steps.length - 1];
        return lastStep?.output || null;
      default:
        // 支持嵌套字段访问 (如: output.data)
        const parts = targetField.split(".");
        let value = execution;
        for (const part of parts) {
          value = value?.[part];
        }
        return value;
    }
  }
}

/**
 * Pack 执行器
 */
class PackExecutor {
  /**
   * @param {Object} options - 配置选项
   */
  constructor(options = {}) {
    this.packs = new Map();
    this.currentExecution = null;
    this.executionHistory = [];
    this.status = ExecutionStatus.IDLE;
    this.options = {
      maxRetries: 3,
      retryDelay: 1000,
      timeout: 60000,
      ...options,
    };
  }

  /**
   * 验证 runtime_overrides 白名单 (prompt-pack-runtime-style Requirement 2)
   * @param {Object} input - 输入数据
   * @returns {Object} 验证后的合法 overrides
   */
  _validateRuntimeOverrides(input) {
    const overrides = input?.runtime_overrides || {};
    const validOverrides = {};
    const invalidKeys = [];
    const warnings = [];

    for (const [key, value] of Object.entries(overrides)) {
      if (ALLOWED_OVERRIDE_KEYS.includes(key)) {
        validOverrides[key] = value;
      } else {
        invalidKeys.push(key);
        warnings.push(
          `Invalid runtime_override key: '${key}' - not in whitelist`,
        );
      }
    }

    // 记录验证警告 (prompt-pack-runtime-style: "SHALL log validation warnings for audit")
    if (warnings.length > 0) {
      console.warn(
        "[PackExecutor] Runtime override validation warnings:",
        warnings,
      );
    }

    return validOverrides;
  }

  /**
   * 加载 Pack
   * @param {Object} pack - Pack 定义
   */
  loadPack(pack) {
    if (!pack.metadata || !pack.metadata.pack_id) {
      throw new Error("Invalid pack: missing metadata or pack_id");
    }
    this.packs.set(pack.metadata.pack_id, pack);
  }

  /**
   * 用一批 Pack **整体替换**执行器里的 Pack
   *
   * 为什么要有这个口子：Pack 的事实源是 chrome.storage.local["packs"]
   * （service-worker 的 CREATE/UPDATE/DELETE/IMPORT 都写它），
   * 而此前执行器只提供了逐个添加的 loadPack()，**没有任何地方调用它**
   * ⇒ getPack() 恒为 null ⇒ 每次执行都报 "Pack not found: <id>"。
   *
   * 逐个添加的写法在「存储是事实源」这个模型下本来就不该用：
   * 删掉的 Pack 会留在执行器里，删了也还在。
   *
   * @param {Array<Object>} packs
   * @returns {string[]} 实际装进去的 pack_id
   */
  replacePacks(packs) {
    this.packs.clear();
    const loaded = [];
    for (const pack of packs || []) {
      try {
        this.loadPack(pack);
        loaded.push(pack.metadata.pack_id);
      } catch (error) {
        // 单个 Pack 不合法不该让整批都进不来——但要留下痕迹
        console.warn(
          "[PackExecutor] 跳过不合法的 Pack：",
          error.message,
          pack?.metadata?.pack_id || "(无 id)",
        );
      }
    }
    return loaded;
  }

  /**
   * 获取 Pack
   * @param {string} packId
   * @returns {Object|null}
   */
  getPack(packId) {
    return this.packs.get(packId) || null;
  }

  /**
   * 执行 Pack
   * @param {string} packId - Pack ID
   * @param {Object} input - 输入数据
   * @param {Object} [options] - 执行选项
   * @param {number|null} [options.tabId] - 目标标签页 id
   * @returns {Promise<Object>}
   */
  async execute(packId, input = {}, options = {}) {
    const pack = this.getPack(packId);
    if (!pack) {
      throw new Error(`Pack not found: ${packId}`);
    }

    // 创建执行上下文
    const validatedOverrides = this._validateRuntimeOverrides(input);

    const execution = {
      packId,
      input,
      runtime_overrides: validatedOverrides, // 存储验证后的合法 overrides
      // 目标标签页：AI 步骤要发到**哪一个**页面上去
      targetTabId: options.tabId ?? null,
      startTime: Date.now(),
      status: ExecutionStatus.RUNNING,
      steps: [],
      output: {},
      errors: [],
      extractedData: {}, // 存储正则提取的数据
      stepIndex: new Map(), // 步骤 ID 到索引的映射
    };

    this.currentExecution = execution;
    this.status = ExecutionStatus.RUNNING;

    try {
      // 执行 workflow 步骤
      const workflow = pack.workflow || {};
      const steps = workflow.steps || [];

      // 构建步骤索引映射
      for (let i = 0; i < steps.length; i++) {
        execution.stepIndex.set(steps[i].id, i);
      }

      // 检查是否有分支逻辑
      const hasBranches = steps.some(
        (step) => step.branches && step.branches.length > 0,
      );

      if (hasBranches) {
        // 使用分支执行流程
        await this._executeWorkflowWithBranching(steps, execution);
      } else {
        // 使用传统顺序执行 (向后兼容)
        for (const step of steps) {
          const stepResult = await this._executeStep(step, execution);
          execution.steps.push(stepResult);

          if (stepResult.output) {
            execution.output[step.output_field || step.id] = stepResult.output;
          }

          if (!stepResult.success) {
            throw new Error(`Step ${step.id} failed: ${stepResult.error}`);
          }
        }
      }

      // 标记完成
      execution.status = ExecutionStatus.COMPLETED;
      execution.endTime = Date.now();
      execution.duration = execution.endTime - execution.startTime;
    } catch (error) {
      execution.status = ExecutionStatus.FAILED;
      execution.endTime = Date.now();
      execution.duration = execution.endTime - execution.startTime;
      execution.errors.push({
        message: error.message,
        timestamp: Date.now(),
      });
    }

    // 保存历史
    this.executionHistory.push(execution);
    this.currentExecution = null;
    this.status = ExecutionStatus.IDLE;

    return execution;
  }

  /**
   * 使用分支逻辑执行 workflow
   * @param {Array} steps - 步骤列表
   * @param {Object} execution - 执行上下文
   */
  async _executeWorkflowWithBranching(steps, execution) {
    let currentStepIndex = 0;
    const executedSteps = new Set();
    const maxIterations = steps.length * 3; // 防止无限循环

    while (
      currentStepIndex < steps.length &&
      executedSteps.size < maxIterations
    ) {
      const step = steps[currentStepIndex];

      // 检查是否已执行过 (防止重复执行)
      if (executedSteps.has(step.id)) {
        console.warn(
          `Step ${step.id} already executed, skipping to prevent loop`,
        );
        currentStepIndex++;
        continue;
      }

      // 执行当前步骤
      const stepResult = await this._executeStep(step, execution);
      execution.steps.push(stepResult);
      executedSteps.add(step.id);

      // 更新 output
      if (stepResult.output) {
        execution.output[step.output_field || step.id] = stepResult.output;
      }

      // 处理错误分支
      if (!stepResult.success && step.on_error) {
        const errorStepIndex = execution.stepIndex.get(step.on_error);
        if (errorStepIndex !== undefined) {
          currentStepIndex = errorStepIndex;
          continue;
        }
      }

      // 确定下一步
      const nextStepId = this._determineNextStep(step, execution);

      if (nextStepId === "end") {
        // 明确结束
        break;
      }

      if (nextStepId) {
        // 跳转到指定步骤
        const nextIndex = execution.stepIndex.get(nextStepId);
        if (nextIndex !== undefined) {
          currentStepIndex = nextIndex;
        } else {
          console.warn(
            `Target step ${nextStepId} not found, continuing sequentially`,
          );
          currentStepIndex++;
        }
      } else {
        // 顺序推进
        currentStepIndex++;
      }
    }

    if (executedSteps.size >= maxIterations) {
      console.warn("Max iterations reached, potential infinite loop detected");
      execution.errors.push({
        message: "Max iterations reached",
        timestamp: Date.now(),
      });
    }
  }

  /**
   * 根据分支条件确定下一步
   * @param {Object} step - 当前步骤
   * @param {Object} execution - 执行上下文
   * @returns {string|null} 下一步 ID 或 null (顺序推进)
   */
  _determineNextStep(step, execution) {
    // 1. 检查显式 next_step
    if (step.next_step) {
      return step.next_step;
    }

    // 2. 检查分支条件
    if (step.branches && step.branches.length > 0) {
      for (const branch of step.branches) {
        const result = BranchEvaluator.evaluate(branch, execution);

        if (result.matched) {
          // 存储提取的数据
          if (result.extracts && Object.keys(result.extracts).length > 0) {
            execution.extractedData = {
              ...execution.extractedData,
              ...result.extracts,
            };
          }

          return result.targetStep;
        }
      }
    }

    // 3. 无分支匹配，顺序推进
    return null;
  }

  /**
   * 执行单个步骤
   * @param {Object} step - 步骤定义
   * @param {Object} execution - 执行上下文
   * @returns {Promise<Object>}
   */
  async _executeStep(step, execution) {
    const stepResult = {
      id: step.id,
      name: step.name,
      type: step.type,
      startTime: Date.now(),
      success: false,
      output: null,
      error: null,
      // N8：投递方式标记。判定与 _executeAIStep 的分支同源：
      // targetTabId 非空 ⇒ chrome.tabs.sendMessage 精确投递到那一个标签页；
      // 否则 chrome.runtime.sendMessage 广播——**每一个**内容脚本都会收到并各自发。
      // popup 据此提示「已广播到所有打开的 AI 页面」，否则用户以为只发了一次。
      // local 步骤不投递，null。
      delivery:
        step.type === "local"
          ? null
          : execution.targetTabId != null
            ? "precise"
            : "broadcast",
    };

    // N3：pack 自己声明的 required_fields 缺失（含空串）——确定性失败，
    // 不进重试、不带空洞继续。残句提示词（「主题：。」）出城是最坏一类失败：
    // 报 completed 但内容是残的。这里 fail 该步骤，顺序路径随即中止整个执行。
    const missing = this._missingRequiredFields(step, execution);
    if (missing.length) {
      stepResult.error = `缺少必填输入: ${missing.join(", ")}`;
      stepResult.endTime = Date.now();
      stepResult.duration = stepResult.endTime - stepResult.startTime;
      return stepResult;
    }

    try {
      switch (step.type) {
        case "local":
          stepResult.output = await this._executeLocalStep(step, execution);
          break;

        case "ai":
        case "analysis":
        case "generation":
        case "validation":
        case "fusion":
        case "tracking":
          stepResult.output = await this._executeAIStep(step, execution);
          break;

        default:
          throw new Error(`Unknown step type: ${step.type}`);
      }

      stepResult.success = true;
    } catch (error) {
      stepResult.error = error.message;

      // ── 重试前的语义分流（N21 的根治）─────────────────────────────
      //
      // 改之前这里是一段**不看错误语义**的重试：失败就再跑一遍这一步。
      // 对 AI 步骤来说「再跑一遍」= 把同一句提示词**再发一次**。
      //
      // 而超时的语义是「**已经发出去了**，只是没等到回复」，不是「没发出去」。
      // 于是重试把超时放大成：会话里多一条重复提问、AI 再答一遍、烧双倍额度。
      // 2026-11-11 chatglm 的耗时指纹就是这么读出来的——step_2 用了 170.7s
      // （≈60+60+50.7）、step_7 用了 151.3s（≈60+60+31.3），errors 却是空的，
      // 说明中途至少重发过一次，只是重发后碰巧等到了回复。
      //
      // 现在：超时走「续等」——让页面盯着同一个会话继续等，**不重发**。
      const strategy = failureStrategy(error);
      const resumeOnly = strategy === FAILURE_STRATEGY.RESUME_WAIT;
      const retryable =
        strategy !== FAILURE_STRATEGY.FAIL && step.retry !== false;

      if (resumeOnly && execution.targetTabId == null) {
        // 广播投递：不知道该让哪一个页面续等。
        // 宁可失败，也不重发——重发是**确定的**副作用，等不到只是慢。
        stepResult.error =
          `${error.message}（超时后不重发：重发会在会话里留下重复提问。` +
          "本次是广播投递，后台不知道该让哪一个页面续等——" +
          "请让扩展精确投递到目标标签页后重试。）";
      } else if (retryable) {
        const retries = step.retries || this.options.maxRetries;
        for (let i = 0; i < retries; i++) {
          try {
            await this._delay(this.options.retryDelay);
            stepResult.output = resumeOnly
              ? await this._resumeWaitForResponse(
                  step,
                  execution,
                  error.baselineCount,
                )
              : await this._executeStepByType(step, execution);
            stepResult.success = true;
            stepResult.error = null;
            break;
          } catch (retryError) {
            stepResult.error = retryError.message;
          }
        }
      }
    }

    stepResult.endTime = Date.now();
    stepResult.duration = stepResult.endTime - stepResult.startTime;

    return stepResult;
  }

  /**
   * 根据类型执行步骤
   */
  async _executeStepByType(step, execution) {
    switch (step.type) {
      case "local":
        return this._executeLocalStep(step, execution);
      case "ai":
      case "analysis":
      case "generation":
      case "validation":
      case "fusion":
      case "tracking":
        return this._executeAIStep(step, execution);
      default:
        throw new Error(`Unknown step type: ${step.type}`);
    }
  }

  /**
   * 执行本地步骤
   * @param {Object} step
   * @param {Object} execution
   * @returns {Promise<any>}
   */
  async _executeLocalStep(step, execution) {
    // 本地步骤：处理数据、转换格式等
    const config = step.config || {};
    const inputFields = step.input_fields || [];

    // 收集输入数据
    const inputData = {};
    for (const field of inputFields) {
      inputData[field] = execution.input[field] || execution.output[field];
    }

    // 简单的数据处理逻辑
    if (config.operation === "merge") {
      return { ...inputData };
    }

    return inputData;
  }

  /**
   * 检查 pack 声明的 config.required_fields 是否齐备（N3）。
   *
   * 空串/纯空白也算缺——`execution.input[field] || ...` 这类取值会把空串
   * 静默吞成 undefined，popup 留空提交时残句就是这么产生的。
   * 值从 input + 上游 output 的并集里找（步骤输入两处都可能来）。
   *
   * @param {Object} step
   * @param {Object} execution
   * @returns {string[]} 缺失的字段名
   */
  _missingRequiredFields(step, execution) {
    const required = (step.config || {}).required_fields || [];
    const pool = { ...(execution.output || {}), ...(execution.input || {}) };
    return required.filter((field) => {
      const value = pool[field];
      if (value === undefined || value === null) return true;
      if (typeof value === "string" && value.trim() === "") return true;
      return false;
    });
  }

  /**
   * 执行 AI 步骤
   * @param {Object} step
   * @param {Object} execution
   * @param {number|null} execution.targetTabId - 目标标签页（null = 广播）
   * @returns {Promise<any>}
   */
  async _executeAIStep(step, execution) {
    // AI 步骤：需要与 AI 平台交互
    // 这里发送消息给 content script 执行
    const config = step.config || {};

    // 构建提示词
    const prompt = this._buildPrompt(step, execution);

    // 发送消息到 content script
    //
    // 发到**哪一个**页面上去，这件事以前是含糊的：
    // 用 `chrome.runtime.sendMessage` 发 ⇒ 扩展里**每一个**内容脚本都会收到
    // ⇒ 用户开着 3 个 AI 页面时，提示词会在 3 个页面里各发一次
    // （聊天记录凭空多出三条，对第一次用的人来说是「这扩展在乱发消息」）。
    //
    // 所以：**已知目标标签页时一律用 `chrome.tabs.sendMessage` 精确投递**；
    // 不知道目标标签页时才退回广播，并在结果里标明是广播。
    const targetTabId = execution.targetTabId;
    if (targetTabId !== null && targetTabId !== undefined) {
      let response;
      try {
        // 注意：消息体是**内联**写的字面量，不是提前存进变量。
        // 静态护栏（tests/extension-wiring.test.mjs）要能从调用点
        // 直接看出发的是哪种消息——存进变量它就看不出来了。
        response = await chrome.tabs.sendMessage(targetTabId, {
          type: "SEND_TO_AI",
          prompt,
          config,
        });
      } catch (error) {
        // 最常见的原因：那个标签页不是受支持的 AI 站点，
        // 或者页面在扩展装好之前就打开着（内容脚本没注入）。
        throw new Error(
          `无法把提示词发到标签页 ${targetTabId}：${error.message}。` +
            "请确认该页面是受支持的 AI 站点（千问/文心/元宝/Kimi/…），" +
            "并在扩展装好之后刷新一次页面。",
        );
      }
      // 消息**送达**了，但内容脚本可能报告自己没干成活
      // （例如页面上是登录墙，提示词压根没发出去）。
      // 这一步在 try/catch **外面**——否则它的错误信息会被
      // 上面的「无法把提示词发到标签页」再包一层，读起来像消息没送到。
      assertAIStepSucceeded(response, targetTabId);
      const content = response?.result?.content ?? "";
      assertUsableAIContent(content, step, targetTabId);
      return content;
    }

    // 没有目标标签页：广播。**每个**内容脚本都会收到并各自执行。
    const response = await chrome.runtime.sendMessage({
      type: "SEND_TO_AI",
      prompt,
      config,
    });
    assertAIStepSucceeded(response, null);
    const content = response?.result?.content ?? "";
    assertUsableAIContent(content, step, null);
    return content;
  }

  /**
   * 续等：不重发，让页面继续盯着**同一个**会话等回复（N21）。
   *
   * ## 和 `_executeAIStep` 的区别只有一个动作
   *
   * `_executeAIStep` 是先注入、再点发送、再等——三步。续等**不碰前两步**，
   * 只让内容脚本把「等」继续下去。这一字之差就是会话里有没有重复提问。
   *
   * ## 为什么要带 `baselineCount`
   *
   * 页面判完成用的 `countGrew` 是 `currentCount > initialCount`。
   * 续等如果让页面重新数一次 `initialCount`，而回复恰好在「超时」与
   * 「续等开始」之间落地，就会变成「拿已经含回复的条数当基准」⇒
   * `countGrew` 恒 false ⇒ 白等满一整个超时窗口。
   * 所以必须把**发送前**那个数带回去（见 retry-policy.resolveInitialCount）。
   *
   * @param {Object} step - 步骤定义（读 `config.timeout`，不设则内容脚本按站点例外表回落）
   * @param {Object} execution - 执行上下文（读 `targetTabId`）
   * @param {number|undefined} baselineCount - 发送前的消息条数
   * @returns {Promise<string>} 取回的正文
   * @throws {Error} 没有目标标签页 / 没有基准条数 / 续等又超时
   */
  async _resumeWaitForResponse(step, execution, baselineCount) {
    const targetTabId = execution.targetTabId;
    if (targetTabId === null || targetTabId === undefined) {
      // 调用方已经拦过这种情况，这里再兜一次：静默退化成「重新数」是最坏的
      const error = new Error(
        "无法续等：本次是广播投递，不知道该让哪一个页面继续等。",
      );
      error.code = "RESUME_WAIT_NO_TARGET";
      throw error;
    }
    if (!Number.isInteger(baselineCount) || baselineCount < 0) {
      // 没有基准条数就续等 = 重新快照 = countGrew 恒 false = 白等。
      // 与其假装在等，不如如实报出来（调用方据此判失败）。
      const error = new Error(
        "无法续等：内容脚本没有报告发送前的消息条数（baselineCount），" +
          "重新数会把已经落地的回复算进基准，导致永远等不到完成。",
      );
      error.code = "RESUME_WAIT_NO_BASELINE";
      throw error;
    }

    const response = await chrome.tabs.sendMessage(targetTabId, {
      type: "WAIT_FOR_RESPONSE",
      // 不传 timeout 时内容脚本按 PLATFORM_RESPONSE_TIMEOUT 回落，
      // 与第一次发送用的是同一个上限——不用在这里复制一份站点表。
      timeout: step?.config?.timeout,
      baselineCount,
    });
    assertAIStepSucceeded(response, targetTabId);
    const content = response?.result?.content ?? "";
    assertUsableAIContent(content, step, targetTabId);
    return content;
  }

  /**
   * 构建提示词
   * @param {Object} step
   * @param {Object} execution
   * @returns {string}
   */
  /**
   * 模板变量值转字符串（N4）。
   *
   * `prompt.replace(..., value)` 遇到对象会隐式调用 String(value) ⇒ 字面量
   * [object Object] 进提示词。对象/数组走 JSON.stringify，其余走 String()；
   * 非字符串值一律 console.warn 留痕（pack 作者据此发现自己的模板在消费对象）。
   *
   * @param {string} key - 变量名（仅用于告警）
   * @param {any} value
   * @returns {string}
   */
  _stringifyVarValue(key, value) {
    if (typeof value === "string") return value;
    console.warn(
      `[pack-executor] 模板变量 {{${key}}} 的值不是字符串（${typeof value}），已序列化后替换`,
    );
    if (value === null) return "null";
    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  }

  _buildPrompt(step, execution) {
    const template = step.prompt_template || "";
    const input = execution.input || {};
    const output = execution.output || {};
    const overrides = execution.runtime_overrides || {};
    const vars = { ...output, ...input };

    // 模板替换 - 优先使用 runtime_overrides 白名单字段
    let prompt = template;

    // 1. 替换 runtime_overrides 字段 (白名单约束)
    for (const key of ALLOWED_OVERRIDE_KEYS) {
      if (overrides[key] !== undefined) {
        prompt = prompt.replace(
          new RegExp(`{{${key}}}`, "g"),
          this._stringifyVarValue(key, overrides[key]),
        );
      }
    }

    // 2. 替换其他变量字段 (上游 output + 初始 input)
    for (const [key, value] of Object.entries(vars)) {
      if (key !== "runtime_overrides" && value !== undefined) {
        prompt = prompt.replace(
          new RegExp(`{{${key}}}`, "g"),
          this._stringifyVarValue(key, value),
        );
      }
    }

    return prompt;
  }

  /**
   * 延迟
   * @param {number} ms
   * @returns {Promise<void>}
   */
  _delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * 获取执行状态
   * @returns {Object}
   */
  getStatus() {
    return {
      status: this.status,
      currentExecution: this.currentExecution
        ? {
            packId: this.currentExecution.packId,
            startTime: this.currentExecution.startTime,
            stepsCompleted: this.currentExecution.steps.filter((s) => s.success)
              .length,
            stepsTotal: this.currentExecution.steps.length,
          }
        : null,
      historyCount: this.executionHistory.length,
      loadedPacks: Array.from(this.packs.keys()),
    };
  }

  /**
   * 获取执行历史
   * @param {number} limit
   * @returns {Object[]}
   */
  getHistory(limit = 10) {
    return this.executionHistory.slice(-limit);
  }

  /**
   * 清除历史
   */
  clearHistory() {
    this.executionHistory = [];
  }
}

export default PackExecutor;
