/**
 * 等待与内容质量策略（纯函数，无 DOM）。
 *
 * ## 为什么存在（2026-11-04 L2 真机实锤）
 *
 * 千问真机首跑（8 步 Pack）里，`handleWaitForResponse` 的旧判据是
 * 「消息数增加 且 不在生成中」——而千问流式期间的真实生成中信号
 * （「努力工作中 用时N秒」）不在 typing 选择器里 ⇒ 每一步都在回复
 * **刚开口**（'收到，'）时就被判「完成」，7 条提示词在生成结束前
 * 就发了出去，产物全是流式开头碎片。docs §6.2 #3 预警的
 * 「太早成功」在真机上兑现。
 *
 * 修法是把「完成」的定义从「看起来不在打字」换成
 * **「内容自己稳住了」**：正文连续一段窗口（默认 4 秒）不再变化
 * 才算生成结束。站点指示器会改版漂移，文本稳定不会。
 *
 * 同一模块还管 ③：AI 步骤取回的正文必须够长度才算可用——
 * 碎片/空串一律判失败，不许再让 '收到，' 冒充回复。
 *
 * 之所以抽成纯函数：这两条判据是「提前返回」缺陷的最后两道闸，
 * 必须能被单测钉死、被变异检查证伪（见 tests/wait-policy.test.mjs
 * 与 tests/real-machine/mutation-check.mjs）。
 */

/** 内容稳定多久才算「生成结束」（毫秒）。 */
// 8 秒（2026-11-04 第二轮）：4 秒在千问「努力工作中」思考停顿期会被误判成
// 生成结束——ack 句定格 4 秒后停顿还在继续，正文还没流出来。
// 8 秒是停顿泄漏的兜底，根修是认出「努力工作中」状态行（见 qianwen-adapter）。
export const STABLE_MS_DEFAULT = 8000;

/** AI 步骤可接受的最短回复长度（字符，trim 后计）。 */
// 50（2026-11-04 第二轮）：20 分不开 ack 与正文——真机第二轮里 ack 句带主题词
// 有 20–26 字，还混入「正在思考中」状态条文本到 25–41 字，全部压线过 20 的闸。
// 真正文 100–300 字；预期短产出的步骤（如一句话开头）用
// `step.config.min_output_length` 按步放宽。
export const MIN_AI_CONTENT_LENGTH_DEFAULT = 50;

/**
 * 「新回复落地」的**内容型**增长信号 —— 虚拟列表平台的 countGrew 替代。
 *
 * ## 为什么需要（2026-11-12 冻结站 A/B 4 轮实测）
 *
 * deepseek / longcat 用虚拟列表，长会话时旧回答会被卸载：发送前数到 N 条，
 * 新回答渲染时滚掉一条老的，计数仍是 N ⇒ `currentCount > initialCount` 恒 false
 * ⇒ `sampleWaitState` 永远不 ready，AI 明明答完也判 Response timeout
 * （4 轮实测失败步骤全是 723.x s = 4×180s，跨两站同型，与 fresh_session 无关）。
 *
 * 这类页面里真正稳定的信号是**最新一条正文的文本**：发送前记录 baseline，
 * 新回答落地后文本必然不同。仍保留 `stable`（正文连续 8 秒不变）与
 * 「空文本永不判完成」两道闸，所以不会退回「流式开头碎片冒充回复」。
 *
 * 只认「变了且非空」：旧回答一直没变时 `text === base` ⇒ false，
 * 不会像「消息组换一批元素」那样把旧回答误当新回复取走。
 *
 * @param {string} content - 本次采样取到的最新正文
 * @param {string} baselineContent - 发送前记录的最新正文（空串表示新会话）
 * @returns {boolean}
 */
export function contentGrew(content, baselineContent) {
  const text = typeof content === "string" ? content.trim() : "";
  const base = typeof baselineContent === "string" ? baselineContent.trim() : "";
  return text.length > 0 && text !== base;
}

/**
 * 哪些平台启用「内容型增长信号」。
 *
 * **这是一张按实测证据开的白名单，不是默认行为**：只有 2026-11-11~12 冻结站
 * A/B 四轮实测里确证「AI 答完但计数不涨」的两个站（及其域名别名）在表内。
 * 其它平台一律沿用原来的 `countGrew`——已跑绿的 5 个活跃站行为一个字节都不变。
 * 要把新平台加进来，必须有该平台的真机假超时证据；未经实测不得晋升为默认值。
 */
