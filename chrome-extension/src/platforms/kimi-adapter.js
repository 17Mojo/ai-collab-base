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
  // typingIndicator 选择器来源：2026-11-04 零发送静态普查（站点 bundle 字面量级证据）。
  // entry.js 16700/38420 段（Segment 组件）+ c8a0d849f0c85-JL2OvW0_.js + cfd0f68ad57e5-CaZXnu1D.js。
  // 生成中状态行是**服务端状态机下发的 tips 文案流**（happy/「正在生成中…」/「不支持此格式」），
  // 渲染为 segment-generate-tip；类名是 BEM 字面量（BOLahTei.css 有 .segment .segment-generate-tip
  // 的字级/行高样式），无哈希。等待首响应 spinner 挂在用户消息条目上：
  // chat-content-item awaiting-first-response 内嵌 .awaiting-loading（条目 2604 行
  // 「awaiting-first-response 类只在等待期挂」）。PENDING 态渲染 div.segment-pending-loading。
  // 停止输出按钮 = 生成中：send-button-container 加 stop 类（cfd0f68ad57e5 的 JSX
  // class 绑定 {stop: P.value}，P 即 isGenerating），停答后 stop 类摘掉。
  // **排除** core-spiral-loading（role=status 仅在传 ariaLabel 时加）——该组件在
  // 历史列表/文件卡等多处复用，「生成中用法」只是其中一处，误命中会让空闲页恒 true。
  typingIndicator: [
    ".segment .segment-generate-tip",
    ".chat-content-item.awaiting-first-response .awaiting-loading",
    ".segment .segment-pending-loading",
    ".send-button-container.stop",
  ],
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
