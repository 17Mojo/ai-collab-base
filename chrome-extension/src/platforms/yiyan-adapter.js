/**
 * Yiyan Adapter (文心一言)
 * 百度文心一言 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

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
    // 2026-10-25 真机实测**删除**了 '[class*="chat"]'。
    //
    // 实测（真机落地页，无会话）：`[class*="chat"]` 命中 37 个元素，
    // 逐个看下来**全是应用外壳**，没有一条是消息气泡：
    //   body.cos-chat / _chat-container_ / _chat-container-body_ /
    //   history-chat-* / _chat-aside-header-* / _chat-top-bar-*
    //
    // 为什么这会坏：findElements 是「按优先级取**第一个有命中**的选择器」，
    // 而 '[class*="message"]' 在落地页一个都不命中 ⇒ 直接落到 '[class*="chat"]'
    // ⇒ 真机上消息数恒为 37。waitForResponseGeneric 拿这个数做「发送前后比较」，
    // 于是要么把导航元素当成 AI 回复返回（静默错数据），要么等不到变化而超时。
    //
    // 真实气泡的类名必须在**已登录会话**里确认（未登录时看不到消息气泡）。
    // 在那之前宁可返回 0（失败会响亮地超时），也不要返回一个错数字。
    '[class*="response"]',
    ".chat-item",
  ],
  messageContent: [".prose", '[class*="answer"]', '[class*="content"]'],
  // typingIndicator 选择器来源：2026-11-04 零发送静态普查（站点 bundle 字面量级证据）。
  // main-130a629d.js（入口主包）：深度思考加载行是自定义元素 <thinking-loading>
  // （「正在思考」文本挂其上，标签名无哈希；仅流式生成期挂载，旧版中间停顿态已弃用）；
  // 纯文本答案的「生成中...」加载行是 text-loading（thinking-loading 同族兄弟）。
  // 生成中 = 状态盒出现「停止回答」按钮：answer-generate-state-button[data-module="stop"]
  // （类名与 data-module 均无哈希，module=stop 区分于发送按钮的 send/insert）。
  // aria 兜底：[class*="statusbox"] 容器内的 [role="button"][aria-label="停止回答"]。
  typingIndicator: [
    "thinking-loading",
    '[class*="thinking-loading"]',
    '[class*="text-loading"]',
    '.answer-generate-state-button[data-module="stop"]',
    '[class*="statusbox"] [role="button"][aria-label="停止回答"]',
  ],
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
    if (!input) throw new Error("Yiyan: Chat input not found");

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
