/**
 * Qianwen Adapter (千问)
 * 阿里云千问 AI 平台适配器 — 完整实现 PlatformAdapter 接口
 */

import PlatformAdapter from "./adapter.js";
import { findElement, findElements, findVisibleElement, injectTextSmart, delay } from "./adapter-utils.js";

/**
 * 千问平台选择器配置
 *
 * 2026-10-25 真机实测（B-3）**整组重写**了这份配置。
 *
 * ## 为什么必须重写：原选择器在千问上从来就不是类名
 *
 * 对千问**自己的** JS+CSS（56 个资源 / 15.45 MB，含懒加载的 async chunk）
 * 做全量普查（只读、未登录、未发消息），原来这六条选择器里的字面量：
 *
 *   .response-content     字符串出现 2 次——但那是下载 URL 的查询参数
 *                         '?response-content-disposition='，**不是类名**
 *   "chat-item"           字符串 0 次，也不是类名
 *   .prose                字符串 5 次——但那是 Tailwind 的 'max-w: prose'
 *                         与 prosemirror-* 编辑器库，**不是类名**
 *   .typing-indicator     字符串 0 次，也不是类名
 *   "message-content"     字符串 11 次——但那是 CSS 变量
 *                         --message-content-width，**不是类名**
 *
 * 也就是说它们是照着别的站点抄来的，在千问上**永远命中 0 个**。
 * 剩下的 '[class*="message"]' / 'div[class*="content"]' 属于「宽松到没意义」：
 * 实测在空闲落地页上分别命中 0 个与 1 个（命中的是宽度为 0 的按钮外壳），
 * 进了会话则会命中 message-list-container 这类**界面外壳**——正是
 * yiyan/yuanbao 那个「消息数被外壳撑大」的老毛病。
 *
 * 普查工具与原始清单：
 *   node tests/real-machine/qianwen-asset-census.mjs
 *   tests/real-machine/evidence/qianwen-asset-census.json
 *
 * ## 证据从哪来：问千问自己
 *
 * 落地页没有会话 ⇒ 没有消息气泡 ⇒ 落地页快照**证不了**任何一条选择器
 * （既证不了对，也证不了错）。所以结构是从千问**自己的产物**里取的，
 * 三个互相独立的来源：
 *
 *   1. 站点自己的 CSS（web/css/async/session-message-runtime.css）用后代
 *      选择器写死了层级；
 *   2. 站点自己的 React 渲染代码（web/js/async/6605.js）给出确切的 class
 *      字符串与 data 属性——包括答案正文卡 'answer-text md-text-card'、
 *      等待首个 token 的 'answer-receiving-card'、答案卡容器
 *      'answer-common-card'、提问卡 'message-card-wrap question'；
 *   3. 站点**自己的文本选择功能**在 6605.js 里声明了它认哪些卡片：
 *        supportedSelectors: [".answer-common-card",
 *                              ".chat-question-card-wrap",
 *                              '[data-card_name="deep_think"]']
 *      ——「哪张卡是答案、哪张卡是问题」是站点自己说了算的。
 *
 * ## 一处刻意**不**采用的类名
 *
 * CSS 里有 `.chat-round .message-card-wrap.answer`，看着正好是「答案卡」。
 * 但 6605.js 里 'message-card-wrap' 只与 'question' 组合出现
 * （className:"message-card-wrap question"），'answer' 变体在**当前**
 * 渲染代码里不存在——那条 CSS 规则多半是给历史会话渲染器
 * （ChatEngineLegacyHistoryAnswerRenderer）用的。所以本表不以它为准，
 * 以当前渲染代码实际写出来的类名为准。
 */
const SELECTORS = {
  // 输入框：千问用的是 **Slate** 富文本编辑器（实测属性 data-slate-editor="true"
  // + contenteditable="true" + data-placeholder="向千问提问"）。
  // 精确的 Slate 标记放前面，免得命中页面上别处的 contenteditable 区域；
  // 通用选择器留作回退，站点若换编辑器仍然命中得了。
  chatInput: ['div[data-slate-editor="true"]', 'div[contenteditable="true"]', "textarea"],

  sendButton: [
    // 2026-10-25 实测新增：**稳定属性**，不随界面语言变。
    // 原来的 'button[aria-label*="发送"]' 依赖 i18n——站点词典里
    // sendMessage = "发送消息" / "傳送訊息"，英文界面下必然落空。
    'button[data-session-switch-target="send-query"]',
    'button[aria-label*="发送"]',
    'button[title*="发送"]',
    'button[class*="send"]',
  ],

  messageList: [
    // 答案正文卡：站点渲染代码里的字面量 class "answer-text md-text-card"
    // （**没有被 CSS Modules 加哈希** ⇒ 跨发版稳定）。
    // 选它而不是外层卡片，是为了**计数契约**：
    // 等待首个 token 期间，站点会先挂一张 "answer-receiving-card"（点点点），
    // 它同样带 answer-common-card 类。若拿卡片当消息，用户一按下发送
    // 计数就 +1，会在回复还没开始时就提前返回。
    'div.answer-text.md-text-card',
    // 站点自己声明的答案卡（文本选择功能的 supportedSelectors 第一个）。
    // 只作回退：万一站点改掉正文卡的类名，还能认得出来。
    // :not(.answer-receiving-card) 把「接收中」卡片排除掉——它是生成中的
    // 信号，不是消息。
    'div.answer-common-card:not(.answer-receiving-card)',
  ],

  messageContent: [
    // 千问的 markdown 容器是**全局类** .qk-markdown（内部由多个 .qk-md-text
    // 片段组成）。取容器而不是片段：一次 querySelector('.qk-md-text') 只会
    // 拿到**第一段**，多段落答案会被截掉一截。
    '.qk-markdown',
    '.qk-md-text',
    // markdown-content-<hash> 是 CSS Modules 哈希类名，哈希随发版变，
    // 但本地名稳定 ⇒ 用属性包含匹配。
    '[class*="markdown-content"]',
  ],

  typingIndicator: [
    // 等待首个 token 的「接收中」点点点卡片（class 字面量，无哈希）。
    'div.answer-receiving-card',
    // 生成中：输入区右下角的按钮从「发送消息」换成「停止回答」
    //（i18n key = qianwenWeb.input.stopAnswer，站点词典实测值「停止回答」）。
    // 这两个按钮占**同一个位置**，所以「停止回答」存在 ⇔ 正在生成。
    'button[aria-label*="停止回答"]',
    // 英文界面下的同一个按钮（aria-label 含 stop，大小写不敏感匹配）。
    'button[aria-label*="stop" i]',
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

    await injectTextSmart(input, text);
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
   *
   * 先看**元素自身**再找后代：站点的 markdown 容器有可能与答案卡是同一个
   * 元素，只查后代会漏掉它，接着退到 '.qk-md-text' 就只拿到第一段，
   * 多段落答案会被截断。
   */
  _extractContent(element) {
    if (!element) return "";
    for (const sel of this.selectors.messageContent) {
      const self = element.matches?.(sel) ? element : null;
      const el = self || element.querySelector(sel);
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
