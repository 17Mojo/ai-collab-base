/**
 * 真机 DOM 契约探针（L1）
 *
 * 用途：模拟层（tests/adapter-matrix/）用的是 **mock DOM fixture**——它证明
 * 「选择器在 fixture 上能命中」，**不**证明「选择器在真机上还能命中」。
 * 真实站点的 DOM 会随前端改版漂移，漂移会让 Pack 执行静默失效。
 * 本探针把**生产 adapter 本身**打进**真实站点**的页面里，调用**真实方法**，
 * 产出可机检的证据。
 *
 * 关键设计：
 * 1. **不复制选择器**。用 esbuild 把 `src/platforms/<platform>-adapter.js`
 *    连同其依赖打成一个 IIFE 注入页面，再在页面里 `new Adapter().getChatInput()`
 *    ——跑的是**生产代码路径**（adapter 自己的 `getChatInput` → `findElement`
 *    → 自己的 SELECTORS），不是抄一份选择器表。
 * 2. **默认只读**：不注入文本、不点发送、不消耗任何账号额度。
 *    需要真实发消息的那一层是 L2（人工），见 docs/REAL_MACHINE_REGRESSION.md。
 * 3. 明确区分「没找到输入框」和「撞到登录墙 / 人机校验」——后两者不是
 *    adapter 的问题，但也**不构成** DOM 契约通过。各种情况在证据里分开记。
 *
 * 用法：
 *   node tests/real-machine/dom-contract-probe.mjs
 *   node tests/real-machine/dom-contract-probe.mjs --platform=chatgpt,claude
 *   node tests/real-machine/dom-contract-probe.mjs --headed
 *   node tests/real-machine/dom-contract-probe.mjs --out=evidence.json
 *   node tests/real-machine/dom-contract-probe.mjs --channel=chrome
 *   node tests/real-machine/dom-contract-probe.mjs --profile-dir=.rm-profile
 *   node tests/real-machine/dom-contract-probe.mjs --probe-send-button
 *   node tests/real-machine/dom-contract-probe.mjs --locale=zh-CN
 *
 * **为什么要 --locale**：DOM 漂移是**随界面语言变化**的。2026-10-25 实测
 * Gemini 发送按钮内层 <button> 的 aria-label 在中文界面是「发送」、英文界面是
 * "Send message"；旧选择器 button[aria-label*="Send"] 在英文界面侥幸命中、
 * 在中文界面一个都命中不了。只跑默认语言就看不见这类漂移——所以两个语言都要跑。
 *
 * 退出码：0 = 无平台判定为 failed；1 = 有平台 failed；2 = 探针自身异常。
 * 「未验证（登录墙 / 人机校验）」不计为 failed——它是环境限制，不是回归结论。
 */

import { chromium } from "playwright";
import { build } from "esbuild";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { PLATFORMS as REGISTERED_PLATFORMS } from "../platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "../..");

/**
 * 平台清单从**唯一事实源**导入（tests/platforms.mjs），不再在本文件里手抄一份。
 *
 * 2026-10-25 之前，本文件只登记了 3 家（chatgpt / claude / gemini），
 * 其余 7 家（deepseek / kimi / longcat / qianwen / yiyan / yuanbao / chatglm）
 * **从未进入过真机回归**——因为「清单只写了 3 家」，而模拟层矩阵
 * 覆盖 10 家却全是手写 mock，于是出现「矩阵 110/114 全绿，
 * 但只有 3 家在真机上验证过」的落差。
 * 平台清单现在只有一份，模拟层与真机层不可能再各说各话。
 */
const PLATFORMS = REGISTERED_PLATFORMS.map((p) => ({
  id: p.id,
  name: p.name,
  adapter: `src/platforms/${p.module}`,
  url: p.url,
}));

/** 登录墙的常见特征——用于把「没找到输入框」拆成两类。 */
const LOGIN_WALL_SELECTORS = [
  'input[type="password"]',
  'a[href*="login"]',
  'a[href*="signin"]',
  'a[href*="auth"]',
  'button[data-testid*="login"]',
];

/**
 * 人机校验 / 机器人拦截页的特征。
 *
 * **必须覆盖多语言**：Cloudflare 拦截页按浏览器语言出文案。
 * 2026-10-24 实测——同一批站点，Playwright 自带 Chromium 出英文
 * "Just a moment..."，本机真实 Chrome 出**中文**「请稍候…」，而当时的
 * marker 集合只有英文，于是中文拦截页被判成 `no_composer`（"疑似 DOM 漂移"），
 * 把一个**环境限制**误报成**产品回归**。判定口径必须对语言不敏感。
 */
