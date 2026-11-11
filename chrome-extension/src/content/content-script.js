/**
 * Prompt Pack - Content Script (ESM Source)
 * 注入到 AI 聊天页面的脚本 — 动态适配所有平台
 *
 * 构建说明：
 * 此文件使用 ESM import 从适配器文件导入选择器配置。
 * Vite 构建时会将此文件打包为 IIFE 格式，解决 Manifest V3
 * content_scripts 不支持 type:module 的问题。
 * 选择器配置与适配器文件自动同步，无需手动维护两份配置。
 */

// ============================================================================
// 从适配器文件导入选择器配置（构建时自动同步）
// ============================================================================

// 等待策略：内容稳定性判据（防「太早成功」）
import { sampleWaitState } from "../utils/wait-policy.js";
// 失败语义：超时必须「续等」而不是重发（台账 N21）
import {
  RESPONSE_TIMEOUT_CODE,
  resolveInitialCount,
} from "../utils/retry-policy.js";

import { SELECTORS as CLAUDE_SELECTORS } from "../platforms/claude-adapter.js";
import { SELECTORS as CHATGPT_SELECTORS } from "../platforms/chatgpt-adapter.js";
import { SELECTORS as GEMINI_SELECTORS } from "../platforms/gemini-adapter.js";
import { SELECTORS as QIANWEN_SELECTORS } from "../platforms/qianwen-adapter.js";
import { SELECTORS as CHATGLM_SELECTORS } from "../platforms/chatglm-adapter.js";
import { SELECTORS as KIMI_SELECTORS } from "../platforms/kimi-adapter.js";
import { SELECTORS as YIYAN_SELECTORS } from "../platforms/yiyan-adapter.js";
import { SELECTORS as YUANBAO_SELECTORS } from "../platforms/yuanbao-adapter.js";
import { SELECTORS as LONGCAT_SELECTORS } from "../platforms/longcat-adapter.js";
import { SELECTORS as DEEPSEEK_SELECTORS } from "../platforms/deepseek-adapter.js";

// 导入 DOM 操作工具函数
import {
  findElement,
  findElements,
  findVisibleElement,
  injectTextSmart,
  extractMessageContent,
  isElementRendered,
} from "../platforms/adapter-utils.js";

// ============================================================================
// 平台选择器配置（从适配器自动导入，域名别名手动映射）
// ============================================================================

/**
 * 平台 ID → 选择器配置的映射表
 *
 * 选择器配置直接从各适配器文件的 SELECTORS 常量导入，
 * 确保与适配器实现自动同步。
 *
 * 域名别名（如 kimi.moonshot.cn → kimi.com）需要在此手动映射，
 * 但选择器本身不需要重复维护。
 */
const PLATFORM_CONFIGS = {
  "claude.ai": CLAUDE_SELECTORS,
  "chat.openai.com": CHATGPT_SELECTORS,
  "chatgpt.com": CHATGPT_SELECTORS,
  "gemini.google.com": GEMINI_SELECTORS,
  "qianwen.com": QIANWEN_SELECTORS,
  "qianwen.aliyun.com": QIANWEN_SELECTORS,
  "tongyi.aliyun.com": QIANWEN_SELECTORS,
  "chatglm.cn": CHATGLM_SELECTORS,
  "kimi.com": KIMI_SELECTORS,
  "kimi.moonshot.cn": KIMI_SELECTORS,
  "yiyan.baidu.com": YIYAN_SELECTORS,
  "wenxin.baidu.com": YIYAN_SELECTORS,
  "yuanbao.tencent.com": YUANBAO_SELECTORS,
  "longcat.chat": LONGCAT_SELECTORS,
  "longcat.ai": LONGCAT_SELECTORS,
  "chat.deepseek.com": DEEPSEEK_SELECTORS,
};

