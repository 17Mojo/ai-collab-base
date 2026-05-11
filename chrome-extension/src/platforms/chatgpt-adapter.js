/**
 * ChatGPT Platform Adapter
 * 实现 chat.openai.com 平台的具体适配器
 */

import PlatformAdapter from "./adapter.js";
import DOMObserver from "../utils/dom-observer.js";

/**
 * ChatGPT 选择器配置
 */
const SELECTORS = {
  // 输入框
  chatInput: '#prompt-textarea',
  chatInputAlt: 'textarea[placeholder*="Message"]',
  chatInputAlt2: 'div[contenteditable="true"]',

  // 发送按钮
  sendButton: 'button[data-testid="send-button"]',
  sendButtonAlt: 'button[aria-label="Send prompt"]',

  // 消息列表
  messageList: '[data-testid="conversation-turn"]',
  messageListAlt: ".text-base",

  // AI 响应状态
  typingIndicator: '[data-testid="typing-indicator"]',
  stopButton: 'button[aria-label="Stop generating"]',

  // 消息内容
  messageContent: ".markdown",
  messageContentAlt: "[data-message-author-role]",
};

/**
 * ChatGPT 适配器
 */
class ChatGPTAdapter extends PlatformAdapter {
  constructor() {
    super("chat.openai.com");
    this.observer = new DOMObserver();
    this.selectors = SELECTORS;
  }

  /**
   * 检测当前页面是否为 ChatGPT
   * @returns {boolean}
   */
  detect() {
    return (
      window.location.hostname.includes("chat.openai.com") ||
      window.location.hostname.includes("chatgpt.com")
    );
  }

  /**
   * 查找元素（支持多个选择器）
   * @param {string} primary - 主选择器
   * @param {string} alt - 备用选择器
   * @param {string} alt2 - 第二备用选择器
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

    // 聚焦输入框
    input.focus();

    // ChatGPT 使用 textarea，设置 value 并触发事件
    if (input.tagName === "TEXTAREA") {
      // 使用 nativeInputValueSetter 绕过 React 受控组件
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

    // 等待 React 状态更新
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
    // 检查停止按钮
    const stopButton = this._findElement(SELECTORS.stopButton);
    if (stopButton) return true;

    // 检查输入指示器
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

export default ChatGPTAdapter;
