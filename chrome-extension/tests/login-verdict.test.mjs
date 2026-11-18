/**
 * 登录判据测试（台账 N34）
 *
 * 守的是一条具体的错误结论，不是一段代码：
 * 2026-11-18 stepfun 实测，游客态首页同样渲染输入框，而脚本当时只判「输入框可见」，
 * 于是「未登录」被判成「已登录」，照常导入 Pack 发消息、超时，产出
 * `step_2_hook failed: Response timeout` —— 把「没登录」误诊成「产品链路超时」。
 *
 * 所以第一个用例就是回归钉子：**composer 可见 + 有登录提示 ⇒ 未登录**。
 * 若有人把判据简化回 `composerVisible`，这条会立刻变红。
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import { AUTH_PATH, LOGIN_HINTS, verdictOf } from "./real-machine/login-verdict.mjs";

const OK_STATE = {
  url: "https://studio.stepfun.com/",
  composerVisible: true,
  hints: [],
  account: { userId: "123", asideText: "17Mojo" },
};

test("N34 回归：composer 可见但页面有登录提示 ⇒ 判未登录，不是已登录", () => {
  const v = verdictOf({ ...OK_STATE, hints: ["登录 / 注册"] });
  assert.equal(v.loggedIn, false);
  assert.match(v.why, /登录 \/ 注册/);
});

test("N34 回归：composer 可见但仍在认证页 ⇒ 判未登录", () => {
  const v = verdictOf({ ...OK_STATE, url: "https://chat.deepseek.com/sign_in" });
  assert.equal(v.loggedIn, false);
  assert.match(v.why, /认证页/);
});

test("composer 不可见 ⇒ 判未登录", () => {
  const v = verdictOf({ ...OK_STATE, composerVisible: false });
  assert.equal(v.loggedIn, false);
  assert.match(v.why, /输入框不可见/);
});

test("三条件全过 ⇒ 判已登录", () => {
  const v = verdictOf(OK_STATE);
  assert.equal(v.loggedIn, true);
  assert.equal(v.accountUnverified, false);
});

test("取不到 userId 只标注 accountUnverified，不回头否掉「已登录」", () => {
  // 已知边界：游客态是否也带匿名 auth_user_id 未采样验证，
  // 故该字段只用于身份比对，不参与 pass/fail —— 否则是拿未验证的假设当判据。
  const v = verdictOf({ ...OK_STATE, account: { userId: null, asideText: "" } });
  assert.equal(v.loggedIn, true, "第一层通过后不得被第二层推翻");
  assert.equal(v.accountUnverified, true);
  assert.match(v.why, /账号身份未取到/);
});

test("探测本身失败 ⇒ 判未登录，并把错误带进 why", () => {
  const v = verdictOf({ error: "Execution context was destroyed" });
  assert.equal(v.loggedIn, false);
  assert.match(v.why, /context was destroyed/);
  assert.equal(verdictOf(null).loggedIn, false);
});

test("hints 缺失或非数组时不得抛错（页面取值可能降级）", () => {
  assert.equal(verdictOf({ ...OK_STATE, hints: undefined }).loggedIn, true);
  assert.equal(verdictOf({ ...OK_STATE, hints: ["请先登录"] }).loggedIn, false);
});

test("AUTH_PATH 覆盖各站分隔符写法", () => {
  for (const u of [
    "https://x/sign_in",
    "https://x/sign-in",
    "https://x/signin",
    "https://x/log_in",
    "https://x/login",
    "https://x/passport/1",
    "https://x/auth/cb",
    "https://x/oauth",
  ]) {
    assert.equal(AUTH_PATH.test(u), true, `应判认证路径: ${u}`);
    assert.equal(verdictOf({ ...OK_STATE, url: u }).loggedIn, false, `应判未登录: ${u}`);
  }
  assert.equal(AUTH_PATH.test("https://studio.stepfun.com/"), false);
  assert.equal(AUTH_PATH.test("https://chat.deepseek.com/a/chat"), false);
});

test("提示语清单是「非空数组」且含 stepfun 游客态那条 CTA", () => {
  assert.ok(Array.isArray(LOGIN_HINTS) && LOGIN_HINTS.length > 0);
  assert.ok(LOGIN_HINTS.includes("登录 / 注册"), "stepfun 游客态侧栏 CTA，缺了会漏判");
});