/**
 * 平台等待上限覆盖（毫秒）。key 与 {@link PLATFORM_CONFIGS} 一致（hostname）。
 *
 * ## 为什么需要这张表（2026-11-11 实测，RMR-2026-11-11-01）
 *
 * `adapter.getConfig().timeouts.response` 是一个**从未被接入**的配置：
 * 内容脚本只取 adapter 的 SELECTORS（见上面的 PLATFORM_CONFIGS 注释），
 * 拿不到 timeouts；而 `message.config` 传的是 **Pack 步骤的 config**
 * （min_output_length 那些），也没有 timeout 字段。
 *
 * 后果：全部平台一律吃 `handleSendToAI` 的 60s 默认值。deepseek / longcat
 * 在带深度思考 / 联网搜索时单步响应会突破 60s，被判超时后
 * pack-executor 重试 3 次 ⇒ 4×60s+3×1s ≈ 244s 全灭——而截图上 AI 回复
 * 其实早已生成完毕。deepseek 的 step_4 耗时 72.6s（= 60s 超时 + 12s 重试成功）
 * 就是这条路径留下的指纹。
 *
 * ## 这张表是技术债，不是终态
 *
 * 正确做法是让 adapter 的 timeouts 真正流过边界（adapter 导出 TIMEOUTS 常量、
 * 内容脚本 import），保持「单一事实源」。当前只列**例外站点**以缩小改动面，
 * 其余平台仍走 60s 默认值。收口时删掉本表。
 */
const PLATFORM_RESPONSE_TIMEOUT = {
  "chat.deepseek.com": 180000,
  "longcat.chat": 180000,
  "longcat.ai": 180000,
  // 2026-11-11 12:41 活跃 5 站回归（RMR-2026-11-11-03）：chatglm 走默认 60s 时，
  // step_2 用了 170.7s、step_7 用了 151.3s，且 errors 为空、字段全非空。
  // 形状 170.7≈60+60+50.7 / 151.3≈60+60+31.3 ⇒ 中途至少重发过 1 次
  // （N21：重发会污染会话、不报错、只在时长上留指纹）。
  // 抬到 180s 是为了让答案在一次尝试里等到稳定，从源头减少重发。
  // ⚠️ 该值**尚未实测验证**：改完后 chatglm 已对本 profile 弹滑块验证，无法复跑。
  "chatglm.cn": 180000,
};

// ============================================================================
// Content Script 主逻辑
// ============================================================================

// 当前平台配置
let currentConfig = null;
let currentPlatformId = null;

/**
 * 初始化 Content Script
 */
async function initialize() {
  console.log("[Prompt Pack] Content Script initialized");

  // 请求获取适配器 ID（Service Worker 返回 { adapterId }）
  const response = await chrome.runtime.sendMessage({ type: "GET_ADAPTER" });

  if (response?.adapterId && PLATFORM_CONFIGS[response.adapterId]) {
    currentPlatformId = response.adapterId;
    currentConfig = PLATFORM_CONFIGS[currentPlatformId];
    console.log(`[Prompt Pack] Using adapter: ${currentPlatformId}`);
    setupEventListeners();
  } else {
    console.log("[Prompt Pack] No adapter available for this page");
  }
}

/**
 * 失败回话的统一信封
 *
 * ## 为什么要带上 code 与 baselineCount
 *
 * 只回 `{success:false, error}` 的话，后台只能靠**文案**猜这是哪一类失败。
 * 而失败语义决定后台能不能重试：超时重试 = 重发 = 会话里多一条重复提问。
 *
 * 所以把语义随信封一起带出去：
 *   - `code`：`RESPONSE_TIMEOUT` 时后台改「续等」，不再重发；
 *   - `baselineCount`：发送前的消息条数，续等时按它算 `countGrew`。
 *
 * 两者都可能在错误对象上不存在（例如早就失败的注入环节），
 * 此时如实回 null，让后台按「可重试」处理——不知道就别乱猜成超时。
 *
 * @param {Error & {code?: string, baselineCount?: number}} error
 * @returns {{success: false, error: string, code: string|null, baselineCount: number|null}}
 */
