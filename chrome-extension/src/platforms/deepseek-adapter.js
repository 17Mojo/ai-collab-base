/**
 * DeepSeek Adapter (深度求索)
 * DeepSeek AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/** DeepSeek 平台选择器配置 */
const SELECTORS = {
  chatInput: [
    "textarea",
    'div[contenteditable="true"]',
    '#chat-input',
    'textarea[placeholder*="message"]',
  ],
  sendButton: [
    'button[data-testid="send-button"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="发送"]',
    'button[class*="send"]',
  ],
  messageList: [
    '[data-testid="conversation-turn"]',
    ".chat-message",
    '[class*="message"]',
    ".ds-chat-message",
  ],
  messageContent: [
    ".ds-assistant-message-main-content",
    ".markdown",
    ".prose",
    '[class*="message-content"]',
    '[class*="content"]',
  ],
  typingIndicator: [
    '[class*="loading"]',
    '[class*="generating"]',
    ".typing-indicator",
  ],
  stopButton: [
    'button[aria-label="Stop generating"]',
    'button[aria-label="Stop"]',
  ],
};

/**
 * DeepSeek AI 平台适配器
 */
class DeepSeekAdapter extends PlatformAdapter {
  constructor() {
    super("chat.deepseek.com");
    this.platformName = "DeepSeek";
    this.company = "DeepSeek (深度求索)";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("chat.deepseek.com");
  }

  getChatInput() {
    return findElement(this.selectors.chatInput);
  }

  getSendButton() {
    return findElement(this.selectors.sendButton);
  }

  /**
   * 获取消息列表
   *
   * 统一走 adapter-utils 的 findElements。旧实现在这里回退到「页面上的全部 div」，
   * 实测那会把 div 总数当成消息数（真机 Gemini 上读到 104），并连带让基于计数的
   * 等待逻辑失真——此处返回空集合，与其余 adapter 行为一致。
   * @returns {Element[]}
   */
  getMessageList() {
    return findElements(this.selectors.messageList);
  }

  async injectText(text) {
    const input = this.getChatInput();
    if (!input) throw new Error("DeepSeek: Chat input not found");

    await injectTextSmart(input, text);
    await delay(100);
  }

  async clickSend() {
    const button = this.getSendButton();
    if (button && !button.disabled) {
      button.click();
      await delay(100);
      return;
    }

    // fallback: Enter 键发送
    const input = this.getChatInput();
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

  isTyping() {
    // 检查停止按钮（生成中才可见）
    const stopButton = findVisibleElement(this.selectors.stopButton);
    if (stopButton) return true;

    return findVisibleElement(this.selectors.typingIndicator) !== null;
  }

  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    const initialCount = this.getMessageList().length;

    return new Promise((resolve, reject) => {
      const interval = setInterval(() => {
        if (Date.now() - startTime > timeout) {
          clearInterval(interval);
          reject(new Error("DeepSeek: Response timeout"));
          return;
        }

        const currentCount = this.getMessageList().length;
        if (currentCount > initialCount && !this.isTyping()) {
          clearInterval(interval);
          const latest = this.getLatestMessage();
          resolve({
            messageCount: currentCount,
            content: latest ? this._extractContent(latest) : "",
            duration: Date.now() - startTime,
          });
        }
      }, 500);
    });
  }

  _extractContent(element) {
    if (!element) return "";
    for (const sel of this.selectors.messageContent) {
      const el = element.querySelector(sel);
      if (el) return el.textContent.trim();
    }
    return element.textContent?.trim() || "";
  }

  getConfig() {
    return {
      platformId: this.platformId,
      selectors: this.selectors,
      timeouts: { response: 60000, typing: 5000, input: 100 },
    };
  }
}

export { SELECTORS };
export default DeepSeekAdapter;
