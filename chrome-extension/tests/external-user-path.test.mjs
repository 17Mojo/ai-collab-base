/**
 * 外部用户走的那条路 —— 2026-10-26 排演（W-D1）查出来的三处断点
 *
 * ## 为什么要有这份测试
 *
 * 2026-10-26 照着《第一次试用指南》做了一遍**排演**（照着指南走一遍，
 * 记下哪里卡住）。指南说外部用户 5 步就能把提示词发出去。排演的结果是：
 * **三步都走不到**——而且每一步都是**确定性的断点**，不是时序问题：
 *
 *   ① **真站上没有内容脚本**
 *      manifest 的 `content_scripts.matches` 写的是 `https://qianwen.com/*`，
 *      而千问的真站是 `https://www.qianwen.com/`。Chrome 的 host 匹配里
 *      `qianwen.com` **只等于** `qianwen.com`，不等于 `www.qianwen.com`
 *      （`*.` 才是通配）⇒ 内容脚本**根本没注入** ⇒ 那个页面上扩展等于没装。
 *      Kimi 同病（真站 www.kimi.com）。
 *      ⇒ 真机实测：www.qianwen.com 上页面控制台**没有**内容脚本的日志；
 *        同一次会话里 qianwen.aliyun.com / longcat.chat **有**。
 *
 *   ② **后台在 service worker 里调了页面侧函数**
 *      `getAdapter()` 调 `adapter.detect()`，而 detect() 读
 *      `window.location.hostname` —— MV3 的 service worker 里**没有 window**
 *      ⇒ `ReferenceError` ⇒ 整个 onMessage 处理器挂掉 ⇒ 永远不 sendResponse
 *      ⇒ 内容脚本初始化时那句 GET_ADAPTER 收不到回答 ⇒
 *      「No adapter available for this page」⇒ `currentConfig` 恒为 null
 *      ⇒ 之后每一次发送都抛同一句话。
 *      ⇒ **改之前，扩展在任何一个站点上都拿不到适配器。**
 *
 *   ③ **导入界面比后台更严**
 *      前端只认 `{packs:[...]}`，后台两种形状都收（单个 Pack 也收）。
 *      于是外部用户照着指南导入 `packs/examples/external-user-smoke.json`
 *      （单个 Pack）时，前端报「文件格式错误: 无效的 Pack 导入格式」，
 *      连「合并 / 覆盖」都出不来 ⇒ 指南第 4 步直接断掉。
 *
 * 这三条之前都没有测试守着：矩阵只测 adapter 本身，接线测试只测
 * 「消息类型对不对得上」，**没有一个测试从「外部用户点下去」这一端看**。
 * 这份测试就是从那一端看。
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { createRequire } from "node:module";
import { JSDOM } from "jsdom";

import { loadServiceWorker } from "./helpers/service-worker-harness.mjs";
import { PLATFORMS } from "./platforms.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EXT_ROOT = resolve(HERE, "..");
const require = createRequire(import.meta.url);

/**
 * 只跑一个 AI 步骤的 Pack（与 extension-wiring.test.mjs 里那份同形）。
 */
const AI_PACK = {
  metadata: { pack_id: "wiring-ai", pack_name: "外部用户路径自检·AI" },
  workflow: {
    steps: [
      {
        id: "step_ai",
        type: "ai",
        prompt_template: "你好",
        // 不重试：失败路径默认会重试 3 次、每次隔 1 秒，
        // 让单测每次多花 3 秒，而这里要验的是错误**怎么说**
        retry: false,
      },
    ],
  },
};

// ─────────────────────────────────────────────────────────────────────
// 工具：Chrome 的 host 匹配模式
// ─────────────────────────────────────────────────────────────────────

/**
 * 判断一个 Chrome 匹配模式（`https://host/path`）能不能盖住某个 URL。
 *
 * Chrome 的规则（来自官方文档）：
 *   - host 可以是精确主机名（`qianwen.com`）——**只等于**它自己；
 *   - host 也可以是 `*.example.com` 形式——等于该域名**及其所有子域**；
 *   - path 部分这里一律是 `/*`，所以只关心 host 与 scheme。
 *
 * @param {string} pattern - 例如 "https://qianwen.com/*"
 * @param {string} url - 例如 "https://www.qianwen.com/"
 * @returns {boolean}
 */
