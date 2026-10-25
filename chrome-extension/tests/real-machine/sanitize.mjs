/**
 * 真实 DOM 快照的脱敏器
 *
 * 真实站点的 DOM 里可能有：
 *   - 登录后的用户标识（邮箱、手机号、昵称、头像 URL 里的 uid）
 *   - 会话令牌（URL query、data-* 属性里的长随机串）
 *   - 第三方脚本（内联代码、埋点）
 *
 * 快照要进 git 仓库，就必须先过这一关。**脱敏规则独立成模块**，
 * 是因为它是唯一有「漏了就出事」风险的一环——必须能被单测钉住，
 * 而不是藏在采集脚本里靠人眼看。
 *
 * 脱敏后的快照只用于**验证 DOM 结构与选择器命中**，
 * 不保留任何可还原的个人信息。
 */

import { JSDOM } from "jsdom";

/** 文本节点的保留上限——超长文本对 DOM 契约判定没有价值，只会撑大仓库。 */
export const MAX_TEXT_LENGTH = 400;

/** 单个属性值的保留上限。 */
export const MAX_ATTR_LENGTH = 200;

/**
 * class 属性的保留上限（单独放宽）。
 *
 * class 是**选择器命中依据**，截断它等于把要守的东西毁掉：
 * 2026-10-25 实测，千问的输入框 class 是一长串 Tailwind 工具类，
 * 按 200 字符截断后，选择器 `[class*="message"]` 之类的匹配就不可靠了。
 * class 里没有个人数据（真要防 uid 泄漏，正则那一档已经处理过了）。
 */
export const MAX_CLASS_LENGTH = 2000;

/** 会被整段丢弃的属性（可能携带令牌 / 用户标识）。 */
const DROPPED_ATTRS = new Set([
  "value",
  "srcdoc",
  "nonce",
  "integrity",
  "crossorigin",
  "data-session",
  "data-token",
  "data-user-id",
  "data-userid",
  "data-uid",
  "data-account",
]);

/** 会被整段丢弃的元素（内容本身没有契约价值，且常携带可执行代码）。 */
const DROPPED_ELEMENTS = ["script", "noscript", "template"];

/**
 * 文本脱敏规则。顺序有意义：先替邮箱，再替长数字串，最后兜底长随机串。
 */
const TEXT_RULES = [
  // 邮箱
  { re: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, repl: "[EMAIL]" },
  // 中国大陆手机号（带或不带 +86）
  { re: /(?:\+?86[-\s]?)?1[3-9]\d{9}/g, repl: "[PHONE]" },
  // 连续 8 位以上数字（含 uid / 订单号 / 时间戳毫秒）
  { re: /\d{8,}/g, repl: "[NUM]" },
  // 长十六进制 / base64 风格随机串（令牌）
  { re: /\b[A-Za-z0-9_-]{40,}\b/g, repl: "[TOKEN]" },
];

/**
 * **结构性属性**——class / id 的值是 DOM 结构的一部分，不是个人数据。
 *
 * 2026-10-25 实测踩到的坑：把「长随机串」规则套到 class 上，
 * 把 CSS Module 的哈希类名（40+ 字符）整个替换成了 `[TOKEN]`，
 * 于是快照里的选择器依据被抹掉——**脱敏反而毁掉了要守的东西**。
 *
 * class / id 上只做「数字串」与「邮箱」级别的脱敏（uid 常常嵌在类名里），
 * 长的哈希类名原样保留。
 */
const STRUCTURAL_ATTRS = new Set(["class", "id"]);

/**
 * 脱敏一段纯文本。
 * @param {string} text
 * @returns {string}
 */
export function sanitizeText(text) {
  if (!text) return "";
  let out = String(text);
  for (const { re, repl } of TEXT_RULES) {
    out = out.replace(re, repl);
  }
  out = out.replace(/\s+/g, " ").trim();
  if (out.length > MAX_TEXT_LENGTH) {
    out = out.slice(0, MAX_TEXT_LENGTH) + "…[TRUNCATED]";
  }
  return out;
}

/**
 * 脱敏一个属性值：URL 去掉 query 与 hash，其余走文本规则。
 *
 * class / id 走**结构保留**口径（见 STRUCTURAL_ATTRS）。
 * @param {string} name
 * @param {string} value
 * @returns {string}
 */
export function sanitizeAttributeValue(name, value) {
  if (value == null) return "";
  let out = String(value);
  if (/^(href|src|action|srcset|poster)$/i.test(name)) {
    // URL：去掉 query / hash——令牌多藏在 query 里
    out = out.replace(/([?#]).*$/, "$1[REDACTED]");
  }
  if (STRUCTURAL_ATTRS.has(String(name).toLowerCase())) {
    // 结构属性：只脱敏数字串与邮箱，保留 CSS Module 哈希类名
    out = out.replace(TEXT_RULES[0].re, TEXT_RULES[0].repl);
    out = out.replace(TEXT_RULES[1].re, TEXT_RULES[1].repl);
    out = out.replace(TEXT_RULES[2].re, TEXT_RULES[2].repl);
    if (out.length > MAX_CLASS_LENGTH) {
      out = out.slice(0, MAX_CLASS_LENGTH) + "…[TRUNCATED]";
    }
    return out;
  }
  out = sanitizeText(out);
  if (out.length > MAX_ATTR_LENGTH) {
    out = out.slice(0, MAX_ATTR_LENGTH) + "…[TRUNCATED]";
  }
  return out;
}

/**
 * 对一段 HTML 做脱敏。
 *
 * 处理顺序：
 *   1. 删掉 script / noscript / template（内容无契约价值）
 *   2. 删掉 on* 事件属性
 *   3. 删掉可能携带令牌的属性
 *   4. 其余属性值脱敏
 *   5. 文本节点脱敏
 *
 * @param {string} html - 原始 HTML 片段
 * @returns {string} 脱敏后的 HTML
 */
export function sanitizeHtml(html) {
  if (!html) return "";
  const dom = new JSDOM(`<!doctype html><html><body>${html}</body></html>`);
  const doc = dom.window.document;

  for (const tag of DROPPED_ELEMENTS) {
    for (const el of doc.querySelectorAll(tag)) {
      el.remove();
    }
  }

  for (const el of doc.querySelectorAll("*")) {
    for (const attr of [...el.attributes]) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
        continue;
      }
      if (DROPPED_ATTRS.has(name)) {
        el.removeAttribute(attr.name);
        continue;
      }
      const cleaned = sanitizeAttributeValue(name, attr.value);
      if (cleaned !== attr.value) {
        el.setAttribute(attr.name, cleaned);
      }
    }
  }

  // 文本节点
  const walker = doc.createTreeWalker(doc.body, dom.window.NodeFilter.SHOW_TEXT);
  const textNodes = [];
  let node = walker.nextNode();
  while (node) {
    textNodes.push(node);
    node = walker.nextNode();
  }
  for (const tn of textNodes) {
    const cleaned = sanitizeText(tn.nodeValue);
    if (cleaned !== tn.nodeValue) {
      tn.nodeValue = cleaned;
    }
  }

  return doc.body.innerHTML;
}

/**
 * 脱敏一段 HTML 并保留可读缩进。
 * @param {string} html
 * @returns {string}
 */
export function sanitizeHtmlPretty(html) {
  const clean = sanitizeHtml(html);
  if (!clean) return "";
  // 简易缩进：只对常见块级标签换行，够人读即可
  return clean
    .replace(/></g, ">\n<")
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .join("\n");
}
