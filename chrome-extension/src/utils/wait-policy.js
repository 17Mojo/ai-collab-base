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
export const STABLE_MS_DEFAULT = 4000;

/** AI 步骤可接受的最短回复长度（字符，trim 后计）。 */
export const MIN_AI_CONTENT_LENGTH_DEFAULT = 20;

/**
 * 采样一次等待状态（内容稳定性判据）。
 *
 * 判据（全部满足才 `ready`）：
 *   1. 消息数比发送前有增长（`countGrew`）；
 *   2. 最新正文**非空**（空串/纯空白永不判完成——那是「还没开始流」）；
 *   3. 正文已经连续 `stableMs` 毫秒没有变化（流式生成中内容持续在变）。
 *
 * @param {Object} state
 * @param {boolean} state.countGrew - 消息数是否比发送前有增长
 * @param {string} state.content - 最新一条消息的正文
 * @param {number} state.now - 本次采样时刻（毫秒）
 * @param {string|null} [state.lastContent] - 上次记录的正文
 * @param {number|null} [state.lastChangeAt] - 正文最后一次变化的时刻
 * @param {number} [stableMs] - 稳定窗口
 * @returns {{lastContent: string|null, lastChangeAt: number|null, ready: boolean}}
 */
export function sampleWaitState(state, stableMs = STABLE_MS_DEFAULT) {
  const { countGrew, content, now, lastContent = null, lastChangeAt = null } = state;
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
    ready: Boolean(countGrew) && stable,
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