export const CONTENT_GROWTH_PLATFORM_IDS = Object.freeze([
  "chat.deepseek.com",
  "longcat.chat",
  "longcat.ai",
]);

/**
 * @param {string} platformId - content-script 的 currentPlatformId（hostname）
 * @returns {boolean} 是否记录「发送前最新正文」并启用内容型增长信号
 */
export function shouldTrackBaselineContent(platformId) {
  return CONTENT_GROWTH_PLATFORM_IDS.includes(platformId);
}

/**
 * 「有新回复落地」的增长信号：计数通道 OR 内容通道。
 *
 * 内容通道**只在显式给了字符串基准时启用**。这条护栏不能省：老调用方
 * （已有的 300+ 单测、`WAIT_FOR_RESPONSE` 的老信封）没有 baselineContent，
 * 若把它们也切到「正文非空就算变了」，就等于把「静止的旧消息」判成新回复，
 * 直接退回 N21 之前的「太早成功」。宁可少救一个站，也不许静默放宽全局判据。
 *
 * @param {Object} signal
 * @param {boolean} signal.countGrew - 消息数是否比发送前增长
 * @param {string} signal.content - 最新一条正文
 * @param {string|null|undefined} signal.baselineContent - 发送前记录的最新正文
 * @returns {boolean}
 */
export function hasNewReply({ countGrew, content, baselineContent }) {
  if (countGrew) return true;
  if (typeof baselineContent !== "string") return false;
  return contentGrew(content, baselineContent);
}

/**
 * 采样一次等待状态（内容稳定性判据）。
 *
 * 判据（全部满足才 `ready`）：
 *   1. 有新回复落地（`hasNewReply`：计数增长，或**有基准时**正文相对发送前变了）；
 *   2. 最新正文**非空**（空串/纯空白永不判完成——那是「还没开始流」）；
 *   3. 正文已经连续 `stableMs` 毫秒没有变化（流式生成中内容持续在变）。
 *
 * @param {Object} state
 * @param {boolean} state.countGrew - 消息数是否比发送前有增长
 * @param {string} state.content - 最新一条消息的正文
 * @param {number} state.now - 本次采样时刻（毫秒）
 * @param {string|null} [state.baselineContent] - 发送前的最新正文（没给就只认计数增长）
 * @param {string|null} [state.lastContent] - 上次记录的正文
 * @param {number|null} [state.lastChangeAt] - 正文最后一次变化的时刻
 * @param {number} [stableMs] - 稳定窗口
 * @returns {{lastContent: string|null, lastChangeAt: number|null, ready: boolean}}
 */
export function sampleWaitState(state, stableMs = STABLE_MS_DEFAULT) {
  const {
    countGrew,
    content,
    now,
    baselineContent = null,
    lastContent = null,
    lastChangeAt = null,
  } = state;
  const text = typeof content === "string" ? content.trim() : "";

  // 空文本也照常跟踪变化时刻——「空内容永不判完成」只靠下面
  // stable 里的 `text.length > 0` 这**一处**守卫（单点才杀得死变异）。
  let nextLastContent = lastContent;
  let nextLastChangeAt = lastChangeAt;
  if (text !== lastContent) {
    nextLastContent = text;
    nextLastChangeAt = now;
  }

  const stable =
    text.length > 0 && nextLastChangeAt != null && now - nextLastChangeAt >= stableMs;

  return {
    lastContent: nextLastContent,
    lastChangeAt: nextLastChangeAt,
    ready: hasNewReply({ countGrew, content, baselineContent }) && stable,
  };
}

/**
 * AI 步骤取回的正文是否可用（够长，不是流式开头碎片）。
 *
 * @param {string} content - 取回的正文
 * @param {number} [minLen] - 最短长度（默认 {@link MIN_AI_CONTENT_LENGTH_DEFAULT}）
 * @returns {boolean}
 */
export function isUsableAIContent(content, minLen = MIN_AI_CONTENT_LENGTH_DEFAULT) {
  const text = typeof content === "string" ? content.trim() : "";
  return text.length >= minLen;
}