export function patternCoversUrl(pattern, url) {
  const m = /^(\*|https?|file|ftp):\/\/([^/]*)(\/.*)$/.exec(pattern);
  if (!m) return false;
  const [, scheme, host] = m;
  let target;
  try {
    target = new URL(url);
  } catch {
    return false;
  }
  if (scheme !== target.protocol.replace(":", "")) return false;

  const patternHost = host.toLowerCase();
  const targetHost = target.hostname.toLowerCase();

  if (patternHost.startsWith("*.")) {
    const bare = patternHost.slice(2);
    // *.example.com 盖住 example.com 本身与所有子域
    return targetHost === bare || targetHost.endsWith(`.${bare}`);
  }
  return targetHost === patternHost;
}

/**
 * 平台注册表声称要支持的全部 URL。
 *
 * 用 `url`（真机探针实际访问的那个）+ `hostnames`（该平台的域名清单），
 * **不**自己发明 `www.` 变体——注册表没写的域名不必覆盖，
 * 否则这条守护就会逼着 manifest 挂上一堆不存在的站点。
 *
 * @param {import("./platforms.mjs").PlatformSpec} platform
 * @returns {string[]}
 */
function requiredUrls(platform) {
  const urls = [];
  if (platform.url) urls.push(platform.url);
  for (const h of platform.hostnames || []) urls.push(`https://${h}/`);
  return urls;
}

// ─────────────────────────────────────────────────────────────────────
// ① manifest 的站点覆盖
// ─────────────────────────────────────────────────────────────────────

test("manifest 必须盖住平台注册表声称支持的**全部**站点", () => {
  const manifest = JSON.parse(
    readFileSync(join(EXT_ROOT, "manifest.json"), "utf-8"),
  );
  const matches = manifest.content_scripts[0].matches;
  const hostPermissions = manifest.host_permissions;

  const missing = [];
  for (const platform of PLATFORMS) {
    for (const url of requiredUrls(platform)) {
      if (!matches.some((p) => patternCoversUrl(p, url))) {
        missing.push(
          `${platform.id}: ${url} 没有被 content_scripts.matches 覆盖` +
            "（那个站点上没有内容脚本 = 扩展等于没装）",
        );
      }
      if (!hostPermissions.some((p) => patternCoversUrl(p, url))) {
        missing.push(`${platform.id}: ${url} 没有被 host_permissions 覆盖`);
      }
    }
  }

  assert.deepEqual(
    missing,
    [],
    `manifest 漏掉了这些站点：\n${missing.join("\n")}`,
  );
});

test("host_permissions 与 content_scripts.matches 必须是同一份清单", () => {
  const manifest = JSON.parse(
    readFileSync(join(EXT_ROOT, "manifest.json"), "utf-8"),
  );
  const a = [...manifest.host_permissions].sort();
  const b = [...manifest.content_scripts[0].matches].sort();
  assert.deepEqual(
    a,
    b,
    "两份清单各写各的 ⇒ 迟早漂移（2026-10-26 实测：manifest.dist.json 就这样少了一个站点）",
  );
});

test("构建产物的 manifest 必须由 manifest.json 生成（不再有手写的第二份）", () => {
  // 此前仓库里有 manifest.dist.json，构建时**优先复制它** ⇒
  // 改 manifest.json 根本不生效。现在产物里的 manifest 由源 manifest 生成。
  const { buildDistManifest } = require("../static-assets.cjs");
  const src = JSON.parse(readFileSync(join(EXT_ROOT, "manifest.json"), "utf-8"));
  const dist = buildDistManifest(src);

  assert.deepEqual(
    dist.host_permissions,
    src.host_permissions,
    "站点清单不许在产物里被改写",
  );
  assert.deepEqual(
    dist.content_scripts[0].matches,
    src.content_scripts[0].matches,
    "站点清单不许在产物里被改写",
  );
  // 路径要按产物的扁平布局改写
  assert.equal(dist.background.service_worker, "service-worker.js");
  assert.deepEqual(dist.content_scripts[0].js, ["content-script.js"]);
  assert.equal(dist.action.default_popup, "popup.html");
  assert.equal(dist.action.default_icon["16"], "icons/icon16.png");
});

// ─────────────────────────────────────────────────────────────────────
// ② 后台必须能在 service worker 里认出站点
// ─────────────────────────────────────────────────────────────────────

