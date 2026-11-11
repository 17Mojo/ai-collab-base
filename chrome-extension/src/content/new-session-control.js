/**
 * 「新对话」入口的定位 / 点击 / 会话重置判定。
 *
 * ## 为什么单独成模块
 *
 * 这段逻辑原先内联在 content-script.js 里：它是 ES module、直接摸全局
 * `document`，没法在 node:test 里跑，于是**只能靠真机**判断它对不对——
 * 而真机每站要 4–7 分钟，且站点改一次 DOM 就要重跑一遍。
 * 抽出来之后把 `document` / `findVisibleElement` / `isElementRendered` /
 * `findElements` 作为依赖注入，jsdom 里就能把 5 个活跃站的真实结构
 * 各自摆一遍，变异锚也终于能咬到**行为**而不是源码长相。
 *
 * 本模块是纯 DOM 逻辑：不发送任何消息、不点发送按钮、不碰验证码。
 * 由 content-script.js 的 `NEW_SESSION` 分支调用。
 */

/** 「新对话」入口的文案候选。站点改文案就失效，所以另有选择器与语义属性两层兜底。 */
export const NEW_SESSION_TEXTS = [
  "新对话",
  "新建对话",
  "新的对话",
  "开始新对话",
  "新建聊天",
  "新建会话", // Kimi 的 `a.logo[aria-label="新建会话"]`，2026-11-11 只读探测实证
  "新会话",
  "New chat",
  "New Chat",
];

/**
 * 找「新对话」控件时要看的标签。
 * 不止 `button`：chatglm 是 `div.new-session`、文心是
 * `div.new-dialog-container-plain`，按标签找在两站上恒 0 命中。
 */
export const NEW_SESSION_CONTROL_SELECTOR = [
  "button",
  '[role="button"]',
  "a",
  '[class*="new-session"]',
  '[class*="new-chat"]',
  '[class*="newChat"]',
  '[class*="new-dialog"]',
].join(", ");

/** 落在输入/发送区里的同名元素一律不认（chatglm 输入框旁有个诱饵）。 */
export const COMPOSER_ZONE_SELECTOR = [
  "form",
  '[class*="input"]',
  '[class*="editor"]',
  '[class*="send"]',
  '[class*="composer"]',
].join(", ");

/**
 * 「隐藏但语义明确」的入口，只在可见匹配全部失败后作为最后一层兜底。
 *
 * 千问（2026-11-11 只读探测实证）：
 *   div[data-session-switch-target="new-chat"] 的文本是「新对话」，但它整条
 *   祖先链挂在 `pointer-events-none opacity-0` 的 hover-reveal 面板里
 *   （`div.newChatReveal-*`），`isElementRendered` 会正确地判为不可见。
 *   ⇒ 前两层永远找不到它，千问因此一直 `available:false`。
 *
 * 为什么敢点一个「不可见」的元素：程序化 `el.click()` 派发的是可冒泡的
 * click 事件，不受 `pointer-events:none` 影响，页面的 click 处理器照常触发；
 * 而**点完到底有没有重置，仍由 `waitForSessionReset` 的消息数下降来判定**——
 * 判不出来就如实失败。安全边界是行为判据，不是可见性。
 *
 * 这里只放「属性值直接声明了 new-chat 语义」的窄选择器，不放通配符：
 * 宁可在新站点上降级，也不要在 DOM 里乱点看不见的东西。
 */
export const HIDDEN_SEMANTIC_SELECTORS = [
  '[data-session-switch-target="new-chat"]',
  '[data-testid="sidebar-new-chat"]',
];

/**
 * 找「新对话」控件。三层兜底，逐层放宽，命中即停。
 *
 * @param {object} deps
 * @param {Document} deps.document
 * @param {object} deps.config 当前平台 adapter 的 SELECTORS
 * @param {(selectors: string[]) => Element|null} deps.findVisibleElement
 * @param {(el: Element) => boolean} deps.isElementRendered
 * @returns {{el: Element, how: "adapter-selector"|"text-match"|"hidden-semantic"}|null}
 */
