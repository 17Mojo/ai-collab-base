/**
 * Prompt Pack - Multi-Platform Executor (优化版)
 * 真正的并发执行多平台 AI 查询
 */

/**
 * 多平台并发执行器
 * 实现同一提示词同时在多个 AI 平台注入
 *
 * 优化策略：
 * 1. 分阶段执行：注入 → 等待响应 → 收集结果
 * 2. 真正并发：同时向所有平台注入，不阻塞等待单个
 * 3. 轮询收集：定期检查响应状态，避免同步阻塞
 * 4. 超时控制：防止某个平台阻塞整体
 */
class MultiPlatformExecutor {
  /**
   * @param {Object} adapters - 平台适配器注册表
   * @param {Object} backendClient - Backend 客户端实例
   */
  constructor(adapters, backendClient) {
    this.adapters = adapters;
    this.backendClient = backendClient;
    this.activeTabs = new Map();

    // 执行状态跟踪
    this.executionStatus = new Map();
  }

  /**
   * 查找已打开的平台标签页
   * @returns {Promise<Array<{tabId: number, platformId: string, url: string}>>}
   */
  async findPlatformTabs() {
    const enabledPlatforms = Object.keys(this.adapters);
    console.log('[MultiPlatform] Enabled platforms:', enabledPlatforms.join(', '));

    let tabs;
    try {
      tabs = await chrome.tabs.query({});
      console.log('[MultiPlatform] Total tabs:', tabs.length);
    } catch (error) {
      console.error('[MultiPlatform] chrome.tabs.query failed:', error.message);
      return [];
    }

    const platformTabs = [];
    for (const tab of tabs) {
      for (const platformId of enabledPlatforms) {
        if (tab.url?.includes(platformId)) {
          platformTabs.push({
            tabId: tab.id,
            platformId,
            url: tab.url,
            adapter: this.adapters[platformId]
          });
          break;
        }
      }
    }

    console.log('[MultiPlatform] Platform tabs matched:', platformTabs.length);
    return platformTabs;
  }

  /**
   * Phase 1: 并发注入 - 同时向所有平台发送提示词（不等待响应）
   * @param {Array<{tabId, platformId}>} platformTabs
   * @param {string} content
   * @returns {Promise<Object>} 注入状态
   */
  async injectToAllPlatforms(platformTabs, content) {
    console.log('[MultiPlatform] Phase 1: Concurrent injection to', platformTabs.length, 'platforms');

    // 初始化执行状态
    const injectPromises = platformTabs.map(({ tabId, platformId }) => {
      this.executionStatus.set(tabId, {
        platformId,
        status: 'injecting',
        startTime: Date.now(),
        response: null
      });

      // 只注入，不等待 AI 响应
      return chrome.tabs.sendMessage(tabId, {
        type: 'INJECT_TEXT',
        text: content
      }).then(response => {
        console.log(`[MultiPlatform] Inject success: ${platformId}`);
        this.executionStatus.get(tabId).status = 'waiting_response';
        return { tabId, platformId, injectSuccess: response?.success ?? true };
      }).catch(error => {
        console.log(`[MultiPlatform] Inject failed: ${platformId}`, error.message);
        this.executionStatus.get(tabId).status = 'inject_failed';
        this.executionStatus.get(tabId).error = error.message;
        return { tabId, platformId, injectSuccess: false, error: error.message };
      });
    });

    // 并发注入（Promise.all 在这里是合理的，因为注入操作很快）
    const injectResults = await Promise.all(injectPromises);

    console.log('[MultiPlatform] Inject complete:',
      injectResults.filter(r => r.injectSuccess).length, 'success');

    return {
      total: platformTabs.length,
      successful: injectResults.filter(r => r.injectSuccess).length,
      results: injectResults
    };
  }

