---
task_id: TASK-W9-D2-PLATFORM-ADAPTER-TEST-002
change_id: platform-adapter-dom-injection-verification
status: completed
assignee: claude_code
reviewer: user
primary_skill: chrome_extension
support_skills: ["testing", "javascript", "dom_automation"]
acceptance_commands: "chrome-extension/tests/test-adapters.js"
created_at: 2026-04-27T09:00:00
estimated_hours: 2.0
priority: P1
depends_on: []
---

# TASK-W9-D2-PLATFORM-ADAPTER-TEST-002

## 任务描述

验证 10 个平台适配器的 DOM 注入和消息监听功能。

## 背景

Chrome Extension 包含 10 个平台适配器，需要验证每个适配器在对应平台的 DOM 注入是否正确。

## 详细任务

### Task 1: Adapter 文件结构验证 (30min)

**检查项**:

| Adapter | 文件 | 验证内容 |
|---------|------|----------|
| claude-adapter.js | 存在 | `getPromptSelector()`, `getResponseSelector()` |
| chatgpt-adapter.js | 存在 | 同上 |
| gemini-adapter.js | 存在 | 同上 |
| qianwen-adapter.js | 存在 | 同上 |
| kimi-adapter.js | 存在 | 同上 |
| chatglm-adapter.js | 存在 | 同上 |
| yiyan-adapter.js | 存在 | 同上 |
| yuanbao-adapter.js | 存在 | 同上 |
| longcat-adapter.js | 存在 | 同上 |
| adapter.js (base) | 存在 | 基类方法 |

---

### Task 2: DOM 选择器验证 (45min)

**验证每个适配器的 DOM 选择器**:

```javascript
// 示例验证代码
const adapter = new ClaudeAdapter();
const promptSelector = adapter.getPromptSelector();
const responseSelector = adapter.getResponseSelector();
const sendButtonSelector = adapter.getSendButtonSelector();

console.log(`Prompt: ${promptSelector}`);
console.log(`Response: ${responseSelector}`);
console.log(`Send: ${sendButtonSelector}`);
```

**验收标准**:
- 每个适配器返回有效选择器字符串
- 选择器格式符合 CSS selector 规范

---

### Task 3: 消息监听验证 (30min)

**验证 Content Script 消息监听**:

```javascript
// 模拟消息测试
chrome.runtime.sendMessage({
  type: 'GET_PROMPT_TEXT',
  platform: 'claude'
}, (response) => {
  console.log('Response:', response);
});
```

---

### Task 4: 测试报告生成 (15min)

**位置**: `collaboration/results/PLATFORM_ADAPTER_TEST_2026-04-27.md`

**内容**:
- 各 Adapter 验证结果
- DOM 选择器配置列表
- 发现问题汇总
- 改进建议

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 10 个 Adapter 文件存在 | `ls` 验证 |
| 每个 Adapter 有核心方法 | 代码审查 |
| DOM 选择器格式正确 | 单元测试 |
| 消息监听模拟测试 | 测试脚本 |
| 测试报告完整 | 文档检查 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| chrome-extension/tests/test-adapters.js | 新建 |
| collaboration/results/PLATFORM_ADAPTER_TEST_2026-04-27.md | 新建 |

---

**创建时间**: 2026-04-27T09:00:00+08:00
