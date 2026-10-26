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
 * 匿名会话 cookie——**未登录时也存在**，因此不能拿来判断「是否已登录」。
 *
 * 2026-10-26 实测踩过：千问匿名访问就会带 `JSESSIONID`，用宽泛的
 * `/session/i` 匹配 cookie 名 → 预热脚本判定「已登录」→ 浏览器在人
 * 还没登录时就被关掉，整轮白跑。
 */
export const ANONYMOUS_SESSION_COOKIES = new Set([
  "jsessionid",
  "phpsessid",
  "session",
  "sessionid",
  "sid",
  "sessid",
  "connect.sid",
]);

/**
 * 判断 cookie 是否属于某个平台。
 *
 * 规则：cookie 的 domain（去掉前导点）等于平台 hostname，
 * 或者是它的**父域**（`.google.com` 之于 `gemini.google.com`）。
 *
 * 为什么需要它：一轮里可能要跑**多个平台**，而登录 cookie 白名单是全局的
 * （`login_aliyunid` / `__Secure-3PSID` 各属一家）。不按域名收窄的话，
 * 「在 A 站上看到 B 站的登录 cookie」就会把 A 站误判成已登录。
 *
 * @param {{domain?: string}} cookie
 * @param {string[]} hostnames
 * @returns {boolean}
 */
export function cookieMatchesHost(cookie, hostnames) {
  const domain = String(cookie?.domain || "").replace(/^\./, "").toLowerCase();
  if (!domain) return false;
  return (hostnames || []).some((h) => {
    const host = String(h || "").toLowerCase();
    if (!host) return false;
    return host === domain || host.endsWith(`.${domain}`);
  });
}

/**
 * 判断是否已登录——**只认白名单里的应用登录 cookie**。
 *
 * 用白名单（而不是正则）是有意的：白名单**在构造上**就不可能把
 * `JSESSIONID` 这类匿名 cookie 判成登录态，而正则会。
 *
 * @param {Array<{name?: string, value?: string, domain?: string}>} cookies
 * @param {string[]} allowedNames - 该站点**自己的**登录 cookie 名
 * @param {string[]} [hostnames] - 平台域名；给了就按域名收窄（多平台时必需）
 * @returns {{name: string, valueLength: number}|null}
 */
export function detectLoginCookie(cookies, allowedNames, hostnames) {
  const allow = new Set((allowedNames || []).map((n) => String(n).toLowerCase()));
  if (allow.size === 0) return null;
  for (const c of cookies || []) {
    const name = String(c.name || "").toLowerCase();
    if (!allow.has(name)) continue;
    if (ANONYMOUS_SESSION_COOKIES.has(name)) continue;
    const value = String(c.value || "");
    if (!value || value.length < 8) continue;
    if (/^(null|undefined|deleted)$/i.test(value)) continue;
    if (hostnames && hostnames.length && !cookieMatchesHost(c, hostnames)) continue;
    return { name: c.name, valueLength: value.length };
  }
  return null;
}

/**
 * 从页面上抓到的语言事实里，判定**界面实际**是哪种语言。
 *
 * 为什么需要它：「en-US 这一轮跑的到底是不是英文界面」不能靠假设。
 * 2026-10-26 实测千问**不认** `Accept-Language`——en-US 那一轮拿到的
 * 仍然是中文界面（发送按钮 `aria=发送消息`），两轮跑的是同一个 DOM。
 * 如果不把「实际观察到的语言」记进证据，「×2 语言」就是自欺。
 *
 * 判定顺序：先看界面文案（有文案比 lang 属性可靠），再看 `document.lang`。
 *
 * @param {{documentLang?: string, sendButtonAria?: string, sendButtonText?: string}} observed
 * @returns {"zh"|"en"|"unknown"}
 */
export function classifyObservedLanguage(observed) {
  const cjk = /[一-鿿]/;
  const texts = [observed?.sendButtonAria, observed?.sendButtonText]
    .filter((t) => typeof t === "string" && t.trim())
    .join(" ");
  if (texts) {
    if (cjk.test(texts)) return "zh";
    if (/[a-z]/i.test(texts)) return "en";
  }
  const lang = String(observed?.documentLang || "").toLowerCase();
  if (lang.startsWith("zh")) return "zh";
  if (lang.startsWith("en")) return "en";
  return "unknown";
}

/**
 * 判定「实际界面语言」与「要求的 locale」是否不一致。
 *
 * @param {string} requestedLocale - 例如 "en-US"
 * @param {object} observed
 * @returns {boolean|null} null = 观察不出来（不算不一致）
 */
export function isLocaleMismatch(requestedLocale, observed) {
  const req = String(requestedLocale || "").toLowerCase();
  if (!req) return null;
  const primary = req.split("-")[0];
  const actual = classifyObservedLanguage(observed);
  if (actual === "unknown") return null;
  return actual !== primary;
}


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
    locales: [],
    channel: "chrome",
    headed: true,
    iWillSend: false,
    prompt: "请用一句话回答：1+1 等于几？",
    // 登录等待：见 l2-send-observer.mjs 的「一个浏览器跑完整轮」说明
    waitForLogin: false,
    loginFlag: null,
    loginCookieNames: [],
    loginTimeout: 900000,
    platformLocales: [],
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
    } else if (raw.startsWith("--locales=")) {
      args.locales = raw
        .slice("--locales=".length)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (raw.startsWith("--channel=")) {
      args.channel = raw.slice("--channel=".length);
    } else if (raw.startsWith("--prompt=")) {
      args.prompt = raw.slice("--prompt=".length);
    } else if (raw.startsWith("--login-flag=")) {
      args.loginFlag = raw.slice("--login-flag=".length);
    } else if (raw.startsWith("--login-cookie=")) {
      args.loginCookieNames = raw
        .slice("--login-cookie=".length)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (raw.startsWith("--platform-locales=")) {
      // 形如 qianwen:zh-CN,gemini:en-US——一个浏览器里按平台各自跑一种语言。
      // 为什么不直接用 --platform + --locales 的笛卡尔积：那会变成 2×2=4 次
      // 人工发送，而实际需要的是「每个平台挑一种它真有语言差异的语言」。
      args.platformLocales = raw
        .slice("--platform-locales=".length)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((entry) => {
          const [platform, locale] = entry.split(":").map((s) => (s || "").trim());
          return { platform, locale: locale || "zh-CN" };
        });
    } else if (raw.startsWith("--login-timeout=")) {
      args.loginTimeout = Number(raw.slice("--login-timeout=".length));
    } else if (raw === "--wait-for-login") {
      args.waitForLogin = true;
    } else if (raw === "--i-will-send") {
      args.iWillSend = true;
    } else if (raw === "--headless") {
      args.headed = false;
    }
  }
  return args;
}

/**
 * 本轮要跑哪几个 locale。
 *
 * `--locales=a,b` 存在时用它，否则退回单个 `--locale`。
 *
 * @param {object} args
 * @returns {string[]}
 */
export function resolveLocales(args) {
  return args.locales && args.locales.length ? [...args.locales] : [args.locale];
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

  // 实际观察到的界面语言。**不能靠 locale 参数推断**——站点认不认
  // Accept-Language 是站点自己的事（千问就不认）。
  const observed = args.observed || null;
  const observedLanguage = observed ? classifyObservedLanguage(observed) : "unknown";
  const localeMismatch = observed ? isLocaleMismatch(args.locale, observed) : null;

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
    observed,
    samples,
    verdict: { ...verdict, observedLanguage, localeMismatch },
  };
}
