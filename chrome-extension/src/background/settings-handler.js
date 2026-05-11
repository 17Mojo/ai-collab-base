/**
 * Settings Handler
 * Service Worker 中的设置处理模块
 */

// 当前设置缓存
let currentSettings = null;

/**
 * 默认设置
 */
const DEFAULT_SETTINGS = {
  platforms: {
    claude: true,
    chatgpt: true,
    gemini: true
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
 * 初始化设置
 */
async function initializeSettings() {
  try {
    const result = await chrome.storage.sync.get('promptPackSettings');
    currentSettings = result.promptPackSettings || DEFAULT_SETTINGS;
    console.log('[Prompt Pack] Settings initialized:', currentSettings);
  } catch (error) {
    console.error('[Prompt Pack] Settings init failed:', error);
    currentSettings = DEFAULT_SETTINGS;
  }
}

/**
 * 获取当前设置
 * @returns {Object}
 */
function getSettings() {
  return currentSettings || DEFAULT_SETTINGS;
}

/**
 * 更新设置
 * @param {Object} newSettings
 */
async function updateSettings(newSettings) {
  currentSettings = newSettings;
  console.log('[Prompt Pack] Settings updated:', currentSettings);

  // 应用到 PackExecutor
  if (globalThis.packExecutor) {
    globalThis.packExecutor.options.maxRetries = currentSettings.execution.retries;
    globalThis.packExecutor.options.retryDelay = currentSettings.execution.retryDelay;
    globalThis.packExecutor.options.timeout = currentSettings.execution.timeout * 1000;
  }
}

/**
 * 检查平台是否启用
 * @param {string} platformId
 * @returns {boolean}
 */
function isPlatformEnabled(platformId) {
  const platformKey = platformId.replace('.', '').replace('com', '').replace('google', '');
  return currentSettings?.platforms?.[platformKey] ?? true;
}

/**
 * 处理设置更新消息
 * @param {Object} message
 */
function handleSettingsMessage(message) {
  if (message.type === 'SETTINGS_UPDATED') {
    updateSettings(message.settings);
  } else if (message.type === 'GET_SETTINGS') {
    return getSettings();
  }
}

// 导出
globalThis.settingsHandler = {
  initialize: initializeSettings,
  get: getSettings,
  update: updateSettings,
  isPlatformEnabled: isPlatformEnabled,
  handleMessage: handleSettingsMessage
};