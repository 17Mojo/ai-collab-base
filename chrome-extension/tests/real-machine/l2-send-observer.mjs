/**
 * L2 半自动发送观测器
 *
 * ## 它解决什么问题
 *
 * L1 探针是**只读**的：它证明「生产 adapter 在真机上还能找到输入框」，
 * 但证明不了「发出去之后能不能等回来」。
 *
 * 缺口 #8 就是这一段：回复等待链路（发送 → 计数增长 → 停止生成 → 取内容）
 * 从来没有被机器验证过。而这一段恰恰是 Pack 能不能用的关键。
 *
 * ## 为什么是「半自动」
 *
 * 纯人工：截图留证。问题是**截图证明不了「取回来的正文非空」**——
 * 看到界面上有字，不等于 adapter 真的取到了那段字。
 *
 * 纯自动：脚本自己打字、自己点发送。这条路被明确否掉了——
 * 「探针永不发送」是本仓的红线（L1 探针必须无副作用）。
 *
 * 所以取中间：**人点一次发送，脚本负责其余的一切**。
 * 脚本全程只读 DOM，同时**并行跑生产代码里的 `waitForResponse`**，
 * 于是产出的是一份**可机检的 JSON**，而不是一张截图。
 *
 * ## 硬红线
 *
 * 1. 本脚本**不注入文本、不点击发送**。发送动作由人在浏览器里完成。
 * 2. 必须显式加 `--i-will-send` 才会启动——避免有人误跑就发出一条消息。
 * 3. 只读：除了给页面打上探针标注（data-probe-role）之外不改页面。
 *
 * ## 一个浏览器跑完整轮（2026-10-26）
 *
 * 登录**也在这个脚本里等**（`--wait-for-login`），浏览器从头到尾只开一次。
 *
 * 之前的设计是「先在别的窗口登录 → 关掉 → 重开同一个 profile 继续」，
 * 实测栽了两次：
 *   1. 用宽泛正则判登录 → 匿名访客的 `JSESSIONID` 就命中 → 人还没登录，
 *      浏览器就被关掉。
 *   2. 人登录完顺手把窗口一关 → node 随之崩溃 → Playwright **杀掉**浏览器
 *      （不是干净关闭）→ cookie 没落盘 → 重开还是访客。
 *
 * 根因是同一个：**登录态在「关—开」之间要过一次磁盘，而这一步不可靠。**
 * 浏览器只开一次，登录完就在**同一个页面**上开始等生产回复，cookie 压根不用落盘。
 *
 * `--locales=zh-CN,en-US` 让**同一个会话**按页覆盖 `Accept-Language` 跑两种语言；
 * 但站点认不认这个头是站点自己的事（千问就不认），所以证据里会记下
 * **实际观察到的界面语言**（`verdict.observedLanguage` / `verdict.localeMismatch`），
 * 让「这一轮跑的到底是什么语言」有据可查，而不是靠参数推断。
 *
 * ## 用法
 *
 *   # 单平台，需要已登录的浏览器 profile
 *   node tests/real-machine/l2-send-observer.mjs --i-will-send \
 *        --platform=gemini --profile-dir=/tmp/rm-profile
 *
 *   # 全部 10 个平台 × 中文
 *   node tests/real-machine/l2-send-observer.mjs --i-will-send --profile-dir=/tmp/rm-profile
 *
 *   # 英文界面（真实站点按 IP 地区决定语言，locale 只影响 Accept-Language）
 *   node tests/real-machine/l2-send-observer.mjs --i-will-send --locale=en-US
 *
 *   # 一次跑完登录 + 两种语言（推荐：浏览器只开一次）
 *   node tests/real-machine/l2-send-observer.mjs --i-will-send \
 *        --platform=gemini --profile-dir=/tmp/rm-profile \
 *        --wait-for-login --login-cookie=__Secure-3PSID \
 *        --locales=zh-CN,en-US
 *
 * 产出：tests/real-machine/evidence/L2-<platform>-<ts>.json
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

import { PLATFORMS, getPlatform } from "../platforms.mjs";
import { injectAdapter } from "./_bundle.mjs";
import {
  parseArgs,
  buildEvidence,
  resolveLocales,
  detectLoginCookie,
  SAMPLE_INTERVAL,
} from "./l2-model.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * 在页面里采样一次生产 adapter 看到的状态。
 *
 * 采的全是**生产方法**的返回值，不自己实现一套查找逻辑——
 * 自己实现就等于验证了一份副本，不是验证生产代码。
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId
 * @returns {Promise<object>}
 */
