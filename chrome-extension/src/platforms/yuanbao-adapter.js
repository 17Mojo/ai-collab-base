/**
 * Yuanbao Adapter (腾讯元宝)
 * 腾讯元宝 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/** 腾讯元宝选择器配置 */
const SELECTORS = {
  chatInput: [
    "div.ql-editor",
    'div[contenteditable="true"]',
    "textarea",
    '[role="textbox"]',
  ],
  sendButton: [
    'button[type="submit"]',
    'button[aria-label*="发送"]',
    'button[class*="send"]',
    "button[data-send]",
  ],
  messageList: [
    '[class*="message"]',
    // 2026-10-25 真机实测**删除**了 '[class*="chat"]'。
    //
    // 实测（真机落地页，无会话）：`[class*="chat"]` 命中 8 个元素，
    // 逐个看下来**全是「新建对话」按钮那一片**，没有一条是消息气泡：
    //   div.yb-new-chat-entry / div.yb-new-chat-entry__item / svg
    //
    // 为什么这会坏：findElements 是「按优先级取**第一个有命中**的选择器」，
    // 而 '[class*="message"]' 在落地页一个都不命中 ⇒ 直接落到 '[class*="chat"]'
    // ⇒ 真机上消息数恒为 8。waitForResponseGeneric 拿这个数做「发送前后比较」，
    // 于是要么把「新建对话」按钮当成 AI 回复返回（静默错数据），要么等不到变化而超时。
    //
    // 真实气泡的类名必须在**已登录会话**里确认（未登录时看不到消息气泡）。
    // 在那之前宁可返回 0（失败会响亮地超时），也不要返回一个错数字。
    '[class*="response"]',
    ".message-item",
  ],
  messageContent: [".prose", '[class*="answer"]', '[class*="content"]'],
  typingIndicator: ['[class*="loading"]', '[class*="generating"]', ".spinner"],
};

/**
 * 腾讯元宝平台适配器
 */
class YuanbaoAdapter extends PlatformAdapter {
  constructor() {
    super("yuanbao.tencent.com");
    this.platformName = "腾讯元宝";
    this.company = "Tencent (腾讯)";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("yuanbao.tencent.com");
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
   * 统一走 adapter-utils 的 findElements：messageList 里的**全部**选择器按优先级
   * 依次尝试（不只是前两个），一个都不命中时返回空集合。
   * @returns {Element[]}
   */
  getMessageList() {
    return findElements(this.selectors.messageList);
  }

  async injectText(text) {
    const input = this.getChatInput();
    if (!input) throw new Error("Yuanbao: Chat input not found");

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
    // 打字指示器必须做可见性判定：真实站点空闲态会把这类元素留在 DOM 里
    // （display:none），按「存在即命中」判定会让 isTyping() 恒为 true。
    return findVisibleElement(this.selectors.typingIndicator) !== null;
  }

  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    const initialCount = this.getMessageList().length;

    return new Promise((resolve, reject) => {
      const interval = setInterval(() => {
        if (Date.now() - startTime > timeout) {
          clearInterval(interval);
          reject(new Error("Yuanbao: Response timeout"));
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
export default YuanbaoAdapter;