const BOT_CHECK_MARKERS = [
  // 英文
  "just a moment",
  "checking your browser",
  "verify you are human",
  "enable javascript and cookies",
  "attention required",
  "unusual traffic",
  "performing security verification",
  // 中文（Cloudflare 简体中文拦截页）
  "请稍候",
  "安全验证",
  "正在进行安全验证",
  "验证您不是自动程序",
  "自动程序",
  "请稍等",
  // 通用签名
  "ray id",
  "cloudflare",
];

/** Cloudflare 挑战页的 DOM 签名——比文案更稳（文案会随语言变）。 */
const BOT_CHECK_SELECTORS = [
  "#challenge-form",
  "#cf-challenge-running",
  "#challenge-running",
  'iframe[src*="challenges.cloudflare.com"]',
  'div[data-translate="checking_browser"]',
];

/**
 * 被判定为「人机校验」的 HTTP 状态码。
 *
 * 403 是**强信号**：三个目标站点的正常首屏都是 200（实测 Gemini 200），
 * 403 意味着请求被边缘节点拦下，页面内容不是应用本身的 DOM。
 */
const BOT_CHECK_HTTP_STATUS = new Set([403, 429, 503]);

function parseArgs(argv) {
  const args = {
    platforms: null,
    headed: false,
    out: null,
    timeout: 30000,
    composerWait: 20000,
    profileDir: null,
    channel: null,
    probeSendButton: false,
    locale: null,
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
    } else if (raw.startsWith("--out=")) {
      args.out = raw.slice("--out=".length);
    } else if (raw.startsWith("--timeout=")) {
      args.timeout = Number(raw.slice("--timeout=".length));
    } else if (raw.startsWith("--composer-wait=")) {
      args.composerWait = Number(raw.slice("--composer-wait=".length));
    } else if (raw.startsWith("--profile-dir=")) {
      args.profileDir = raw.slice("--profile-dir=".length);
    } else if (raw.startsWith("--channel=")) {
      args.channel = raw.slice("--channel=".length);
    } else if (raw === "--probe-send-button") {
      args.probeSendButton = true;
    } else if (raw.startsWith("--locale=")) {
      args.locale = raw.slice("--locale=".length);
    }
  }
  return args;
}

/** 把生产 adapter 打成可在页面里直接执行的 IIFE。 */
async function bundleAdapter(adapterRelPath) {
  const result = await build({
    entryPoints: [resolve(EXT_ROOT, adapterRelPath)],
    bundle: true,
    format: "iife",
    globalName: "__PROBE_ADAPTER__",
    platform: "browser",
    write: false,
    logLevel: "silent",
  });
  return result.outputFiles[0].text;
}

/**
 * 在真实页面上跑**生产 adapter 的真实方法**。
 * 返回 adapter 实际找到的输入框 / 发送按钮 / 消息列表，以及各选择器的命中情况。
 *
 * 注入方式用 `context.addInitScript` 而不是 `page.addScriptTag`：
 * 后者走 `script.text` 赋值，会被页面的 CSP / TrustedTypes 挡住
 * （实测 Claude.ai 报 "Executing inline script violates ... Content Security Policy"，
 * Gemini 报 "This document requires 'TrustedScript' assignment"）。
 * addInitScript 走 CDP 的 `Page.addScriptToEvaluateOnNewDocument`，**不受页面 CSP 约束**。
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId - 读 globalThis.__PROBE_ADAPTERS__[platformId]
 */