async function sampleOnce(page, platformId) {
  return page.evaluate((adapterId) => {
    const registry = window.__PROBE_ADAPTERS__ || {};
    const mod = registry[adapterId];
    if (!mod || !mod.default) return { error: "adapter bundle 未注入页面" };
    let adapter;
    try {
      adapter = new mod.default();
    } catch (e) {
      return { error: `adapter 实例化失败：${e.message}` };
    }

    const out = { error: null };
    try {
      const list = Array.from(adapter.getMessageList() || []);
      out.messageCount = list.length;
      const last = list.length ? list[list.length - 1] : null;
      out.lastTag = last ? last.tagName.toLowerCase() : null;
      out.lastClassName = last && typeof last.className === "string" ? last.className : null;
      out.lastContent = last
        ? (last.innerText || last.textContent || "").trim().slice(0, 2000)
        : "";
      out.lastContentLength = out.lastContent.length;
    } catch (e) {
      out.error = `取消息列表失败：${e.message}`;
      out.messageCount = null;
    }
    try {
      out.isTyping = typeof adapter.isTyping === "function" ? Boolean(adapter.isTyping()) : null;
    } catch (e) {
      out.isTyping = null;
    }
    return out;
  }, platformId);
}

/**
 * 在页面里启动**生产代码**的 waitForResponse，并记下它启动那一刻的消息数。
 *
 * 关键：必须在人发送**之前**启动——生产函数在调用那一刻同步取 initialCount，
 * 之后比较「当前计数 > 初始计数」。等发送完再调用就永远看不到增长了。
 *
 * 记下 baseline 是为了后续重放时间线时用**同一个**基准；
 * 改用第一个采样做基准的话，中间若恰好落进一条消息就会得出「没增长」的假结论。
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId
 * @param {number} timeout
 * @returns {Promise<object>}
 */
async function startProductionWait(page, platformId, timeout) {
  return page.evaluate(
    ({ adapterId, waitTimeout }) => {
      const registry = window.__PROBE_ADAPTERS__ || {};
      const mod = registry[adapterId];
      if (!mod || !mod.default) return { error: "adapter bundle 未注入页面" };
      const adapter = new mod.default();

      let baselineCount = null;
      try {
        baselineCount = adapter.getMessageList().length;
      } catch (e) {
        baselineCount = null;
      }

      globalThis.__L2_WAIT__ = {
        startedAt: Date.now(),
        baselineCount,
        settled: false,
        result: null,
        error: null,
      };
      adapter
        .waitForResponse(waitTimeout)
        .then((result) => {
          globalThis.__L2_WAIT__.settled = true;
          globalThis.__L2_WAIT__.result = result;
        })
        .catch((e) => {
          globalThis.__L2_WAIT__.settled = true;
          globalThis.__L2_WAIT__.error = e.message;
        });
      return { started: true, baselineCount };
    },
    { adapterId: platformId, waitTimeout: timeout },
  );
}

/**
 * 读生产 waitForResponse 的当前状态。
 * @param {import('playwright').Page} page
 * @returns {Promise<object>}
 */
async function readProductionWait(page) {
  return page.evaluate(() => {
    const w = globalThis.__L2_WAIT__;
    if (!w) return { error: "等待尚未启动", settled: false, result: null };
    return {
      startedAt: w.startedAt,
      baselineCount: w.baselineCount,
      settled: w.settled,
      result: w.result,
      error: w.error,
    };
  });
}

