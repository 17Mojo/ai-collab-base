/**
 * Prompt Pack - Content Script (ESM Source)
 * 注入到 AI 聊天页面的脚本 — 动态适配所有平台
 *
 * 构建说明：
 * 此文件使用 ESM import 从适配器文件导入选择器配置。
 * Vite 构建时会将此文件打包为 IIFE 格式，解决 Manifest V3
 * content_scripts 不支持 type:module 的问题。
 * 选择器配置与适配器文件自动同步，无需手动维护两份配置。
 */

// ============================================================================
// 从适配器文件导入选择器配置（构建时自动同步）
// ============================================================================

import { SELECTORS as CLAUDE_SELECTORS } from "../platforms/claude-adapter.js";
import { SELECTORS as CHATGPT_SELECTORS } from "../platforms/chatgpt-adapter.js";
import { SELECTORS as GEMINI_SELECTORS } from "../platforms/gemini-adapter.js";
import { SELECTORS as QIANWEN_SELECTORS } from "../platforms/qianwen-adapter.js";
import { SELECTORS as CHATGLM_SELECTORS } from "../platforms/chatglm-adapter.js";
import { SELECTORS as KIMI_SELECTORS } from "../platforms/kimi-adapter.js";
import { SELECTORS as YIYAN_SELECTORS } from "../platforms/yiyan-adapter.js";
import { SELECTORS as YUANBAO_SELECTORS } from "../platforms/yuanbao-adapter.js";
import { SELECTORS as LONGCAT_SELECTORS } from "../platforms/longcat-adapter.js";
import { SELECTORS as DEEPSEEK_SELECTORS } from "../platforms/deepseek-adapter.js";

// 导入 DOM 操作工具函数
import {
  findElement,
  findElements,
  findVisibleElement,
  injectTextSmart,
  extractMessageContent,
} from "../platforms/adapter-utils.js";

// ============================================================================
// 平台选择器配置（从适配器自动导入，域名别名手动映射）
// ============================================================================

/**
 * 平台 ID → 选择器配置的映射表
 *
 * 选择器配置直接从各适配器文件的 SELECTORS 常量导入，
 * 确保与适配器实现自动同步。
 *
 * 域名别名（如 kimi.moonshot.cn → kimi.com）需要在此手动映射，
 * 但选择器本身不需要重复维护。
 */
const PLATFORM_CONFIGS = {
  "claude.ai": CLAUDE_SELECTORS,
  "chat.openai.com": CHATGPT_SELECTORS,
  "chatgpt.com": CHATGPT_SELECTORS,
  "gemini.google.com": GEMINI_SELECTORS,
  "qianwen.com": QIANWEN_SELECTORS,
  "qianwen.aliyun.com": QIANWEN_SELECTORS,
  "tongyi.aliyun.com": QIANWEN_SELECTORS,
  "chatglm.cn": CHATGLM_SELECTORS,
  "kimi.com": KIMI_SELECTORS,
  "kimi.moonshot.cn": KIMI_SELECTORS,
  "yiyan.baidu.com": YIYAN_SELECTORS,
  "wenxin.baidu.com": YIYAN_SELECTORS,
  "yuanbao.tencent.com": YUANBAO_SELECTORS,
  "longcat.chat": LONGCAT_SELECTORS,
  "longcat.ai": LONGCAT_SELECTORS,
  "chat.deepseek.com": DEEPSEEK_SELECTORS,
};

// ============================================================================
// Content Script 主逻辑
// ============================================================================

// 当前平台配置
let currentConfig = null;
let currentPlatformId = null;

/**
 * 初始化 Content Script
 */
