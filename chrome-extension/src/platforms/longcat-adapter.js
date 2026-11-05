/**
 * LongCat Adapter
 * LongCat AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/** LongCat 平台选择器配置 */
const SELECTORS = {
  chatInput: ['div[role="textbox"]', 'div[contenteditable="true"]'],
  sendButton: ['button[type="submit"]', 'img[cursor="pointer"]'],
  messageList: [".message", '[class*="response"]', '[class*="chat-item"]'],
  messageContent: [".prose", ".response-content", '[class*="content"]'],
  // typingIndicator 选择器来源：2026-11-04 零发送静态普查（站点 bundle 字面量级证据）。
  // s3.meituan.net/.../js/ chunk 8575268a + 27443337 + f8ccdd86。
  // 聊天流式主链：等待首 token 打字点 v-loading-dot（chatStatus===LOADING 时渲染，
  // LoadingDot 组件类名无哈希）；生成中 = 停止按钮 stop-generate（StopGenerator.vue
  // 渲染 div.stop-generate，仅 LOADING||OUTPUT 挂载，答完即卸——停止按钮存在 ⇔ 正在生成）。
  // 深研/文件任务：PROCESSING 态点点点 loading-dot-box（点击→中断）；
  // 图片/视频生成中 loading-text（「正在生成图片...」）。
  // **排除** reason-title（「正在思考中...」标题）：DeepthinkThinkingStatus.vue 的标题
  // 元素思考完成后文案变「已完成思考」但**元素保留**（qianwen data-status=complete
  // 同类边界——完成后还在 DOM 里的不许算生成中，否则 isTyping 恒 true ⇒ 每次必超时）。
  // 也排除 generating:"正在生成中，请稍后再试"（conversation.js:1369 冲突拦截提示，非状态行）。
  typingIndicator: [
    ".assistant-main .v-loading-dot",
    ".v-loading-dot",
    '[class*="stop-generate"]',
    '[class*="loading-dot-box"]',
    '[class*="loading-text"]',
  ],
};

/**
 * LongCat AI 平台适配器
 */
class LongCatAdapter extends PlatformAdapter {
  constructor() {
    super("longcat.chat");
    this.platformName = "LongCat AI";
    this.company = "LongCat";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("longcat.chat");
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
    if (!input) throw new Error("LongCat: Chat input not found");

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
export default LongCatAdapter;