function failureEnvelope(error) {
  return {
    success: false,
    error: error?.message || String(error),
    code: error?.code || null,
    baselineCount: Number.isInteger(error?.baselineCount)
      ? error.baselineCount
      : null,
  };
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case "INJECT_TEXT":
        handleInjectText(message.text)
          .then(() => sendResponse({ success: true }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;

      case "CLICK_SEND":
        handleClickSend()
          .then(() => sendResponse({ success: true }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
        return true;

      case "GET_PAGE_STATE":
        const state = getPageState();
        sendResponse(state);
        break;

      // 🔧 2026-11-11（Pack 会话边界）：开一个新会话。
      //
      // 为什么需要：deepseek / longcat 的 step_8（fusion）在同一会话里跑到第 8 轮
      // 时撞墙——deepseek 是答案超出 4×180s 窗口，longcat 直接报「服务出错」。
      // 隔离实验把那条 2437 字的 fusion 提示词原样发进**全新会话**：21 秒答完、
      // 产出 1481 字。⇒ 提示词本身没问题，**长会话才是变量**。
      //
      // 所以 Pack 需要一个显式的「会话边界」：某些步骤自足（所需字段全在
      // 提示词里内联），就不该继续背着前面 7 轮的上下文。
      case "NEW_SESSION":
        handleNewSession(message.strict === true)
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) => sendResponse(failureEnvelope(error)));
        return true;

      case "WAIT_FOR_RESPONSE":
        // 🔧 2026-11-11（N21）：续等。后台在 AI 步骤超时后**不再重发**，
        // 而是让页面继续盯同一个会话——所以这里必须能把「发送前的基准条数」
        // 传回去。不传就等于重新快照，countGrew 会恒为 false
        // （见 retry-policy.resolveInitialCount 的注释）。
        handleWaitForResponse(
          message.timeout ?? PLATFORM_RESPONSE_TIMEOUT[currentPlatformId],
          message.baselineCount,
        )
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) => sendResponse(failureEnvelope(error)));
        return true;

      // Pack 执行链路的最后一环：后台 pack-executor 的 AI 步骤发的是
      // SEND_TO_AI。此前**没有任何分支处理它** ⇒ chrome.runtime.sendMessage
      // 拿不到响应 ⇒ 那个 AI 步骤拿到一个空值，却仍然被当成「成功」，
      // 流程照往下走，最后产物是空的——用户看到的是「点了没反应」。
      //
      // 这条分支是 Pack 能不能真正跑通的关键，不是可选的增强。
      case "SEND_TO_AI":
        // 🔧 2026-11-11：等待上限的正确来源是 PLATFORM_RESPONSE_TIMEOUT（见其注释）。
        // 踩过两次才定位（两次都被实测打回：244s 一秒没变）：
        //   1. `message.config?.timeout` —— message.config 是 **Pack 步骤的 config**，
        //      装 min_output_length / example_hooks，没有 timeout 字段；
        //   2. `message.config?.timeouts?.response` —— 同样落空；
        //   3. `currentConfig?.timeouts?.response` —— currentConfig 是
        //      PLATFORM_CONFIGS[hostname] = adapter 的 **SELECTORS**，也不含 timeouts。
        // 优先级：Pack 步骤级显式覆盖（config.timeout）> 站点例外表 > 60s 默认。
        handleSendToAI(
          message.prompt,
          message.config?.timeout ?? PLATFORM_RESPONSE_TIMEOUT[currentPlatformId],
        )
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) => sendResponse(failureEnvelope(error)));
        return true;
    }
  });
}

/**
 * 获取页面状态
 */
function getPageState() {
  if (!currentConfig) {
    return {
      url: window.location.href,
      platformId: null,
      hasInput: false,
      messageCount: 0,
    };
  }

  const input = findElement(currentConfig.chatInput);
  const messages = findElements(currentConfig.messageList);

  return {
    url: window.location.href,
    platformId: currentPlatformId,
    hasInput: !!input,
    messageCount: messages.length,
  };
}

/**
 * 处理文本注入
 */