async function initialize() {
  console.log("[Prompt Pack] Content Script initialized");

  // 请求获取适配器 ID（Service Worker 返回 { adapterId }）
  const response = await chrome.runtime.sendMessage({ type: "GET_ADAPTER" });

  if (response?.adapterId && PLATFORM_CONFIGS[response.adapterId]) {
    currentPlatformId = response.adapterId;
    currentConfig = PLATFORM_CONFIGS[currentPlatformId];
    console.log(`[Prompt Pack] Using adapter: ${currentPlatformId}`);
    setupEventListeners();
  } else {
    console.log("[Prompt Pack] No adapter available for this page");
  }
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case "INJECT_TEXT":
        handleInjectText(message.text)
          .then(() => sendResponse({ success: true }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;

      case "CLICK_SEND":
        handleClickSend()
          .then(() => sendResponse({ success: true }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;

      case "GET_PAGE_STATE":
        const state = getPageState();
        sendResponse(state);
        break;

      case "WAIT_FOR_RESPONSE":
        handleWaitForResponse(message.timeout)
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;

      // Pack 执行链路的最后一环：后台 pack-executor 的 AI 步骤发的是
      // SEND_TO_AI。此前**没有任何分支处理它** ⇒ chrome.runtime.sendMessage
      // 拿不到响应 ⇒ 那个 AI 步骤拿到一个空值，却仍然被当成「成功」，
      // 流程照往下走，最后产物是空的——用户看到的是「点了没反应」。
      //
      // 这条分支是 Pack 能不能真正跑通的关键，不是可选的增强。
      case "SEND_TO_AI":
        handleSendToAI(message.prompt, message.config?.timeout)
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;
    }
  });
}

/**
 * 获取页面状态
 */
function getPageState() {
  if (!currentConfig) {
    return {
      url: window.location.href,
      platformId: null,
      hasInput: false,
      messageCount: 0,
    };
  }

  const input = findElement(currentConfig.chatInput);
  const messages = findElements(currentConfig.messageList);

  return {
    url: window.location.href,
    platformId: currentPlatformId,
    hasInput: !!input,
    messageCount: messages.length,
  };
}

/**
 * 处理文本注入
 */
async function handleInjectText(text) {
  if (!currentConfig) throw new Error("No adapter available");

  const input = findElement(currentConfig.chatInput);
  if (!input) throw new Error("Chat input not found");

  await injectTextSmart(input, text);
  await new Promise((resolve) => setTimeout(resolve, 150));
}

/**
 * 处理点击发送
 */
async function handleClickSend() {
  if (!currentConfig) throw new Error("No adapter available");

  const button = findElement(currentConfig.sendButton);
  if (button && !button.disabled) {
    button.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    return;
  }

  // fallback: Enter 键发送
  const input = findElement(currentConfig.chatInput);
  if (input) {
    input.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        bubbles: true,
      }),
    );
  }
}

/**
 * 执行一次「向 AI 发消息并等回复」
 *
 * 后台 pack-executor 的 AI 步骤发的是 SEND_TO_AI（见 pack-executor.js 的
 * _executeAIStep）。这条链路此前是**断的**：内容脚本没有对应分支，
 * sendMessage 拿不到响应，AI 步骤拿到 undefined 还被当成成功，
 * 流程继续往下走 ⇒ Pack 「执行成功」但产物是空的。
 *
 * 这里把三件事串起来：注入文本 → 点发送 → 等回复。
 *
 * **三件事的验证状态不一样，不要一概而论**（见 docs/REAL_MACHINE_REGRESSION.md）：
 *   - 等回复：真机验证过；
 *   - 注入文本：**此前没有**被真机验证过。2026-10-26 W-D1 彩排实测发现，
 *     千问（Slate 编辑器）上注入只改了 DOM、**没进框架的模型** ⇒
 *     发送按钮保持 disabled ⇒ 点击等于没点 ⇒ 必然超时。
 *     现在由 slate-editor.js 的模型感知注入修掉，注入失败会**抛错**
 *     而不是留一个假成功。
 *
 * @param {string} prompt - 要发给 AI 的提示词
 * @param {number} [timeout=60000] - 等回复的超时（毫秒）
 * @returns {Promise<{messageCount: number, content: string, duration: number}>}
 */
async function handleSendToAI(prompt, timeout = 60000) {
  if (!currentConfig) throw new Error("No adapter available");
  if (!prompt || !String(prompt).trim()) {
    throw new Error("SEND_TO_AI requires a non-empty prompt");
  }

  await handleInjectText(prompt);
  await handleClickSend();
  return await handleWaitForResponse(timeout);
}

/**
 * 检查 AI 是否正在输入
 */
function isTyping() {
  if (!currentConfig) return false;

  // 检查停止按钮
  // 停止按钮与打字指示器都必须做**可见性**判定：真实站点空闲态会把这类元素
  // 留在 DOM 里（display:none）。按「存在即命中」判定会让 isTyping() 恒为 true，
  // 于是 handleWaitForResponse 永远等不到「不再打字」，每次执行都超时。
  if (currentConfig.stopButton) {
    const stopButton = findVisibleElement(currentConfig.stopButton);
    if (stopButton) return true;
  }

  // 检查输入指示器
  if (currentConfig.typingIndicator) {
    const indicator = findVisibleElement(currentConfig.typingIndicator);
    if (indicator) return true;
  }

  return false;
}

/**
 * 等待 AI 响应完成
 */
async function handleWaitForResponse(timeout = 60000) {
  if (!currentConfig) throw new Error("No adapter available");

  const startTime = Date.now();
  const initialCount = findElements(currentConfig.messageList).length;

  return new Promise((resolve, reject) => {
    const interval = setInterval(() => {
      if (Date.now() - startTime > timeout) {
        clearInterval(interval);
        reject(new Error("Response timeout"));
        return;
      }

      const currentCount = findElements(currentConfig.messageList).length;
      if (currentCount > initialCount && !isTyping()) {
        clearInterval(interval);

        const messages = findElements(currentConfig.messageList);
        const latestMessage = messages[messages.length - 1];
        const content = extractMessageContent(
          latestMessage,
          currentConfig.messageContent,
        );

        resolve({
          messageCount: currentCount,
          content,
          duration: Date.now() - startTime,
        });
      }
    }, 500);
  });
}

// 启动
initialize();
