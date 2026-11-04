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
  // typingIndicator 选择器来源：2026-11-04 零发送静态普查（站点 bundle 字面量级证据）。
  // yb_v2 chunks：136（conv-item）+ 7972（SendButton）+ 3807/6742（hyc-deepthink）+ 7538（markdown）。
  // 最强信号是**无哈希 data 属性**：data-conv-speaker="ai" + data-conv-outputting="true"
  // （40280 段 renderDataConv 的 data-conv-outputting/e.dataAttrString 状态机）；
  // 等首 token 的 ai-placeholder（outputing===2）兜底。
  // 生成中 = 停止按钮：#yuanbao-send-btn[aria-label="停止回答"]（zh-CN）与
  // [class*="SendButton_sendStop"]（类名本地名无哈希、语言无关）双轨。
  // 深度思考骨架屏 .hyc-deepthink-steps__header-icon--anim 仅在 !isEnd && loading 挂载
  // （thinkComplete 后 anim 动画移除，isEnd=true——不会误报完成态）。
  // 流式打字点 .hyc-common-markdown__code__generating-dots（与数据插值同条件显隐）。
  typingIndicator: [
    '[data-conv-speaker="ai"][data-conv-outputting="true"]',
    '[class*="ai-placeholder"]',
    '#yuanbao-send-btn[aria-label="停止回答"]',
    '[class*="SendButton_sendStop"]',
    ".hyc-deepthink-steps__header-icon--anim",
    ".hyc-common-markdown__code__generating-dots",
  ],
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
export default YuanbaoAdapter;
