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
  // 🔧 2026-11-11 A/B 第 1 轮真机实测（evidence/L2-deepseek-auto-2026-11-11.ab-no-boundary.json）：
  // A 组在 step_5_boundary 判 Response timeout（723.7s = 4×180s + 3.7s），
  // 但同轮截图里 step_5 的提问气泡**和 AI 完整回答都在页面上** ⇒ 假超时。
  //
  // 只读诊断（evidence/deepseek-message-contract-probe-2026-11-11.json，历史会话页）：
  //   div.ds-message                        = 5（3 条 AI 回答 + 2 条 human 气泡）
  //   .ds-assistant-message-main-content   = 3（**正好每条 AI 回答一个**）
  //   [class*="message"]                   = 8（上面两组混在一起！）
  //
  // `findElements` 按优先级只取**第一个有命中的选择器**的整组元素，所以旧的
  // `[class*="message"]` 会把「消息卡」和「正文容器」混成一组：发送前的基准
  // 与回答落地后的计数不是同一批元素，虚拟列表一滚动就再也不增长，
  // `countGrew` 恒 false ⇒ AI 明明答完却一直等到超时（N24 文心同款假基准）。
  //
  // 只认 AI 正文容器：human 气泡出现时计数不动（不会把提示词当回复取走），
  // 新回答渲染时 +1，且 latestMessage 自身就命中 messageContent 的第一条
  // 选择器，正文干净。宁可落地页 0 命中（响亮地给出正确基准 0），
  // 也不要一个会跳组、会混进 human 气泡的假基准。
  messageList: [".ds-assistant-message-main-content"],
  messageContent: [
    ".ds-assistant-message-main-content",
    ".markdown",
    ".prose",
    '[class*="message-content"]',
    '[class*="content"]',
  ],
  // 🔧 2026-11-12 后续步骤①：B 组 available:false 的直接原因就在这里。
  //
  // ab3 四轮真机回执 L2-deepseek-auto-2026-11-12.ab3-with-boundary.json 的
  // sessionResets[0].reason 明写「adapter 没有声明 newChat 选择器」，
  // 3→3 / strategy:none / durationMs:4 ⇒ prefer 降级照发，那一轮按判据作废。
  // §19.7 的「待修 ②」当时只点了 longcat，F2 因此只补了 longcat，本站漏掉。
  //
  // 只读探针 evidence/new-session-probe-2026-11-11.deepseek-ab-diagnostic.json
  // 早就抓到了真入口：`<span>开启新对话</span>`，但它的形状决定了
  // **写不出稳定的 CSS 选择器**：
  //   - 自身无 class / id / aria / title / role / testid；
  //   - `clickableAncestor: null`（不是 button / a / [role=button]）；
  //   - 六层祖先全是构建期哈希类名（_5a8ac7a / dc1f7bee _4bcc731 /
  //     _7b40dad / b8812f16 a2f3d50e / dc04ec1d / c3ecdb44），下次发版即变。
  // 所以不写 `newChat` 选择器（写了也是猜），改用 adapter 级的精确文案逃生口：
  // 只在 `span` 里找 trim 后全等「开启新对话」的可见元素，且仍排除输入区。
  // 该逃生口**只有声明了它的 adapter 才启用**，不会把公共标签兜底放宽到 span/div，
  // longcat 的历史会话诱饵 div.conv-title「新对话」因此依然碰不到。
  //
  // ⚠️ 点击能否真的清空会话仍由 waitForSessionReset 的消息数下降判定；
  // 点不动就如实 available:false，绝不假装重置。真机未验（冻结站，需授权重跑）。
  newChatText: {
    selector: "span",
    texts: ["开启新对话"],
  },
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
      // 🔧 2026-11-11 实测（RMR-2026-11-11-01）：多轮会话下本站单步响应会突破 60s
      // —— step_2/3/4 各约 10s 成功，step_5 用了 132.7s，step_6 四次 60s 全超时。
      // 取回链路本身**有效**（前 5 步都取到了真正文），卡的是单次等待上限。
      // ⇒ 放到 180s 容纳长响应。这是 per-adapter 上限，不改公共判据。
      timeouts: { response: 180000, typing: 5000, input: 100 },
    };
  }
}

export { SELECTORS };
export default DeepSeekAdapter;
