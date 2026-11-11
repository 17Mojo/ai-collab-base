/**
 * ChatGLM Adapter (智谱清言)
 * 智谱 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/** 智谱清言选择器配置 */
const SELECTORS = {
  // 2026-11-11 只读 DOM 探测实证（/tmp/newchat-probe.json，chatglm.cn）：
  // 「新对话」不是一个按钮，而是
  //   div.new-session.flex…el-tooltip__trigger > div.text
  // 挂在 aside.aside-container 下。它不是 button/a/[role=button]，
  // 所以纯标签匹配永远找不到它——Pack 的 fresh_session 因此在 13:40 那轮
  // 直接把 step_8 判失败（拒绝把提示词发进旧会话，是对的行为，但没办成事）。
  newChat: [".new-session"],
  chatInput: ['div[contenteditable="true"]', "textarea", '[role="textbox"]'],
  sendButton: [
    'button[type="submit"]',
    'button[aria-label*="发送"]',
    'button[class*="send"]',
  ],
  // 2026-11-10 发送期 DOM 采样实证（L2-chatglm-auto-2026-11-10.probe1.dom-samples.json）：
  // 旧三个选择器在整个生成过程中恒为 0 ⇒ countGrew 恒 false ⇒ 60s 超时。
  // `.answer-content-wrap` 实测随时间 0 → 1 → 2 → 3 递增，且只对应 AI 回复卡，
  // 因此「最新一条」天然就是最新回复；自身带 content 子串，正好命中下方
  // messageContent 的 [class*="content"] 自身判定（extractMessageContent 先看自身）。
  messageList: [
    ".answer-content-wrap",
    ".chat-message",
    '[class*="message"]',
    '[class*="response"]',
  ],
  messageContent: [".chat-content", ".message-text", '[class*="content"]'],
  // 2026-10-25 真机实测**删除**了 '[class*="loading"]'。
  //
  // 实测（空闲落地页，无会话）：`[class*="loading"]` 命中 2 个元素，
  // 是**会话列表的「正在加载...」占位条**，且**可见**（239×32，文字「正在加载...」）——
  // 于是 isTyping() 在空闲页恒为 true ⇒ waitForResponse 的
  // `!this.isTyping()` 条件**永远不成立** ⇒ 每次发送都必然 60 秒超时。
  //
  // typingIndicator 选择器来源：2026-11-04 零发送静态普查（站点 bundle 字面量级证据）。
  // 停止回答按钮 = 生成中：StopGenerator 组件（c1a5e4f2910a4b555ce0.chunk.js JSX）
  // 只在 isEventSourceaOpen 时渲染 button ga-data="stop"——**必须限定 button 标签**：
  // div.sensitive[ga-data="stop"] 是内容安全敏感态的同名属性，不是生成指示器。
  // 流式光标：85202fed1c5821c734fb.css「.markdown-body .loadingGif」注释明说
  // 「当连续的图片输出且未结束时会显示这个图片」，仅流式注入、稳定后移除。
  // 心跳思考态（「还在思考中，你先忙别的吧～」）渲染 div.loading-text，
  // 但 bare loading-text 类在 16 个 chunk 里复用（知识加载中/认证中/图片上传中…），
  // 不加限定误命中会让空闲页恒 true——加 is-no-data 限定（8461 chunk 的绑定
  // class:["loading-text", isHeartbeat&&"is-no-data"]，仅心跳态带该修饰）。
  // 编辑器场景另有 .stop-generate（sftc-edit 的「停止生成」遮罩按钮）。
  typingIndicator: [
    'button[ga-data="stop"]',
    ".markdown-body .loadingGif",
    ".loading-text.is-no-data",
    ".stop-generate",
  ],
};

/**
 * 智谱清言平台适配器
 */
class ChatGLMAdapter extends PlatformAdapter {
  constructor() {
    super("chatglm.cn");
    this.platformName = "智谱清言";
    this.company = "Zhipu AI (智谱AI)";
    this.selectors = SELECTORS;
  }

  detect() {
    return window.location.hostname.includes("chatglm.cn");
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
    if (!input) throw new Error("ChatGLM: Chat input not found");

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
export default ChatGLMAdapter;