/**
 * 等待人完成登录。
 *
 * ## 为什么登录要在这个脚本里等，而不是「先在别的窗口登录、再重开浏览器」
 *
 * 2026-10-26 实测踩了两次：
 *   1. 判定「已登录」用了宽泛的 cookie 名正则 → 匿名访客的 `JSESSIONID`
 *      就命中了 → 浏览器在人还没登录时就被关掉。
 *   2. 改成「关掉浏览器 → 重开 → 用同一个 profile 继续」→ 人登录完、
 *      窗口一关，node 进程随之崩溃，Playwright 把浏览器**杀掉**（不是干净关闭），
 *      cookie 根本没落盘 → 登录态丢失，重开还是访客。
 *
 * 根因是同一个：**登录态在「关—开」之间要过一次磁盘**，而这一步不可靠。
 * 所以这里把登录也放进观测器自己的流程：浏览器**从头到尾只开一次**，
 * 登录完直接在**同一个页面**上开始等待生产回复，cookie 压根不需要落盘。
 *
 * 登录信号有两条：
 *   - `--login-cookie=<名,...>`：该站点**自己的**登录 cookie 白名单（判定逻辑
 *     见 l2-model.mjs 的 detectLoginCookie——只认白名单，不认正则）。
 *   - `--login-flag=<路径>`：人确认后创建标记文件（最可靠，优先用这条）。
 *
 * 两条都不满足就一直等，直到 `--login-timeout`（默认 15 分钟）。
 *
 * @param {import('playwright').BrowserContext} context
 * @param {import('playwright').Page} page
 * @param {object} args
 * @param {{hostnames?: string[]}} [platform] - 平台；给了就按域名收窄 cookie
 * @returns {Promise<string>} 退出原因：flag / cookie / timeout
 */
async function waitForLogin(context, page, args, platform) {
  const deadline = Date.now() + (args.loginTimeout || 900000);
  const hostnames = (platform && platform.hostnames) || [];
  // 标记文件支持 {platform} 占位符。一轮里要登**多个平台**时，
  // 共用一个标记文件会出事：千问的标记文件留着，Gemini 那一步会**立刻**
  // 看到它 → 把没登录的 Gemini 误判成已登录。
  const flagPath = args.loginFlag
    ? String(args.loginFlag).replace("{platform}", platform ? platform.id : "platform")
    : null;
  let lastNotice = 0;
  while (Date.now() < deadline) {
    if (flagPath && existsSync(flagPath)) {
      return "flag";
    }
    const cookies = await context.cookies().catch(() => []);
    const hit = detectLoginCookie(cookies, args.loginCookieNames, hostnames);
    if (hit) {
      return "cookie";
    }
    if (Date.now() - lastNotice > 15000) {
      console.log("  … 等待登录中（请在浏览器窗口里完成登录；脚本不注入、不点击）");
      lastNotice = Date.now();
    }
    try {
      await page.waitForTimeout(2000);
    } catch (err) {
      // 浏览器/页面被人关掉了——这在「人等不及了先关窗口」时会发生。
      // 明确报出来，不要让它变成一个空栈的诡异错误。
      throw new Error(`等待登录期间浏览器被关闭：${err.message.split("\n")[0]}`);
    }
  }
  return "timeout";
}

/**
 * 抓取**界面上实际呈现的语言事实**。
 *
 * 为什么不能只看 `--locale` 参数：站点认不认 `Accept-Language` 是站点自己的事。
 * 2026-10-26 实测千问**不认**——en-US 那一轮拿到的仍然是中文界面，
 * 于是「×2 语言」实际跑的是同一个 DOM，结论是自欺的。
 * 所以证据里必须记「实际观察到的语言」，让复核的人一眼看出这一轮到底跑的是什么。
 *
 * @param {import('playwright').Page} page
 * @param {string} platformId
 * @returns {Promise<object>}
 */
async function collectObservedLanguage(page, platformId) {
  return page
    .evaluate((adapterId) => {
      const out = { documentLang: null, sendButtonAria: null, sendButtonText: null };
      try {
        out.documentLang = document.documentElement.getAttribute("lang") || null;
      } catch {
        /* 读不到就留 null */
      }
      try {
        const registry = window.__PROBE_ADAPTERS__ || {};
        const mod = registry[adapterId];
        if (mod && mod.default) {
          const adapter = new mod.default();
          const btn = adapter.getSendButton();
          if (btn) {
            out.sendButtonAria = btn.getAttribute("aria-label") || null;
            out.sendButtonText = (btn.innerText || btn.textContent || "").trim().slice(0, 80) || null;
          }
        }
      } catch {
        /* adapter 取不到就留 null */
      }
      return out;
    }, platformId)
    .catch(() => ({ documentLang: null, sendButtonAria: null, sendButtonText: null }));
}

