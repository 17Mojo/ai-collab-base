# 任务：Chrome Extension 基础框架实现

**日期**: 2026-04-13
**优先级**: P0
**执行者**: CodeArts Agent
**参考文档**: `docs/CHROME_EXTENSION_ARCHITECTURE.md`

---

## 任务背景

Prompt Pack v2.0 需要一个 Chrome Extension 来实现 AI 聊天自动化。架构设计已完成，现在需要实现基础框架。

## 任务列表

### Task 1: 创建 Manifest V3 基础结构

**目标**: 创建 Chrome Extension 的基础文件结构

```bash
# 创建目录结构
mkdir -p chrome-extension/src/{background,content,popup,platforms,utils}
mkdir -p chrome-extension/public
mkdir -p chrome-extension/dist
```

**文件清单**:

1. `chrome-extension/manifest.json` - Manifest V3 配置
```json
{
  "manifest_version": 3,
  "name": "Prompt Pack",
  "version": "0.1.0",
  "description": "AI Chat Automation with Prompt Pack v2.0",
  "permissions": ["storage", "activeTab", "scripting"],
  "host_permissions": ["https://claude.ai/*", "https://chat.openai.com/*"],
  "background": {
    "service_worker": "src/background/service-worker.js",
    "type": "module"
  },
  "content_scripts": [
    {
      "matches": ["https://claude.ai/*", "https://chat.openai.com/*"],
      "js": ["src/content/content-script.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "public/popup.html",
    "default_icon": {
      "16": "public/icons/icon16.png",
      "48": "public/icons/icon48.png",
      "128": "public/icons/icon128.png"
    }
  }
}
```

2. `chrome-extension/src/background/service-worker.js` - Service Worker 入口
3. `chrome-extension/src/content/content-script.js` - Content Script 入口
4. `chrome-extension/public/popup.html` - Popup 页面

### Task 2: 实现 Platform Adapter 接口

**目标**: 创建平台适配器抽象层

**文件**: `chrome-extension/src/platforms/adapter.js`

```javascript
/**
 * Platform Adapter Interface
 * 所有平台适配器必须实现此接口
 */
class PlatformAdapter {
  constructor(platformId) {
    this.platformId = platformId;
  }

  // 检测当前页面是否匹配此平台
  detect() {
    throw new Error('detect() must be implemented');
  }

  // 获取聊天输入框
  getChatInput() {
    throw new Error('getChatInput() must be implemented');
  }

  // 获取发送按钮
  getSendButton() {
    throw new Error('getSendButton() must be implemented');
  }

  // 获取消息列表
  getMessageList() {
    throw new Error('getMessageList() must be implemented');
  }

  // 注入文本到输入框
  async injectText(text) {
    throw new Error('injectText() must be implemented');
  }

  // 点击发送按钮
  async clickSend() {
    throw new Error('clickSend() must be implemented');
  }

  // 等待 AI 响应完成
  async waitForResponse(timeout = 60000) {
    throw new Error('waitForResponse() must be implemented');
  }
}

export default PlatformAdapter;
```

### Task 3: 实现 Claude.ai 适配器

**目标**: 实现 Claude.ai 平台的具体适配器

**文件**: `chrome-extension/src/platforms/claude-adapter.js`

参考 `docs/CHROME_EXTENSION_ARCHITECTURE.md` 中的选择器定义：
- 输入框: `div[contenteditable="true"]`
- 发送按钮: `button[aria-label="Send"]`
- 消息列表: `[data-testid="conversation-turn"]`

### Task 4: 实现 DOM Observer

**目标**: 监控 DOM 变化，检测 AI 响应状态

**文件**: `chrome-extension/src/utils/dom-observer.js`

功能：
- 监控消息列表变化
- 检测 AI 正在输入状态
- 检测 AI 响应完成状态
- 提供回调机制

### Task 5: 创建 Pack 执行引擎

**目标**: 实现 Pack 执行的核心逻辑

**文件**: `chrome-extension/src/background/pack-executor.js`

功能：
- 加载 Pack 定义
- 按步骤执行 workflow
- 管理执行状态
- 处理错误和重试

---

## 验收标准

| 任务 | 验收条件 |
|------|----------|
| Task 1 | manifest.json 验证通过，目录结构完整 |
| Task 2 | PlatformAdapter 类定义完整，包含所有必需方法 |
| Task 3 | ClaudeAdapter 能正确检测页面元素 |
| Task 4 | DOM Observer 能检测消息变化 |
| Task 5 | Pack Executor 能执行简单 workflow |

---

## 技术约束

1. **Manifest V3**: 必须使用 Manifest V3，不支持 V2
2. **ES Modules**: 使用 ES Modules 而非 CommonJS
3. **无外部依赖**: 核心功能不依赖第三方库
4. **最小权限**: 只请求必要的权限

---

## 完成后回复

```
A.ACK|task=chrome-extension-base|status=ok|result=chrome-extension/ 目录创建完成
```

---

**创建时间**: 2026-04-13T23:30:00
**有效期**: 2 小时
