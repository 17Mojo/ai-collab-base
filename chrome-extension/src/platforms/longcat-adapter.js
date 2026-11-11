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
  // 🔧 2026-11-11 真机实测（evidence/L2-longcat-selector-count-2026-11-11.json）：
  // 旧三件套 `.message` / `[class*="response"]` / `[class*="chat-item"]` 在已登录
  // 会话页分别 **0 / 0 / 0** 命中 ⇒ getMessageList() 返回空 ⇒ `countGrew` 恒 false
  // ⇒ 每一步都判 Response timeout（fix2 实测 723.9s = 4×180s + 3.9s）。
  // 真实形状：`.v-message-list` 是**唯一**容器（1 个，14 个子元素），
  // 每条消息是 `.v-chat-messge-view`（类名里的 messge 是站点自己的拼写错误，别改），
  // AI 侧再包一层 `.v-chat-assistant-message` > `.assistant-message`。
  //
  // 只收 AI 条目，不收 `.v-chat-messge-view`（它会连 human 气泡一起数）：
  // 混进来以后「最新一条」有可能是用户自己的 prompt ⇒ countGrew 一成立就把
  // 提示词当成回复取走，属静默错数据（yuanbao / kimi 轮已踩过同款）。
  messageList: [".assistant-message", ".v-chat-assistant-message"],
  // 正文只认 markdown 容器：`.assistant-message` 的 textContent 比正文**多 10 个字**，
  // 多出来的正是「已搜到 14 个网页」这条联网搜索状态行（真机逐条 dump 实测）。
  // 整卡回退会把状态行带进产物，且长度足以顶过 50 字闸门。
  messageContent: [".md-show-container", ".mt-markdown-body", ".markdown"],
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
  //
  // 🔧 2026-11-11 警示：正文容器的 `.mt-markdown-body` **永久带 `result-streaming` 类**，
  // 即使回复早已生成完毕（真机实测 5/5 条完成态仍带）。所以 `result-streaming`
  // 绝对不能进这张表——加进去 isTyping() 就恒 true，与上面 reason-title 同一个坑。
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
      // 先看元素自身再找后代（同 adapter-utils 契约：markdown 容器可能与消息卡同元素）
      const el = element.matches?.(sel) ? element : element.querySelector(sel);
      if (el) return el.textContent.trim();
    }
    // 契约收紧（与 adapter-utils.extractMessageContent 对齐）：给了内容选择器却一个都没命中时
    // **不回退整卡 textContent**。本站整卡里带「已搜到 14 个网页」状态行（比正文多 10 字），
    // 回退等于把状态行当正文交出去，长度还够顶过 50 字闸门 ⇒ 静默错数据。
    // 返回空串让等待继续，等真正的 markdown 容器渲染出来再取。
    return "";
  }

  getConfig() {
    return {
      platformId: this.platformId,
      selectors: this.selectors,
      // 🔧 2026-11-11 结论修正：180s 这一档**不是**为本站「联网搜索慢」定的。
      // 真实情况是 adapter 里声明的 timeouts 此前从未被内容脚本消费（所有平台恒 60s，
      // 见 content-script.js 的 PLATFORM_RESPONSE_TIMEOUT 注释）。本站 fix2 实测
      // 723.9s = 4×180s + 3.9s，说明 180s 确实生效了，而失败原因是 messageList 0 命中，
      // 跟响应时长无关。保留 180s 只是给联网搜索留余量，不再往上加。
      timeouts: { response: 180000, typing: 5000, input: 100 },
    };
  }
}

export { SELECTORS };
export default LongCatAdapter;
