/**
 * 登录助手（只登录，不发消息）
 *
 * ## 为什么需要它
 *
 * 2026-11-11 预检：deepseek 被重定向到 `/sign_in`（composerVisible=false），
 * longcat 是游客态（composerVisible=true 但页面带「请先登录」）。
 * 这两类阻塞**不是选择器能修的**——`findElements` 再准，也数不出一个没登录的账号
 * 不存在的消息。L2 的语义是「真实用户使用场景的端到端回归」，游客态不满足该语义，
 * 且历史会话不可复现（longcat 的 `/t` 短链会被重定向回首页）。
 *
 * 所以缺的是一次**真人登录**。本脚本只负责把窗口摆好、检测登录结果，
 * 登录态写进持久 profile（`rm-qianwen-l2-profile`），后续 `l2-platform-auto.mjs` 直接复用。
 *
 * ## 判据（两层，缺一层就会自欺）
 *
 * ### 第一层：**是否**已登录（决定 pass/fail）
 *
 * longcat 游客态**也能看到输入框**，只凭 composer 可见会误判成「已登录」。
 * 因此每个站点同时看三件事：
 *   1. composer（textarea / contenteditable / role=textbox）在视口内可见；
 *   2. 页面正文里**没有**登录提示语（「请先登录」「扫码登录」…）；
 *   3. URL 不在认证路径上（`sign_in` / `login` / `auth` / `passport`）。
 *
 * ### 第二层：登录的是**谁**（决定这条证据能不能用）
 *
 * 第一层只回答「有人登录了」。换一个号登录，第一层同样会亮绿灯——
 * 2026-11-11 的 dots 小号接入就差点栽在这：判定 `loggedIn: true`，
 * 但当时**没有任何字段能证明**登的是 `17Mojo` 还是新小号，
 * 只能回头读 `localStorage` 的 `auth_user_id` 才分清（两者相差 3 个数量级的账号）。
 *
 * 所以额外采集 `account`：
 *   - `userId`：`localStorage` 里键名匹配 `auth_user_id` / `user_id` / `uid` 的值；
 *   - `asideText`：侧栏文本（登录后含账号名与历史会话标题）；
 *   - `accountUnverified`：`loggedIn=true` 但**取不到 userId** 时置真
 *     —— 此时证据只能说「已登录」，不能说「是某某账号」。
 *
 * ⚠️ 已知边界：`userId` 取不到时**不能**反推为游客态。游客态是否也会有
 * `auth_user_id`（匿名身份）**未采样验证**，故该字段只用于**身份比对**，
 * 不参与第一层的 pass/fail —— 否则就是拿未验证的假设当判据。
 *
 * ## 硬红线
 *
 * 只打开页面并检测，**不发消息、不点发送、不导入 Pack、不改任何站点数据**。
 * 登录动作由真人在窗口里完成。
 *
 * ## 用法
 *
 *   SITES=deepseek,longcat WAIT_MIN=8 node tests/real-machine/login-helper.mjs
 *
 *   # 尚未登记的新平台（登记前必须先能登录，否则永远差一个环）
 *   SITES='dots@https://dots.ai' WAIT_MIN=8 node tests/real-machine/login-helper.mjs
 *
 * 环境变量：
 *   SITES     逗号分隔的平台 id（取自 tests/platforms.mjs）；
 *             也接受 `id@url` 形式，用于**尚未登记**的新平台——这类站点
 *             先要真人登录拿到账号态，之后才谈得上登记与探针。
 *   WAIT_MIN  最多等待分钟数（默认 8）
 *   PROFILE   持久 profile（默认与 l2-platform-auto.mjs 一致）
 *   OUT       结果 JSON 路径
 */

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { getPlatform } from "../platforms.mjs";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const EVIDENCE_DIR = `${REPO_ROOT}collaboration/results/real-machine-runs/evidence`;
const PROFILE =
  process.env.PROFILE ||
  `${homedir()}/Library/Application Support/rm-qianwen-l2-profile`;
const IDS = (process.env.SITES || "deepseek,longcat")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const WAIT_MIN = Number(process.env.WAIT_MIN || 8);
const TODAY = new Date();
const STAMP = `${TODAY.getFullYear()}-${String(TODAY.getMonth() + 1).padStart(2, "0")}-${String(
  TODAY.getDate(),
).padStart(2, "0")}`;
const OUT = process.env.OUT || `${EVIDENCE_DIR}/login-helper-${STAMP}.json`;

const LOGIN_HINTS = ["请先登录", "登录后", "扫码登录", "立即登录", "Sign in", "Log in"];
const AUTH_PATH = /sign[_-]?in|log[_-]?in|passport|\/auth|oauth/i;

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

