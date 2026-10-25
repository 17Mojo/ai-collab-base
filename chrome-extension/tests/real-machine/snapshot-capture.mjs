/**
 * 真实 DOM 快照采集器（B-2）
 *
 * 用途：把**真实站点**的 DOM 采下来，存成「带 data-role 标注的 HTML 片段」，
 * 让模拟层的 fixture 不再是**手写的假 DOM**，而是「从真机上拍下来的、经过
 * 脱敏的、按生产 adapter 的实际命中结果标注过的」快照。
 *
 * 为什么值得做：
 *   模拟层矩阵长期全绿，但它守的是**手写 fixture**——手写 fixture 天然
 *   「让选择器能命中」。2026-10-25 真机实测抓到的 Gemini 缺陷就是
 *   「fixture 说命中、真机上不命中」。真实快照把「真机长什么样」变成
 *   可版本控制的证据，矩阵从此有了一个**不依赖手写**的守护对象。
 *
 * 两条红线：
 *   1. **只读**：不注入文本、不点发送、不消耗账号额度。
 *   2. **必须脱敏**：进 git 的东西不能带个人信息和令牌。见 sanitize.mjs。
 *
 * 「采不到就写原因」：每家平台都会产出一条记录，成功是 pass，
 * 失败是 login_wall / bot_check / unreachable——**没采到不等于失败，
 * 但必须留下原因**，否则「采不到」会悄悄变成「没人管」。
 *
 * 用法：
 *   node tests/real-machine/snapshot-capture.mjs
 *   node tests/real-machine/snapshot-capture.mjs --platform=gemini,qianwen
 *   node tests/real-machine/snapshot-capture.mjs --out-dir=tests/real-machine/fixtures/real
 *   node tests/real-machine/snapshot-capture.mjs --locale=zh-CN
 *   node tests/real-machine/snapshot-capture.mjs --headed
 *
 * 退出码：0 = 至少采到一家；1 = 一家都没采到；2 = 采集器自身异常。
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

import { PLATFORMS } from "../platforms.mjs";
import { injectAdapter } from "./_bundle.mjs";
import { sanitizeHtmlPretty, sanitizeText } from "./sanitize.mjs";
import { assessMessageCountModel } from "./message-model.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "../..");
const DEFAULT_OUT_DIR = join(HERE, "fixtures", "real");

/** 登录墙特征。 */
const LOGIN_WALL_SELECTORS = [
  'input[type="password"]',
  'a[href*="login"]',
  'a[href*="signin"]',
  'a[href*="auth"]',
  'button[data-testid*="login"]',
];

/** 人机校验文案（必须覆盖多语言——Cloudflare 拦截页按浏览器语言出文案）。 */
const BOT_CHECK_MARKERS = [
  "just a moment",
  "checking your browser",
  "verify you are human",
  "enable javascript and cookies",
  "attention required",
  "unusual traffic",
  "performing security verification",
  "请稍候",
  "安全验证",
  "正在进行安全验证",
  "验证您不是自动程序",
  "自动程序",
  "请稍等",
  "ray id",
  "cloudflare",
];

/** 人机校验的 DOM 签名——比文案更稳。 */
const BOT_CHECK_SELECTORS = [
  "#challenge-form",
  "#cf-challenge-running",
  "#challenge-running",
  'iframe[src*="challenges.cloudflare.com"]',
  'div[data-translate="checking_browser"]',
];

/** 被判定为人机校验的 HTTP 状态码。 */
const BOT_CHECK_HTTP_STATUS = new Set([403, 429, 503]);

