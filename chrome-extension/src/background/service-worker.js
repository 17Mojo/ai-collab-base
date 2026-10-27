/**
 * Prompt Pack - Service Worker
 * Chrome Extension Background Script (Manifest V3)
 */

// 导入模块
import PlatformAdapter from "../platforms/adapter.js";
import ClaudeAdapter from "../platforms/claude-adapter.js";
import ChatGPTAdapter from "../platforms/chatgpt-adapter.js";
import GeminiAdapter from "../platforms/gemini-adapter.js";
import QianwenAdapter from "../platforms/qianwen-adapter.js";
import ChatGLMAdapter from "../platforms/chatglm-adapter.js";
import KimiAdapter from "../platforms/kimi-adapter.js";
import YiyanAdapter from "../platforms/yiyan-adapter.js";
import YuanbaoAdapter from "../platforms/yuanbao-adapter.js";
import LongCatAdapter from "../platforms/longcat-adapter.js";
import DeepSeekAdapter from "../platforms/deepseek-adapter.js";
import PackExecutor from "./pack-executor.js";
import NotebookLMPackExecutorBridge from "./notebooklm-packexecutor-bridge.js";

// 平台适配器注册表 — 11 个平台全部注册
// key: URL 中匹配的域名片段（用于 getAdapter() 的 url.includes(platform) 匹配）
// value: 对应的适配器实例
const adapters = {
  "claude.ai": new ClaudeAdapter(),
  "chat.openai.com": new ChatGPTAdapter(),
  "chatgpt.com": new ChatGPTAdapter(),
  "gemini.google.com": new GeminiAdapter(),
  "qianwen.aliyun.com": new QianwenAdapter(),
  "tongyi.aliyun.com": new QianwenAdapter(),
  "qianwen.com": new QianwenAdapter(),
  "chatglm.cn": new ChatGLMAdapter(),
  "kimi.moonshot.cn": new KimiAdapter(),
  "kimi.com": new KimiAdapter(),
  "yiyan.baidu.com": new YiyanAdapter(),
  "wenxin.baidu.com": new YiyanAdapter(),
  "yuanbao.tencent.com": new YuanbaoAdapter(),
  "longcat.ai": new LongCatAdapter(),
  "longcat.chat": new LongCatAdapter(),
  "chat.deepseek.com": new DeepSeekAdapter(),
};

// Pack 执行器实例
let packExecutor = null;

/**
 * 初始化扩展
 */
function initialize() {
  console.log(
    `[Prompt Pack] Service Worker initialized — ${Object.keys(adapters).length} platform adapters registered`,
  );
  packExecutor = new PackExecutor();
  // Pack 的事实源是 storage，执行器得自己同步过去。
  // 失败不致命：storage 读不到时执行器就是空的，报 "Pack not found"，
  // 比静默用一个错的 Pack 强。
  syncPacksToExecutor().catch((error) =>
    console.warn("[Prompt Pack] 同步 Pack 失败：", error.message),
  );
}

/**
 * 把 storage 里的 Pack 同步进执行器
 *
 * 此前执行器从来没有拿到过 Pack：loadPack() 定义了却没人调用，
 * 而 getPack() 读的是执行器自己那张表 ⇒ 恒为 null ⇒
 * 每次点「执行」都是 "Pack not found: <id>"。
 *
 * 事实源是 chrome.storage.local["packs"]（CREATE/UPDATE/DELETE/IMPORT
 * 都写它），所以同步的方向只能是 storage → 执行器。
 *
 * @returns {Promise<string[]>} 装进去的 pack_id
 */
async function syncPacksToExecutor() {
  if (!packExecutor) return [];
  const result = await chrome.storage.local.get("packs");
  const packs = result.packs || [];
  return packExecutor.replacePacks(packs);
}

/**
 * 从 URL 里取主机名（取不到就返回空串）。
 * @param {string} url
 * @returns {string}
 */