async function probeWithAdapter(page, platformId) {
  return page.evaluate(
    ({ wallSelectors, botSelectors, adapterId }) => {
      const registry = window.__PROBE_ADAPTERS__ || {};
      const mod = registry[adapterId];
      if (!mod || !mod.default) {
        return { error: "adapter bundle 未注入页面" };
      }

      let adapter;
      try {
        adapter = new mod.default();
      } catch (err) {
        return { error: `adapter 构造失败：${err.message}` };
      }

      const selectors = adapter.selectors || {};
      const hits = {};
      for (const [group, list] of Object.entries(selectors)) {
        hits[group] = (list || []).map((sel) => {
          try {
            const el = document.querySelector(sel);
            return { selector: sel, matched: !!el, tag: el ? el.tagName.toLowerCase() : null };
          } catch {
            return { selector: sel, matched: false, error: "invalid-selector" };
          }
        });
      }

      const input = adapter.getChatInput();
      const send = adapter.getSendButton();
      let messages = [];
      try {
        messages = Array.from(adapter.getMessageList() || []);
      } catch {
        messages = [];
      }

      return {
        detected: (() => {
          try {
            return !!adapter.detect();
          } catch {
            return false;
          }
        })(),
        hasInput: !!input,
        inputTag: input ? input.tagName.toLowerCase() : null,
        inputContentEditable: input ? input.getAttribute("contenteditable") : null,
        hasSendButton: !!send,
        sendButtonTag: send ? send.tagName.toLowerCase() : null,
        messageCount: messages.length,
        hits,
        loginWall: wallSelectors.some((s) => {
          try {
            return !!document.querySelector(s);
          } catch {
            return false;
          }
        }),
        botCheckDom: botSelectors.some((s) => {
          try {
            return !!document.querySelector(s);
          } catch {
            return false;
          }
        }),
        pageTitle: document.title,
        bodySnippet: (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 240),
      };
    },
    {
      wallSelectors: LOGIN_WALL_SELECTORS,
      botSelectors: BOT_CHECK_SELECTORS,
      adapterId: platformId,
    }
  );
}

/**
 * 判断当前页面是不是人机校验 / 机器人拦截页。
 *
 * 三个互相独立的信号，任一命中即可——**不依赖单一语言**：
 *   1. HTTP 状态码 403 / 429 / 503（最稳）；
 *   2. Cloudflare 挑战页的 DOM 签名（不随语言变）；
 *   3. 多语言文案标记（含中文）。
 */
async function detectBotCheck(page, httpStatus) {
  if (httpStatus && BOT_CHECK_HTTP_STATUS.has(httpStatus)) {
    return { hit: true, signal: `http-status-${httpStatus}` };
  }
  const domHit = await page
    .evaluate((selectors) =>
      selectors.some((s) => {
        try {
          return !!document.querySelector(s);
        } catch {
          return false;
        }
      }),
      BOT_CHECK_SELECTORS
    )
    .catch(() => false);
  if (domHit) {
    return { hit: true, signal: "cloudflare-dom-signature" };
  }
  const title = (await page.title().catch(() => "")).toLowerCase();
  const text = await page
    .evaluate(() => (document.body?.innerText || "").toLowerCase())
    .catch(() => "");
  const marker = BOT_CHECK_MARKERS.find(
    (m) => title.includes(m) || text.includes(m)
  );
  if (marker) {
    return { hit: true, signal: `text-marker:${marker}` };
  }
  return { hit: false, signal: null };
}

/**
 * 页面里「发送按钮类元素」是否存在的**独立**判据。
 *
 * 为什么要有这条独立信号：只记录 adapter 自己的 `getSendButton()` 命中与否，
 * 无法区分两种完全不同的失败——
 *   (a) 站点改了形状，页面上**根本没有**发送按钮；
 *   (b) 页面**有**发送按钮，但 adapter 的选择器过时了（**adapter 漂移**）。
 * (b) 是产品缺陷，(a) 是站点行为变化——处置完全不同，不能混为一谈。
 *
 * 这里用的是**与语言无关**的结构特征（class 名），不依赖 aria-label 文案。
 */
const SEND_BUTTON_DOM_SELECTORS = [
  ".send-button",
  "gem-icon-button.send-button",
  "button.send-button",
  "[class*='send-button']",
];

/**
 * 可选：往输入框里敲**一个字母**，让「只有有内容时才渲染」的发送按钮出现，
 * 然后**清空输入**、**不点击发送**。
 *
 * 为什么需要：Gemini 的发送按钮在 zero-state（输入框为空）时**根本不存在**，
 * 只敲入内容后才渲染成 `<gem-icon-button class="send-button"><button …></gem-icon-button>`。
 * 不做这一步，L1 就永远看不到发送按钮的 DOM 契约——而发送按钮漂移恰恰是
 * 会让 Pack 执行**静默失败**（走不到发送，消息永远发不出去）的那类漂移。
 *
 * **必须敲字母，不能敲空格**：实测敲一个空格后 Gemini 仍停留在 zero-state，
 * 发送按钮**不出现**——那会让探针报出「按钮不存在」的假阴性。
 * 用字母后按钮稳定出现（en-US 与 zh-CN 均实测 = 1）。
 *
 * 安全边界：只敲一个字母，不点发送，不消耗额度，测完立刻清空输入。
 */
