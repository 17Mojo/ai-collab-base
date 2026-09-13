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
}

/**
 * 获取当前平台的适配器（遍历所有注册的平台，返回第一个匹配的）
 * @param {string} url - 当前页面 URL
 * @returns {{ adapter: PlatformAdapter, platformId: string }|null}
 */
function getAdapter(url) {
  for (const [platform, adapter] of Object.entries(adapters)) {
    if (url.includes(platform) && adapter?.detect?.()) {
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
        packExecutor
          .execute(message.packId, message.input)
          .then((result) => sendResponse({ success: true, result }))
          .catch((error) =>
            sendResponse({ success: false, error: error.message }),
          );
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
          const incoming = parsed.packs || [];
          const result = await chrome.storage.local.get("packs");
          const existing = result.packs || [];
          const imported = [];
          const errors = [];

          for (const pack of incoming) {
            const packId = pack.metadata?.pack_id || pack.pack_id;
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

// 初始化
initialize();