function hostOf(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

/**
 * 获取当前平台的适配器（遍历所有注册的平台，返回第一个匹配的）
 *
 * ## 为什么**不能**在这里调 `adapter.detect()`
 *
 * `detect()` 是**页面侧**函数——它读 `window.location.hostname`。
 * 而这个函数跑在 **service worker** 里：MV3 的 SW 没有 `window`
 * （2026-10-26 实测：`typeof window === "undefined"`），
 * 于是 `adapter.detect()` 抛 `ReferenceError: window is not defined`。
 *
 * 那个异常发生在 `chrome.runtime.onMessage` 的处理器里 ⇒
 * **整个处理器挂掉 ⇒ 永远不调用 sendResponse** ⇒
 * 内容脚本初始化时问的那句 GET_ADAPTER 收不到回答 ⇒
 * 它只能打印「No adapter available for this page」⇒
 * `currentConfig` 恒为 null ⇒ 之后每一次 SEND_TO_AI 都抛
 * 「No adapter available for this page」。
 *
 * 也就是说：**改之前，扩展在任何一个站点上都拿不到适配器**——
 * 整条 Pack 链路是死的，而且不报任何错（只是"没适配器"）。
 *
 * 所以这里改成**只按 URL 判定**：注册表的 key 本来就是
 * 「URL 中匹配的域名片段」，主机的子串判定与各 adapter 自己
 * `detect()` 里的写法一致（例如 `www.qianwen.com` 命中 `qianwen.com`）。
 * `detect()` 仍然保留——它是**页面侧**该用的函数（见 content-script）。
 *
 * @param {string} url - 当前页面 URL
 * @returns {{ adapter: PlatformAdapter, platformId: string }|null}
 */
function getAdapter(url) {
  const host = hostOf(url);
  if (!host) return null;
  for (const [platform, adapter] of Object.entries(adapters)) {
    if (host.includes(platform)) {
      return { adapter, platformId: adapter.platformId };
    }
  }
  return null;
}

// 监听扩展安装
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[Prompt Pack] Installed:", details.reason);
  initialize();
});