async function probe(page) {
  return page
    .evaluate(
      ({ hints }) => {
        const comp = [...document.querySelectorAll(
          'textarea, div[contenteditable="true"], div[data-slate-editor="true"], [role="textbox"]',
        )].filter((el) => {
          const r = el.getBoundingClientRect();
          const st = window.getComputedStyle(el);
          return r.width > 50 && r.height > 10 && st.display !== "none" && st.visibility !== "hidden";
        });
        const body = (document.body?.innerText || "").slice(0, 20000);

        // —— 第二层：身份信号（只用于「是谁」，不参与 pass/fail）——
        const userIds = {};
        try {
          for (let i = 0; i < localStorage.length; i += 1) {
            const k = localStorage.key(i);
            if (/^(auth_user_id|user_?id|uid)$/i.test(k || "")) userIds[k] = localStorage.getItem(k);
          }
        } catch {
          /* 某些上下文禁用 localStorage，忽略 */
        }
        const aside = document.querySelector("aside, nav");
        const asideText = (aside?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 200);

        return {
          url: location.href,
          composerVisible: comp.length > 0,
          hints: hints.filter((t) => body.includes(t)),
          title: document.title,
          account: {
            userIds,
            userId: Object.values(userIds).find(Boolean) || null,
            asideText,
          },
        };
      },
      { hints: LOGIN_HINTS },
    )
    .catch((e) => ({ error: String(e.message).slice(0, 120) }));
}

function verdictOf(s) {
  if (!s || s.error) return { loggedIn: false, why: s?.error || "探测失败" };
  if (AUTH_PATH.test(s.url)) return { loggedIn: false, why: `仍在认证页 ${s.url}` };
  if (!s.composerVisible) return { loggedIn: false, why: "输入框不可见" };
  if (s.hints.length) return { loggedIn: false, why: `页面仍提示「${s.hints[0]}」` };
  // 第一层通过。第二层只是**标注**，绝不回头否定第一层。
  const accountUnverified = !s.account?.userId;
  return {
    loggedIn: true,
    why: accountUnverified
      ? "输入框可见 + 无登录提示 + 非认证路径（⚠️ 账号身份未取到，只能证明「有人登录了」）"
      : "输入框可见 + 无登录提示 + 非认证路径",
    accountUnverified,
  };
}

/**
 * 把 SITES 里的 token 解析成 { id, name, url }。
 *
 * `id@url` 是给**尚未登记**的新平台留的口子：新站点要先进登录态，
 * 才谈得上登记进 platforms.mjs（登记后 `getPlatform` 才有东西返回）。
 * 先登记再登录是行不通的——登记表要跟生产层 PLATFORM_CONFIGS 对齐，
 * 而生产层需要一个真的 adapter 与真的选择器。
 */
function resolveSpec(token) {
  const at = token.indexOf("@");
  if (at > 0) {
    const id = token.slice(0, at).trim();
    const url = token.slice(at + 1).trim();
    if (!id || !url) throw new Error(`SITES 里的 "${token}" 形式不合法，应为 id@url`);
    return { id, name: `${id}（未登记，按 URL 直连）`, url, unregistered: true };
  }
  const spec = getPlatform(token);
  if (!spec) throw new Error(`平台未登记: ${token}（若是新平台，用 id@url 形式）`);
  return spec;
}

async function main() {
  const specs = IDS.map(resolveSpec);

  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    viewport: null,
    args: ["--no-first-run", "--no-default-browser-check"],
  });

  const pages = [];
  for (const spec of specs) {
    const page = await context.newPage();
    await page.goto(spec.url, { waitUntil: "domcontentloaded", timeout: 60000 }).catch((e) => {
      log(`${spec.id} 打开失败: ${e.message.slice(0, 80)}`);
    });
    pages.push({ spec, page });
    log(`已打开 ${spec.name} — 请在窗口里完成登录`);
  }

  const deadline = Date.now() + WAIT_MIN * 60 * 1000;
  const results = new Map();
  while (Date.now() < deadline) {
    let allDone = true;
    for (const { spec, page } of pages) {
      if (results.get(spec.id)?.loggedIn) continue;
      const s = await probe(page);
      const v = verdictOf(s);
      results.set(spec.id, { platform: spec.id, state: s, ...v, checkedAt: new Date().toISOString() });
      if (!v.loggedIn) allDone = false;
    }
    if (allDone) {
      log("✅ 全部站点已登录");
      break;
    }
    const pending = [...results.values()]
      .filter((r) => !r.loggedIn)
      .map((r) => `${r.platform}(${r.why})`)
      .join("  ");
    log("等待中:", pending);
    await new Promise((r) => setTimeout(r, 5000));
  }

  // 收尾再采样一次并截图，作为登录态证据
  for (const { spec, page } of pages) {
    const s = await probe(page);
    const v = verdictOf(s);
    results.set(spec.id, { platform: spec.id, state: s, ...v, checkedAt: new Date().toISOString() });
    await page
      .screenshot({ path: `${EVIDENCE_DIR}/login-${spec.id}-${STAMP}.png` })
      .catch(() => {});
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    mode: "login-helper",
    waitMinutes: WAIT_MIN,
    profile: PROFILE,
    results: [...results.values()],
  };
  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify(payload, null, 2));
  log("结果已写:", OUT);
  for (const r of payload.results) {
    const uid = r.state?.account?.userId;
    log(`${r.loggedIn ? "✅" : "❌"} ${r.platform} — ${r.why}`);
    if (r.loggedIn) {
      log(`    账号: ${uid ? `userId=${uid}` : "⚠️ 未取到 userId"}`);
      if (r.state?.account?.asideText) log(`    侧栏: ${r.state.account.asideText.slice(0, 80)}`);
    }
  }
  if (payload.results.some((r) => r.loggedIn && r.accountUnverified)) {
    log("⚠️ 有站点登录成功但账号身份未取到 —— 这份证据只能证明「有人登录了」，不能证明「是谁」");
  }

  await context.close();
  log("DONE");
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
