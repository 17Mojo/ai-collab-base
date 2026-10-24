/**
 * Gemini Platform Adapter
 * 实现 gemini.google.com 平台的具体适配器
 */

import PlatformAdapter from "./adapter.js";
import DOMObserver from "../utils/dom-observer.js";
import { findElement, findElements, findVisibleElement, extractMessageContent } from "./adapter-utils.js";

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
  //
  // 2026-10-25 真机实测（真实 Chrome，zh-CN / en-US 各测一次，落地页+输入框有内容）：
  // 真实的发送按钮是
  //   <gem-icon-button class="send-button … has-input submit …" aria-disabled="false">
  //     <button class="mdc-icon-button mat-mdc-icon-button …"
  //             aria-label="发送"（zh-CN）| "Send message"（en-US）" disabled=false>
  //   </gem-icon-button>
  // 外层容器是 <div data-test-id="send-button-container" class="… visible …">。
  //
  // 旧选择器（button[aria-label="Send prompt"] / send-button / button[aria-label*="Send"]）
  // 的命中情况**随界面语言变化**——这正是它长期没被发现的原因：
  //   zh-CN：0 命中（aria-label 是「发送」，不含 "Send"）→ L1 探针报 adapter_drift，
  //          即生产 adapter 的发送按钮选择器已与站点漂移；
  //   en-US：1 命中（`button[aria-label*="Send"]` 侥幸匹配到 "Send message"）——
  //          英文界面下缺陷被完全掩盖。
  // 因此优先使用**与语言无关**的 class 选择器，中英文 aria-label 作为补充。
  sendButton: [
    'gem-icon-button.send-button button',
    '.send-button button',
    'button[aria-label="发送"]',
    'button[aria-label="Send message"]',
    // 旧选择器保留，兼容历史 DOM
    'button[aria-label="Send prompt"]',
    'send-button',
    'button[aria-label*="Send"]',
  ],

  // 消息列表
  messageList: ['model-response', '.chat-turn', '[class*="conversation-turn"]'],

  // AI 响应状态
  //
  // 真实站点的加载 spinner 是 div.loading-content-spinner-container
  // （实测：常驻 DOM，空闲态 display:none，故 isTyping 必须做可见性判定）。
  // 宽泛的 [class*="loading"] 会命中 <body>（其 class 含 enable-lm-loading-animation），
  // 已由 findVisibleElement/findElement 统一排除页面根节点。
  typingIndicator: [
    '.loading-content-spinner-container',
    'mat-progress-bar',
    '[class*="loading"]',
  ],
  // 停止按钮的 aria-label 同样随语言变化，zh-CN 为「停止生成」
  stopButton: [
    'button[aria-label="停止生成"]',
    'button[aria-label*="停止"]',
    'button[aria-label="Stop"]',
    'button[aria-label*="Stop"]',
  ],

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
    return findElement(this.selectors.chatInput);
  }

  /**
   * 获取发送按钮
   * @returns {HTMLElement|null}
   */
  getSendButton() {
    return findElement(this.selectors.sendButton);
  }

  /**
   * 获取消息列表
   * @returns {Element[]}
   */
  getMessageList() {
    return findElements(this.selectors.messageList);
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
    // 停止按钮（生成中才出现）——必须做可见性判定：
    // 真实站点空闲态会把这类元素留在 DOM 里，只是 display:none。
    const stopButton = findVisibleElement(this.selectors.stopButton);
    if (stopButton) return true;

    // 检查进度条 / spinner
    return !!findVisibleElement(this.selectors.typingIndicator);
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
