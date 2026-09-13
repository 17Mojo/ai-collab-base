/**
 * Yiyan Adapter (文心一言)
 * 百度文心一言 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, injectTextSmart, delay } from "./adapter-utils.js";

/** 文心一言选择器配置 */
const SELECTORS = {
  chatInput: [
    "textarea.ci-textarea",
    "textarea",
    'div[contenteditable="true"]',
    '[role="textbox"]',
    'input[type="text"]',
  ],
  sendButton: [
    'button[type="submit"]',
    'button[aria-label*="发送"]',
    'button[class*="send"]',
    "button[data-send]",
  ],
  messageList: [
    '[class*="message"]',
    '[class*="chat"]',
    '[class*="response"]',
    ".chat-item",
  ],
  messageContent: [".prose", '[class*="answer"]', '[class*="content"]'],
  typingIndicator: ['[class*="loading"]', '[class*="generating"]', ".spinner"],
};

/**
 * 文心一言平台适配器
 */
class YiyanAdapter extends PlatformAdapter {
  constructor() {
    super("yiyan.baidu.com");
    this.platformName = "文心一言";
    this.company = "Baidu (百度)";
    this.selectors = SELECTORS;
  }

  detect() {
    const hostname = window.location.hostname;
    return hostname.includes("yiyan.baidu.com") || hostname.includes("wenxin.baidu.com");
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
    if (!input) throw new Error("Yiyan: Chat input not found");

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
          reject(new Error("Yiyan: Response timeout"));
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
export default YiyanAdapter;