function parseArgs(argv) {
  const args = {
    platforms: null,
    headed: false,
    outDir: DEFAULT_OUT_DIR,
    timeout: 30000,
    composerWait: 20000,
    settleTimeout: 8000,
    settleDelay: 2000,
    locale: null,
    channel: "chrome",
  };
  for (const raw of argv) {
    if (raw.startsWith("--platform=")) {
      args.platforms = raw
        .slice("--platform=".length)
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (raw === "--headed") {
      args.headed = true;
    } else if (raw.startsWith("--out-dir=")) {
      args.outDir = resolve(raw.slice("--out-dir=".length));
    } else if (raw.startsWith("--timeout=")) {
      args.timeout = Number(raw.slice("--timeout=".length));
    } else if (raw.startsWith("--composer-wait=")) {
      args.composerWait = Number(raw.slice("--composer-wait=".length));
    } else if (raw.startsWith("--settle-timeout=")) {
      args.settleTimeout = Number(raw.slice("--settle-timeout=".length));
    } else if (raw.startsWith("--settle-delay=")) {
      args.settleDelay = Number(raw.slice("--settle-delay=".length));
    } else if (raw.startsWith("--locale=")) {
      args.locale = raw.slice("--locale=".length);
    } else if (raw.startsWith("--channel=")) {
      args.channel = raw.slice("--channel=".length);
    }
  }
  return args;
}

/**
 * 在页面上判定环境状态：登录墙 / 人机校验 / 正常。
 * @param {import('playwright').Page} page
 * @returns {Promise<{state: string, signal: string|null}>}
 */
async function classifyEnvironment(page) {
  const dom = await page.evaluate(
    ({ wallSelectors, botSelectors, markers }) => {
      const bodyText = (document.body?.innerText || "").toLowerCase();
      const botDom = botSelectors.find((sel) => {
        try {
          return document.querySelector(sel) !== null;
        } catch {
          return false;
        }
      });
      if (botDom) return { state: "bot_check", signal: botDom };
      const marker = markers.find((m) => bodyText.includes(m.toLowerCase()));
      if (marker) return { state: "bot_check", signal: `text:${marker}` };
      const wall = wallSelectors.find((sel) => {
        try {
          return document.querySelector(sel) !== null;
        } catch {
          return false;
        }
      });
      if (wall) return { state: "login_wall", signal: wall };
      return { state: "ok", signal: null };
    },
    {
      wallSelectors: LOGIN_WALL_SELECTORS,
      botSelectors: BOT_CHECK_SELECTORS,
      markers: BOT_CHECK_MARKERS,
    },
  );
  return dom;
}

/**
 * 采集一页真实 DOM 里，生产 adapter 实际能找到的东西。
 *
 * **标注规则**：用生产 adapter 的**真实命中结果**打 data-role——
 *   data-role="chat-input"  → getChatInput() 命中的那个元素
 *   data-role="send-button" → getSendButton() 命中的那个元素
 *   data-role="message"     → getMessageList() 命中的每个元素
 *
 * 这样模拟层矩阵对真实快照跑时，判定的是**同一份标注**，
 * 而标注本身来自生产代码的实测行为，不是人手写上去的。
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId
 */
async function captureDom(page, platformId) {
  return page.evaluate((adapterId) => {
    const registry = window.__PROBE_ADAPTERS__ || {};
    const mod = registry[adapterId];
    if (!mod || !mod.default) {
      return { error: "adapter bundle 未注入页面" };
    }

    let adapter;
    try {
      adapter = new mod.default();
    } catch (e) {
      return { error: `adapter 实例化失败：${e.message}` };
    }

    const out = { error: null };
    let chatInputEl = null;
    let sendButtonEl = null;
    let messageEls = [];

    // —— 输入框 ——
    try {
      const input = adapter.getChatInput();
      chatInputEl = input;
      out.chatInput = input
        ? {
            found: true,
            tag: input.tagName.toLowerCase(),
            className: typeof input.className === "string" ? input.className : "",
            html: input.outerHTML || "",
            // 往上取 3 层祖先——fixture 需要足够的上下文才能体现选择器依赖的结构
            ancestors: (() => {
              const list = [];
              let el = input.parentElement;
              for (let i = 0; i < 3 && el; i += 1) {
                list.push({
                  tag: el.tagName.toLowerCase(),
                  className: typeof el.className === "string" ? el.className : "",
                  html: (el.outerHTML || "").slice(0, 4000),
                });
                el = el.parentElement;
              }
              return list;
            })(),
          }
        : { found: false };
    } catch (e) {
      out.chatInput = { found: false, error: e.message };
    }

    // —— 发送按钮 ——
    try {
      const btn = adapter.getSendButton();
      sendButtonEl = btn;
      out.sendButton = btn
        ? {
            found: true,
            tag: btn.tagName.toLowerCase(),
            className: typeof btn.className === "string" ? btn.className : "",
            html: btn.outerHTML || "",
          }
        : { found: false };
    } catch (e) {
      out.sendButton = { found: false, error: e.message };
    }

    // —— 消息列表 ——
    try {
      const messages = adapter.getMessageList();
      const arr = Array.isArray(messages) ? messages : Array.from(messages || []);
      messageEls = arr;
      out.messageList = {
        found: arr.length > 0,
        count: arr.length,
        samples: arr.slice(0, 5).map((el) => ({
          tag: el.tagName.toLowerCase(),
          className: typeof el.className === "string" ? el.className : "",
          text: (el.innerText || el.textContent || "").slice(0, 200),
          html: (el.outerHTML || "").slice(0, 2000),
        })),
      };
    } catch (e) {
      out.messageList = { found: false, error: e.message };
    }

    // —— 每个 messageList 选择器各自的命中情况 ——
    // 用来发现「宽松选择器误命中」：比如 [class*="chat"] 在落地页命中 37 个
    // 导航元素——那不是消息气泡，计数模型就是错的。
    const auditSelectors = (selectors) =>
      (selectors || []).map((sel) => {
        let els = [];
        try {
          els = Array.from(document.querySelectorAll(sel));
        } catch {
          return { selector: sel, matched: false, count: 0, error: "选择器非法" };
        }
        return {
          selector: sel,
          matched: els.length > 0,
          count: els.length,
          samples: els.slice(0, 3).map((el) => {
            // 量一下几何尺寸：零尺寸的元素即便 display/visibility/opacity 都正常，
            // 也不可能是「正在生成」的提示条。jsdom 里没有布局，rect 全是 0，
            // 所以这条度量只在真浏览器里有意义（真机采集场景）。
            let rect = null;
            try {
              const r = el.getBoundingClientRect();
              rect = {
                width: Math.round(r.width),
                height: Math.round(r.height),
                top: Math.round(r.top),
                left: Math.round(r.left),
              };
            } catch {
              /* 某些环境不支持布局度量 */
            }
            return {
              tag: el.tagName.toLowerCase(),
              className: typeof el.className === "string" ? el.className : "",
              text: (el.innerText || el.textContent || "").slice(0, 120),
              // 「空容器」与「有内容的界面元素」是两回事，必须分开量：
              //   - Kimi 的 message-list-container 在落地页是**空的**（没会话）
              //     ⇒ 它只是列表容器，增长检测仍然可用；
              //   - Yiyan 的 _chat-container_ 装着整个应用外壳（侧边栏 + 顶栏）
              //     ⇒ 它是界面元素，命中它等于把导航当成消息。
              textLength: (el.innerText || el.textContent || "").trim().length,
              childCount: el.children ? el.children.length : 0,
              rect,
            };
          }),
        };
      });

    try {
      out.messageListSelectors = auditSelectors(adapter.selectors?.messageList);
    } catch (e) {
      out.messageListSelectors = [];
    }

    // —— messageContent / typingIndicator 同样要审 ——
    //
    // 「宽松选择器误命中」不是只有 messageList 一处：
    // typingIndicator 命中假阳性会让 isTyping() 永远为 true，
    // 于是 waitForResponseGeneric 永远等不到「不忙」→ 必然超时。
    try {
      out.messageContentSelectors = auditSelectors(adapter.selectors?.messageContent);
    } catch (e) {
      out.messageContentSelectors = [];
    }
    try {
      out.typingIndicatorSelectors = auditSelectors(adapter.selectors?.typingIndicator);
    } catch (e) {
      out.typingIndicatorSelectors = [];
    }

    // —— isTyping() 的真实取值 ——
    // 落地页（空闲态）必须是 false；true 说明 typingIndicator 误命中。
    try {
      out.isTyping = typeof adapter.isTyping === "function" ? Boolean(adapter.isTyping()) : null;
    } catch (e) {
      out.isTyping = null;
    }

    // —— 标注（在所有测量**之后**做，避免影响前面的选择器命中）——
    //
    // 标注直接打在元素上，序列化**元素自身**的 outerHTML。
    //
    // 曾经序列化「父元素的 outerHTML」——那会让嵌套的匹配项把彼此的祖先
    // 反复带出来：Yiyan 一次就产出 155KB、127 个重复的标注。
    // 元素自身的 markup 已经包含它自己的 class（选择器依赖的就是这个），
    // 祖先结构另用「tag + class」的紧凑上下文单独记。
    //
    // 标注属性用 **data-probe-role** 而不是 data-role：
    // 真实站点自己也会用 data-role（实测千问就有 data-role="icon"），
    // 共用命名空间会让站点自己的元素被误读成「消息气泡」。
    const annotate = (el, role) => {
      if (!el) return null;
      el.setAttribute("data-probe-role", role);
      return el.outerHTML || "";
    };

    const ancestorContext = (el) => {
      const list = [];
      let cur = el ? el.parentElement : null;
      for (let i = 0; i < 4 && cur; i += 1) {
        list.push({
          tag: cur.tagName.toLowerCase(),
          className: typeof cur.className === "string" ? cur.className : "",
        });
        cur = cur.parentElement;
      }
      return list;
    };

    out.annotated = {
      chatInput: chatInputEl ? annotate(chatInputEl, "chat-input") : null,
      sendButton: sendButtonEl ? annotate(sendButtonEl, "send-button") : null,
      messages: messageEls.map((el) => annotate(el, "message")).filter(Boolean),
      context: {
        chatInput: ancestorContext(chatInputEl),
        firstMessage: ancestorContext(messageEls[0] || null),
      },
    };

    return out;
  }, platformId);
}

/**
 * 把采集结果渲染成「带 data-role 标注」的 HTML 片段。
 *
 * 标注已经在页面里打好了（见 captureDom 的 annotate），这里只负责拼装。
 * @param {object} dom - captureDom 的返回
 * @returns {string}
 */
function renderAnnotatedHtml(dom) {
  const parts = [];
  const annotated = dom?.annotated || {};
  if (annotated.chatInput) parts.push(annotated.chatInput);
  if (annotated.sendButton) parts.push(annotated.sendButton);
  for (const msg of annotated.messages || []) {
    if (msg) parts.push(msg);
  }
  return parts.join("\n");
}

/** 采集一家平台。 */
async function capturePlatform(browser, platform, args) {
  const context = await browser.newContext({
    locale: args.locale || "zh-CN",
    viewport: { width: 1440, height: 900 },
  });
  try {
    await injectAdapter(context, `src/platforms/${platform.module}`, platform.id);

    const page = await context.newPage();
    const response = await page.goto(platform.url, {
      waitUntil: "domcontentloaded",
      timeout: args.timeout,
    });
    const httpStatus = response ? response.status() : null;

    // 等输入框出现（生产 adapter 的真实 getChatInput）
    const composerAppeared = await page
      .waitForFunction(
        (adapterId) => {
          const registry = window.__PROBE_ADAPTERS__ || {};
          const mod = registry[adapterId];
          if (!mod || !mod.default) return false;
          try {
            return !!new mod.default().getChatInput();
          } catch {
            return false;
          }
        },
        platform.id,
        { timeout: args.composerWait },
      )
      .then(() => true)
      .catch(() => false);

    // 等页面**稳定**再采样。
    //
    // 2026-10-25 实测踩到的坑：输入框一出现就采样，采到的是**加载中的骨架屏**
    // ——Yiyan 的 `_sk-loading_*` / `_loading-bar_*` 这类占位元素在加载期间就在 DOM 里，
    // 于是 isTyping() 读成 true，而那其实是「还在加载」，不是「正在生成」。
    // 同一份代码上一轮读 false、这一轮读 true，纯粹是采样时刻不同。
    //
    // 所以不变量「空闲即不忙」必须在一个**确定的时刻**判定：页面稳定之后。
    await page
      .waitForLoadState("networkidle", { timeout: args.settleTimeout })
      .catch(() => {
        /* 长轮询站点可能永远不 networkidle，用固定静默期兜底 */
      });
    await page.waitForTimeout(args.settleDelay);

    const env = await classifyEnvironment(page);
    const dom = await captureDom(page, platform.id);

    return {
      platform: platform.id,
      name: platform.name,
      url: platform.url,
      httpStatus,
      composerAppeared,
      env: env.state,
      envSignal: env.signal,
      dom,
    };
  } finally {
    await context.close();
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targets = args.platforms
    ? PLATFORMS.filter((p) => args.platforms.includes(p.id))
    : PLATFORMS;

  if (targets.length === 0) {
    console.error(`--platform 未匹配到任何平台。可选：${PLATFORMS.map((p) => p.id).join(", ")}`);
    return 2;
  }

  mkdirSync(args.outDir, { recursive: true });

  console.log("=== 真实 DOM 快照采集（B-2，只读）===");
  console.log(`采集平台：${targets.map((p) => p.name).join("、")}`);
  console.log(`输出目录：${args.outDir}`);
  console.log("注意：只读，不注入文本、不点发送。\n");

  const browser = await chromium.launch({
    channel: args.channel,
    headless: !args.headed,
  });

  const summary = [];
  let captured = 0;
  let modelViolations = 0;

  for (const platform of targets) {
    let record;
    try {
      record = await capturePlatform(browser, platform, args);
    } catch (e) {
      record = {
        platform: platform.id,
        name: platform.name,
        url: platform.url,
        outcome: "capture_failed",
        reason: `采集过程异常：${e.message}`,
      };
    }

    const dom = record.dom;
    if (!dom || dom.error) {
      record.outcome = record.outcome || "capture_failed";
      record.reason = record.reason || (dom?.error ? `页面内采集失败：${dom.error}` : "未知原因");
    } else if (record.env === "bot_check") {
      record.outcome = "unverified";
      record.reason = `命中人机校验/机器人拦截页（信号：${record.envSignal}）——不是 adapter 的结论`;
    } else if (record.env === "login_wall") {
      record.outcome = "unverified";
      record.reason = `落在登录墙（信号：${record.envSignal}）——需要已登录的 profile 才能采到`;
    } else if (!dom.chatInput?.found) {
      record.outcome = "unverified";
      record.reason = "生产 adapter 在真机上没找到输入框——可能是 DOM 漂移，也可能是未登录";
    } else {
      record.outcome = "captured";
      record.reason = "";
      captured += 1;
    }

    // 写 sidecar 元数据（**每家平台都写**，包括没采到的——原因要留痕）
    const messageModel = dom ? assessMessageCountModel(dom) : null;
    const meta = {
      capturedAt: new Date().toISOString(),
      platform: platform.id,
      name: platform.name,
      url: platform.url,
      locale: args.locale || "zh-CN",
      httpStatus: record.httpStatus ?? null,
      composerAppeared: record.composerAppeared ?? false,
      outcome: record.outcome,
      reason: record.reason || "",
      composerFound: Boolean(dom?.chatInput?.found),
      sendButtonFound: Boolean(dom?.sendButton?.found),
      messageCount: dom?.messageList?.count ?? null,
      messageListSelectors: dom?.messageListSelectors || [],
      messageContentSelectors: dom?.messageContentSelectors || [],
      typingIndicatorSelectors: dom?.typingIndicatorSelectors || [],
      isTyping: dom?.isTyping ?? null,
      messageCountModel:
        record.outcome === "captured" && messageModel
          ? {
              ok: messageModel.ok,
              count: messageModel.count,
              reason: messageModel.reason,
              falsePositiveSelectors: messageModel.falsePositiveSelectors,
            }
          : null,
      sanitized: true,
    };
    writeFileSync(
      join(args.outDir, `${platform.id}.json`),
      `${JSON.stringify(meta, null, 2)}\n`,
      "utf-8",
    );

    // 写脱敏后的 HTML 片段（只有采到才写）
    if (record.outcome === "captured") {
      const html = sanitizeHtmlPretty(renderAnnotatedHtml(dom));
      writeFileSync(join(args.outDir, `${platform.id}.html`), `${html}\n`, "utf-8");
    }

    const tag =
      record.outcome === "captured"
        ? "[CAPTURED]"
        : record.outcome === "unverified"
          ? "[UNVERIFIED]"
          : "[FAILED]";
    console.log(`${tag} ${platform.name} — ${record.reason || "已采到输入框并标注"}`);
    if (dom?.messageListSelectors?.length) {
      for (const sel of dom.messageListSelectors) {
        if (sel.matched) {
          console.log(`         消息选择器命中 ${sel.count} 个：${sel.selector}`);
        }
      }
    }
    if (messageModel && !messageModel.ok) {
      console.log(`         [硬伤] ${messageModel.reason}`);
      modelViolations += 1;
    } else if (messageModel && messageModel.count !== 0) {
      console.log(`         [待确认] ${messageModel.reason}`);
    }
    summary.push(meta);
  }

  await browser.close();

  const unverified = summary.filter((s) => s.outcome === "unverified").length;
  const failed = summary.filter((s) => s.outcome === "capture_failed").length;

  console.log("\n=== 采集结论 ===");
  console.log(`采到：${captured}　未验证：${unverified}　失败：${failed}　共 ${summary.length} 家`);
  console.log(`消息计数模型不成立：${modelViolations} 家`);
  console.log(`每家平台的记录（含未采到的原因）已写入：${args.outDir}`);

  if (captured === 0) {
    console.error("\n[FAIL] 一家都没采到——通常是网络 / 代理 / 全部命中登录墙或人机校验。");
    return 1;
  }
  if (modelViolations > 0) {
    console.error(
      `\n[FAIL] ${modelViolations} 家平台的消息计数模型不成立——` +
        "落地页上数出了一堆「消息」，那不是消息气泡。",
    );
    return 1;
  }
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    console.error("[ERROR] 采集器自身异常：", e);
    process.exit(2);
  });
