/**
 * Prompt Pack - Settings Script
 * 设置页面逻辑，使用 chrome.storage.sync API
 */

// 默认设置
const DEFAULT_SETTINGS = {
  platforms: {
    claude: true,
    chatgpt: true,
    gemini: true,
    kimi: true,
    qianwen: true,
    chatglm: true,
    longcat: true,
    yuanbao: true,
    yiyan: true
  },
  execution: {
    timeout: 60,
    retries: 3,
    retryDelay: 1000
  },
  logging: {
    enabled: true,
    verbose: false
  }
};

/**
 * 加载设置
 */
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get('promptPackSettings');
    const settings = result.promptPackSettings || DEFAULT_SETTINGS;

    // 平台设置
    document.getElementById('platform-claude').checked = settings.platforms.claude;
    document.getElementById('platform-chatgpt').checked = settings.platforms.chatgpt;
    document.getElementById('platform-gemini').checked = settings.platforms.gemini;
    document.getElementById('platform-kimi').checked = settings.platforms.kimi ?? true;
    document.getElementById('platform-qianwen').checked = settings.platforms.qianwen ?? true;
    document.getElementById('platform-chatglm').checked = settings.platforms.chatglm ?? true;
    document.getElementById('platform-longcat').checked = settings.platforms.longcat ?? true;
    document.getElementById('platform-yuanbao').checked = settings.platforms.yuanbao ?? true;
    document.getElementById('platform-yiyan').checked = settings.platforms.yiyan ?? true;

    // 执行设置
    document.getElementById('timeout').value = settings.execution.timeout;
    document.getElementById('retries').value = settings.execution.retries;
    document.getElementById('retry-delay').value = settings.execution.retryDelay;

    // 日志设置
    document.getElementById('logging-enabled').checked = settings.logging.enabled;
    document.getElementById('verbose-logging').checked = settings.logging.verbose;

    updateStatus('设置已加载');
  } catch (error) {
    console.error('加载设置失败:', error);
    updateStatus('加载失败，使用默认设置');
  }
}

/**
 * 保存设置
 */
async function saveSettings() {
  const settings = {
    platforms: {
      claude: document.getElementById('platform-claude').checked,
      chatgpt: document.getElementById('platform-chatgpt').checked,
      gemini: document.getElementById('platform-gemini').checked,
      kimi: document.getElementById('platform-kimi').checked,
      qianwen: document.getElementById('platform-qianwen').checked,
      chatglm: document.getElementById('platform-chatglm').checked,
      longcat: document.getElementById('platform-longcat').checked,
      yuanbao: document.getElementById('platform-yuanbao').checked,
      yiyan: document.getElementById('platform-yiyan').checked
    },
    execution: {
      timeout: parseInt(document.getElementById('timeout').value) || 60,
      retries: parseInt(document.getElementById('retries').value) || 3,
      retryDelay: parseInt(document.getElementById('retry-delay').value) || 1000
    },
    logging: {
      enabled: document.getElementById('logging-enabled').checked,
      verbose: document.getElementById('verbose-logging').checked
    }
  };

  try {
    await chrome.storage.sync.set({ promptPackSettings: settings });
    updateStatus('✅ 设置已保存');

    // 通知 Service Worker 设置已更新
    chrome.runtime.sendMessage({
      type: 'SETTINGS_UPDATED',
      settings: settings
    }).catch(() => {}); // 忽略连接错误

  } catch (error) {
    console.error('保存设置失败:', error);
    updateStatus('❌ 保存失败');
  }
}

/**
 * 更新状态显示
 * @param {string} message
 */
function updateStatus(message) {
  const statusEl = document.getElementById('status');
  statusEl.textContent = message;
  setTimeout(() => {
    statusEl.textContent = '';
  }, 3000);
}

/**
 * 初始化
 */
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();

  // 保存按钮
  document.getElementById('save-btn').addEventListener('click', saveSettings);

  // 打开 Pack 编辑器按钮
  const packEditorBtn = document.getElementById('openPackEditorBtn');
  if (packEditorBtn) {
    packEditorBtn.addEventListener('click', () => {
      chrome.tabs.create({ url: chrome.runtime.getURL('public/pack-editor.html') });
    });
  }

  // 打开风格编辑器按钮
  const styleEditorBtn = document.getElementById('openStyleEditorBtn');
  if (styleEditorBtn) {
    styleEditorBtn.addEventListener('click', () => {
      chrome.tabs.create({ url: chrome.runtime.getURL('public/style-editor.html') });
    });
  }

  // 实时保存（可选）
  const inputs = document.querySelectorAll('input');
  inputs.forEach(input => {
    input.addEventListener('change', () => {
      // 可选：自动保存
      // saveSettings();
    });
  });
});