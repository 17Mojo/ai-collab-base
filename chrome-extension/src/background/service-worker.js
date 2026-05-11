/**
 * Prompt Pack - Service Worker
 * Chrome Extension Background Script (Manifest V3)
 */

// 导入模块
import PlatformAdapter from '../platforms/adapter.js';
import ClaudeAdapter from '../platforms/claude-adapter.js';
import PackExecutor from './pack-executor.js';
import NotebookLMPackExecutorBridge from './notebooklm-packexecutor-bridge.js';

// 平台适配器注册表
const adapters = {
  'claude.ai': new ClaudeAdapter(),
  'chat.openai.com': null // TODO: 实现 ChatGPT 适配器
};

// Pack 执行器实例
let packExecutor = null;

/**
 * 初始化扩展
 */
function initialize() {
  console.log('[Prompt Pack] Service Worker initialized');
  packExecutor = new PackExecutor();
}

/**
 * 获取当前平台的适配器
 * @param {string} url - 当前页面 URL
 * @returns {PlatformAdapter|null}
 */
function getAdapter(url) {
  for (const [platform, adapter] of Object.entries(adapters)) {
    if (url.includes(platform) && adapter) {
      return adapter;
    }
  }
  return null;
}

// 监听扩展安装
chrome.runtime.onInstalled.addListener((details) => {
  console.log('[Prompt Pack] Installed:', details.reason);
  initialize();
});

// 监听来自 Content Script 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Prompt Pack] Message received:', message.type);

  switch (message.type) {
    case 'GET_ADAPTER':
      const adapter = getAdapter(sender.tab?.url || '');
      sendResponse({ adapterId: adapter?.platformId || null });
      break;

    case 'EXECUTE_PACK':
      if (packExecutor) {
        packExecutor.execute(message.packId, message.input)
          .then(result => sendResponse({ success: true, result }))
          .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // 保持消息通道开放
      }
      break;

    case 'GET_PACK_STATUS':
      if (packExecutor) {
        const status = packExecutor.getStatus();
        sendResponse(status);
      }
      break;

    case 'GENERATE_STUDIO_ARTIFACTS':
      (async () => {
        try {
          const bridge = new NotebookLMPackExecutorBridge();
          const artifacts = [];

          for (const contentType of message.contentTypes) {
            const result = await bridge.generateArtifact(
              message.notebookId,
              contentType,
              { focus: message.focus, language: 'zh-CN' }
            );
            artifacts.push({ ...result, content_type: contentType });
          }

          sendResponse({ success: true, artifacts });
        } catch (error) {
          sendResponse({ success: false, error: error.message, artifacts: [] });
        }
      })();
      return true; // 保持消息通道开放

    default:
      sendResponse({ error: 'Unknown message type' });
  }
});

// 监听标签页更新
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const adapter = getAdapter(tab.url);
    if (adapter) {
      console.log(`[Prompt Pack] Platform detected: ${adapter.platformId}`);
    }
  }
});

// 初始化
initialize();
