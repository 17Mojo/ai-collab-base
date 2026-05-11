---
task_id: TASK-W10-D1-CONTENT-SCRIPT-DOM-TEST-001
change_id: content-script-real-dom-injection-test
status: completed
assignee: claude_code
reviewer: user
primary_skill: chrome_extension
support_skills: ["testing", "dom_automation", "browser_automation"]
acceptance_commands: "chrome-extension/tests/test-content-script-real.js"
created_at: 2026-04-28T09:00:00
estimated_hours: 2.0
priority: P1
depends_on: []
---

# TASK-W10-D1-CONTENT-SCRIPT-DOM-TEST-001

## 任务描述

在真实 AI 平台页面验证 Content Script DOM 注入和消息监听功能。

## 背景

Content Script 已编写完成，需要在真实环境验证注入和交互。

## 详细任务

### Task 1: Content Script 结构检查 (30min)

**检查项**:

| 文件 | 验证内容 |
|------|----------|
| content-script.js | 存在、结构完整 |
| DOM Observer | 监听逻辑正确 |
| 消息监听 | chrome.runtime.onMessage 正确 |

---

### Task 2: Claude.ai 平台测试 (40min)

**测试步骤**:

1. 打开 Chrome DevTools MCP 浏览器
2. 导航到 `https://claude.ai`
3. 验证 Content Script 注入
4. 测试输入框监听
5. 测试消息传递

**验证项**:
- `div[contenteditable="true"]` 输入框检测
- 输入内容变化监听
- `chrome.runtime.sendMessage` 调用成功

---

### Task 3: ChatGPT 平台测试 (40min)

**测试步骤**:

1. 导航到 `https://chat.openai.com`
2. 验证 ChatGPT Adapter 选择器
3. 测试输入框监听
4. 测试发送按钮检测

**验证项**:
- `#prompt-textarea` 输入框检测
- `button[data-testid="send-button"]` 检测

---

### Task 4: Gemini 平台测试 (30min)

**测试步骤**:

1. 导航到 `https://gemini.google.com`
2. 验证 Gemini Adapter 选择器
3. 测试输入框监听

**验证项**:
- `div[contenteditable="true"][aria-label*="prompt"]` 检测

---

### Task 5: 测试报告生成 (20min)

**位置**: `collaboration/results/CONTENT_SCRIPT_TEST_2026-04-28.md`

**内容**:
- 各平台注入结果
- DOM 选择器验证
- 消息传递测试
- 发现问题汇总

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 3 个平台注入测试 | 测试报告 |
| DOM 选择器匹配 | 元素检测 |
| 消息监听正确 | Console 日志 |
| 测试报告完整 | 文档检查 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| chrome-extension/tests/test-content-script-real.js | 新建 |
| collaboration/results/CONTENT_SCRIPT_TEST_2026-04-28.md | 新建 |

---

**创建时间**: 2026-04-28T09:00:00+08:00
