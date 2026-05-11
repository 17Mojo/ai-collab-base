/**
 * Pack Executor
 * Pack 执行引擎，负责执行 Prompt Pack 的 workflow
 */

/**
 * Runtime Override 白名单 (prompt-pack-runtime-style Requirement 2)
 */
const ALLOWED_OVERRIDE_KEYS = [
  'user_query',
  'context_injection',
  'platform_selection',
  'model_preference'
];

/**
 * 执行状态枚举
 */
const ExecutionStatus = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

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
  static match(pattern, text, flags = '') {
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
        index: match.index
      };
    } catch (error) {
      console.error('RegexMatcher.match error:', error);
      return { matched: false, extracts: {}, fullMatch: null, error: error.message };
    }
  }

  /**
   * 全部匹配
   * @param {string} pattern - 正则模式
   * @param {string} text - 待匹配文本
   * @param {string} flags - 正则标志 (默认包含 g)
   * @returns {Array<Object>} 匹配结果数组
   */
  static matchAll(pattern, text, flags = 'g') {
    try {
      const regex = new RegExp(pattern, flags);
      const matches = [...text.matchAll(regex)];

      return matches.map(match => ({
        matched: true,
        extracts: match.groups || {},
        fullMatch: match[0],
        index: match.index
      }));
    } catch (error) {
      console.error('RegexMatcher.matchAll error:', error);
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
      case 'regex_match':
        if (branch.regex_config) {
          const result = RegexMatcher.match(
            branch.regex_config.pattern,
            String(targetValue),
            branch.regex_config.flags || ''
          );
          matched = result.matched;
          extracts = result.extracts;
        }
        break;

      case 'contains':
        matched = String(targetValue).includes(branch.condition_value);
        break;

      case 'equals':
        matched = String(targetValue) === branch.condition_value;
        break;

      case 'exists':
        matched = targetValue !== null && targetValue !== undefined && String(targetValue) !== '';
        break;

      case 'threshold':
        const numValue = parseFloat(targetValue);
        const threshold = branch.threshold_value || 0;
        matched = !isNaN(numValue) && numValue >= threshold;
        break;

      default:
        console.warn('Unknown condition_type:', branch.condition_type);
        matched = false;
    }

    // 处理否定条件
    if (branch.negate) {
      matched = !matched;
    }

    return {
      matched,
      targetStep: matched ? branch.target_step : null,
      extracts
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
      case 'output':
        return execution.output || {};
      case 'input':
        return execution.input || {};
      case 'context':
        return execution.context || {};
      case 'last_step_output':
        const lastStep = execution.steps[execution.steps.length - 1];
        return lastStep?.output || null;
      default:
        // 支持嵌套字段访问 (如: output.data)
        const parts = targetField.split('.');
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
      ...options
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
        warnings.push(`Invalid runtime_override key: '${key}' - not in whitelist`);
      }
    }

    // 记录验证警告 (prompt-pack-runtime-style: "SHALL log validation warnings for audit")
    if (warnings.length > 0) {
      console.warn('[PackExecutor] Runtime override validation warnings:', warnings);
    }

    return validOverrides;
  }

  /**
   * 加载 Pack
   * @param {Object} pack - Pack 定义
   */
  loadPack(pack) {
    if (!pack.metadata || !pack.metadata.pack_id) {
      throw new Error('Invalid pack: missing metadata or pack_id');
    }
    this.packs.set(pack.metadata.pack_id, pack);
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
   * @returns {Promise<Object>}
   */
  async execute(packId, input = {}) {
    const pack = this.getPack(packId);
    if (!pack) {
      throw new Error(`Pack not found: ${packId}`);
    }

    // 创建执行上下文
    const validatedOverrides = this._validateRuntimeOverrides(input);

    const execution = {
      packId,
      input,
      runtime_overrides: validatedOverrides,  // 存储验证后的合法 overrides
      startTime: Date.now(),
      status: ExecutionStatus.RUNNING,
      steps: [],
      output: {},
      errors: [],
      extractedData: {},  // 存储正则提取的数据
      stepIndex: new Map()  // 步骤 ID 到索引的映射
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
      const hasBranches = steps.some(step => step.branches && step.branches.length > 0);

      if (hasBranches) {
        // 使用分支执行流程
        await this._executeWorkflowWithBranching(steps, execution);
      } else {
        // 使用传统顺序执行 (向后兼容)
        for (const step of steps) {
          const stepResult = await this._executeStep(step, execution);
          execution.steps.push(stepResult);

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
        timestamp: Date.now()
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
    const maxIterations = steps.length * 3;  // 防止无限循环

    while (currentStepIndex < steps.length && executedSteps.size < maxIterations) {
      const step = steps[currentStepIndex];

      // 检查是否已执行过 (防止重复执行)
      if (executedSteps.has(step.id)) {
        console.warn(`Step ${step.id} already executed, skipping to prevent loop`);
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

      if (nextStepId === 'end') {
        // 明确结束
        break;
      }

      if (nextStepId) {
        // 跳转到指定步骤
        const nextIndex = execution.stepIndex.get(nextStepId);
        if (nextIndex !== undefined) {
          currentStepIndex = nextIndex;
        } else {
          console.warn(`Target step ${nextStepId} not found, continuing sequentially`);
          currentStepIndex++;
        }
      } else {
        // 顺序推进
        currentStepIndex++;
      }
    }

    if (executedSteps.size >= maxIterations) {
      console.warn('Max iterations reached, potential infinite loop detected');
      execution.errors.push({
        message: 'Max iterations reached',
        timestamp: Date.now()
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
            execution.extractedData = { ...execution.extractedData, ...result.extracts };
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
      error: null
    };

    try {
      switch (step.type) {
        case 'local':
          stepResult.output = await this._executeLocalStep(step, execution);
          break;

        case 'ai':
          stepResult.output = await this._executeAIStep(step, execution);
          break;

        default:
          throw new Error(`Unknown step type: ${step.type}`);
      }

      stepResult.success = true;

    } catch (error) {
      stepResult.error = error.message;

      // 重试逻辑
      if (step.retry !== false) {
        const retries = step.retries || this.options.maxRetries;
        for (let i = 0; i < retries; i++) {
          try {
            await this._delay(this.options.retryDelay);
            stepResult.output = await this._executeStepByType(step, execution);
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
      case 'local':
        return this._executeLocalStep(step, execution);
      case 'ai':
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
    if (config.operation === 'merge') {
      return { ...inputData };
    }

    return inputData;
  }

  /**
   * 执行 AI 步骤
   * @param {Object} step
   * @param {Object} execution
   * @returns {Promise<any>}
   */
  async _executeAIStep(step, execution) {
    // AI 步骤：需要与 AI 平台交互
    // 这里发送消息给 content script 执行
    const config = step.config || {};

    // 构建提示词
    const prompt = this._buildPrompt(step, execution);

    // 发送消息到 content script
    const response = await chrome.runtime.sendMessage({
      type: 'SEND_TO_AI',
      prompt,
      config
    });

    return response;
  }

  /**
   * 构建提示词
   * @param {Object} step
   * @param {Object} execution
   * @returns {string}
   */
  _buildPrompt(step, execution) {
    const template = step.prompt_template || '';
    const input = execution.input;
    const overrides = execution.runtime_overrides || {};

    // 模板替换 - 优先使用 runtime_overrides 白名单字段
    let prompt = template;

    // 1. 替换 runtime_overrides 字段 (白名单约束)
    for (const key of ALLOWED_OVERRIDE_KEYS) {
      if (overrides[key] !== undefined) {
        prompt = prompt.replace(new RegExp(`{{${key}}}`, 'g'), overrides[key]);
      }
    }

    // 2. 替换其他 input 字段 (向后兼容)
    for (const [key, value] of Object.entries(input)) {
      if (key !== 'runtime_overrides') {
        prompt = prompt.replace(new RegExp(`{{${key}}}`, 'g'), value);
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
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 获取执行状态
   * @returns {Object}
   */
  getStatus() {
    return {
      status: this.status,
      currentExecution: this.currentExecution ? {
        packId: this.currentExecution.packId,
        startTime: this.currentExecution.startTime,
        stepsCompleted: this.currentExecution.steps.filter(s => s.success).length,
        stepsTotal: this.currentExecution.steps.length
      } : null,
      historyCount: this.executionHistory.length,
      loadedPacks: Array.from(this.packs.keys())
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