async function handleInjectText(text) {
  if (!currentConfig) throw new Error("No adapter available");

  const input = findElement(currentConfig.chatInput);
  if (!input) throw new Error("Chat input not found");

  await injectTextSmart(input, text);
  await new Promise((resolve) => setTimeout(resolve, 150));
}

/**
 * 处理点击发送
 */
async function handleClickSend() {
  if (!currentConfig) throw new Error("No adapter available");

  const button = findElement(currentConfig.sendButton);
  if (button && !button.disabled) {
    button.click();
    await new Promise((resolve) => setTimeout(resolve, 100));
    return;
  }

  // fallback: Enter 键发送
  const input = findElement(currentConfig.chatInput);
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
 * 「新对话」入口的文案候选。
 *
 * 用文案而不是 per-adapter 选择器，是有取舍的：
 *   - 选择器精确，但 5 个活跃站 + 4 个冻结站都要各写一份，而且**每一份都无法
 *     在没有真机的情况下验证**——写了也是猜的；
 *   - 文案匹配跨站通用，一次覆盖全部站点，代价是站点改文案就失效。
 *
 * 所以做成「两层」：adapter 真声明了 `newChat` 选择器就优先用它（精度），
 * 没有才落到文案匹配（覆盖）。失效时**必须失败**而不是悄悄继续——
 * 见 handleNewSession 的错误分支。
 */
const NEW_SESSION_TEXTS = [
  "新对话",
  "新建对话",
  "新的对话",
  "开始新对话",
  "新建聊天",
  "新会话",
  "New chat",
  "New Chat",
];

/**
 * 找「新对话」控件时要看的标签。
 *
 * 为什么不止 `button`：2026-11-11 只读探测实测，两个站的入口都**不是按钮**——
 *   chatglm: `div.new-session.flex…`（挂在 aside 下）
 *   文心:    `div.new-dialog-container-plain`
 * 只按标签找（button / a / [role=button]）在这两个站上恒为 0 命中，
 * 于是「开新会话」永远失败、step_8 直接被判不合格。
 */
const NEW_SESSION_CONTROL_SELECTOR = [
  "button",
  '[role="button"]',
  "a",
  '[class*="new-session"]',
  '[class*="new-chat"]',
  '[class*="newChat"]',
  '[class*="new-dialog"]',
].join(", ");

/**
 * 落在输入/发送区里的元素一律不认。
 *
 * 实测证据（/tmp/newchat-probe.json，chatglm）：同一个「新对话」文案在
 * 输入框附近还有一个 `div.enter.is-main-chat`（祖先链是
 * input-box-container → input-wrap → …）。它长得像入口、位置却在发送区旁边，
 * 点它的后果不可预料。所以按祖先类名把它排除掉。
 */
const COMPOSER_ZONE_SELECTOR = [
  "form",
  '[class*="input"]',
  '[class*="editor"]',
  '[class*="send"]',
  '[class*="composer"]',
].join(", ");

/**
 * 找「新对话」控件。
 * @returns {{el: Element, how: "adapter-selector"|"text-match"}|null}
 */
function findNewSessionControl() {
  if (currentConfig?.newChat) {
    const el = findVisibleElement(currentConfig.newChat);
    if (el) return { el, how: "adapter-selector" };
  }

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
  return null;
}

/**
 * 等会话真的被清空。
 *
 * **点到了 ≠ 重置了**：按钮可能禁用、可能被遮挡、可能只滚回顶部。
 * 判据用「消息数下降」——新会话要么 0 条，要么只有一条欢迎语，
 * 两种情况都严格小于「重置前」的条数。
 *
 * @param {number} beforeCount
 * @param {number} [timeout=8000]
 * @returns {Promise<number>} 重置后的消息数
 */
async function waitForSessionReset(beforeCount, timeout = 8000) {
  const deadline = Date.now() + timeout;
  let last = beforeCount;
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 300));
    last = findElements(currentConfig.messageList).length;
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
 *
 * `strict` 由调用方（后台）给，来自步骤的 `fresh_session` 取值：
 *   - strict（`true` / `"strict"`）：开不成 ⇒ **抛错**，后台据此判这一步失败，
 *     一条提示词都不会发出去。适合「上一轮的上下文会污染这一步」的 Pack。
 *   - 非 strict（`"prefer"`）：开不成 ⇒ 回 `available:false` + 原因，
 *     后台记进回执后**照常发送**，行为与修复前一致。
 *
 * 为什么非 strict 不能直接抛错：2026-11-11 实测，5 个活跃站里只有 chatglm
 * 与文心能识别出「新对话」入口，千问是纯 Tailwind 类名、元宝/Kimi 不用这个
 * 措辞。一律 strict 会让一个结构性优化把**本来跑得通**的站点打成 7/8。
 * 但降级必须可见——`available:false` 会随回执落盘。
 *
 * @param {boolean} [strict=false]
 * @returns {Promise<{available: boolean, strategy: string, messageCountBefore: number,
 *   messageCountAfter?: number, reason?: string}>}
 * @throws {Error} strict 模式下找不到入口 / 点了没生效
 */
