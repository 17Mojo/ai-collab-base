/**
 * 登录判据（唯一事实源）
 *
 * ## 为什么单独抽出来
 *
 * 2026-11-18 实测暴露：`l2-platform-auto.mjs` 与 `l2-qianwen-auto.mjs` 各自写了一份
 * 「输入框可见 ⇒ 已登录」，而 stepfun 游客态首页**同样渲染输入框**，于是未登录被判成
 * 已登录，直接导入 Pack 发消息，白烧一轮真机并产出 `Response timeout`（台账 N34）。
 *
 * `login-helper.mjs` 里本来就有正确判据（三层），但它是脚本文件，import 会跑主流程，
 * 所以另外两份只能复制粘贴——复制出来的就是两把不同的尺子。这里把它抽成纯模块：
 * 判据只有一份，三个调用点都从这里取。
 *
 * ## 判据（第一层决定 pass/fail）
 *
 * 三件事同时成立才算已登录：
 *   1. composer（textarea / contenteditable / role=textbox）在视口内可见且尺寸合理；
 *   2. 页面正文里**没有**登录提示语（「请先登录」「扫码登录」「登录 / 注册」…）；
 *   3. URL 不在认证路径上（`sign_in` / `login` / `auth` / `passport` / `oauth`）。
 *
 * ⚠️ 不要退化成「只要 composer 可见就继续」——那正是 N34 本身。
 *
 * ## 已知残留风险（**故意的**，不是疏忽）
 *
 * 提示语是对 `document.body.innerText` 前 20000 字做**子串**匹配。若某个已登录页面的
 * 正文里恰好出现「登录后」这类词（例如历史会话标题叫「如何实现登录后跳转」），
 * 就会被判成未登录，本轮白等一个 LOGIN_WAIT。
 *
 * 之所以接受：这两种错的代价不对称——
 *   - **假阳性**（未登录判成已登录）会产生**归因错误**的证据：脚本照常发消息、超时，
 *     结论写成 `Response timeout`，把「没登录」误诊成「产品链路超时」，并诱导人去改
 *     重试/超时策略（N34 就是这么来的）；
 *   - **假阴性**（已登录判成未登录）不产生任何结论，且失败信息里带着命中的提示语原文，
 *     一眼能看出是文案误命中还是真没登录。
 *
 * 宁可无结论，也不要错结论。若将来要收紧，方向是「只在可交互元素内做精确全等匹配」，
 * 但必须先有真机证据表明子串匹配确实误伤过——否则就是用未验证的假设替换已验证的判据。
 *
 * ## 第二层：登录的是**谁**（只标注，不参与 pass/fail）
 *
 * `userId` 取不到时置 `accountUnverified=true`：此时证据只能说「有人登录了」，
 * 不能说「是某某账号」。**不反过来否掉第一层**——游客态是否也带匿名 `auth_user_id`
 * 未采样验证，拿未验证的假设当判据比缺字段更坏。
 */

/** 页面正文出现即判「未登录」的提示语。 */
export const LOGIN_HINTS = [
  "请先登录",
  "登录后",
  "扫码登录",
  "立即登录",
  "登录 / 注册", // 2026-11-18 stepfun：游客态首页也有输入框，但侧栏带这个 CTA
  "手机号登录",
  "邮箱登录",
  "Sign in",
  "Log in",
];

/** URL 命中即判「仍在认证页」。各站分隔符不一（sign_in / sign-in / signin / log_in）。 */
export const AUTH_PATH = /sign[_-]?in|log[_-]?in|passport|\/auth|oauth/i;

/**
 * 在页面里采一次登录相关状态。只读：不点、不发、不改任何站点数据。
 *
 * @param {{evaluate: Function}} page - Playwright Page
 * @returns {Promise<{url?: string, composerVisible?: boolean, hints?: string[],
 *   title?: string, account?: {userIds: Object, userId: string|null, asideText: string},
 *   error?: string}>}
 */
export async function probeLogin(page) {
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

/**
 * 由 {@link probeLogin} 的状态给出结论。纯函数，可单测。
 *
 * @param {Object} s - probeLogin 的返回
 * @returns {{loggedIn: boolean, why: string, accountUnverified?: boolean}}
 */
export function verdictOf(s) {
  if (!s || s.error) return { loggedIn: false, why: s?.error || "探测失败" };
  if (AUTH_PATH.test(String(s.url || ""))) return { loggedIn: false, why: `仍在认证页 ${s.url}` };
  if (!s.composerVisible) return { loggedIn: false, why: "输入框不可见" };
  if (Array.isArray(s.hints) && s.hints.length) {
    return { loggedIn: false, why: `页面仍提示「${s.hints[0]}」` };
  }
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
