/**
 * Gemini Platform Adapter
 * 实现 gemini.google.com 平台的具体适配器
 */

import PlatformAdapter from "./adapter.js";
import DOMObserver from "../utils/dom-observer.js";
import { findElement, findElements, extractMessageContent } from "./adapter-utils.js";

/**
 * Gemini 选择器配置
 */
const SELECTORS = {
  // 输入框
  chatInput: [
    'div[contenteditable="true"][aria-label*="prompt"]',
    'div[contenteditable="true"][aria-label*="Gemini"]',
    'div[contenteditable="true"].ql-editor',
    '[role="textbox"]',
    'textarea[placeholder*="prompt"]',
  ],

  // 发送按钮
  sendButton: [
    'button[aria-label="Send prompt"]',
    'send-button',
    'button[aria-label*="Send"]',
  ],

  // 消息列表
  messageList: ['model-response', '.chat-turn', '[class*="conversation-turn"]'],

  // AI 响应状态
  typingIndicator: ['mat-progress-bar', '[class*="loading"]'],
  stopButton: ['button[aria-label="Stop"]', 'button[aria-label*="Stop"]'],

  // 消息内容
  messageContent: ['.model-response-text', 'message-content', '.markdown'],
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
   * 获取聊天输入框
   * @returns {HTMLElement|null}
   */
  getChatInput() {
    return findElement(SELECTORS.chatInput);
  }

  /**
   * 获取发送按钮
   * @returns {HTMLElement|null}
   */
  getSendButton() {
    return findElement(SELECTORS.sendButton);
  }

  /**
   * 获取消息列表
   * @returns {NodeList}
   */
  getMessageList() {
    return findElements(SELECTORS.messageList);
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
    const progressBar = findElement(SELECTORS.typingIndicator);
    if (progressBar) return true;

    // 检查停止按钮
    const stopButton = findElement(SELECTORS.stopButton);
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
          const content = extractMessageContent(latestMessage, SELECTORS.messageContent);

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

export { SELECTORS };
export default GeminiAdapter;
