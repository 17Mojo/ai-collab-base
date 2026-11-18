/**
 * 平台冻结守卫 —— 把用户 2026-11-11 的红线落成**代码级**约束。
 *
 * 红线原文：「仅保留 qianwen、yuanbao、chatglm、yiyan、kimi 平台，
 * 其他都暂时冻结不去碰。」
 *
 * 2026-11-18 用户改判：千问有防范非人类操作机制，**活跃白名单中的 qianwen
 * 换成 stepfun**（https://studio.stepfun.com/，真人已登录）。qianwen 的
 * 生产 adapter 保留，但本轮真机不再碰它；deepseek / longcat 仍冻结。
 * 下面的红线注释保留原文，便于对账「谁在什么时候改过白名单」。
 *
 * 同日第二次裁定（N25 收口）：deepseek / longcat 真机 A/B 只跑了 deepseek
 * 两轮（A/B 都撞在 step_5，fresh_session 在 step_8 未获触发机会），用户据
 * 现场反自动化判断裁定停止并收口，两站**降级为目标源外平台**。本文件把
 * 它们从活跃白名单排除的事实不变；「目标源外」是治理定性，不通过改白名单
 * 常量或 adapter 表达——避免动到变异锚点。详见
 * collaboration/results/RESULT-N25-AB-2026-11-18.md。
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
  "stepfun",
  "yuanbao",
  "chatglm",
  "yiyan",
  "kimi",
]);

/** 本轮 A/B 待验证、但当前**冻结**的样本（写进方案，不许跑）。 */
export const FROZEN_AB_PLATFORMS = Object.freeze(["deepseek", "longcat"]);

/**
 * 本轮真机 A/B 的**实验对象**——与上面的「冻结样本集」是两件事，别再混用。
 *
 * ## 为什么要拆成两个常量（B1，2026-11-19）
 *
 * 此前 `session-wall-ab.mjs` 直接读 `FROZEN_AB_PLATFORMS` 生成计划。后果是：
 * 一旦解冻 deepseek，`FROZEN_AB_PLATFORMS` 会缩成 `["longcat"]`，
 * **A/B 的实验对象跟着被静默改掉**——计划从「2 站 × 2 变体 = 4 轮」变成 2 轮，
 * 而没有任何东西会说「这是实验设计变了，还是治理状态变了」。
 * 改一个常量同时改了两件事，这是耦合，不是简洁。
 *
 * ## 两个常量各自表达什么
 *
 *   FROZEN_AB_PLATFORMS  治理事实：哪些站被冻结、且曾经是 A/B 样本（会被解冻影响）
 *   AB_PLATFORMS         实验设计：这一轮 A/B 要跑哪些站（由实验进度决定）
 *
 * 不变式（`session-wall-ab.test.mjs` 守着）：**AB_PLATFORMS ⊆ FROZEN_AB_PLATFORMS**。
 * 这条红线是「不许拿活跃站当 A/B 实验对象」——活跃站是交付源，实验会扰动它。
 * 拆开之后，解冻 deepseek 会让**这条断言**说话（要么把 deepseek 移出实验对象，
 * 要么解释为什么它还能实验），而不是让计划悄悄少两轮命令。
 *
 * ## 当前为什么只有 longcat
 *
 *   - **deepseek 的 A/B 已结案**：2026-11-11/12 两轮真机回执齐全，step_8 撞墙
 *     4×180s 的形态已定性；用户 2026-11-18 据现场反自动化判断裁定停止收口（N25），
 *     deepseek 降级为目标源外平台。它的回执与计划留在 evidence/ 里当历史，不再「待跑」。
 *   - **longcat 仍待跑**：2026-11-12 的两轮是**无效**数据——`ab2-no-boundary` 第 3 步
 *     就失败（3 步里只成功 2 步），`ab2-with-boundary` 虽然跑完 8 步，但
 *     `sessionResets[0] = {available:false, strategy:"none"}`（本站 adapter 没有声明
 *     newChat，重置根本没发生）⇒ 两组不具备可比性，不能拿来判命题。
 *     本站至今只有只读预检，没有有效 A/B 数据（N56 记的残留失败也在这里）。
 *
 * ## 改它的时候要一起改什么
 *
 *   - 加站：必须同时确认它在 `FROZEN_AB_PLATFORMS` 里（否则子集断言红），
 *     并想清楚额度（每站 × 2 变体 × 8 步 = 16 步真实发送）。
 *   - 解冻某站：先把它从**这里**移出，再改 `FROZEN_AB_PLATFORMS` 与 `ACTIVE_PLATFORM_IDS`。
 *   - 顺序反了会红——这正是要的效果：让「实验对象变了」成为一次**显式决定**。
 */
export const AB_PLATFORMS = Object.freeze(["longcat"]);

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

/**
 * 是否应当打出「冻结平台已按 ALLOW_FROZEN=1 放行」这条留痕日志（N35）。
 *
 * ## 为什么单独成一个函数
 *
 * 原实现是 `if (!policy.active)`——拿「是否活跃」当「是否已解冻」的代理。
 * PRECHECK 模式下 PLATFORM 默认仍是已被移出白名单的 qianwen，于是
 * active=false、unfrozenBy=null、ALLOW_FROZEN 也没设，却打出
 * 「⚠️ 冻结平台已按 ALLOW_FROZEN=1 放行: qianwen」——一句与事实相反的日志，
 * 而预检其实只打开 CANDIDATES，压根没碰 qianwen。
 *
 * 这条日志是「谁在什么时候解冻过」的唯一运行时线索，假报会污染解冻审计，
 * 所以判据要能单测，不能埋在脚本里。
 *
 * ## 两个条件都要
 *
 * 1. `precheck` 为真时一律不打：预检不打开 PLATFORM，对该平台做任何断言都无依据；
 * 2. `unfrozenBy` 必须是**非空字符串**。注意不能用 `!== null`：字段缺失时
 *    `undefined !== null` 为真，会把「没有该字段」误当成「已解冻」。
 *
 * @param {{unfrozenBy?: string|null}|null|undefined} policy
 * @param {{precheck?: boolean}} [opts]
 * @returns {boolean}
 */
export function shouldAnnounceUnfreeze(policy, opts = {}) {
  if (opts.precheck === true) return false;
  return typeof policy?.unfrozenBy === "string" && policy.unfrozenBy.length > 0;
}