test("后台要能从「发消息过来的那个标签页的 URL」认出平台（service worker 里没有 window）", async () => {
  const { sendAs } = await loadServiceWorker([]);

  // 2026-10-26 修之前：getAdapter() 里调 adapter.detect()，
  // 而 detect() 读 window.location.hostname —— service worker 里没有 window
  // ⇒ ReferenceError ⇒ 整个处理器挂掉 ⇒ 这里根本收不到回答。
  const response = await sendAs(
    { type: "GET_ADAPTER" },
    { tab: { url: "https://www.qianwen.com/" } },
  );

  assert.ok(response, "GET_ADAPTER 必须回话（不回话 = 处理器抛异常了）");
  assert.equal(
    response.adapterId,
    "qianwen.com",
    "www.qianwen.com 应当被认成千问（适配器的 platformId 是 qianwen.com）",
  );
});

test("后台对**每一个**平台都能从 URL 认出适配器（别只测一个）", async () => {
  const { sendAs } = await loadServiceWorker([]);

  const wrong = [];
  for (const platform of PLATFORMS) {
    if (!platform.url) continue;
    const response = await sendAs(
      { type: "GET_ADAPTER" },
      { tab: { url: platform.url } },
    );
    if (!response || !response.adapterId) {
      wrong.push(`${platform.id}（${platform.url}）→ ${JSON.stringify(response)}`);
    }
  }

  assert.deepEqual(
    wrong,
    [],
    `这些站点后台认不出来（认不出来 = 内容脚本拿不到适配器 = 整条链路是死的）：\n${wrong.join("\n")}`,
  );
});

test("不是 AI 站点的 URL 不该被认成任何平台（别把「什么都认」测成通过）", async () => {
  const { sendAs } = await loadServiceWorker([]);
  const response = await sendAs(
    { type: "GET_ADAPTER" },
    { tab: { url: "https://example.com/index.html" } },
  );
  assert.equal(
    response?.adapterId ?? null,
    null,
    "example.com 不是 AI 站点，不该有适配器",
  );
});

// ─────────────────────────────────────────────────────────────────────
// ④ 内容脚本报告失败时，执行器不许说「成功」
// ─────────────────────────────────────────────────────────────────────

test("内容脚本报告失败时，整个 Pack 必须失败（不许 popup 显示「执行成功」）", async () => {
  // 2026-10-26 排演实测（第二十二步）：修好前三处断点后，
  // 排演在**匿名会话**下拿到了 popup 的「状态: 执行成功」，
  // 但页面上**提示词还留在输入框里**（压根没发出去），
  // 而且页面上有「登录」——即匿名会话被登录墙挡住了。
  //
  // 为什么会显示「执行成功」？内容脚本确实会如实报告失败
  // （`sendResponse({success:false, error})`），但**执行器没看**：
  // `_executeAIStep` 把回话原样返回，`_executeStep` 紧接着
  // 无条件 `stepResult.success = true` ⇒ 失败被吞成成功。
  //
  // 这条守护钉住：失败必须冒泡成失败。
  const { send } = await loadServiceWorker([AI_PACK], {
    tabsSendMessageResponse: {
      success: false,
      error: "No adapter available for this page",
    },
  });

  const response = await send({
    type: "EXECUTE_PACK",
    packId: "wiring-ai",
    input: {},
    tabId: 42,
  });

  assert.equal(
    response?.success,
    false,
    `内容脚本报告失败时，Pack 必须失败，实际：${JSON.stringify(response?.result || response)}`,
  );
  assert.match(
    response?.error || "",
    /adapter|失败|失败|fail/i,
    "错误信息里要能看到内容脚本说的原因",
  );
});

test("内容脚本成功时，Pack 必须成功（别把这条测成永远失败）", async () => {
  const { send } = await loadServiceWorker([AI_PACK]);
  const response = await send({
    type: "EXECUTE_PACK",
    packId: "wiring-ai",
    input: {},
    tabId: 42,
  });
  assert.equal(
    response?.success,
    true,
    `内容脚本成功时 Pack 必须成功，实际：${JSON.stringify(response?.error || response)}`,
  );
});

// ─────────────────────────────────────────────────────────────────────
// ③ 导入界面不许比后台更严
// ─────────────────────────────────────────────────────────────────────

/**
 * 在 jsdom 里把**生产 Pack 编辑器**跑起来，模拟外部用户选文件的那一步。
 *
 * @param {string} jsonText - 用户选中的文件内容
 * @param {string} fileName - 文件名
 * @returns {Promise<{status: string, optionsVisible: boolean, sent: any[], window: any}>}
 */
