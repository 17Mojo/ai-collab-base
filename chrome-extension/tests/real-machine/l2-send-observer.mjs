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
 * 产出：tests/real-machine/evidence/L2-<platform>-<ts>.json
 */

import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

import { PLATFORMS, getPlatform } from "../platforms.mjs";
import { injectAdapter } from "./_bundle.mjs";
import { parseArgs, buildEvidence, SAMPLE_INTERVAL } from "./l2-model.mjs";

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

  console.log("=== L2 半自动发送观测器 ===");
  console.log(`平台：${targets.map((p) => p.name).join("、")}`);
  console.log(`语言：${args.locale}`);
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

  try {
    for (const p of targets) {
      await injectAdapter(context, `src/platforms/${p.module}`, p.id);
      const page = await context.newPage();
      await page.goto(p.url, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(3000);

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

      const ev = buildEvidence({
        platform: p.id,
        platformName: p.name,
        url: p.url,
        locale: args.locale,
        prompt: args.prompt,
        startedAt,
        samples,
        waitResult,
        baselineCount,
      });
      evidence.push(ev);

      const v = ev.verdict;
      console.log(
        `[${p.name}] 采样 ${ev.sampleCount} 次｜计数增长=${v.countGrew}｜` +
          `生成中解除=${v.typingCleared}｜页面正文非空=${v.contentNonEmpty}｜` +
          `生产取到的正文非空=${v.productionContentNonEmpty}｜` +
          `按生产口径会成功=${v.wouldResolve}`,
      );
      if (v.productionWaitError) {
        console.log(`         生产 waitForResponse 的结果：${v.productionWaitError}`);
      }
      if (!v.consistent) {
        console.log("         ⚠️ 生产实际结果与时间线重放不一致——两者都要看");
      }

      await page.close();
    }
  } finally {
    await close();
  }

  const outPath = args.out
    ? resolve(args.out)
    : join(HERE, "evidence", `L2-${targets[0].id}-${Date.now()}.json`);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, `${JSON.stringify(evidence, null, 2)}\n`, "utf-8");
  console.log(`\n证据已写入：${outPath}`);
  console.log(
    "登记方式：python3 scripts/real_machine_regression.py record --layer L2 ... --evidence-file <上面这个路径>",
  );

  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    console.error("[ERROR] 观测器自身异常：", e);
    process.exit(2);
  });