export function findNewSessionControl({
  document,
  config,
  findVisibleElement,
  isElementRendered,
}) {
  // 1) adapter 声明的选择器（精度最高）
  if (config?.newChat) {
    const el = findVisibleElement(config.newChat);
    if (el) return { el, how: "adapter-selector" };
  }

  // 2) 可见控件 + 文案/aria/title 精确匹配（跨站覆盖）
  const wanted = new Set(NEW_SESSION_TEXTS);
  for (const el of document.querySelectorAll(NEW_SESSION_CONTROL_SELECTOR)) {
    if (!isElementRendered(el)) continue;
    if (el.closest(COMPOSER_ZONE_SELECTOR)) continue; // 发送区旁边的同名元素不认
    const candidates = [
      (el.textContent || "").trim(),
      (el.getAttribute("aria-label") || "").trim(),
      (el.getAttribute("title") || "").trim(),
    ];
    if (candidates.some((t) => t && wanted.has(t))) {
      return { el, how: "text-match" };
    }
  }

  // 3) 隐藏但语义明确的入口（千问的 hover-reveal 层）
  for (const sel of HIDDEN_SEMANTIC_SELECTORS) {
    for (const el of document.querySelectorAll(sel)) {
      if (el.closest(COMPOSER_ZONE_SELECTOR)) continue;
      const text = (el.textContent || "").trim();
      if (text && wanted.has(text)) return { el, how: "hidden-semantic" };
      // 有些入口是纯图标（Kimi 的 a.new-chat-btn），文本为空也认，
      // 但必须同时命中「语义属性」和「带 href 的锚点」才算数。
      const label = (el.getAttribute("aria-label") || "").trim();
      if ((label && wanted.has(label)) || el.matches('a[href*="new_chat"]')) {
        return { el, how: "hidden-semantic" };
      }
    }
  }
  return null;
}

/**
 * 点「新对话」控件。
 *
 * Kimi 的入口是 `<a href="/?chat_enter_method=new_chat">`。直接 `.click()`
 * 可能触发**整页导航**：内容脚本会随文档一起销毁，`NEW_SESSION` 的
 * `sendResponse` 永远发不出去，后台只会看到一次莫名的「开新会话失败」。
 *
 * 所以在点击期间挂一个捕获阶段的 `preventDefault`：拦掉浏览器默认跳转，
 * 但**不拦页面自己的 click 处理器**（SPA 路由照常生效）。如果站点真的
 * 只能靠整页跳转开新会话，这次拦截会让它失效——`waitForSessionReset`
 * 会如实判失败，不会假装成功。
 *
 * @param {Document} document
 * @param {Element} el
 */
export function clickNewSessionControl(document, el) {
  const isAnchor = !!el.closest("a[href]");
  const blockNavigation = (event) => event.preventDefault();
  if (isAnchor) document.addEventListener("click", blockNavigation, true);
  try {
    el.click();
  } finally {
    // click() 同步派发，默认动作在同一次事件里就已决定，同步移除即可。
    if (isAnchor) document.removeEventListener("click", blockNavigation, true);
  }
}

/**
 * 等会话真的被清空。
 *
 * **点到了 ≠ 重置了**：按钮可能禁用、可能被遮挡、可能只滚回顶部。
 * 判据用「消息数下降」——新会话要么 0 条，要么只有一条欢迎语，
 * 两种情况都严格小于「重置前」的条数。
 *
 * @param {object} deps
 * @param {Document} deps.document
 * @param {(selectors: string[]) => Element[]} deps.findElements
 * @param {string[]} deps.messageList
 * @param {number} deps.beforeCount
 * @param {number} [deps.timeout=8000]
 * @returns {Promise<number>} 重置后的消息数
 */
export async function waitForSessionReset({
  document: _document,
  findElements,
  messageList,
  beforeCount,
  timeout = 8000,
}) {
  const deadline = Date.now() + timeout;
  let last = beforeCount;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    last = findElements(messageList).length;
    if (last < beforeCount) return last;
  }
  const error = new Error(
    `点了「新对话」但消息数没有下降（${beforeCount} → ${last}），` +
      "无法确认会话已重置。",
  );
  error.code = "NEW_SESSION_NOT_CONFIRMED";
  throw error;
}