  /**
   * Phase 2: 轮询收集响应 - 定期检查各平台 AI 响应状态
   * @param {Array<{tabId, platformId}>} platformTabs
   * @param {number} maxWaitTime 最大等待时间（毫秒）
   * @param {number} pollInterval 轮询间隔（毫秒）
   * @returns {Promise<Array>} 收集到的响应
   */
  async collectResponses(platformTabs, maxWaitTime = 60000, pollInterval = 2000) {
    console.log('[MultiPlatform] Phase 2: Collecting responses, max wait:', maxWaitTime);

    const startTime = Date.now();
    const successfulTabs = platformTabs.filter(t =>
      this.executionStatus.get(t.tabId)?.status === 'waiting_response'
    );

    console.log('[MultiPlatform] Waiting for', successfulTabs.length, 'platforms to respond');

    const collectedResponses = [];

    // 轮询直到超时或所有响应收集完成
    while (Date.now() - startTime < maxWaitTime) {
      const remainingTime = maxWaitTime - (Date.now() - startTime);
      console.log(`[MultiPlatform] Polling... remaining: ${Math.round(remainingTime/1000)}s`);

      // 并发检查所有等待中的平台
      const pollPromises = successfulTabs.map(async ({ tabId, platformId }) => {
        const status = this.executionStatus.get(tabId);

        // 已经收集到响应的跳过
        if (status.status === 'response_collected') {
          return null;
        }

        try {
          // 检查是否正在生成响应（typing 状态）
          const pageState = await chrome.tabs.sendMessage(tabId, { type: 'GET_PAGE_STATE' });

          // 如果不在 typing 状态，尝试获取响应
          if (!pageState.isTyping) {
            const aiResponse = await chrome.tabs.sendMessage(tabId, {
              type: 'GET_LATEST_RESPONSE'
            });

            if (aiResponse && aiResponse.content && aiResponse.content.length > 20) {
              // 有有效响应
              console.log(`[MultiPlatform] ✅ Response from ${platformId}:`,
                aiResponse.content.substring(0, 30));

              status.status = 'response_collected';
              status.response = aiResponse.content;
              status.responseTime = Date.now() - status.startTime;

              return {
                platform: platformId,
                content: aiResponse.content,
                duration: status.responseTime
              };
            }
          }
        } catch (error) {
          // 连接失败，标记为错误
          console.log(`[MultiPlatform] Poll failed for ${platformId}:`, error.message);
          status.status = 'poll_failed';
          status.error = error.message;
        }

        return null;
      });

      // 执行轮询
      const pollResults = await Promise.all(pollPromises);

      // 收集新响应
      pollResults.forEach(result => {
        if (result) {
          collectedResponses.push(result);
        }
      });

      // 检查是否所有响应都已收集
      const collectedCount = successfulTabs.filter(t =>
        this.executionStatus.get(t.tabId)?.status === 'response_collected'
      ).length;

      console.log(`[MultiPlatform] Collected: ${collectedCount}/${successfulTabs.length}`);

      if (collectedCount >= successfulTabs.length) {
        console.log('[MultiPlatform] All responses collected!');
        break;
      }

      // 等待下一轮轮询
      await this._sleep(pollInterval);
    }

    // 超时后，收集已获得的响应并标记未响应的
    const finalResponses = [];
    successfulTabs.forEach(({ tabId, platformId }) => {
      const status = this.executionStatus.get(tabId);

      if (status.status === 'response_collected' && status.response) {
        finalResponses.push({
          platform: platformId,
          content: status.response,
          duration: status.responseTime
        });
      } else if (status.status === 'waiting_response') {
        // 超时未响应
        console.log(`[MultiPlatform] ⏱️ Timeout for ${platformId}`);
        status.status = 'timeout';
      }
    });

    console.log('[MultiPlatform] Final responses:', finalResponses.length);

    return finalResponses;
  }

  /**
   * 执行完整并发流程
   * @param {string} content
   * @param {Object} options
   * @param {Array} preFilteredTabs - 可选：预过滤的平台标签页
   * @returns {Promise<Object>}
   */
  async executeAll(content, options = {}, preFilteredTabs = null) {
    // 使用预过滤的标签页，或重新查找
    const platformTabs = preFilteredTabs || await this.findPlatformTabs();

    if (platformTabs.length === 0) {
      console.log('[MultiPlatform] No platform tabs found');
      return {
        totalPlatforms: 0,
        successful: 0,
        failed: 0,
        aiResponses: []
      };
    }

    console.log(`[MultiPlatform] === Starting concurrent execution ===`);
    console.log(`[MultiPlatform] Platforms: ${platformTabs.map(t => t.platformId).join(', ')}`);

    const startTime = Date.now();
    const maxWaitTime = options.timeout || 60000;

    // 清理执行状态
    this.executionStatus.clear();

    // Phase 1: 并发注入
    const injectResult = await this.injectToAllPlatforms(platformTabs, content);

    // Phase 2: 轮询收集响应
    const aiResponses = await this.collectResponses(platformTabs, maxWaitTime);

    const duration = Date.now() - startTime;

    console.log(`[MultiPlatform] === Execution complete ===`);
    console.log(`[MultiPlatform] Duration: ${duration}ms`);
    console.log(`[MultiPlatform] Responses: ${aiResponses.length}/${platformTabs.length}`);

    return {
      totalPlatforms: platformTabs.length,
      successful: aiResponses.length,
      failed: platformTabs.length - aiResponses.length,
      aiResponses,
      duration,
      injectResult,
      _debug: {
        executionStatus: Array.from(this.executionStatus.entries()).map(([tabId, status]) => ({
          tabId,
          platformId: status.platformId,
          status: status.status,
          responseTime: status.responseTime
        }))
      }
    };
  }

