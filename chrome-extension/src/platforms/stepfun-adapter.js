/**
 * StepFun Adapter (阶跃星辰 AI Studio)
 *
 * 2026-11-18 真人登录后只读 DOM 探测 + 一条短消息验证的结构（证据见
 * evidence/stepfun-message-probe-2026-11-18.png 与 N30 台账）：
 *   - 输入框是 textarea[data-slot="textarea"]；
 *   - 发送按钮是 button[aria-label="发送"]；
 *   - 「新对话」入口是侧栏 button[data-slot="sidebar-menu-button"][data-active="true"]，
 *     文本为「新对话」；输入区旁边的 button[aria-label="新会话"] 是模型/会话下拉，
 *     点了不会开新会话——不要把它写进 newChat。
 *   - 消息区没有语义 class，只有 [data-split-pane="chat"] 下的
 *     div[class="flex flex-col gap-6"]，其直接子节点一条＝一条消息（提问 + 回答）。
 *     实测 2 条消息 → 2 个直接子节点；点侧栏「新对话」后 → 0。
 *
 * 用户指令：千问有防范非人类操作机制，活跃真机白名单改用本站。
 * 本站仍按真人登录态跑，探针不绕验证码 / 滑块。
 */

import PlatformAdapter from "./adapter.js";
import {
  findElement,
  findElements,
  findVisibleElement,
  injectTextSmart,
  delay,
} from "./adapter-utils.js";

const SELECTORS = {
  newChat: ['button[data-slot="sidebar-menu-button"][data-active="true"]'],
  chatInput: ['textarea[data-slot="textarea"]', "textarea", '[role="textbox"]'],
  sendButton: ['button[aria-label="发送"]', 'button[aria-label*="发送"]', 'button[type="submit"]'],
  messageList: [
    '[data-split-pane="chat"] div[class="flex flex-col gap-6"] > div',
  ],
  messageContent: [
    'div[class*="leading-relaxed"]',
    "p.my-6",
    '[class*="markdown"]',
  ],
  // 短问答采样期未观察到稳定的停止按钮；完成判定由 waitForResponseGeneric
  // 的「内容连续稳定」负责，不用未验证的选择器制造假阳性。
  typingIndicator: [],
};

class StepFunAdapter extends PlatformAdapter {
  constructor() {
    super("studio.stepfun.com");
    this.platformName = "阶跃星辰 AI Studio";
    this.company = "StepFun (阶跃星辰)";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("stepfun.com");
  }

  getChatInput() {
    return findElement(this.selectors.chatInput);
  }

  getSendButton() {
    return findElement(this.selectors.sendButton);
  }

  getMessageList() {
    return findElements(this.selectors.messageList);
  }

  isTyping() {
    return findVisibleElement(this.selectors.typingIndicator) !== null;
  }

  async injectText(text) {
    const input = this.getChatInput();
    if (!input) throw new Error("StepFun: Chat input not found");
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
    throw new Error("StepFun: Send button not available");
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
export default StepFunAdapter;
