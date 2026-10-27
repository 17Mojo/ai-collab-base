/**
 * 测试台：起一个假的 chrome 环境，把**生产 service-worker** 跑起来。
 *
 * ## 为什么抽出来
 *
 * 此前这段只在 `extension-wiring.test.mjs` 里。2026-10-26 排演又查出一条
 * 「后台在 service worker 里调页面侧函数」的缺陷，要给它写守护用例时，
 * 需要的正是这套环境——与其抄一份（抄一份 = 又一个平行宇宙，
 * 生产接线断了它照样全绿），不如共用这一份。
 *
 * ## 关键点：sender
 *
 * `send()` 默认用**空 sender**（`{}`）——那正是 2026-10-26 之前所有测试的写法，
 * 于是 `sender.tab?.url` 恒为 undefined ⇒ `getAdapter("")` 恒为 null ⇒
 * 「后台能不能认出站点」这件事**从来没被测过**。
 * `sendAs()` 可以带上传入者，用来测这条路径。
 */

import assert from "node:assert/strict";

let swImportCounter = 0;

/**
 * 起一个假的 chrome 环境，把生产 service-worker 跑起来。
 *
 * @param {Object[]} packs - 放进 chrome.storage.local["packs"] 的 Pack
 * @param {Object} [options]
 * @param {any} [options.tabsSendMessageResponse] - 内容脚本对 SEND_TO_AI 的回话
 *   （默认 `{success: true, result: {content: "回声"}}`）。
 *   传 `{success: false, error: "..."}` 可以模拟「内容脚本报告失败」。
 * @returns {Promise<{listener: Function, send: Function, sendAs: Function, store: Object, tabMessages: Array}>}
 */
export async function loadServiceWorker(packs, options = {}) {
  const store = { packs };
  const listeners = [];
  const tabMessages = [];

  globalThis.chrome = {
    runtime: {
      sendMessage: async () => undefined,
      onInstalled: { addListener: () => {} },
      onMessage: {
        addListener: (fn) => listeners.push(fn),
      },
    },
    storage: {
      local: {
        get: async (key) => (key === "packs" ? { packs: store.packs } : {}),
        set: async (obj) => {
          Object.assign(store, obj);
        },
      },
      onChanged: { addListener: () => {} },
    },
    tabs: {
      onUpdated: { addListener: () => {} },
      sendMessage: async (tabId, msg) => {
        tabMessages.push({ tabId, msg });
        return options.tabsSendMessageResponse ?? {
          success: true,
          result: { content: "回声" },
        };
      },
    },
  };

  swImportCounter += 1;
  await import(`../../src/background/service-worker.js?bust=${swImportCounter}`);
  await new Promise((r) => setTimeout(r, 0));

  const listener = listeners[0];
  assert.ok(listener, "service-worker 必须注册 onMessage 监听器");

  /**
   * 给后台发一条消息并等它回话（**异步**回话型消息）。
   *
   * 断言 `keepAlive === true`：异步回话的消息必须保持通道开放，
   * 否则真实 Chrome 里 sendResponse 会被丢弃（消息直接哑掉）。
   *
   * @param {Object} message
   * @returns {Promise<any>}
   */
  const send = (message) =>
    new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error(`${message.type} 没有响应`)),
        5000,
      );
      const keepAlive = listener(message, {}, (r) => {
        clearTimeout(timer);
        resolve(r);
      });
      assert.equal(
        keepAlive,
        true,
        `${message.type} 的监听器必须返回 true（保持消息通道开放）`,
      );
    });

  /**
   * 给后台发一条消息并等它回话，**可以带上传入者**。
   *
   * 断言放宽到「不能返回 false」：`undefined`（同步 sendResponse）也是合法的
   * ——例如 GET_ADAPTER 就在监听器里同步回话。
   * `false` 则是明确表示「这条消息我不处理」⇒ 一定收不到回答。
   *
   * @param {Object} message
   * @param {Object} [sender] - 传入者（默认空）
   * @returns {Promise<any>}
   */
  const sendAs = (message, sender = {}) =>
    new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error(`${message.type} 没有响应`)),
        5000,
      );
      const keepAlive = listener(message, sender, (r) => {
        clearTimeout(timer);
        resolve(r);
      });
      // `true` = 异步回话，通道保持；`undefined` = 同步 sendResponse（同样有效，
      // 例如 GET_ADAPTER）；`false` = 明确表示不处理这条消息 ⇒ 一定收不到回答。
      assert.notEqual(
        keepAlive,
        false,
        `${message.type} 的监听器不能返回 false（那样消息就没人接了）`,
      );
    });

  return { listener, send, sendAs, store, tabMessages };
}