  /**
   * 单平台执行（保持兼容性）
   * @param {number} tabId
   * @param {string} content
   * @param {number} timeout
   * @returns {Promise<Object>}
   */
  async executeOnPlatform(tabId, content, timeout = 60000) {
    console.log('[MultiPlatform] Single platform execution, tabId:', tabId);

    try {
      // 注入
      await chrome.tabs.sendMessage(tabId, {
        type: 'INJECT_TEXT',
        text: content
      });

      // 等待响应
      await this._sleep(2000);

      // 获取响应
      const aiResponse = await chrome.tabs.sendMessage(tabId, {
        type: 'GET_LATEST_RESPONSE'
      });

      return {
        tabId,
        status: 'success',
        aiResponse: aiResponse?.content || ''
      };
    } catch (error) {
      return {
        tabId,
        status: 'failed',
        error: error.message
      };
    }
  }

  /**
   * 完整工作流
   */
  async executeFullWorkflow(topic, config = {}) {
    console.log('[MultiPlatform] Starting full workflow for:', topic);

    const startTime = Date.now();

    // Phase 1: 多平台并发
    let platformResults = null;
    try {
      platformResults = await this.executeAll(topic, config);
    } catch (error) {
      console.log('[MultiPlatform] Execution failed:', error.message);
    }

    // Phase 2: Backend 共识
    const consensusResult = await this.backendClient.generateConsensus(topic, {
      real_responses: platformResults?.aiResponses?.length > 0
        ? platformResults.aiResponses
        : undefined
    });

    // Phase 3: 灵魂注入
    const soulProfile = config.soulProfile || 'luoyonghao';
    const soulResult = await this.backendClient.injectSoul(
      consensusResult.consensus,
      soulProfile
    );

    const duration = Date.now() - startTime;

    return {
      workflow: 'complete',
      duration,
      platformExecution: platformResults,
      consensus: consensusResult,
      soulInjection: soulResult,
      finalOutput: soulResult.personalized_content
    };
  }

  /**
   * 打开平台标签页
   */
  async openPlatformTab(platformId) {
    const platformUrls = {
      'claude.ai': 'https://claude.ai',
      'chat.openai.com': 'https://chat.openai.com',
      'chatgpt.com': 'https://chatgpt.com',
      'gemini.google.com': 'https://gemini.google.com',
      'kimi.com': 'https://kimi.com',
      'qianwen.com': 'https://qianwen.com',
      'chatglm.cn': 'https://chatglm.cn',
      'longcat.chat': 'https://longcat.chat',
      'yuanbao.tencent.com': 'https://yuanbao.tencent.com/chat/',
      'yiyan.baidu.com': 'https://yiyan.baidu.com/'
    };

    const url = platformUrls[platformId];
    if (!url) {
      throw new Error(`Unknown platform: ${platformId}`);
    }

    const tab = await chrome.tabs.create({ url });
    this.activeTabs.set(platformId, tab.id);

    // 等待加载
    await new Promise(resolve => {
      chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
        if (tabId === tab.id && changeInfo.status === 'complete') {
          resolve();
        }
      });
    });

    return tab.id;
  }

  /**
   * 批量打开平台
   */
  async openAllPlatforms(platformIds) {
    const tabIds = {};
    for (const platformId of platformIds) {
      try {
        tabIds[platformId] = await this.openPlatformTab(platformId);
      } catch (error) {
        console.error(`[MultiPlatform] Failed to open ${platformId}:`, error);
      }
    }
    return tabIds;
  }

  /**
   * 辅助函数：延迟
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

export default MultiPlatformExecutor;