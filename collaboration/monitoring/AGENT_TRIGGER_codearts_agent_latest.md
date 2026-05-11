# Agent Session Dispatch Payload

- Assignee: `codearts_agent` (CodeArts)
- GeneratedAt: `2026-04-13T23:45:00`
- Mode: `direct_execution`

## 任务：Chrome Extension 基础框架实现

### 任务背景

Prompt Pack v2.0 需要一个 Chrome Extension 来实现 AI 聊天自动化。架构设计已完成（见 `docs/CHROME_EXTENSION_ARCHITECTURE.md`），现在需要实现基础框架。

### 任务详情

**任务文件**: `collaboration/tasks/TASK_W6_CHROME_EXTENSION_BASE_2026-04-13.md`

### Task 1: 创建 Manifest V3 基础结构

```bash
# 创建目录结构
mkdir -p chrome-extension/src/{background,content,popup,platforms,utils}
mkdir -p chrome-extension/public/icons
mkdir -p chrome-extension/dist
```

创建以下文件：
1. `chrome-extension/manifest.json` - Manifest V3 配置
2. `chrome-extension/src/background/service-worker.js` - Service Worker 入口
3. `chrome-extension/src/content/content-script.js` - Content Script 入口
4. `chrome-extension/public/popup.html` - Popup 页面

### Task 2: 实现 Platform Adapter 接口

创建 `chrome-extension/src/platforms/adapter.js`：
- 定义 PlatformAdapter 抽象类
- 包含 detect(), getChatInput(), getSendButton() 等方法

### Task 3: 实现 Claude.ai 适配器

创建 `chrome-extension/src/platforms/claude-adapter.js`：
- 继承 PlatformAdapter
- 实现 Claude.ai 特定的选择器

### Task 4: 实现 DOM Observer

创建 `chrome-extension/src/utils/dom-observer.js`：
- 监控消息列表变化
- 检测 AI 响应状态

### Task 5: 创建 Pack 执行引擎

创建 `chrome-extension/src/background/pack-executor.js`：
- 加载 Pack 定义
- 执行 workflow 步骤

### 参考文档

```bash
# 查看架构设计
cat docs/CHROME_EXTENSION_ARCHITECTURE.md
```

### 验收命令

```bash
# 检查文件结构
ls -la chrome-extension/
ls -la chrome-extension/src/
```

### 完成后回复

```
A.ACK|task=chrome-extension-base|status=ok|result=chrome-extension/ 目录创建完成
```

---

**创建时间**: 2026-04-13T23:30:00
**有效期**: 2 小时
