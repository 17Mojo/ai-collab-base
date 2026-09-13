/**
 * Kimi Adapter (Kimi AI)
 * 月之暗面 Kimi AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, injectTextSmart, delay } from "./adapter-utils.js";

/** Kimi 平台选择器配置 */
const SELECTORS = {
  chatInput: ['div.chat-input-editor', 'div[contenteditable="true"]', "textarea"],
  sendButton: [
    'button[type="submit"]',
    'button[aria-label*="发送"]',
    'button[class*="send"]',
  ],
  messageList: [".chat-message", '[class*="message"]'],
  messageContent: [".prose", ".chat-content", '[class*="content"]'],
  typingIndicator: [".loading", '[class*="loading"]', ".generating"],
};

/**
 * Kimi AI 平台适配器
 */
class KimiAdapter extends PlatformAdapter {
  constructor() {
    super("kimi.com");
    this.platformName = "Kimi AI";
    this.company = "Moonshot AI (月之暗面)";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("kimi.com");
  }

  getChatInput() {
    return findElement(this.selectors.chatInput);
  }

  getSendButton() {
    return findElement(this.selectors.sendButton);
  }

  getMessageList() {
    const els = document.querySelectorAll(this.selectors.messageList[0]);
    return els.length > 0
      ? els
      : document.querySelectorAll(this.selectors.messageList[1]);
  }

  async injectText(text) {
    const input = this.getChatInput();
    if (!input) throw new Error("Kimi: Chat input not found");

    injectTextSmart(input, text);
    await delay(100);
  }

  async clickSend() {
    const button = this.getSendButton();
    if (button && !button.disabled) {
      button.click();
      await delay(100);
      return;
    }

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
    return findElement(this.selectors.typingIndicator) !== null;
  }

  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    const initialCount = this.getMessageList().length;

    return new Promise((resolve, reject) => {
      const interval = setInterval(() => {
        if (Date.now() - startTime > timeout) {
          clearInterval(interval);
          reject(new Error("Kimi: Response timeout"));
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
export default KimiAdapter;
