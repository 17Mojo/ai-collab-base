/**
 * Qianwen Adapter (千问)
 * 阿里云千问 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/** 千问平台选择器配置 */
const SELECTORS = {
  chatInput: ['div[contenteditable="true"]', "textarea"],
  sendButton: [
    'button[aria-label*="发送"]',
    'button[title*="发送"]',
    'button[class*="send"]',
  ],
  messageList: [
    '[class*="message"]',
    '[class*="chat-item"]',
    ".response-content",
  ],
  messageContent: [
    ".prose",
    '[class*="message-content"]',
    'div[class*="content"]',
  ],
  typingIndicator: [
    '[class*="loading"]',
    '[class*="generating"]',
    ".typing-indicator",
  ],
};

/**
 * 千问平台适配器
 */
class QianwenAdapter extends PlatformAdapter {
  constructor() {
    super("qianwen.com");
    this.platformName = "千问";
    this.company = "Alibaba Cloud (阿里云)";
    this.selectors = SELECTORS;
  }

  /**
   * 检测当前页面是否为千问
   */
  detect() {
    const hostname = window.location.hostname;
    return (
      hostname.includes("qianwen.com") || hostname.includes("tongyi.aliyun.com")
    );
  }

  /**
   * 获取聊天输入框
   */
  getChatInput() {
    return findElement(this.selectors.chatInput);
  }

  /**
   * 获取发送按钮
   */
  getSendButton() {
    return findElement(this.selectors.sendButton);
  }

  /**
   * 获取消息列表
   */
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

  /**
   * 注入文本到输入框
   */
  async injectText(text) {
    const input = this.getChatInput();
    if (!input) throw new Error("Qianwen: Chat input not found");

    injectTextSmart(input, text);
    // 千问需要额外触发 React 事件
    await delay(100);
  }

  /**
   * 点击发送按钮
   */
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

  /**
   * 检查 AI 是否正在输入
   */
  isTyping() {
    // 打字指示器必须做可见性判定：真实站点空闲态会把这类元素留在 DOM 里
    // （display:none），按「存在即命中」判定会让 isTyping() 恒为 true。
    return findVisibleElement(this.selectors.typingIndicator) !== null;
  }

  /**
   * 等待 AI 响应完成
   */
  async waitForResponse(timeout = 60000) {
    const startTime = Date.now();
    const initialCount = this.getMessageList().length;

    return new Promise((resolve, reject) => {
      const interval = setInterval(() => {
        if (Date.now() - startTime > timeout) {
          clearInterval(interval);
          reject(new Error("Qianwen: Response timeout"));
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

  /**
   * 提取消息内容
   */
  _extractContent(element) {
    if (!element) return "";
    for (const sel of this.selectors.messageContent) {
      const el = element.querySelector(sel);
      if (el) return el.textContent.trim();
    }
    return element.textContent?.trim() || "";
  }

  /**
   * 获取平台配置
   */
  getConfig() {
    return {
      platformId: this.platformId,
      selectors: this.selectors,
      timeouts: { response: 60000, typing: 5000, input: 100 },
    };
  }
}

export { SELECTORS };
export default QianwenAdapter;