async function handleNewSession(strict = false) {
  if (!currentConfig) throw new Error("No adapter available");

  const before = findElements(currentConfig.messageList).length;

  /** strict 就抛，不 strict 就如实回报「没办成」 */
  const refuse = (reason, strategy, code) => {
    if (strict) {
      const error = new Error(reason);
      error.code = code;
      throw error;
    }
    return {
      available: false,
      strategy,
      reason,
      messageCountBefore: before,
      messageCountAfter: before,
    };
  };

  if (before === 0) {
    // 本来就是空会话，没什么可重置的——这一步不该判失败
    return {
      available: true,
      strategy: "already-empty",
      messageCountBefore: 0,
      messageCountAfter: 0,
    };
  }

  const found = findNewSessionControl();
  if (!found) {
    return refuse(
      "找不到「新对话」入口：adapter 没有声明 newChat 选择器，" +
        `页面上也没有文案为 ${NEW_SESSION_TEXTS.slice(0, 4).join(" / ")} 等的可见控件。`,
      "none",
      "NEW_SESSION_CONTROL_NOT_FOUND",
    );
  }

  found.el.click();
  try {
    const after = await waitForSessionReset(before);
    return {
      available: true,
      strategy: found.how,
      messageCountBefore: before,
      messageCountAfter: after,
    };
  } catch (error) {
    return refuse(error.message, "click-no-effect", error.code);
  }
}

/**
 * 执行一次「向 AI 发消息并等回复」
 *
 * 后台 pack-executor 的 AI 步骤发的是 SEND_TO_AI（见 pack-executor.js 的
 * _executeAIStep）。这条链路此前是**断的**：内容脚本没有对应分支，
 * sendMessage 拿不到响应，AI 步骤拿到 undefined 还被当成成功，
 * 流程继续往下走 ⇒ Pack 「执行成功」但产物是空的。
 *
 * 这里把三件事串起来：注入文本 → 点发送 → 等回复。
 *
 * **三件事的验证状态不一样，不要一概而论**（见 docs/REAL_MACHINE_REGRESSION.md）：
 *   - 等回复：真机验证过；
 *   - 注入文本：**此前没有**被真机验证过。2026-10-26 W-D1 彩排实测发现，
 *     千问（Slate 编辑器）上注入只改了 DOM、**没进框架的模型** ⇒
 *     发送按钮保持 disabled ⇒ 点击等于没点 ⇒ 必然超时。
 *     现在由 slate-editor.js 的模型感知注入修掉，注入失败会**抛错**
 *     而不是留一个假成功。
 *
 * @param {string} prompt - 要发给 AI 的提示词
 * @param {number} [timeout=60000] - 等回复的超时（毫秒）
 * @returns {Promise<{messageCount: number, content: string, duration: number}>}
 */
