/**
 * 平台登记表（**测试侧唯一事实源**）
 *
 * 背景：平台清单此前分散在**三处**——
 *   1. `tests/adapter-matrix/adapter-test-runner.js` 的 PLATFORMS（模拟层，10 家）
 *   2. `tests/real-machine/dom-contract-probe.mjs` 的 PLATFORMS（真机层，**只有 3 家**）
 *   3. `src/content/content-script.js` 的 PLATFORM_CONFIGS（生产层，16 个 hostname）
 *   4. `src/background/multi-platform-executor.js` 的 platformUrls（生产层，10 个 URL）
 *
 * 三四处各写一份，就会重演 2026-10-25 抓到的那个缺陷的老毛病：
 * **一处更新了、另几处没更新，谁也不知道**——真机探针漏掉 7 家平台，
 * 正是「清单只登记 3 家」的直接后果。
 *
 * 现在三处（矩阵 / 真机探针 / 真机观测器）都从**本文件**派生；
 * 生产层的两处**不改**（超出本工单范围），但由
 * `tests/platform-registry.test.mjs` 做**跨文件一致性守护**，
 * 一旦生产层与本登记表对不上，测试立刻报红。
 *
 * **不登记选择器**：选择器一律从生产 adapter 模块读取（`import()` 后取 SELECTORS），
 * 这里只登记「平台 ↔ 域名 ↔ 站点 ↔ 模块 ↔ fixture」的对应关系。
 * 登记选择器 = 复制一份 = 漂移的温床（2026-10-25 的真机缺陷正是这么潜伏的）。
 */

/**
 * @typedef {object} PlatformSpec
 * @property {string} id          - 平台标识（同时是记录器 / 工单里的 platform 名）
 * @property {string} name        - 显示名称
 * @property {string[]} hostnames - 生产层用于识别该平台的域名
 * @property {string} url         - 真机探针 / 观测器访问的站点首页
 * @property {string} module      - 生产 adapter 文件名（相对 src/platforms/）
 * @property {string} fixture     - 模拟层 fixture 标识（对应 fixtures/mock-dom-<fixture>.html）
 */

/** @type {PlatformSpec[]} */
export const PLATFORMS = [
  {
    id: "chatgpt",
    name: "ChatGPT",
    hostnames: ["chat.openai.com", "chatgpt.com"],
    url: "https://chatgpt.com/",
    module: "chatgpt-adapter.js",
    fixture: "chatgpt",
  },
  {
    id: "claude",
    name: "Claude.ai",
    hostnames: ["claude.ai"],
    url: "https://claude.ai/",
    module: "claude-adapter.js",
    fixture: "claude",
  },
  {
    id: "gemini",
    name: "Gemini",
    hostnames: ["gemini.google.com"],
    url: "https://gemini.google.com/",
    module: "gemini-adapter.js",
    fixture: "gemini",
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    hostnames: ["chat.deepseek.com"],
    url: "https://chat.deepseek.com/",
    module: "deepseek-adapter.js",
    fixture: "deepseek",
  },
  {
    id: "kimi",
    name: "Kimi AI",
    hostnames: ["kimi.com", "kimi.moonshot.cn"],
    url: "https://www.kimi.com/",
    module: "kimi-adapter.js",
    fixture: "kimi",
  },
  {
    id: "longcat",
    name: "LongCat AI",
    hostnames: ["longcat.chat", "longcat.ai"],
    url: "https://longcat.chat/",
    module: "longcat-adapter.js",
    fixture: "longcat",
  },
  {
    id: "qianwen",
    name: "Qianwen (千问)",
    hostnames: ["qianwen.com", "qianwen.aliyun.com", "tongyi.aliyun.com"],
    url: "https://www.qianwen.com/",
    module: "qianwen-adapter.js",
    fixture: "qianwen",
  },
  {
    id: "yiyan",
    name: "Yiyan (文心一言)",
    hostnames: ["yiyan.baidu.com", "wenxin.baidu.com"],
    url: "https://yiyan.baidu.com/",
    module: "yiyan-adapter.js",
    fixture: "yiyan",
  },
  {
    id: "yuanbao",
    name: "Yuanbao (腾讯元宝)",
    hostnames: ["yuanbao.tencent.com"],
    url: "https://yuanbao.tencent.com/",
    module: "yuanbao-adapter.js",
    fixture: "yuanbao",
  },
  {
    id: "chatglm",
    name: "ChatGLM (智谱清言)",
    hostnames: ["chatglm.cn"],
    url: "https://chatglm.cn/",
    module: "chatglm-adapter.js",
    fixture: "chatglm",
  },
];

/**
 * 按 id 查平台。
 * @param {string} id
 * @returns {PlatformSpec|undefined}
 */
export function getPlatform(id) {
  return PLATFORMS.find((p) => p.id === id);
}

/**
 * 列出全部 hostname（跨文件一致性守护用）。
 * @returns {string[]}
 */
export function allHostnames() {
  return PLATFORMS.flatMap((p) => p.hostnames);
}
