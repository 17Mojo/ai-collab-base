/**
 * Gemini Platform Adapter
 * 实现 gemini.google.com 平台的具体适配器
 */

import PlatformAdapter from "./adapter.js";
import DOMObserver from "../utils/dom-observer.js";

/**
 * Gemini 选择器配置
 */
const SELECTORS = {
  // 输入框
  chatInput: 'div[contenteditable="true"][aria-label*="prompt"]',
  chatInputAlt: 'div[contenteditable="true"].ql-editor',
  chatInputAlt2: 'textarea[placeholder*="prompt"]',

  // 发送按钮
  sendButton: 'button[aria-label="Send prompt"]',
  sendButtonAlt: 'send-button',

  // 消息列表
  messageList: 'model-response',
  messageListAlt: '.chat-turn',

  // AI 响应状态
  typingIndicator: 'mat-progress-bar',
  stopButton: 'button[aria-label="Stop"]',

  // 消息内容
  messageContent: '.model-response-text',
  messageContentAlt: 'message-content',
};

/**
 * Gemini 适配器
 */
class GeminiAdapter extends PlatformAdapter {
  constructor() {
    super("gemini.google.com");
    this.observer = new DOMObserver();
    this.selectors = SELECTORS;
  }

  /**
   * 检测当前页面是否为 Gemini
   * @returns {boolean}
   */
  detect() {
    return window.location.hostname.includes("gemini.google.com");
  }

  /**
   * 查找元素（支持多个选择器）
   * @param {string} primary
   * @param {string} alt
   * @param {string} alt2
   * @returns {HTMLElement|null}
   */
  _findElement(primary, alt = null, alt2 = null) {
    let element = document.querySelector(primary);
    if (!element && alt) {
      element = document.querySelector(alt);
    }
    if (!element && alt2) {
      element = document.querySelector(alt2);
    }
    return element;
  }

  /**
   * 获取聊天输入框
   * @returns {HTMLElement|null}
   */
  getChatInput() {
    return this._findElement(
      SELECTORS.chatInput,
      SELECTORS.chatInputAlt,
      SELECTORS.chatInputAlt2
    );
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

    input.focus();

    // Gemini 使用 contenteditable div
    if (input.tagName === "TEXTAREA") {
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      ).set;
      nativeInputValueSetter.call(input, text);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      // contenteditable div
      document.execCommand("selectAll", false, null);
      document.execCommand("delete", false, null);
      document.execCommand("insertText", false, text);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    await new Promise((resolve) => setTimeout(resolve, 150));
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
    // 检查进度条
    const progressBar = this._findElement(SELECTORS.typingIndicator);
    if (progressBar) return true;

    // 检查停止按钮
    const stopButton = this._findElement(SELECTORS.stopButton);
    return !!stopButton;
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
        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          reject(new Error("Response timeout"));
          return;
        }

        const currentMessageCount = this.getMessageList().length;
        const isStillTyping = this.isTyping();

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
        input: 150,
      },
    };
  }
}

export default GeminiAdapter;
