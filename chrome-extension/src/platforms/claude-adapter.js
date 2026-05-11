/**
 * Claude.ai Platform Adapter
 * 实现 Claude.ai 平台的具体适配器
 */

import PlatformAdapter from "./adapter.js";
import DOMObserver from "../utils/dom-observer.js";

/**
 * Claude.ai 选择器配置
 */
const SELECTORS = {
  // 输入框
  chatInput: 'div[contenteditable="true"]',
  chatInputAlt: 'div.ProseMirror[contenteditable="true"]',

  // 发送按钮
  sendButton: 'button[aria-label="Send"]',
  sendButtonAlt: 'button[data-testid="send-button"]',

  // 消息列表
  messageList: '[data-testid="conversation-turn"]',
  messageListAlt: ".conversation-turn",

  // AI 响应状态
  typingIndicator: '[data-testid="typing-indicator"]',
  stopButton: 'button[aria-label="Stop generating"]',

  // 消息内容
  messageContent: ".prose",
  messageContentAlt: '[data-testid="message-content"]',
};

/**
 * Claude.ai 适配器
 */
class ClaudeAdapter extends PlatformAdapter {
  constructor() {
    super("claude.ai");
    this.observer = new DOMObserver();
    this.selectors = SELECTORS;
  }

  /**
   * 检测当前页面是否为 Claude.ai
   * @returns {boolean}
   */
  detect() {
    return window.location.hostname.includes("claude.ai");
  }

  /**
   * 查找元素（支持多个选择器）
   * @param {string} primary - 主选择器
   * @param {string} alt - 备用选择器
   * @returns {HTMLElement|null}
   */
  _findElement(primary, alt = null) {
    let element = document.querySelector(primary);
    if (!element && alt) {
      element = document.querySelector(alt);
    }
    return element;
  }

  /**
   * 获取聊天输入框
   * @returns {HTMLElement|null}
   */
  getChatInput() {
    return this._findElement(SELECTORS.chatInput, SELECTORS.chatInputAlt);
  }

  /**
   * 获取发送按钮
   * @returns {HTMLElement|null}
   */
  getSendButton() {
    return this._findElement(SELECTORS.sendButton, SELECTORS.sendButtonAlt);
  }

  /**
   * 获取消息列表
   * @returns {NodeList}
   */
  getMessageList() {
    let messages = document.querySelectorAll(SELECTORS.messageList);
    if (messages.length === 0) {
      messages = document.querySelectorAll(SELECTORS.messageListAlt);
    }
    return messages;
  }

  /**
   * 注入文本到输入框
   * @param {string} text
   * @returns {Promise<void>}
   */
  async injectText(text) {
    const input = this.getChatInput();
    if (!input) {
      throw new Error("Chat input not found");
    }

    // 聚焦输入框
    input.focus();

    // 清空现有内容
    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);

    // 插入新文本
    document.execCommand("insertText", false, text);

    // 触发事件
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "a", bubbles: true }),
    );

    // 等待一小段时间确保文本已插入
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  /**
   * 点击发送按钮
   * @returns {Promise<void>}
   */
  async clickSend() {
    const button = this.getSendButton();
    if (!button) {
      throw new Error("Send button not found");
    }

    button.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  /**
   * 检查 AI 是否正在输入
   * @returns {boolean}
   */
  isTyping() {
    // 检查是否有停止按钮（表示正在生成）
    const stopButton = this._findElement(SELECTORS.stopButton);
    if (stopButton) return true;

    // 检查是否有输入指示器
    const typingIndicator = this._findElement(SELECTORS.typingIndicator);
    return !!typingIndicator;
  }

  /**
   * 等待 AI 响应完成
   * @param {number} timeout
   * @returns {Promise<Object>}
   */
  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    const initialMessageCount = this.getMessageList().length;

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        // 检查超时
        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          reject(new Error("Response timeout"));
          return;
        }

        const currentMessageCount = this.getMessageList().length;
        const isStillTyping = this.isTyping();

        // 响应完成条件：消息数量增加且不再输入
        if (currentMessageCount > initialMessageCount && !isStillTyping) {
          clearInterval(checkInterval);

          const latestMessage = this.getLatestMessage();
          const content = this._extractMessageContent(latestMessage);

          resolve({
            messageCount: currentMessageCount,
            content,
            duration: Date.now() - startTime,
          });
        }
      }, 500);
    });
  }

  /**
   * 提取消息内容
   * @param {HTMLElement} messageElement
   * @returns {string}
   */
  _extractMessageContent(messageElement) {
    if (!messageElement) return "";

    const contentEl =
      messageElement.querySelector(SELECTORS.messageContent) ||
      messageElement.querySelector(SELECTORS.messageContentAlt);

    return contentEl ? contentEl.textContent.trim() : "";
  }

  /**
   * 获取平台配置
   * @returns {Object}
   */
  getConfig() {
    return {
      platformId: this.platformId,
      selectors: SELECTORS,
      timeouts: {
        response: 60000,
        typing: 5000,
        input: 100,
      },
    };
  }
}

export default ClaudeAdapter;
