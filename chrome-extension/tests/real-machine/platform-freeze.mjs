/**
 * 平台冻结守卫 —— 把用户 2026-11-11 的红线落成**代码级**约束。
 *
 * 红线原文：「仅保留 qianwen、yuanbao、chatglm、yiyan、kimi 平台，
 * 其他都暂时冻结不去碰。」
 *
 * ## 为什么必须是代码，不能只是报告里的一句话
 *
 * 真机驱动 `l2-platform-auto.mjs` 只要给一个 `PLATFORM=deepseek` 就会照跑：
 * 启动浏览器 → 打开站点 → 导入 Pack → 真实发消息。报告里写「冻结了」
 * 挡不住环境变量。上一个同类教训是「探针只读」——注释写了红线，
 * 谁加一行 click 也不会红（N23）。所以这里同样配单测 + 变异锚。
 *
 * ## 「不去碰」的边界
 *
 * 预检（PRECHECK）虽然不发包，但**会打开页面**，也算「碰」。
 * 因此守卫同时管 `PLATFORM`（L2）与 `CANDIDATES`（PRECHECK），
 * 且必须在 `launch()` **之前**执行——连浏览器都不为冻结站启动。
 *
 * ## 唯一事实源
 *
 * `ACTIVE_PLATFORM_IDS` 是白名单唯一事实源。别处不许再抄一份；
 * 生产平台清单 `tests/platforms.mjs` 管「有哪些平台」，本文件管
 * 「这一轮允许碰哪些」，两者刻意分离。
 *
 * ## 解冻
 *
 * 只有一个显式开关 `ALLOW_FROZEN=1`，且必须由**用户明确授权**后才能在
 * 命令行里加。放行时返回 `unfrozenBy`，调用方须写进回执留痕——
 * 「谁在什么时候解冻过」要能从磁盘复核，不能靠聊天记录。
 */

/** 当前允许真机动作的 5 个活跃平台（顺序无关，别处不许复制）。 */
export const ACTIVE_PLATFORM_IDS = Object.freeze([
  "qianwen",
  "yuanbao",
  "chatglm",
  "yiyan",
  "kimi",
]);

/** 本轮 A/B 待验证、但当前**冻结**的样本（写进方案，不许跑）。 */
export const FROZEN_AB_PLATFORMS = Object.freeze(["deepseek", "longcat"]);

export function isPlatformActive(id) {
  return ACTIVE_PLATFORM_IDS.includes(id);
}

/**
 * 判定单个平台能否动作。不抛错，便于调用方留痕 / 写回执。
 * @param {string} id
 * @param {{allowFrozen?: boolean}} [opts]
 * @returns {{allowed: boolean, active: boolean, unfrozenBy: string|null, reason: string}}
 */
export function evaluatePlatformPolicy(id, opts = {}) {
  const active = isPlatformActive(id);
  if (active) {
    return { allowed: true, active: true, unfrozenBy: null, reason: "active" };
  }
  if (opts.allowFrozen === true) {
    return {
      allowed: true,
      active: false,
      unfrozenBy: "ALLOW_FROZEN=1",
      reason: "frozen-but-explicitly-unfrozen",
    };
  }
  return {
    allowed: false,
    active: false,
    unfrozenBy: null,
    reason: "frozen-by-user-redline",
  };
}

/**
 * 硬闸门：冻结平台直接抛错，别给调用方「catch 掉继续跑」的机会。
 * @param {string} id
 * @param {{allowFrozen?: boolean}} [opts]
 * @returns {{allowed: boolean, active: boolean, unfrozenBy: string|null, reason: string}}
 */
export function assertPlatformAllowed(id, opts = {}) {
  const policy = evaluatePlatformPolicy(id, opts);
  if (!policy.allowed) {
    throw new Error(
      `平台 ${id} 已冻结（用户 2026-11-11 红线：仅保留 ${ACTIVE_PLATFORM_IDS.join(" / ")}）。` +
        " 本脚本不会为它启动浏览器、打开页面、导入 Pack 或发消息。" +
        " 需用户明确解冻后才可用 ALLOW_FROZEN=1 放行。",
    );
  }
  return policy;
}

/**
 * 候选集逐个过闸：只要有一个冻结平台就整体拒绝。
 * 不做「跳过冻结站、其余继续」的半吊子放行——那会让预检回执看起来
 * 像是「这轮只测了这些站」，掩盖了本轮其实想跑冻结站的事实。
 * @param {string[]} ids
 * @param {{allowFrozen?: boolean}} [opts]
 */
export function assertCandidatesAllowed(ids, opts = {}) {
  const frozen = ids.filter((id) => !isPlatformActive(id));
  if (frozen.length > 0 && opts.allowFrozen !== true) {
    throw new Error(
      `候选集含冻结平台 [${frozen.join(", ")}]（用户 2026-11-11 红线：仅保留 ` +
        `${ACTIVE_PLATFORM_IDS.join(" / ")}）。预检也会打开页面，所以同样不许碰。` +
        " 需用户明确解冻后才可用 ALLOW_FROZEN=1 放行。",
    );
  }
  return ids.map((id) => ({ id, ...evaluatePlatformPolicy(id, opts) }));
}
