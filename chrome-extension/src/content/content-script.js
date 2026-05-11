/**
 * Prompt Pack - Content Script
 * 注入到 AI 聊天页面的脚本
 */

// 平台适配器实例
let currentAdapter = null;

/**
 * 初始化 Content Script
 */
async function initialize() {
  console.log('[Prompt Pack] Content Script initialized');

  // 请求获取适配器
  const response = await chrome.runtime.sendMessage({ type: 'GET_ADAPTER' });

  if (response.adapterId) {
    console.log(`[Prompt Pack] Using adapter: ${response.adapterId}`);
    setupEventListeners();
  } else {
    console.log('[Prompt Pack] No adapter available for this page');
  }
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
  // 监听来自 Background 的消息
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case 'INJECT_TEXT':
        handleInjectText(message.text)
          .then(() => sendResponse({ success: true }))
          .catch(error => sendResponse({ success: false, error: error.message }));
        return true;

      case 'GET_PAGE_STATE':
        const state = getPageState();
        sendResponse(state);
        break;

      case 'WAIT_FOR_RESPONSE':
        handleWaitForResponse(message.timeout)
          .then(result => sendResponse({ success: true, result }))
          .catch(error => sendResponse({ success: false, error: error.message }));
        return true;
    }
  });
}

/**
 * 获取页面状态
 * @returns {Object}
 */
function getPageState() {
  return {
    url: window.location.href,
    hasInput: !!document.querySelector('div[contenteditable="true"]'),
    hasMessages: document.querySelectorAll('[data-testid="conversation-turn"]').length > 0
  };
}

/**
 * 处理文本注入
 * @param {string} text
 */
async function handleInjectText(text) {
  const input = document.querySelector('div[contenteditable="true"]');
  if (!input) {
    throw new Error('Input element not found');
  }

  // 聚焦输入框
  input.focus();

  // 使用 document.execCommand 插入文本
  document.execCommand('insertText', false, text);

  // 触发 input 事件
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

/**
 * 等待 AI 响应
 * @param {number} timeout
 */
async function handleWaitForResponse(timeout = 60000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    let lastMessageCount = document.querySelectorAll('[data-testid="conversation-turn"]').length;

    const checkInterval = setInterval(() => {
      // 检查超时
      if (Date.now() - startTime > timeout) {
        clearInterval(checkInterval);
        reject(new Error('Response timeout'));
        return;
      }

      // 检查 AI 是否正在输入
      const isTyping = document.querySelector('[data-testid="typing-indicator"]') !== null;

      // 检查消息数量变化
      const currentMessageCount = document.querySelectorAll('[data-testid="conversation-turn"]').length;

      if (!isTyping && currentMessageCount > lastMessageCount) {
        clearInterval(checkInterval);
        resolve({ messageCount: currentMessageCount });
      }
    }, 500);
  });
}

// 启动
initialize();