// 监听来自 Content Script 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("[Prompt Pack] Message received:", message.type);

  switch (message.type) {
    case "GET_ADAPTER":
      const adapter = getAdapter(sender.tab?.url || "");
      sendResponse({ adapterId: adapter?.platformId || null });
      break;

    case "EXECUTE_PACK":
      if (packExecutor) {
        (async () => {
          // 先同步一次：Pack 可能在执行器初始化之后才被创建/导入，
          // 不同步就是 "Pack not found"。
          await syncPacksToExecutor();
          try {
            const result = await packExecutor.execute(
              message.packId,
              message.input,
              // 目标标签页：popup 告诉后台「用户当前在哪个页面」，
              // AI 步骤据此精确投递，而不是给每个打开的 AI 页面都发一遍。
              { tabId: message.tabId ?? null },
            );
            // 执行器把失败**收进结果里**（status: "failed" + errors[]），
            // 不抛异常 ⇒ 这里必须看 status，不能一律回 success: true。
            //
            // 2026-10-26 排演实测：此前一律回 success:true，
            // 于是 popup 显示「执行成功」——而那次执行**压根没成功**
            // （匿名会话被登录墙挡住，提示词还留在输入框里）。
            // 「成功」两个字是假的，外部用户会以为链路通了。
            //
            // 守护：tests/external-user-path.test.mjs 的
            // 「内容脚本报告失败时，整个 Pack 必须失败」。
            if (result?.status === "failed") {
              sendResponse({
                success: false,
                error:
                  result.errors?.[0]?.message || "Pack 执行失败",
                result,
              });
            } else {
              sendResponse({ success: true, result });
            }
          } catch (error) {
            sendResponse({ success: false, error: error.message });
          }
        })();
        return true; // 保持消息通道开放
      }
      break;

    case "GET_PACK_STATUS":
      if (packExecutor) {
        const status = packExecutor.getStatus();
        sendResponse(status);
      }
      break;

    case "GENERATE_STUDIO_ARTIFACTS":
      (async () => {
        try {
          const bridge = new NotebookLMPackExecutorBridge();
          const artifacts = [];

          for (const contentType of message.contentTypes) {
            const result = await bridge.generateArtifact(
              message.notebookId,
              contentType,
              { focus: message.focus, language: "zh-CN" },
            );
            artifacts.push({ ...result, content_type: contentType });
          }

          sendResponse({ success: true, artifacts });
        } catch (error) {
          sendResponse({ success: false, error: error.message, artifacts: [] });
        }
      })();
      return true; // 保持消息通道开放

    case "GET_ALL_PACKS":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          const packs = result.packs || [];
          sendResponse({ packs });
        } catch (error) {
          sendResponse({ packs: [], error: error.message });
        }
      })();
      return true;

    case "CREATE_PACK":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          const packs = result.packs || [];
          const packId = message.packData?.metadata?.pack_id || message.packId;
          if (packs.some((p) => (p.metadata?.pack_id || p.pack_id) === packId)) {
            sendResponse({ success: false, error: `Pack 已存在: ${packId}` });
            return;
          }
          packs.push(message.packData);
          await chrome.storage.local.set({ packs });
          sendResponse({ success: true, packId });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case "UPDATE_PACK":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          const packs = result.packs || [];
          const packId = message.packId;
          const index = packs.findIndex(
            (p) => (p.metadata?.pack_id || p.pack_id) === packId,
          );
          if (index === -1) {
            sendResponse({ success: false, error: `Pack 不存在: ${packId}` });
            return;
          }
          packs[index] = message.packData;
          await chrome.storage.local.set({ packs });
          sendResponse({ success: true, packId });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case "DELETE_PACK":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          const packs = result.packs || [];
          const filtered = packs.filter(
            (p) => (p.metadata?.pack_id || p.pack_id) !== message.packId,
          );
          await chrome.storage.local.set({ packs: filtered });
          sendResponse({ success: true, packId: message.packId });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case "EXPORT_PACKS":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          let packs = result.packs || [];
          if (message.packIds && Array.isArray(message.packIds)) {
            packs = packs.filter((p) =>
              message.packIds.includes(p.metadata?.pack_id || p.pack_id),
            );
          }
          const data = JSON.stringify({ packs }, null, 2);
          sendResponse({ success: true, data });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case "IMPORT_PACKS":
      (async () => {
        try {
          const parsed = JSON.parse(message.jsonData);
          // 两种形状都收：
          //   - { "packs": [ ... ] }  批量导出格式
          //   - { "metadata": {...} }  单个 Pack 文件（packs/examples/ 下的
          //     每个文件都是这个形状）——此前只认前者，于是目录里那 16 个
          //     文件**一个都导不进来**（得到「没有找到任何 Pack」）。
          const incoming = Array.isArray(parsed?.packs)
            ? parsed.packs
            : parsed?.metadata || parsed?.pack_id
              ? [parsed]
              : [];
          if (incoming.length === 0) {
            sendResponse({
              imported: [],
              errors: [{ error: "没有找到任何 Pack（既没有 packs 数组，也不是单个 Pack）" }],
            });
            return;
          }
          const result = await chrome.storage.local.get("packs");
          const existing = result.packs || [];
          const imported = [];
          const errors = [];

          for (const pack of incoming) {
            const packId = pack.metadata?.pack_id || pack.pack_id;
            if (!packId) {
              errors.push({ packId: "(无 id)", error: "缺少 metadata.pack_id" });
              continue;
            }
            const exists = existing.some(
              (p) => (p.metadata?.pack_id || p.pack_id) === packId,
            );
            if (exists && message.mergeStrategy === "skip") {
              errors.push({ packId, error: "已存在，跳过" });
              continue;
            }
            if (exists && message.mergeStrategy === "overwrite") {
              const idx = existing.findIndex(
                (p) => (p.metadata?.pack_id || p.pack_id) === packId,
              );
              existing[idx] = pack;
            } else {
              existing.push(pack);
            }
            imported.push(packId);
          }

          await chrome.storage.local.set({ packs: existing });
          sendResponse({ imported, errors });
        } catch (error) {
          sendResponse({ imported: [], errors: [{ error: error.message }] });
        }
      })();
      return true;

    case "REFRESH_PACKS":
      (async () => {
        try {
          const result = await chrome.storage.local.get("packs");
          sendResponse({ success: true, packs: result.packs || [] });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      })();
      return true;

    case "SETTINGS_UPDATED":
      console.log("[Prompt Pack] Settings updated:", Object.keys(message.settings || {}));
      sendResponse({ success: true });
      break;

    default:
      sendResponse({ error: "Unknown message type" });
  }
});

// 监听标签页更新
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    const adapter = getAdapter(tab.url);
    if (adapter) {
      console.log(`[Prompt Pack] Platform detected: ${adapter.platformId}`);
    }
  }
});

// 监听 Pack 存储变化：Pack 编辑器、导入、删除都会写 storage.local["packs"]
// ⇒ 执行器要跟着更新，否则执行时拿到的是旧表。
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !changes.packs) return;
  syncPacksToExecutor().catch((error) =>
    console.warn("[Prompt Pack] 同步 Pack 失败：", error.message),
  );
});

// 初始化
initialize();