async function probeSendButtonInTypedState(page) {
  const input = await page.$("div[contenteditable='true'], textarea, [role='textbox']");
  if (!input) {
    return { available: false, reason: "no-input-element" };
  }
  try {
    await input.click();
    await page.keyboard.type("a");
    await page.waitForTimeout(1500);
    const state = await page.evaluate(
      ({ domSelectors }) => {
        const registry = window.__PROBE_ADAPTERS__ || {};
        const adapterId = document.documentElement.getAttribute("data-probe-adapter");
        const mod = registry[adapterId];
        let send = null;
        let matched = [];
        if (mod && mod.default) {
          const adapter = new mod.default();
          send = adapter.getSendButton();
          const selectors = (adapter.selectors || {}).sendButton || [];
          matched = selectors
            .map((sel) => {
              try {
                const el = document.querySelector(sel);
                return {
                  selector: sel,
                  matched: !!el,
                  tag: el ? el.tagName.toLowerCase() : null,
                };
              } catch {
                return { selector: sel, matched: false, error: "invalid-selector" };
              }
            })
            .filter((h) => h.matched)
            .map((h) => h.selector);
        }
        const domPresent = domSelectors.filter((s) => {
          try {
            return document.querySelector(s) !== null;
          } catch {
            return false;
          }
        });
        return {
          hasSendButton: !!send,
          sendButtonTag: send ? send.tagName.toLowerCase() : null,
          sendButtonAria: send ? send.getAttribute("aria-label") : null,
          matchedSelectors: matched,
          // DOM 事实：页面上到底有没有发送按钮类元素
          sendButtonDomPresent: domPresent.length > 0,
          sendButtonDomSelectors: domPresent,
        };
      },
      { domSelectors: SEND_BUTTON_DOM_SELECTORS }
    );
    // 清空输入——探针不在页面上留下任何内容（select-all + delete，
    // 单个 Backspace 对已被浏览器合并的输入不可靠）
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.press("Backspace");
    await page.waitForTimeout(500);
    return { available: true, ...state };
  } catch (err) {
    return { available: false, reason: err.message.split("\n")[0] };
  }
}

