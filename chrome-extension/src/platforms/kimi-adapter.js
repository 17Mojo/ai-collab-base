/**
 * Kimi Adapter (Kimi AI)
 * 月之暗面 Kimi AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

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
  // 2026-10-25 真机实测**删除**了 '[class*="loading"]'。
  //
  // 实测（空闲落地页，无会话）：`[class*="loading"]` 命中 9 个元素，
  // 全部是**侧边栏的历史记录骨架屏**，且**几何尺寸非零**（224×224）——
  // 所以既躲得过 display/visibility/opacity 判定，也躲得过尺寸判定：
  //
  //   div.next-sidebar__history-loading
  //   div.next-sidebar__history-loading-header
  //   span.next-sidebar__history-loading-title
  //
  // 后果：isTyping() 在空闲页恒为 true ⇒ waitForResponse 的
  // `!this.isTyping()` 条件**永远不成立** ⇒ 每次发送都必然 60 秒超时。
  //
  // 保留 '.loading' 与 '.generating'（都是具体类名）承担「正在生成」的判定。
  // **残留风险**：真正的生成指示器是否命中这两个类名，尚未在已登录会话里
  // 验证——若都不命中，isTyping() 会一直为 false，等待可能**提前**返回
  // （回复还在流式输出中）。该项已登记为 L2 真机会话必验项。
  typingIndicator: [".loading", ".generating"],
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
    if (!input) throw new Error("Kimi: Chat input not found");

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
