/**
 * 生产 adapter 打包（真机三件套共用）
 *
 * 三个真机工具都需要同一件事：把**生产** adapter 源码（`src/platforms/*.js`）
 * 连同其依赖打成一个能在页面里直接执行的 IIFE。
 *   - `dom-contract-probe.mjs`   L1 只读契约探针
 *   - `l2-send-observer.mjs`     L2 半自动观测器
 *   - `snapshot-capture.mjs`     真实 DOM 快照采集器
 *
 * 三处各写一份 esbuild 配置，就会出现「探针打了包、观测器忘了打」这类
 * 静默不一致——而且**打进去的可能不是同一份生产代码**。
 * 所以打包逻辑只有这一份。
 *
 * 关键点：
 *   1. **不复制选择器**。打进去的是生产模块本身，页面里 `new Adapter()` 调的是
 *      生产的 `getChatInput()` / `getSendButton()` / `getMessageList()`。
 *   2. `globalName` 用 IIFE 形式，注入时必须显式挂到 `globalThis`
 *      （`addInitScript` 会把内容包进函数作用域，`var` 不是全局变量）。
 *   3. **按平台 id 建索引**而不是覆盖同一个全局名：`--profile-dir` 模式下
 *      多个平台共用一个 persistent context，init script 会**累积**——
 *      覆盖式写入会让后一个平台探到的是别人的 adapter。
 */

import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
export const EXT_ROOT = resolve(HERE, "../..");

/**
 * 把生产 adapter 打成可在页面里直接执行的 IIFE。
 *
 * @param {string} adapterRelPath - 相对仓库根的路径，如 'src/platforms/gemini-adapter.js'
 * @returns {Promise<string>} IIFE 源码
 */
export async function bundleAdapter(adapterRelPath) {
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
 * 构造注入脚本：把打好的 adapter 挂到 `globalThis.__PROBE_ADAPTERS__[platformId]`。
 *
 * @param {string} adapterCode - bundleAdapter 的产物
 * @param {string} platformId - 平台标识（作为 registry 的键）
 * @returns {string} 可直接交给 context.addInitScript({content}) 的脚本文本
 */
export function adapterInitScript(adapterCode, platformId) {
  return (
    `${adapterCode}\n` +
    `;globalThis.__PROBE_ADAPTERS__ = globalThis.__PROBE_ADAPTERS__ || {};` +
    `globalThis.__PROBE_ADAPTERS__[${JSON.stringify(platformId)}] = __PROBE_ADAPTER__;`
  );
}

/**
 * 把 adapter 注入到 context（按平台 id 建索引）。
 *
 * @param {import('playwright').BrowserContext} context
 * @param {string} adapterRelPath
 * @param {string} platformId
 * @returns {Promise<void>}
 */
export async function injectAdapter(context, adapterRelPath, platformId) {
  const code = await bundleAdapter(adapterRelPath);
  await context.addInitScript({ content: adapterInitScript(code, platformId) });
}