async function probePlatform(context, platform, args) {
  const started = Date.now();
  const record = {
    platform: platform.id,
    name: platform.name,
    url: platform.url,
    outcome: "unreachable",
    detail: "",
    probe: null,
    durationMs: 0,
  };

  let adapterCode;
  try {
    adapterCode = await bundleAdapter(platform.adapter);
  } catch (err) {
    record.outcome = "adapter_build_failed";
    record.detail = `无法打包生产 adapter：${err.message.split("\n")[0]}`;
    record.durationMs = Date.now() - started;
    return record;
  }

  // 在任何页面脚本之前把生产 adapter 注入主世界（不受页面 CSP 约束）。
  // addInitScript 会把内容包进一个函数作用域——`var __PROBE_ADAPTER__` 因此**不是**
  // 全局变量，必须显式挂到 globalThis 上，否则页面里读到 undefined。
  //
  // 按平台 id 建索引而不是直接覆盖同一个全局名：`--profile-dir` 模式下多个平台
  // 共用一个 persistent context，init script 会**累积**——后注入的会盖掉先注入的，
  // 导致后面那个平台探到的是别人的 adapter。
  await context.addInitScript({
    content:
      `${adapterCode}\n` +
      `;globalThis.__PROBE_ADAPTERS__ = globalThis.__PROBE_ADAPTERS__ || {};` +
      `globalThis.__PROBE_ADAPTERS__[${JSON.stringify(platform.id)}] = __PROBE_ADAPTER__;`,
  });
  const page = await context.newPage();
  try {
    const response = await page.goto(platform.url, {
      waitUntil: "domcontentloaded",
      timeout: args.timeout,
    });
    record.httpStatus = response ? response.status() : null;

    // SPA 前端挂 composer 需要时间：轮询等待**生产 adapter 自己的
    // getChatInput()** 找到输入框，而不是死等固定秒数。
    //
    // 为什么不用硬编码选择器等：此前这段写的是 ChatGPT/Claude/Gemini 三家的
    // 专用选择器（#prompt-textarea 等）。探针扩到 10 家之后，那段对另外 7 家
    // **永远等不到**——会把「等不到」误当成「adapter 找不到输入框」，
    // 报出一个假的 DOM 漂移。用生产 adapter 自己的方法等，才是对账同一份代码。
    const composerWait = await page
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
        { timeout: args.composerWait }
      )
      .then(() => true)
      .catch(() => false);
    record.composerAppeared = composerWait;

    // 记录当前 adapter id，供 send-button 二次探测在页面里定位 registry 项
    await page
      .evaluate((id) => {
        document.documentElement.setAttribute("data-probe-adapter", id);
      }, platform.id)
      .catch(() => {});

    const probe = await probeWithAdapter(page, platform.id);
    record.probe = probe;

    // 人机校验判定放在最前面：被拦截时页面根本不是应用 DOM，
    // 此时任何「选择器没命中」都是**环境限制**的假象，不是 DOM 漂移。
    const botCheck = await detectBotCheck(page, record.httpStatus);
    record.botCheckSignal = botCheck.signal;

    if (probe.error) {
      record.outcome = "adapter_probe_error";
      record.detail = probe.error;
    } else if (botCheck.hit) {
      record.outcome = "bot_check";
      record.detail = `命中人机校验/机器人拦截页（信号：${botCheck.signal}）——DOM 契约**未**被验证（不是 adapter 的结论）`;
    } else if (!probe.detected) {
      record.outcome = "detect_failed";
      record.detail = "adapter.detect() 在真机页面上返回 false——主机名判定已漂移";
    } else if (probe.loginWall) {
      record.outcome = "login_wall";
      record.detail = "到达站点但落在登录墙：DOM 契约**未**被验证（不是 adapter 的结论）";
    } else if (probe.hasInput) {
      record.outcome = "pass";
      record.detail = `生产 adapter 在真机 DOM 上找到输入框（<${probe.inputTag}>）`;
    } else {
      record.outcome = "no_composer";
      record.detail = "到达站点、未见登录墙/拦截页、但生产 adapter 找不到输入框——疑似 DOM 漂移，需人工确认";
    }

    // 发送按钮契约：需要输入框里有内容才会渲染，所以单独做一次「敲一个字母」
    // 的二次探测（不发送、测完清空）。默认不跑——保持 L1 严格只读。
    if (args.probeSendButton && record.outcome === "pass") {
      record.sendButtonProbe = await probeSendButtonInTypedState(page);
      const sb = record.sendButtonProbe;
      if (sb.available && !sb.hasSendButton) {
        // 区分「adapter 选择器漂移」（产品缺陷）与「站点形状变化」（非 adapter 结论）
        record.sendButtonVerdict = sb.sendButtonDomPresent
          ? "adapter_drift"
          : "site_shape_changed";
        if (sb.sendButtonDomPresent) {
          record.detail +=
            "；⚠️ 发送按钮：页面上存在但生产 adapter 选择器已漂移（产品缺陷）";
        }
      } else if (sb.available) {
        record.sendButtonVerdict = "ok";
      }
    }
  } catch (err) {
    record.outcome = "unreachable";
    record.detail = `访问失败：${err.message.split("\n")[0]}`;
  } finally {
    if (!args.profileDir) {
      await context.close();
    }
  }
  record.durationMs = Date.now() - started;
  return record;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const selected = args.platforms
    ? PLATFORMS.filter((p) => args.platforms.includes(p.id))
    : PLATFORMS;

  if (selected.length === 0) {
    console.error(`--platform 未匹配到任何平台。可选：${PLATFORMS.map((p) => p.id).join(", ")}`);
    process.exit(1);
  }

  console.log("=== 真机 DOM 契约探针（L1，只读）===");
  console.log(`覆盖平台：${selected.map((p) => p.name).join("、")}`);
  console.log(
    "判定口径：pass = 生产 adapter 在真机 DOM 上找到输入框；" +
      "login_wall / bot_check = 未验证（环境限制，不计失败）；no_composer = 疑似漂移\n"
  );

  const launchOptions = { headless: !args.headed };
  if (args.channel) {
    // 用本机装的**真实** Chrome（channel=chrome），而不是 Playwright 自带的
    // Chromium——后者在真实站点上会直接撞人机校验页，DOM 契约根本无从验证。
    launchOptions.channel = args.channel;
  }

  // 持久 profile（--profile-dir）可带上已登录的会话，绕开登录墙；
  // 没有它就只能验证「公开首屏」的 DOM。
  const browser = args.profileDir ? null : await chromium.launch(launchOptions);
  const persistentContext = args.profileDir
    ? await chromium.launchPersistentContext(args.profileDir, launchOptions)
    : null;

  const results = [];
  try {
    for (const platform of selected) {
      // locale 必须显式设定：**漂移是随界面语言变化的**——
      // 2026-10-25 实测 Gemini 的发送按钮 aria-label 中文界面是「发送」、
      // 英文界面是 "Send message"，旧的 button[aria-label*="Send"] 在英文界面
      // 侥幸命中、在中文界面一个都命中不了。只跑默认语言就看不见这类漂移。
      const context = persistentContext
        ? persistentContext
        : await browser.newContext(args.locale ? { locale: args.locale } : {});
      const record = await probePlatform(context, platform, args);
      results.push(record);
      console.log(
        `[${record.outcome.toUpperCase()}] ${record.name} (${record.durationMs}ms) — ${record.detail}`
      );
      const matchedInput = (record.probe?.hits?.chatInput || [])
        .filter((h) => h.matched)
        .map((h) => h.selector);
      if (matchedInput.length) {
        console.log(`         命中的输入框选择器：${matchedInput.join(" | ")}`);
      }
      if (record.sendButtonProbe) {
        const sb = record.sendButtonProbe;
        if (!sb.available) {
          console.log(`         发送按钮探测不可用：${sb.reason}`);
        } else if (sb.hasSendButton) {
          console.log(
            `         发送按钮：找到 <${sb.sendButtonTag}> aria=${sb.sendButtonAria}` +
              (sb.matchedSelectors?.length ? `（命中：${sb.matchedSelectors.join(" | ")}）` : "")
          );
        } else if (sb.sendButtonDomPresent) {
          // 关键区分：页面上**有**发送按钮，但生产 adapter 找不到它
          // → 这是**产品缺陷（选择器漂移）**，不是站点行为变化。
          console.log(
            `         发送按钮：**adapter 选择器已漂移**——页面上存在发送按钮类元素` +
              `（${sb.sendButtonDomSelectors.join(" | ")}），但生产 adapter 一个都没命中`
          );
        } else {
          console.log(
            "         发送按钮：页面上未发现发送按钮类元素——站点形状已变（需人工确认，非 adapter 结论）"
          );
        }
      }
      if (record.outcome === "login_wall" || record.outcome === "bot_check") {
        console.log("         ⚠️ 未验证：DOM 契约未结论——需要已登录的浏览器 profile 才能得出结论");
      }
    }
  } finally {
    if (persistentContext) {
      await persistentContext.close();
    }
    if (browser) {
      await browser.close();
    }
  }

  const verdict = {
    generatedAt: new Date().toISOString(),
    layer: "L1-real-machine-dom-contract",
    method: "生产 adapter 经 esbuild 打包注入真实页面，调用真实方法",
    // 探针**从不**注入文本、**从不**点击发送——两种模式都是只读的。
    // --probe-send-button 只是**多比对一次**发送按钮的 DOM 形状，不点击。
    // （此前这里写的是 readOnly: !args.probeSendButton，会在证据文件里
    //  留下「readOnly: false」，让复核方误以为探针发过消息——口径不实。）
    readOnly: true,
    sendsMessages: false,
    sendButtonProbed: args.probeSendButton,
    browserChannel: args.channel || "playwright-chromium",
    locale: args.locale || "default(en-US)",
    platforms: results,
    passed: results.filter((r) => r.outcome === "pass").length,
    unverified: results.filter(
      (r) => r.outcome === "login_wall" || r.outcome === "bot_check"
    ).length,
    failed: results.filter(
      (r) =>
        r.outcome !== "pass" &&
        r.outcome !== "login_wall" &&
        r.outcome !== "bot_check"
    ).length,
  };
  verdict.verdict =
    verdict.failed > 0 ? "failed" : verdict.unverified > 0 ? "partially-unverified" : "pass";

  console.log("\n=== 结论 ===");
  console.log(
    `pass=${verdict.passed}  未验证(登录墙/拦截)=${verdict.unverified}  失败=${verdict.failed}  → ${verdict.verdict}`
  );

  if (args.out) {
    writeFileSync(args.out, JSON.stringify(verdict, null, 2), "utf-8");
    console.log(`证据已写入：${args.out}`);
  }

  // 未验证不算失败（登录墙/拦截是环境限制，不是回归结论），失败才算。
  process.exit(verdict.failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error("探针自身异常：", err);
  process.exit(2);
});
