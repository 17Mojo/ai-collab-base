/**
 * 失败语义分流（台账 N21 的根治）
 *
 * ## 缺陷长什么样
 *
 * `_executeStep` 的 catch 里有一段**不看错误语义**的重试：
 * 失败了就再跑一遍这一步。对 AI 步骤来说，「再跑一遍」= 把同一句提示词
 * **再发一次**。
 *
 * 于是 `Response timeout` 这种失败被重试放大成灾难：
 *
 *   - 超时的语义是「**已经发出去了**，只是没等到回复」——不是「没发出去」。
 *   - 重发于是让会话里留下**重复提问**，AI 也会再答一遍（烧双倍额度）。
 *   - 2026-11-11 chatglm 的耗时指纹就是这么读出来的：
 *     step_2 用了 170.7s（≈60+60+50.7）、step_7 用了 151.3s（≈60+60+31.3），
 *     errors 却是空的 ⇒ 中途至少重发过一次，只是重发后碰巧等到了回复。
 *
 * ## 修法
 *
 * 超时**不重发**，改「续等」：让页面继续盯着同一个会话等，而不是再问一遍。
 * 判据必须来自**语义**（错误码），不能来自「是否抛错」这种形状——
 * 因为可重试的失败（输入框没找到、页面没适配）和不可重试的失败（超时）
 * 在形状上一模一样，都是一次 throw。
 *
 * 老路径（`adapter-utils.js` 的 `label: Response timeout`）没设错误码，
 * 所以留一条**收窄的**文案兜底：只认整串以 `Response timeout` 结尾的，
 * 不做子串包含——否则一句「Response timeout 后我改了选择器」会被误判。
 */

/** 分流结果 */
export const FAILURE_STRATEGY = {
  /** 已经发出去了但没等到 ⇒ 继续等同一个会话，**不许重发** */
  RESUME_WAIT: "resume-wait",
  /** 没送出去 / 送出去之前就失败了 ⇒ 重跑这一步是安全的 */
  RETRY: "retry",
  /** 重试也没用，直接失败（配置错误、前置条件不满足） */
  FAIL: "fail",
};

/** 内容脚本在等回复超时时使用的错误码（content-script.js） */
export const RESPONSE_TIMEOUT_CODE = "RESPONSE_TIMEOUT";

/**
 * 老路径的文案兜底：形如 `"千问: Response timeout"` 或 `"Response timeout"`。
 * 用 `$` 锚尾，且要求前面是开头或 `": "`，避免子串误伤。
 */
const LEGACY_TIMEOUT_RE = /(?:^|: )Response timeout$/;

/**
 * 判断这个失败该怎么处理。
 *
 * @param {Error & {code?: string}} error
 * @returns {string} FAILURE_STRATEGY 之一
 */
export function failureStrategy(error) {
  if (!error) return FAILURE_STRATEGY.RETRY;

  // 1. 语义优先：有错误码就只信错误码
  if (error.code === RESPONSE_TIMEOUT_CODE) return FAILURE_STRATEGY.RESUME_WAIT;

  // 2. 确定性的配置类失败：重试只是白等
  if (error.code === "MISSING_REQUIRED_FIELDS") return FAILURE_STRATEGY.FAIL;

  // 3. 老路径兜底（没有错误码，只有文案）
  const msg = typeof error.message === "string" ? error.message : "";
  if (LEGACY_TIMEOUT_RE.test(msg)) return FAILURE_STRATEGY.RESUME_WAIT;

  return FAILURE_STRATEGY.RETRY;
}

/**
 * 「续等」时要用哪个基准条数。
 *
 * ## 为什么这件事必须钉住
 *
 * `handleWaitForResponse` 的完成判据里有 `countGrew: currentCount > initialCount`。
 * 续等如果重新快照一次 `initialCount`，而 AI 的回复恰好在超时之后、续等开始之前
 * 落到了页面上，那么：
 *
 *   initialCount = 已经包含回复的条数
 *   currentCount = 同一批条数
 *   ⇒ countGrew 恒为 false ⇒ 永远等不到 ready ⇒ 续等白等满一个超时窗口
 *
 * 也就是说：**续等必须沿用发送前那个基准**，不能重新数。这个函数把
 * 「用哪个数」这件事收成一处，免得下次改动又把它写成 `findElements(...).length`。
 *
 * @param {number} snapshotCount - 续等开始时现场数到的条数
 * @param {number|undefined|null} baselineCount - 发送前记录的基准条数
 * @returns {number}
 */
export function resolveInitialCount(snapshotCount, baselineCount) {
  if (Number.isInteger(baselineCount) && baselineCount >= 0) return baselineCount;
  return snapshotCount;
}
