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
  /**
   * 发送按钮：**空数组，这是结论不是遗漏**（N54 / A3，2026-11-19）。
   *
   * 此前是四条：
   *   'button[data-testid="send-button"]'
   *   'button[aria-label*="Send"]'
   *   'button[aria-label*="发送"]'
   *   'button[class*="send"]'
   *
   * 为什么删：这四条在真机上一次都没命中过，有工件为证——
   * `tests/real-machine/fixtures/real/deepseek.json` 的 `sendButtonFound=false`
   * 是采集器**用本数组里这四条选择器**在登录态真机页面上跑出来的结论。
   * 也就是说「它们命中不了」不是猜测，是采过的。
   *
   * 那它们为什么曾经看起来能用：`tests/adapter-matrix/fixtures/mock-dom-deepseek.html`
   * 里摆了一个 `<button data-testid="send-button" aria-label="发送" class="send-button">`，
   * 它同时命中这四条——而那个 button 在真机上不存在。等于照着选择器写 fixture、
   * 再用 fixture 验选择器（N59）。fixture 已在 A2 清掉，选择器在 A3 清掉，
   * 两头都不再自己骗自己。
   *
   * 为什么不换成「猜一个更像真机的选择器」：发送区的真实 DOM 从来没有落过盘
   * （N60：`fixtures/real/deepseek.html` 只有 270 字节的输入框子树）。没有工件就填，
   * 填进去的只是记忆或猜测；而这个文件的读者会以为它是验证过的。
   *
   * 后果与意图：`getSendButton()` 恒返回 null（`findElement([])` 不循环，直接 null），
   * 于是 `clickSend()` 的唯一活路径是 **Enter 键**——这是**设计**，不是退化：
   * 历史 L2 回执里 deepseek 的消息确实发出去过，走的就是 Enter。
   * 该路径现在有单测与变异锚守着（`tests/deepseek-clicksend.test.mjs`）。
   *
   * 什么时候该往里填：等 N60 补采到输入区容器的 `outerHTML` 工件之后，
   * 按工件写，并且**同时**改 `data-expect-send-button` 那一侧的声明与矩阵断言。
   * 在拿到工件之前，任何人想把四条中的任何一条加回来，都会被
   * `tests/deepseek-clicksend.test.mjs` 的「选择器必须为空」判红——那道门就是拦这个的。
   */
  sendButton: [],
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
  // 🔧 2026-11-18 实测（真机全量 L2，step_5 稳定复现 723.44s 假超时）：
  // 这里原本第一条是 `[class*="loading"]`，它把**联网搜索的来源站点图标**当成「正在生成」。
  //
  //   页面现象：step_5「写边界标注」那一步触发了联网搜索（截图里有「搜索到 23 个网页」
  //   与引用角标），于是页面渲染出 6 个来源站点 logo 占位：
  //     <div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px">
  //   class 里带 loading ⇒ findVisibleElement(['[class*="loading"]']) 命中 ⇒
  //   isTyping() **恒为 true** ⇒ handleWaitForResponse 的 `state.ready && !isTyping()`
  //   永远不成立 ⇒ 白等 4×180s。截图同期证明 AI 回答早已完整落在页面上。
  //
  // 为什么删掉而不是改成 `:not([class*="site_logo"])`：那只是把今天的哈希类名
  // 钉进选择器，站点下次改版就复发。宽通配 `[class*="..."]` 误命中界面外壳
  // 是这个项目反复踩的同一个坑（文心命中通知中心、元宝命中新建按钮）。
  //
  // 删掉后靠什么判忙闲：stopButton（生成中才出现的停止按钮）+ generating +
  // .typing-indicator + 等待循环里的 8 秒正文稳定窗。真机上这三条在空闲态
  // 实测均 0 命中，所以 step_2/3/4 本来就是走「稳定窗」这条路成功的；
  // 删掉宽通配不引入「太早成功」，只是把 step_5 拉回与前 3 步同样的路径。
  // 宁可少一个信号，也不要一个恒为 true 的忙闲判定——后者让每一步都必然超时。
  typingIndicator: [
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

  /**
   * 发送。
   *
   * 顺序仍是「有按钮就点、没有就按 Enter」，但**在当前选择器配置下第一条是死分支**：
   * `sendButton: []`（见上面的注释），`getSendButton()` 恒 null ⇒ 一定走 Enter。
   *
   * 为什么还留着第一条而不是删掉：它是 `PlatformAdapter` 的通用形状，
   * 一旦 N60 补采到按钮工件、选择器被填回去，这里不需要再改一次。
   *
   * 但它**现在不会被真的执行到**（选择器空 ⇒ 永远取不到按钮），所以它的正确性
   * 只由「替身」验过：`deepseek-clicksend.test.mjs` 里有两条用例把 `getSendButton()`
   * 换成假按钮，分别钉住「有按钮就点」与「disabled 就回落 Enter」。
   * 换句话说，分支的**逻辑**有守护，分支的**前提**（真机上有这么个按钮）没有——
   * 后者是 N60 的事。别把这两件事读成一件事。
   *
   * Enter 事件带 `key` + `code` + `bubbles`：真机站点把 keydown 挂在祖先上监听，
   * 不冒泡就收不到；只给 `code` 不给 `key` 时，部分实现读 `event.key` 会拿到空串。
   * 这两个属性是被历史 L2 回执（消息确实发出去了）间接验证过的最小集合，
   * 单测把事件形状钉住了——删任何一个都会红。
   */
  async clickSend() {
    const button = this.getSendButton();
    if (button && !button.disabled) {
      button.click();
      await delay(100);
      return;
    }

    // fallback: Enter 键发送 —— 当前配置下这是唯一活路径
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
