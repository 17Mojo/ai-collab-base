/**
 * typingIndicator 的「忙闲判定」守卫 —— 2026-11-18 真机 723.44s 假超时的守护。
 *
 * ## 缺陷长什么样
 *
 * deepseek 的 typingIndicator 第一条原本是 `[class*="loading"]`。
 * 联网搜索那一步（step_5 写边界标注）会在页面上渲染**来源站点图标占位**：
 *
 *   <div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px">
 *
 * class 里带 `loading` ⇒ `findVisibleElement` 命中 ⇒ `isTyping()` **恒为 true**
 * ⇒ `handleWaitForResponse` 里的 `state.ready && !isTyping()` 永远不成立
 * ⇒ 白等 4×180s。真机截图同时证明：AI 回答**早已完整落在页面上**、输入框已空闲。
 *
 * 注意 `isElementRendered` 只看 display / visibility / opacity，**不看尺寸**，
 * 所以哪怕是 16×16 的小图标、哪怕是 0 尺寸的占位，只要不是 display:none
 * 就会被判「可见」。宽通配撞上这类元素，忙闲判定就永久失真。
 *
 * ## 守什么
 *
 *   1. 空闲页上任何带 loading 字样的**界面元素**都不能让 isTyping 变 true；
 *   2. 真正的生成信号（generating / 停止按钮）仍然要能判 true —— 不许为了
 *      修假超时把判据一起删空（那会变成「太早成功」，比超时更危险）。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

import DeepSeekAdapter from "../src/platforms/deepseek-adapter.js";

function site(html) {
  const dom = new JSDOM(`<!doctype html><html><body>${html}</body></html>`);
  global.window = dom.window;
  global.document = dom.window.document;
  return dom.window.document;
}

/** 真机空闲态就会存在的结构：联网搜索的来源站点图标占位。 */
const SEARCH_SOURCE_LOGOS = `
  <div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px;"></div>
  <div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px;"></div>
  <div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px;"></div>`;

test("DeepSeek：空闲页上的搜索来源图标（class 带 loading）不得被判成「正在生成」", () => {
  const doc = site(SEARCH_SOURCE_LOGOS);
  // 先确认诱饵真的在，且真的会被判「可见」（display 不是 none）
  assert.equal(doc.querySelectorAll('[class*="loading"]').length, 3, "先确认诱饵真的在");
  const adapter = new DeepSeekAdapter();
  assert.equal(
    adapter.isTyping(),
    false,
    "`[class*=\"loading\"]` 命中搜索来源图标就会让 isTyping 恒 true，" +
      "等待循环里 `state.ready && !isTyping()` 永不成立 ⇒ 每步必然超时",
  );
});

test("DeepSeek：空的落地页上 isTyping 为 false", () => {
  site("");
  const adapter = new DeepSeekAdapter();
  assert.equal(adapter.isTyping(), false);
});

test("DeepSeek：真正的生成信号仍然要判 true（不许把判据删空）", () => {
  site('<div class="is-generating-indicator"></div>');
  const adapter = new DeepSeekAdapter();
  assert.equal(
    adapter.isTyping(),
    true,
    "generating 通道被删空的话，流式生成中会被判「已完成」——那是「太早成功」，比超时更危险",
  );
});

test("DeepSeek：停止按钮可见时 isTyping 为 true", () => {
  site('<button aria-label="Stop generating"></button>');
  const adapter = new DeepSeekAdapter();
  assert.equal(adapter.isTyping(), true);
});

test("DeepSeek：生成信号被隐藏（display:none）时不算正在生成", () => {
  site('<div class="is-generating-indicator" style="display:none;"></div>');
  const adapter = new DeepSeekAdapter();
  assert.equal(adapter.isTyping(), false);
});