async function runEditorImport(jsonText, fileName) {
  const html = readFileSync(join(EXT_ROOT, "public", "pack-editor.html"), "utf-8");
  // runScripts: "dangerously" —— 生产脚本是经典脚本（<script src="pack-editor.js">），
  // 要在**窗口自己的 realm** 里跑，才能拿到 window/document。
  const dom = new JSDOM(html, {
    url: "chrome-extension://fake/pack-editor.html",
    runScripts: "dangerously",
  });
  const { window } = dom;

  const sent = [];
  // 后台侧的假实现：把导入的 Pack 真的收进去（与生产后台同语义）
  let storedPacks = [];
  window.chrome = {
    runtime: {
      sendMessage: async (msg) => {
        sent.push(msg);
        if (msg.type === "IMPORT_PACKS") {
          const parsed = JSON.parse(msg.jsonData);
          const incoming = Array.isArray(parsed?.packs)
            ? parsed.packs
            : parsed?.metadata || parsed?.pack_id
              ? [parsed]
              : [];
          const imported = [];
          const errors = [];
          for (const pack of incoming) {
            const packId = pack.metadata?.pack_id || pack.pack_id;
            if (!packId) {
              errors.push({ packId: "(无 id)", error: "缺少 metadata.pack_id" });
              continue;
            }
            storedPacks.push(pack);
            imported.push(packId);
          }
          return { imported, errors };
        }
        if (msg.type === "GET_ALL_PACKS") return { packs: storedPacks };
        if (msg.type === "REFRESH_PACKS") return { success: true };
        return {};
      },
      getURL: (p) => `chrome-extension://fake/${p}`,
    },
    storage: {
      local: { get: async () => ({}), set: async () => {} },
    },
  };

  // 生产脚本是经典脚本：直接在 jsdom 里执行
  const script = readFileSync(join(EXT_ROOT, "public", "pack-editor.js"), "utf-8");
  const scriptEl = window.document.createElement("script");
  scriptEl.textContent = script;
  window.document.body.appendChild(scriptEl);

  // 模拟「用户在文件选择框里选了一个文件」
  const file = new window.File([jsonText], fileName, { type: "application/json" });
  const input = window.document.getElementById("importFile");
  Object.defineProperty(input, "files", {
    value: Object.assign([file], { length: 1, item: (i) => file }),
    configurable: true,
  });
  input.dispatchEvent(new window.Event("change"));
  await new Promise((r) => setTimeout(r, 100));

  const status = window.document.getElementById("statusBar").textContent.trim();
  const optionsVisible =
    window.document.getElementById("importOptions").classList.contains("visible");

  return { status, optionsVisible, sent, window };
}

test("导入界面不许把「单个 Pack 文件」挡在门外（后台是收的）", async () => {
  const smokePack = readFileSync(
    join(EXT_ROOT, "..", "packs", "examples", "external-user-smoke.json"),
    "utf-8",
  );

  const { status, optionsVisible } = await runEditorImport(
    smokePack,
    "external-user-smoke.json",
  );

  assert.ok(
    optionsVisible,
    `选完文件后必须出现「合并 / 覆盖」选项，状态栏现在是：${status}`,
  );
  assert.ok(
    !status.includes("文件格式错误"),
    `单个 Pack 文件不该被判成格式错误，状态栏现在是：${status}`,
  );
});

test("选完文件后点「确认导入」，状态栏要出现指南承诺的那句话", async () => {
  const smokePack = readFileSync(
    join(EXT_ROOT, "..", "packs", "examples", "external-user-smoke.json"),
    "utf-8",
  );
  const { window, sent } = await runEditorImport(
    smokePack,
    "external-user-smoke.json",
  );

  window.document.getElementById("confirmImportBtn").click();
  await new Promise((r) => setTimeout(r, 200));

  const status = window.document.getElementById("statusBar").textContent.trim();
  assert.match(
    status,
    /导入成功: 1 个 Pack/,
    `指南承诺的成功标志必须真的出现（而且要留得住，别被后续刷新冲掉），状态栏现在是：${status}`,
  );

  const importMsg = sent.find((m) => m.type === "IMPORT_PACKS");
  assert.ok(importMsg, "必须把文件内容发给后台");
  assert.ok(
    JSON.parse(importMsg.jsonData).metadata?.pack_id === "external-user-smoke",
    "发后台的必须是用户选中的那个文件的内容（不能被前端改写）",
  );
});

test("真的不是 JSON 仍然要报错（别把闸门拆成没有闸门）", async () => {
  const { status, optionsVisible } = await runEditorImport(
    "这不是 JSON",
    "broken.json",
  );
  assert.ok(
    status.includes("文件格式错误"),
    `非 JSON 文件必须报错，状态栏现在是：${status}`,
  );
  assert.equal(optionsVisible, false, "非 JSON 文件不该出现「合并 / 覆盖」选项");
});
