/**
 * NotebookLMPackExecutorBridge
 * NotebookLM + PackExecutor 协作桥接器
 *
 * 职责：
 * - NotebookLM 知识查询 → 注入 PackExecutor 执行上下文
 * - enhance_prompt() → 增强 workflow prompt
 * - 引用标注 → 输出包含 Source 信息
 */

/**
 * 协作执行状态
 */
const BridgeStatus = {
  IDLE: 'idle',
  QUERYING_KNOWLEDGE: 'querying_knowledge',
  ENHANCING_PROMPT: 'enhancing_prompt',
  EXECUTING_WORKFLOW: 'executing_workflow',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

/**
 * NotebookLMPackExecutorBridge 类
 */
class NotebookLMPackExecutorBridge {
  /**
   * @param {Object} options - 配置选项
   * @param {PackExecutor} options.packExecutor - PackExecutor 实例
   * @param {Object} options.notebooklmConfig - NotebookLM 配置
   */
  constructor(options = {}) {
    this.packExecutor = options.packExecutor || null;
    this.notebooklmConfig = options.notebooklmConfig || {
      notebookId: null,
      fallbackToMock: true
    };
    this.status = BridgeStatus.IDLE;
    this.currentBridgeExecution = null;
    this.bridgeHistory = [];
    this._logger = console;
  }

  /**
   * 设置 PackExecutor 实例
   * @param {PackExecutor} packExecutor
   */
  setPackExecutor(packExecutor) {
    this.packExecutor = packExecutor;
  }

  /**
   * 设置 NotebookLM 配置
   * @param {Object} config
   */
  setNotebookLMConfig(config) {
    this.notebooklmConfig = {
      ...this.notebooklmConfig,
      ...config
    };
  }

  /**
   * 知识增强执行（核心方法）
   * @param {string} packId - Pack ID
   * @param {Object} input - 用户输入
   * @param {Object} knowledgeOptions - 知识查询选项
   * @returns {Promise<Object>} - 增强执行结果
   */
  async executeWithKnowledge(packId, input = {}, knowledgeOptions = {}) {
    if (!this.packExecutor) {
      throw new Error('PackExecutor not set. Call setPackExecutor() first.');
    }

    // 创建桥接执行上下文
    const bridgeExecution = {
      packId,
      input,
      knowledgeOptions,
      startTime: Date.now(),
      status: BridgeStatus.IDLE,
      knowledgeResult: null,
      enhancedPrompt: null,
      executionResult: null,
      sources: [],
      errors: []
    };

    this.currentBridgeExecution = bridgeExecution;

    try {
      // === Phase 1: 知识查询 ===
      bridgeExecution.status = BridgeStatus.QUERYING_KNOWLEDGE;
      this._logger.log('[Bridge] Phase 1: Querying knowledge from NotebookLM...');

      const knowledgeResult = await this._queryKnowledge(input, knowledgeOptions);
      bridgeExecution.knowledgeResult = knowledgeResult;

      if (knowledgeResult.error && !this.notebooklmConfig.fallbackToMock) {
        throw new Error(`Knowledge query failed: ${knowledgeResult.error}`);
      }

      // === Phase 2: Prompt 增强 ===
      bridgeExecution.status = BridgeStatus.ENHANCING_PROMPT;
      this._logger.log('[Bridge] Phase 2: Enhancing prompt with knowledge...');

      const pack = this.packExecutor.getPack(packId);
      if (!pack) {
        throw new Error(`Pack not found: ${packId}`);
      }

      const enhancedPrompt = this._enhancePrompt(pack, knowledgeResult);
      bridgeExecution.enhancedPrompt = enhancedPrompt;

      // === Phase 3: 执行 Workflow ===
      bridgeExecution.status = BridgeStatus.EXECUTING_WORKFLOW;
      this._logger.log('[Bridge] Phase 3: Executing workflow with enhanced context...');

      // 创建增强的执行输入
      const enhancedInput = {
        ...input,
        knowledge_context: knowledgeResult.response || '',
        knowledge_sources: knowledgeResult.sources || []
      };

      const executionResult = await this.packExecutor.execute(packId, enhancedInput);
      bridgeExecution.executionResult = executionResult;

      // === Phase 4: 添加引用标注 ===
      bridgeExecution.sources = knowledgeResult.sources || [];

      if (executionResult.output) {
        executionResult.output.knowledge_sources = bridgeExecution.sources;
      }

      // === Phase 5: 完成 ===
      bridgeExecution.status = BridgeStatus.COMPLETED;
      bridgeExecution.endTime = Date.now();
      bridgeExecution.duration = bridgeExecution.endTime - bridgeExecution.startTime;

      this._logger.log('[Bridge] Execution completed with knowledge enhancement.');

    } catch (error) {
      bridgeExecution.status = BridgeStatus.FAILED;
      bridgeExecution.endTime = Date.now();
      bridgeExecution.duration = bridgeExecution.endTime - bridgeExecution.startTime;
      bridgeExecution.errors.push({
        message: error.message,
        timestamp: Date.now()
      });

      this._logger.error('[Bridge] Execution failed:', error);

      // 如果有 fallback，尝试无知识执行
      if (this.notebooklmConfig.fallbackToMock) {
        this._logger.log('[Bridge] Falling back to execution without knowledge...');
        try {
          bridgeExecution.executionResult = await this.packExecutor.execute(packId, input);
          bridgeExecution.status = BridgeStatus.COMPLETED;
          bridgeExecution.fallbackUsed = true;
        } catch (fallbackError) {
          bridgeExecution.errors.push({
            message: fallbackError.message,
            timestamp: Date.now(),
            isFallback: true
          });
        }
      }
    }

    // 保存历史
    this.bridgeHistory.push(bridgeExecution);
    this.currentBridgeExecution = null;
    this.status = BridgeStatus.IDLE;

    return bridgeExecution;
  }

  /**
   * 查询 NotebookLM 知识
   * @param {Object} input - 用户输入
   * @param {Object} options - 查询选项
   * @returns {Promise<Object>} - 知识结果
   */
  async _queryKnowledge(input, options = {}) {
    const topic = input.topic || input.subject || '';
    const context = options.context || '创作原则';
    const notebookId = this.notebooklmConfig.notebookId;

    // 构建 query
    const query = options.query || `关于${topic}的${context}，请简要总结要点`;

    // 尝试 Backend API 调用（推荐方式）
    try {
      const result = await this._queryViaBackendAPI(notebookId, query);
      if (result && result.response) {
        return result;
      }
    } catch (apiError) {
      this._logger.warn('[Bridge] Backend API query failed:', apiError);
    }

    // 尝试 MCP 调用（仅在 Claude Code 环境可用）
    try {
      if (typeof mcp__plugin_notebooklm__notebook_query === 'function') {
        const result = await mcp__plugin_notebooklm__notebook_query({
          notebook_id: notebookId,
          query: query
        });

        return {
          response: result.answer || result.response || '',
          sources: this._extractSources(result.references || []),
          mode: 'real'
        };
      }
    } catch (mcpError) {
      this._logger.warn('[Bridge] MCP query failed:', mcpError);
    }

    // 尝试 nlm CLI 调用（通过 subprocess - 仅在 Node 环境可用）
    try {
      const result = await this._queryViaNlmCLI(notebookId, query);
      if (result) {
        return result;
      }
    } catch (cliError) {
      this._logger.warn('[Bridge] nlm CLI query failed:', cliError);
    }

    // Mock 模式
    if (this.notebooklmConfig.fallbackToMock) {
      return this._getMockKnowledge(topic, context);
    }

    return {
      error: 'NotebookLM query failed',
      response: '',
      sources: [],
      mode: 'error'
    };
  }

  /**
   * 通过 Backend API 查询 NotebookLM
   * @param {string} notebookId
   * @param {string} query
   * @returns {Promise<Object>}
   */
  async _queryViaBackendAPI(notebookId, query) {
    const backendUrl = this.notebooklmConfig.backendUrl || 'http://127.0.0.1:8000';

    try {
      const response = await fetch(`${backendUrl}/api/notebooklm/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          notebook_id: notebookId,
          query: query
        })
      });

      if (!response.ok) {
        throw new Error(`Backend API error: ${response.status}`);
      }

      const data = await response.json();

      return {
        response: data.response || '',
        sources: data.sources || [],
        mode: 'real',
        notebook_id: data.notebook_id,
        query: data.query
      };
    } catch (error) {
      this._logger.error('[Bridge] Backend API fetch failed:', error);
      throw error;
    }
  }

  /**
   * 通过 nlm CLI 查询
   * @param {string} notebookId
   * @param {string} query
   * @returns {Promise<Object>}
   */
  async _queryViaNlmCLI(notebookId, query) {
    // 在 Chrome Extension 中无法直接调用 CLI
    // 这里仅作为文档说明，实际需要通过 backend 或 MCP
    this._logger.log('[Bridge] nlm CLI query would be: nlm query notebook ' + notebookId + ' "' + query + '"');
    return null;
  }

  /**
   * 从 references 提取 source 名称
   * @param {Array} references
   * @returns {string[]}
   */
  _extractSources(references) {
    if (!references || references.length === 0) return [];
    return references.map(ref => ref.source_title || ref.title || '未知来源');
  }

  /**
   * Mock 知识查询（用于测试/fallback）
   * @param {string} topic - 主题
   * @param {string} context - 上下文
   * @returns {Object} - Mock 知识结果
   */
  _getMockKnowledge(topic, context) {
    // 小红书创作规范 Mock 数据
    const mockKnowledgeBase = {
      '创作原则': {
        response: `
## 小红书知识型内容创作原则

1. **先给结论，再解释原因**
   - 开头必须是明确观点或反常识判断
   - 避免铺垫、背景介绍、学术定义

2. **讲人话，不讲术语**
   - 能不用专业名词就不用，必须用时一句话翻译
   - 多用生活类比、工作场景、真实体验

3. **场景化表达**
   - 每条内容包含至少1个具体场景
   - 明确：谁 + 在做什么 + 为什么用到它

4. **小红书友好结构**
   - 一句话结论 / 反直觉观点
   - 2-4个短段落解释（每段只讲1点）
   - 一个真实例子或对比
   - 一个避坑点 / 行内经验

5. **主动标注边界**
   - 允许说"目前还不成熟"
   - 明确什么人适合、什么人不适合
   - 不做"万能工具"叙事

6. **结尾给可带走的东西**
   - 一个判断标准
   - 一个简单框架
   - 一个可立即尝试的小动作
`,
        sources: ['小红书知识型博主创作指南.md', '小红书内容规范.md']
      },
      '图片格式': {
        response: `
## 小红书图片格式规范

1. **基础参数**
   - 比例：3:4 竖版（最佳）
   - 分辨率：1080×1440px
   - 数量：3-6张
   - 格式：PNG/JPG，单张 ≤ 20MB

2. **封面图要求**
   - 超大标题（占画面1/3以上）
   - 字号：80-120px
   - 高对比度（黑底白字/黄底黑字）
   - 一句话核心观点

3. **内容图要求**
   - 每张图只讲1个点
   - 文字占比 ≤ 40%
   - 字号：标题60-80px，正文40-50px
   - 序号提示（如2/5）

4. **配色规范**
   - 主色调：黑白灰 + 1个高亮色
   - 禁止超过4种颜色
   - 禁止低对比度

5. **字体规范**
   - 推荐：思源黑体、阿里巴巴普惠体、苹方
   - 禁止：花体、艺术字、过细字体
`,
        sources: ['小红书图片格式规范.md', '小红书视觉指南.md']
      },
      '避坑指南': {
        response: `
## 小红书创作避坑指南

❌ **禁止事项**:
- 标题党但内容空
- 过度乐观或恐吓式表达
- 把复杂问题一句话"神化解决"
- 明显的割韭菜话术
- 虚假宣传或夸大功效

⚠️ **常见错误**:
- 开头铺垫太多，读者3秒内不知道值不值得看
- 使用太多专业术语，普通人看不懂
- 没有具体场景，泛泛而谈
- 没有标注边界，读者不知道适不适合自己
- 结尾没有可带走的东西，看完就忘

✅ **正确做法**:
- 3秒内让读者知道核心观点
- 用生活类比解释复杂概念
- 至少1个具体使用场景
- 明确适用人群和不适用人群
- 结尾给判断标准或小动作
`,
        sources: ['小红书避坑指南.md', '内容合规规范.md']
      }
    };

    // 查找匹配的知识
    const knowledgeKey = Object.keys(mockKnowledgeBase).find(key =>
      context.includes(key) || topic.toLowerCase().includes(key.toLowerCase())
    );

    if (knowledgeKey) {
      return {
        response: mockKnowledgeBase[knowledgeKey].response,
        sources: mockKnowledgeBase[knowledgeKey].sources,
        mode: 'mock'
      };
    }

    // 默认返回创作原则
    return {
      response: mockKnowledgeBase['创作原则'].response,
      sources: mockKnowledgeBase['创作原则'].sources,
      mode: 'mock'
    };
  }

  /**
   * 增强 Prompt
   * @param {Object} pack - Pack 定义
   * @param {Object} knowledgeResult - 知识查询结果
   * @returns {string} - 增强后的 prompt
   */
  _enhancePrompt(pack, knowledgeResult) {
    const systemPrompt = pack.system_prompt || '';
    const knowledgeContext = knowledgeResult.response || '';

    if (!knowledgeContext) {
      return systemPrompt;
    }

    // 构建增强 prompt
    const enhancedPrompt = `
${systemPrompt}

---

## 参考知识（必须遵循）

${knowledgeContext}

---

## 执行要求

1. 严格按照"参考知识"中的创作原则生成内容
2. 确保内容结构符合小红书友好结构
3. 使用生活类比而非专业术语
4. 包含至少1个具体使用场景
5. 结尾给出可带走的东西
6. 标注适用人群边界

`;

    return enhancedPrompt;
  }

  /**
   * 获取桥接状态
   * @returns {Object}
   */
  getStatus() {
    return {
      status: this.status,
      currentBridgeExecution: this.currentBridgeExecution ? {
        packId: this.currentBridgeExecution.packId,
        startTime: this.currentBridgeExecution.startTime,
        phase: this.currentBridgeExecution.status,
        sources: this.currentBridgeExecution.sources
      } : null,
      historyCount: this.bridgeHistory.length,
      notebooklmConfig: this.notebooklmConfig
    };
  }

  /**
   * 获取桥接历史
   * @param {number} limit - 限制数量
   * @returns {Object[]}
   */
  getHistory(limit = 10) {
    return this.bridgeHistory.slice(-limit);
  }

  /**
   * 清除历史
   */
  clearHistory() {
    this.bridgeHistory = [];
  }

  /**
   * 独立产物生成（不依赖 Pack）
   * @param {string} notebookId - Notebook ID
   * @param {string} contentType - 内容类型 (audio/video/slides/infographic/mindmap/flashcards/briefing)
   * @param {Object} options - 生成选项
   * @returns {Promise<Object>}
   */
  async generateArtifact(notebookId, contentType, options = {}) {
    this._logger.log(`[Bridge] Generating artifact: ${contentType} from notebook ${notebookId}`);

    const validTypes = ['audio', 'video', 'slides', 'infographic', 'mindmap', 'flashcards', 'briefing'];
    if (!validTypes.includes(contentType)) {
      return {
        success: false,
        error: `Invalid content_type: ${contentType}. Valid types: ${validTypes.join(', ')}`,
        mode: 'error'
      };
    }

    // 尝试 Backend API 调用（推荐方式）
    try {
      const result = await this._generateViaBackendAPI(notebookId, contentType, options);
      if (result && result.success) {
        return result;
      }
    } catch (apiError) {
      this._logger.warn('[Bridge] Backend API generate failed:', apiError);
    }

    // 尝试 MCP 调用（仅在 Claude Code 环境可用）
    try {
      if (typeof mcp__plugin_notebooklm__studio_create === 'function') {
        const result = await mcp__plugin_notebooklm__studio_create({
          notebook_id: notebookId,
          content_type: contentType,
          style: options.style || 'default',
          orientation: options.orientation || 'vertical'
        });

        return {
          success: true,
          artifact_id: result.artifact_id || result.id,
          content_type: contentType,
          mode: 'real'
        };
      }
    } catch (mcpError) {
      this._logger.warn('[Bridge] Studio create MCP failed:', mcpError);
    }

    // Mock 模式
    return {
      success: true,
      artifact_id: `mock-${contentType}-${Date.now()}`,
      content_type: contentType,
      mode: 'mock',
      message: 'Studio artifact generated in mock mode',
      download_url: `/api/notebooklm/download/mock-${contentType}-${Date.now()}`
    };
  }

  /**
   * 通过 Backend API 生成产物
   * @param {string} notebookId
   * @param {string} contentType
   * @param {Object} options
   * @returns {Promise<Object>}
   */
  async _generateViaBackendAPI(notebookId, contentType, options) {
    const backendUrl = this.notebooklmConfig.backendUrl || 'http://127.0.0.1:8000';

    try {
      const response = await fetch(`${backendUrl}/api/notebooklm/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          notebook_id: notebookId,
          content_type: contentType,
          style: options.style || 'default',
          orientation: options.orientation || 'vertical',
          focus: options.focus || '',
          language: options.language || 'zh-CN'
        })
      });

      if (!response.ok) {
        throw new Error(`Backend API error: ${response.status}`);
      }

      const data = await response.json();
      const artifactId = data.artifact_id;

      // 等待产物生成完成
      if (artifactId) {
        await this._waitForArtifactCompletion(artifactId, backendUrl);
      }

      return {
        success: data.success,
        artifact_id: artifactId,
        content_type: data.content_type || contentType,
        mode: 'real',
        message: data.message,
        download_url: artifactId ? await this._getDownloadUrl(artifactId, backendUrl) : null
      };
    } catch (error) {
      this._logger.error('[Bridge] Backend API generate fetch failed:', error);
      throw error;
    }
  }

  /**
   * 等待产物生成完成
   * @param {string} artifactId
   * @param {string} backendUrl
   * @param {number} maxWaitMs - 最大等待时间
   * @returns {Promise<void>}
   */
  async _waitForArtifactCompletion(artifactId, backendUrl, maxWaitMs = 120000) {
    const pollInterval = 3000;
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitMs) {
      try {
        const response = await fetch(`${backendUrl}/api/notebooklm/status/${artifactId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.status === 'completed') return;
          if (data.status === 'failed') throw new Error(`Artifact generation failed: ${data.error || 'unknown'}`);
        }
      } catch (e) {
        if (e.message.includes('failed')) throw e;
      }
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
    throw new Error('Artifact generation timed out');
  }

  /**
   * 获取产物下载 URL
   * @param {string} artifactId
   * @param {string} backendUrl
   * @returns {Promise<string|null>}
   */
  async _getDownloadUrl(artifactId, backendUrl) {
    try {
      const response = await fetch(`${backendUrl}/api/notebooklm/download-url/${artifactId}`);
      if (response.ok) {
        const data = await response.json();
        return data.download_url || `${backendUrl}/api/notebooklm/download/${artifactId}`;
      }
    } catch (e) {
      this._logger.warn('[Bridge] Could not get download URL:', e);
    }
    return `${backendUrl}/api/notebooklm/download/${artifactId}`;
  }

  /**
   * 下载产物
   * @param {string} artifactId - 产物 ID
   * @param {string} savePath - 保存路径（可选）
   * @returns {Promise<Object>}
   */
  async downloadArtifact(artifactId, savePath = null) {
    this._logger.log(`[Bridge] Downloading artifact: ${artifactId}`);

    // 尝试 Backend API 下载
    try {
      const result = await this._downloadViaBackendAPI(artifactId, savePath);
      if (result && result.success) {
        return result;
      }
    } catch (apiError) {
      this._logger.warn('[Bridge] Backend API download failed:', apiError);
    }

    // Mock 模式
    return {
      success: true,
      artifact_id: artifactId,
      file_path: savePath || `/tmp/${artifactId}.mp3`,
      mode: 'mock',
      message: 'Artifact download in mock mode'
    };
  }

  /**
   * 通过 Backend API 下载产物
   * @param {string} artifactId
   * @param {string} savePath
   * @returns {Promise<Object>}
   */
  async _downloadViaBackendAPI(artifactId, savePath) {
    const backendUrl = this.notebooklmConfig.backendUrl || 'http://127.0.0.1:8000';

    try {
      const response = await fetch(`${backendUrl}/api/notebooklm/download/${artifactId}`, {
        method: 'GET'
      });

      if (!response.ok) {
        throw new Error(`Backend API error: ${response.status}`);
      }

      // 获取文件内容
      const blob = await response.blob();

      // 如果指定了保存路径，使用 Chrome Downloads API
      if (savePath && chrome.downloads) {
        const url = URL.createObjectURL(blob);
        await chrome.downloads.download({
          url: url,
          filename: savePath.split('/').pop(),
          saveAs: false
        });

        return {
          success: true,
          artifact_id: artifactId,
          file_path: savePath,
          mode: 'real'
        };
      }

      // 返回 Blob URL
      return {
        success: true,
        artifact_id: artifactId,
        blob_url: URL.createObjectURL(blob),
        mode: 'real'
      };
    } catch (error) {
      this._logger.error('[Bridge] Backend API download fetch failed:', error);
      throw error;
    }
  }
}

// 导出
export { NotebookLMPackExecutorBridge, BridgeStatus };
export default NotebookLMPackExecutorBridge;