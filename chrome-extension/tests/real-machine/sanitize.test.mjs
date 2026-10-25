/**
 * 脱敏器单测
 *
 * 脱敏是本工单里唯一「漏了就出事」的一环——真实 DOM 快照要进 git 仓库，
 * 里面不能有个人信息和令牌。所以它必须有单测钉住，而不是靠人眼看输出。
 *
 * 这里守的是**规则本身**，不是「刚好这几个例子脱敏了」。
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  sanitizeText,
  sanitizeAttributeValue,
  sanitizeHtml,
  sanitizeHtmlPretty,
  MAX_TEXT_LENGTH,
  MAX_CLASS_LENGTH,
} from "./sanitize.mjs";

test("邮箱被替换", () => {
  assert.equal(sanitizeText("请联系 zhang.san@example.com 获取"), "请联系 [EMAIL] 获取");
});

test("中国大陆手机号被替换", () => {
  assert.equal(sanitizeText("我的号是 13812345678 谢谢"), "我的号是 [PHONE] 谢谢");
});

test("带 +86 前缀的手机号被替换", () => {
  assert.ok(!sanitizeText("+8613812345678").includes("13812345678"));
});

test("连续 8 位以上数字被替换（uid / 订单号）", () => {
  assert.equal(sanitizeText("order 20261025123456 ok"), "order [NUM] ok");
});

test("短数字不被误伤（版本号、步数）", () => {
  assert.equal(sanitizeText("v1.2.3 build 42 step 7"), "v1.2.3 build 42 step 7");
});

test("长随机串被替换（令牌）", () => {
  const token = "a".repeat(50);
  assert.equal(sanitizeText(`token=${token}`), "token=[TOKEN]");
});

test("超长文本被截断并标记", () => {
  const long = "字".repeat(MAX_TEXT_LENGTH + 100);
  const out = sanitizeText(long);
  assert.ok(out.length <= MAX_TEXT_LENGTH + 20, "截断后长度应受限");
  assert.ok(out.includes("[TRUNCATED]"));
});

test("空白被折叠", () => {
  assert.equal(sanitizeText("  a   b \n c  "), "a b c");
});

test("URL 的 query 与 hash 被抹掉（令牌常藏在这里）", () => {
  const out = sanitizeAttributeValue("href", "https://x.com/a?token=secret&b=2#frag");
  assert.ok(!out.includes("secret"), `query 里的令牌不该留下：${out}`);
  assert.ok(out.includes("[REDACTED]"));
});

test("URL 的 path 部分保留（结构信息有用）", () => {
  const out = sanitizeAttributeValue("href", "https://x.com/conversation/abc?token=secret");
  assert.ok(out.includes("/conversation/abc"), `path 应保留：${out}`);
});

test("class 属性不做长随机串脱敏（CSS Module 哈希类名是结构，不是令牌）", () => {
  // 注意这里必须用**超过 40 字符**的类名：令牌规则是 /\b[A-Za-z0-9_-]{40,}\b/，
  // 用短类名去测它等于没测（这条用例曾经就是这么空转的）。
  const cls = "_message-list-container_10y6s_1a2b3c4d5e6f7g8h9i";
  assert.ok(cls.length > 40, `样例类名必须超过 40 字符才能触发令牌规则，实际 ${cls.length}`);
  assert.equal(sanitizeAttributeValue("class", cls), cls);
});

test("class 属性里的邮箱仍然被脱敏", () => {
  const out = sanitizeAttributeValue("class", "user-zhang.san@example.com-box");
  assert.ok(!out.includes("@example.com"), `class 里的邮箱不该留下：${out}`);
});

test("class 属性里的长数字串仍被脱敏（uid 常常嵌在类名里）", () => {
  const out = sanitizeAttributeValue("class", "user-20261025123456");
  assert.ok(!out.includes("20261025123456"), `class 里的长数字不该留下：${out}`);
});

test("class 属性不被 200 字符上限截断（截断会毁掉选择器命中依据）", () => {
  const cls = "c".repeat(MAX_CLASS_LENGTH);
  assert.ok(sanitizeAttributeValue("class", cls).length >= MAX_CLASS_LENGTH);
});

test("普通属性受 200 字符上限约束", () => {
  // 用带空格的值：一整串 500 个 x 会被「长随机串」规则当成令牌替换掉，
  // 那条路径由上面的用例覆盖；这里测的是**长度上限**。
  const out = sanitizeAttributeValue("style", "color: red; ".repeat(50));
  assert.ok(out.includes("[TRUNCATED]"), `超长属性值应当被截断：${out.slice(0, 80)}`);
  assert.ok(out.length <= 220, `截断后长度应受限，实际 ${out.length}`);
});

test("script 元素被整段删除", () => {
  const out = sanitizeHtml('<div>ok</div><script>alert("x")</script>');
  assert.ok(!out.includes("script"), `script 不该留下：${out}`);
  assert.ok(out.includes("ok"));
});

test("noscript / template 被整段删除", () => {
  const out = sanitizeHtml("<noscript>ns</noscript><template>tpl</template><p>keep</p>");
  assert.ok(!out.includes("noscript"));
  assert.ok(!out.includes("template"));
  assert.ok(out.includes("keep"));
});

test("on* 事件属性被删除", () => {
  const out = sanitizeHtml('<div onclick="steal()" onmouseover="x()">hi</div>');
  assert.ok(!/onclick|onmouseover/i.test(out), `事件属性不该留下：${out}`);
});

test("value 属性被删除（输入框内容）", () => {
  const out = sanitizeHtml('<input type="password" value="hunter2">');
  assert.ok(!out.includes("hunter2"), `value 不该留下：${out}`);
});

test("data-token / data-uid 等可能带令牌的属性被删除", () => {
  const out = sanitizeHtml('<div data-token="abc" data-uid="42">x</div>');
  assert.ok(!out.includes("abc"));
  assert.ok(!out.includes("42"));
});

test("文本节点里的邮箱被脱敏", () => {
  const out = sanitizeHtml("<p>联系 zhang.san@example.com</p>");
  assert.ok(!out.includes("@example.com"), `文本里的邮箱不该留下：${out}`);
});

test("结构（标签、class）被保留——脱敏不能毁掉要守的东西", () => {
  const out = sanitizeHtml('<div class="ci-textarea ci-scroll-style" id="chat-textarea"></div>');
  assert.ok(out.includes("ci-textarea"), `class 应保留：${out}`);
  assert.ok(out.includes("chat-textarea"), `id 应保留：${out}`);
});

test("空输入返回空串", () => {
  assert.equal(sanitizeHtml(""), "");
  assert.equal(sanitizeText(""), "");
  assert.equal(sanitizeAttributeValue("href", null), "");
});

test("sanitizeHtmlPretty 输出可读缩进", () => {
  const out = sanitizeHtmlPretty("<div><p>a</p></div>");
  assert.ok(out.includes("\n"), `应当有换行：${out}`);
});