/**
 * 开一个新会话（Pack 的「会话边界」，由步骤的 `fresh_session` 触发）。
 *
 * ## 两档语义
 *   - strict（`true` / `"strict"`）：开不成 ⇒ **抛错**，后台据此判这一步失败，
 *     一条提示词都不会发出去。适合「上一轮的上下文会污染这一步」的 Pack。
 *   - 非 strict（`"prefer"`）：开不成 ⇒ 回 `available:false` + 原因，
 *     后台记进回执后**照常发送**，行为与修复前一致。
 *
 * 为什么非 strict 不能直接抛错：第一版的可见入口只覆盖 chatglm / 文心两站，
 * 一律 strict 会把本来跑得通的站打成 7/8。但降级必须可见。
 *
 * ## 为什么要记 `durationMs`
 * 会话边界上线后，chatglm 整包耗时 349.8s → 419.6s，光看总数既不能说
 * 「重置拖慢了」，也不能反过来说「重置免费」。把「找入口 + 点 + 等消息数
 * 下降」的耗时单独记下来，重置的**固定开销**才是一个可复核的数，
 * 而不是混在 AI 回答耗时里猜。见 RESULT §14。
 *
 * @param {object} deps
 * @param {Document} deps.document
 * @param {object} deps.config
 * @param {boolean} [deps.strict=false]
 * @param {(selectors: string[]) => Element|null} deps.findVisibleElement
 * @param {(el: Element) => boolean} deps.isElementRendered
 * @param {(selectors: string[]) => Element[]} deps.findElements
 * @param {number} [deps.resetTimeout=8000] 等消息数下降的上限；单测里可调短
 * @returns {Promise<{available: boolean, strategy: string, messageCountBefore: number,
 *   messageCountAfter: number, durationMs: number, reason?: string}>}
 * @throws {Error} strict 模式下找不到入口 / 点了没生效
 */
export async function handleNewSession({
  document,
  config,
  strict = false,
  findVisibleElement,
  isElementRendered,
  findElements,
  resetTimeout = 8000,
}) {
  if (!config) throw new Error("No adapter available");

  const startedAt = Date.now();
  /** 每条返回路径都带上耗时，包括降级——降级也要能看出它花了多久才放弃 */
  const finish = (result) => ({ ...result, durationMs: Date.now() - startedAt });
  const before = findElements(config.messageList).length;

  /** strict 就抛，不 strict 就如实回报「没办成」 */
  const refuse = (reason, strategy, code) => {
    if (strict) {
      const error = new Error(reason);
      error.code = code;
      throw error;
    }
    return finish({
      available: false,
      strategy,
      reason,
      messageCountBefore: before,
      messageCountAfter: before,
    });
  };

  if (before === 0) {
    // 本来就是空会话，没什么可重置的——这一步不该判失败
    return finish({
      available: true,
      strategy: "already-empty",
      messageCountBefore: 0,
      messageCountAfter: 0,
    });
  }

  const found = findNewSessionControl({
    document,
    config,
    findVisibleElement,
    isElementRendered,
  });
  if (!found) {
    return refuse(
      "找不到「新对话」入口：adapter 没有声明 newChat 选择器，" +
        `页面上也没有文案为 ${NEW_SESSION_TEXTS.slice(0, 4).join(" / ")} 等的可见控件。`,
      "none",
      "NEW_SESSION_CONTROL_NOT_FOUND",
    );
  }

  clickNewSessionControl(document, found.el);
  try {
    const after = await waitForSessionReset({
      document,
      findElements,
      messageList: config.messageList,
      beforeCount: before,
      timeout: resetTimeout,
    });
    return finish({
      available: true,
      strategy: found.how,
      messageCountBefore: before,
      messageCountAfter: after,
    });
  } catch (error) {
    return refuse(error.message, "click-no-effect", error.code);
  }
}