/**
 * 打开浏览器/上下文。
 *
 * 带 `--profile-dir` 时用 persistent context——这是**必须的**：
 * L2 要验证的是「已登录的真实会话」，而登录态存在浏览器 profile 里。
 * 普通 newContext() 每次都是干净的访客会话，落到登录墙上，什么都验证不了。
 *
 * @param {object} args
 * @returns {Promise<{context: object, close: Function}>}
 */
async function openContext(args) {
  const opts = {
    locale: args.locale,
    viewport: { width: 1440, height: 900 },
    headless: !args.headed,
  };

  if (args.profileDir) {
    const context = await chromium.launchPersistentContext(resolve(args.profileDir), {
      channel: args.channel,
      ...opts,
    });
    return {
      context,
      close: async () => {
        await context.close();
      },
    };
  }

  const browser = await chromium.launch({ channel: args.channel, headless: !args.headed });
  const context = await browser.newContext(opts);
  return {
    context,
    close: async () => {
      await context.close();
      await browser.close();
    },
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!args.iWillSend) {
    console.error(
      "本工具会让人**手动**发送一条真实消息，脚本只读不写。\n" +
        "确认要跑就加上 --i-will-send。",
    );
    return 2;
  }

  const platform = args.platform ? getPlatform(args.platform) : null;
  if (args.platform && !platform) {
    console.error(`未知平台 ${args.platform}。可选：${PLATFORMS.map((p) => p.id).join(", ")}`);
    return 2;
  }

  const targets = platform ? [platform] : PLATFORMS;
  const locales = resolveLocales(args);

  /**
   * 本轮要观测的「活儿」清单：每项 = 一个平台 + 一种语言。
   *
   * `--platform-locales=qianwen:zh-CN,gemini:en-US` 时按它来；
   * 否则是「选定平台 × 全部 locale」的笛卡尔积。
   */
  const jobs = [];
  if (args.platformLocales && args.platformLocales.length) {
    for (const item of args.platformLocales) {
      const p = getPlatform(item.platform);
      if (!p) {
        console.error(
          `未知平台 ${item.platform}。可选：${PLATFORMS.map((x) => x.id).join(", ")}`,
        );
        return 2;
      }
      jobs.push({ platform: p, locale: item.locale });
    }
  } else {
    for (const p of targets) {
      for (const locale of locales) {
        jobs.push({ platform: p, locale });
      }
    }
  }

  console.log("=== L2 半自动发送观测器 ===");
  console.log(`本轮观测：${jobs.map((j) => `${j.platform.name}/${j.locale}`).join("、")}`);
  console.log(`登录态：${args.profileDir ? `持久 profile ${args.profileDir}` : "临时会话（多半落到登录墙上）"}`);
  console.log(
    "\n请在弹出的浏览器窗口里：\n" +
      "  1. 确认已登录\n" +
      `  2. 在输入框里输入：${args.prompt}\n` +
      "  3. **手动点击发送**\n" +
      "脚本只读 DOM，不注入文本、不点发送。\n",
  );

  const { context, close } = await openContext(args);
  const evidence = [];
  const outPath = args.out
    ? resolve(args.out)
    : join(HERE, "evidence", `L2-${targets[0].id}-${Date.now()}.json`);

  /**
   * 把已采到的证据写盘。
   *
   * 证据必须在**异常路径**上也要落盘：这工具跑的是「真人点击」，
   * 人等不及把窗口一关的情况很常见。证据写不出来，这一轮就白跑了。
   */
  const flushEvidence = () => {
    try {
      mkdirSync(dirname(outPath), { recursive: true });
      writeFileSync(outPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf-8");
      console.log(`\n证据已写入：${outPath}`);
      console.log(
        "登记方式：python3 scripts/real_machine_regression.py record --layer L2 ... --evidence-file <上面这个路径>",
      );
    } catch (err) {
      console.error(`[ERROR] 证据写盘失败：${err.message}`);
    }
  };

  // 登录态是**按平台**记的：同一个浏览器里登录了千问，不代表 Gemini 也登录了。
  const loggedIn = new Set();
  const injected = new Set();

  try {
    for (const job of jobs) {
      const p = job.platform;
      const locale = job.locale;

      if (!injected.has(p.id)) {
        await injectAdapter(context, `src/platforms/${p.module}`, p.id);
        injected.add(p.id);
      }

      const page = await context.newPage();
      // 同一浏览器会话里逐个语言跑：**按页**覆盖 Accept-Language。
      // 站点认不认这个头是站点自己的事——证据里会记下实际观察到的语言。
      await page.setExtraHTTPHeaders({ "Accept-Language": locale }).catch(() => {});
      await page.goto(p.url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(3000);
      await page.bringToFront().catch(() => {});

      if (args.waitForLogin && !loggedIn.has(p.id)) {
        console.log(`\n=== 等待登录（${p.name}）===`);
        console.log("请在这个 Chrome 窗口里完成登录。脚本只读、不注入、不点击。");
        const reason = await waitForLogin(context, page, args, p);
        console.log(`登录阶段结束：${reason}`);
        if (reason === "timeout") {
          console.error("[ERROR] 登录等待超时——这一轮无法验证「已登录的真实会话」，中止。");
          await page.close();
          flushEvidence();
          return 3;
        }
        loggedIn.add(p.id);
        // 登录后页面可能已经跳到对话页，给它一点时间落定
        await page.waitForTimeout(2000);
      }

      console.log(
        `\n=== 观测 ${p.name} / ${locale} ===\n` +
          `请在浏览器窗口里输入「${args.prompt}」并**手动点击发送**（脚本不注入、不点击）。\n` +
          `等待上限 ${Math.round(args.timeout / 1000)} 秒。`,
      );

      const startedAt = new Date().toISOString();
      const samples = [];

      // 先起生产等待——它要自己记初始消息数
      await startProductionWait(page, p.id, args.timeout);

      // 再开始采样
      const deadline = Date.now() + args.timeout;
      let waitResult = null;
      let baselineCount = null;
      while (Date.now() < deadline) {
        const s = await sampleOnce(page, p.id);
        samples.push({ t: Date.now(), ...s });
        waitResult = await readProductionWait(page);
        if (typeof waitResult.baselineCount === "number") baselineCount = waitResult.baselineCount;
        if (waitResult.settled) {
          // 等待已定案，再采一次把定案那一刻的 DOM 留下来
          const final = await sampleOnce(page, p.id);
          samples.push({ t: Date.now(), ...final });
          break;
        }
        await page.waitForTimeout(SAMPLE_INTERVAL);
      }

      const observed = await collectObservedLanguage(page, p.id);
      const ev = buildEvidence({
        platform: p.id,
        platformName: p.name,
        url: p.url,
        locale,
        prompt: args.prompt,
        startedAt,
        samples,
        waitResult,
        baselineCount,
        observed,
      });
      evidence.push(ev);

      const v = ev.verdict;
      console.log(
        `[${p.name}/${locale}] 采样 ${ev.sampleCount} 次｜计数增长=${v.countGrew}｜` +
          `生成中解除=${v.typingCleared}｜页面正文非空=${v.contentNonEmpty}｜` +
          `生产取到的正文非空=${v.productionContentNonEmpty}｜` +
          `按生产口径会成功=${v.wouldResolve}｜实际界面语言=${v.observedLanguage}`,
      );
      if (v.localeMismatch) {
        console.log(
          `         ⚠️ 要求 ${locale}，但界面上实际是 ${v.observedLanguage}——` +
            "这一轮**不是**该语言的 DOM 契约",
        );
      }
      if (v.productionWaitError) {
        console.log(`         生产 waitForResponse 的结果：${v.productionWaitError}`);
      }
      if (!v.consistent) {
        console.log("         ⚠️ 生产实际结果与时间线重放不一致——两者都要看");
      }

      await page.close();
    }
  } catch (err) {
    // 观测器自身出错时，已采到的证据照样要落盘
    console.error("[ERROR] 观测过程中出错：", err.message);
    flushEvidence();
    return 2;
  } finally {
    await close().catch(() => {});
  }

  flushEvidence();
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    console.error("[ERROR] 观测器自身异常：", e);
    process.exit(2);
  });
