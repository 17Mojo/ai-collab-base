/**
 * L2 观测器的纯逻辑（判定 + 证据组装）
 *
 * 单独拆出来是为了能被单测覆盖——观测器本体要真浏览器 + 真人点击，
 * 没法进 CI。但**判定口径**是最容易写错、又最值钱的部分
 * （它决定「这次真机验证算不算通过」），必须能离线钉住。
 *
 * 这里不含任何浏览器 API，也不含任何写操作。
 */

import { sanitizeText } from "./sanitize.mjs";

/** 采样间隔（毫秒）——与生产 waitForResponse 的 500ms 轮询一致。 */
export const SAMPLE_INTERVAL = 500;

/** 单次采样里正文保留的最大长度（脱敏前）。 */
const MAX_CONTENT_CHARS = 2000;

/**
 * 解析命令行参数。
 *
 * `--i-will-send` 是硬闸门：没有它整个工具拒绝启动。
 * 理由见 l2-send-observer.mjs 顶部——本工具会让人在真站上发一条真实消息，
 * 误跑一次就是一条真实的消息和一个真实的对话。
 *
 * @param {string[]} argv
 * @returns {object}
 */
export function parseArgs(argv) {
  const args = {
    platform: null,
    profileDir: null,
    out: null,
    timeout: 120000,
    locale: "zh-CN",
    channel: "chrome",
    headed: true,
    iWillSend: false,
    prompt: "请用一句话回答：1+1 等于几？",
  };
  for (const raw of argv) {
    if (raw.startsWith("--platform=")) {
      args.platform = raw.slice("--platform=".length).trim();
    } else if (raw.startsWith("--profile-dir=")) {
      args.profileDir = raw.slice("--profile-dir=".length);
    } else if (raw.startsWith("--out=")) {
      args.out = raw.slice("--out=".length);
    } else if (raw.startsWith("--timeout=")) {
      args.timeout = Number(raw.slice("--timeout=".length));
    } else if (raw.startsWith("--locale=")) {
      args.locale = raw.slice("--locale=".length);
    } else if (raw.startsWith("--channel=")) {
      args.channel = raw.slice("--channel=".length);
    } else if (raw.startsWith("--prompt=")) {
      args.prompt = raw.slice("--prompt=".length);
    } else if (raw === "--i-will-send") {
      args.iWillSend = true;
    } else if (raw === "--headless") {
      args.headed = false;
    }
  }
  return args;
}

/**
 * 依据采样时间线判定「生产的等待逻辑会不会成功」。
 *
 * 判定口径与生产 `waitForResponseGeneric` **逐字一致**：
 *   当前消息数 > 初始消息数  且  不在生成中
 *
 * 为什么要重放一遍而不直接看生产结果：
 *   生产结果是黑盒，只能告诉你「成功/失败」。重放能告诉你
 *   「在第几个样本上、因为哪个条件不成立而卡住」——
 *   这才是能指导修选择器的信息。
 *
 * 两者的不一致本身也是有价值的信息，所以 `consistent` 单独记一位。
 *
 * @param {Array<object>} samples - 采样序列
 * @param {object} waitResult - 生产 waitForResponse 的结果
 * @param {number|null} [baselineCount] - 生产等待启动那一刻的消息数
 * @returns {object}
 */
export function buildVerdict(samples, waitResult, baselineCount = null) {
  const usable = samples.filter((s) => typeof s.messageCount === "number");

  // 基准优先用「生产等待启动那一刻」的计数——生产函数就是在那一刻
  // 同步取 initialCount 的。如果改用第一个采样，中间隔了一条消息，
  // 就会得出「没增长」的假结论。
  const initial =
    typeof baselineCount === "number"
      ? baselineCount
      : usable.length
        ? usable[0].messageCount
        : null;

  const grew = initial !== null && usable.some((s) => s.messageCount > initial);
  const typingCleared = usable.some((s) => s.isTyping === false);
  const lastContent = usable.length ? usable[usable.length - 1].lastContent || "" : "";
  const contentNonEmpty = lastContent.trim().length > 0;

  // 「按生产口径重放时间线，第一次同时满足两个条件是在第几个样本」
  let resolveAtIndex = null;
  for (let i = 0; i < usable.length; i += 1) {
    if (usable[i].messageCount > initial && usable[i].isTyping === false) {
      resolveAtIndex = i;
      break;
    }
  }

  const settled = Boolean(waitResult?.settled);
  const prodResult = waitResult?.result || null;

  return {
    initialMessageCount: initial,
    baselineFromProduction: typeof baselineCount === "number",
    countGrew: grew,
    typingCleared,
    contentNonEmpty,
    // 生产代码自己取到的正文是否非空——这是「截图证明不了」的那一环
    productionContentNonEmpty: Boolean(prodResult && (prodResult.content || "").trim().length > 0),
    wouldResolve: resolveAtIndex !== null,
    resolveAtSampleIndex: resolveAtIndex,
    productionWaitSettled: settled,
    productionWaitError: settled ? waitResult?.error || null : null,
    productionWaitMessageCount: prodResult?.messageCount ?? null,
    productionWaitDurationMs: prodResult?.duration ?? null,
    // 生产实际结果与时间线重放是否一致——不一致说明生产实现里有别的因素
    consistent: settled === (resolveAtIndex !== null),
  };
}

/**
 * 组装证据文件。
 *
 * 证据文件要进 git 仓库，所以正文必须脱敏。
 * 脱敏规则见 sanitize.mjs。
 *
 * @param {object} args
 * @returns {object}
 */
export function buildEvidence(args) {
  const samples = (args.samples || []).map((s) => ({
    t: s.t,
    messageCount: s.messageCount ?? null,
    isTyping: s.isTyping ?? null,
    lastContentLength: typeof s.lastContent === "string" ? s.lastContent.length : 0,
    lastContent: typeof s.lastContent === "string" ? sanitizeText(s.lastContent) : "",
    error: s.error || null,
  }));

  const verdict = buildVerdict(args.samples || [], args.waitResult, args.baselineCount ?? null);

  return {
    layer: "L2-send-observer",
    generatedAt: new Date().toISOString(),
    platform: args.platform,
    platformName: args.platformName,
    url: args.url,
    locale: args.locale,
    // 本工具从不自己发消息——这条是给审阅者看的机器可读声明
    sendsMessages: false,
    sentBy: "human-in-browser",
    promptSuggestedToHuman: args.prompt,
    startedAt: args.startedAt,
    finishedAt: new Date().toISOString(),
    sampleIntervalMs: SAMPLE_INTERVAL,
    sampleCount: samples.length,
    sanitized: true,
    samples,
    verdict,
  };
}