async function handleSendToAI(prompt, timeout = 60000) {
  if (!currentConfig) throw new Error("No adapter available");
  if (!prompt || !String(prompt).trim()) {
    throw new Error("SEND_TO_AI requires a non-empty prompt");
  }

  // 发送**之前**数一次消息条数。这个数就是本次发送的「基准」：
  // 超时后后台改「续等」时要用它算 countGrew，不能重新数——否则
  // 「回复在超时之后、续等开始之前刚落地」这种情况会让 countGrew 恒 false，
  // 续等白等满一整个超时窗口。见 retry-policy.resolveInitialCount。
  const baselineCount = findElements(currentConfig.messageList).length;

  await handleInjectText(prompt);
  await handleClickSend();

  try {
    return await handleWaitForResponse(timeout, baselineCount);
  } catch (error) {
    // 超时不是「没发出去」，是「发出去了没等到」。把基准条数挂上去，
    // 好让后台选择「续等」而不是「重发」（N21）。
    if (error?.code === RESPONSE_TIMEOUT_CODE) {
      error.baselineCount = baselineCount;
    }
    throw error;
  }
}

/**
 * 检查 AI 是否正在输入
 */
function isTyping() {
  if (!currentConfig) return false;

  // 检查停止按钮
  // 停止按钮与打字指示器都必须做**可见性**判定：真实站点空闲态会把这类元素
  // 留在 DOM 里（display:none）。按「存在即命中」判定会让 isTyping() 恒为 true，
  // 于是 handleWaitForResponse 永远等不到「不再打字」，每次执行都超时。
  if (currentConfig.stopButton) {
    const stopButton = findVisibleElement(currentConfig.stopButton);
    if (stopButton) return true;
  }

  // 检查输入指示器
  if (currentConfig.typingIndicator) {
    const indicator = findVisibleElement(currentConfig.typingIndicator);
    if (indicator) return true;
  }

  return false;
}

/**
 * 等待 AI 响应完成
 *
 * 「完成」的定义（2026-11-04 起）：**内容稳定**——正文连续
 * 一段窗口（wait-policy 的 STABLE_MS_DEFAULT）不再变化才算生成结束。
 * 旧判据「消息数增加 且 不在生成中」在千问真机上提前返回，
 * 取回的全是流式开头碎片（'收到，'）——见 wait-policy.js 顶部。
 * `isTyping()` 仍保留为**继续等**的信号：指示器认得准的平台
 * 在思考暂停期不会被稳定性判据误放行。
 *
 * @param {number} [timeout=60000] - 等多久算超时（毫秒）
 * @param {number} [baselineCount] - 发送前的消息条数。给了就必须用它，
 *   **不许重新快照**（那是续等路径，见 retry-policy.resolveInitialCount）
 */
async function handleWaitForResponse(timeout = 60000, baselineCount) {
  if (!currentConfig) throw new Error("No adapter available");

  const startTime = Date.now();
  const initialCount = resolveInitialCount(
    findElements(currentConfig.messageList).length,
    baselineCount,
  );
  let lastContent = null;
  let lastChangeAt = null;

  return new Promise((resolve, reject) => {
    const interval = setInterval(() => {
      if (Date.now() - startTime > timeout) {
        clearInterval(interval);
        // 带错误码：后台据此判「续等」而不是「重发」（N21）
        const error = new Error("Response timeout");
        error.code = RESPONSE_TIMEOUT_CODE;
        reject(error);
        return;
      }

      const messages = findElements(currentConfig.messageList);
      const currentCount = messages.length;
      const latestMessage = messages[messages.length - 1];
      const content = latestMessage
        ? extractMessageContent(latestMessage, currentConfig.messageContent)
        : "";

      const state = sampleWaitState({
        countGrew: currentCount > initialCount,
        content,
        now: Date.now(),
        lastContent,
        lastChangeAt,
      });
      lastContent = state.lastContent;
      lastChangeAt = state.lastChangeAt;

      if (state.ready && !isTyping()) {
        clearInterval(interval);
        resolve({
          messageCount: currentCount,
          content,
          duration: Date.now() - startTime,
        });
      }
    }, 500);
  });
}

// 启动
initialize();
