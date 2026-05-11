---
task_id: TASK-W8-D5-CHROME-EXTENSION-TEST-005
change_id: chrome-extension-browser-integration-test
status: completed
assignee: claude_code
reviewer: user
primary_skill: chrome_extension
support_skills: ["testing", "javascript", "browser_automation"]
acceptance_commands: "chrome-extension/tests/e2e/test_popup_ui.html"
created_at: 2026-04-26T09:00:00
estimated_hours: 1.0
priority: P1
depends_on: ["TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002"]
---

# TASK-W8-D5-CHROME-EXTENSION-TEST-005

## 任务描述

在真实浏览器环境测试 Chrome Extension 功能，包括 Popup UI、知识增强执行、Studio 产物生成。

## 背景

Chrome Extension 基础框架已完成，需要在真实环境验证功能正确性。

## 详细任务

### Task 1: Extension 加载测试 (15min)

**操作步骤**:

1. 打开 Chrome 浏览器
2. 进入 `chrome://extensions/`
3. 开启开发者模式
4. 加载 `chrome-extension/` 目录
5. 验证 Extension ID 生成

**验证项**:
- Extension 图标显示
- Popup 打开正常
- Service Worker 运行

---

### Task 2: Popup UI 测试 (20min)

**测试场景**:

| 场景 | 操作 | 验证 |
|------|------|------|
| Pack 选择 | 点击 Pack 下拉 | 列表显示 17 个 Pack |
| 风格选择 | 选择风格 | 选项保存 |
| 平台勾选 | 勾选 Claude/Gemini | checkbox 状态 |
| 知识增强执行 | 点击按钮 | 消息发送成功 |
| Studio 面板 | 选择 Audio/Video | checkbox 可勾选 |

**截图要求**:
- Popup 整体截图
- Studio 面板截图

---

### Task 3: 知识增强执行测试 (20min)

**测试步骤**:

1. 打开 https://claude.ai
2. 打开 Extension Popup
3. 选择 Pack: `xiaohongshu_knowledge_creator`
4. 输入 prompt: "小红书创作原则"
5. 点击 "知识增强执行"
6. 等待响应

**验证**:
- Service Worker 收到 EXECUTE_WITH_KNOWLEDGE 消息
- Backend API 被调用
- 知识来源标注显示

---

### Task 4: Studio 产物生成测试 (25min)

**测试步骤**:

1. 打开 Popup
2. 进入 Studio 面板
3. 勾选 Audio + Slides
4. 输入 Focus: "知识型博主创作方法"
5. 点击 "生成 Studio 产物"
6. 观察 status area

**验证**:
- GENERATE_STUDIO_ARTIFACTS 消息发送
- Backend API /generate 调用
- Artifact ID 返回
- Status 显示 "生成中" → "完成"

---

### Task 5: 测试报告 (10min)

**位置**: `collaboration/results/CHROME_EXTENSION_TEST_REPORT_2026-04-26.md`

**内容**:
- 测试场景截图
- 功能验证结果
- 发现问题汇总
- 改进建议

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| Extension 加载成功 | Chrome 扩展列表显示 |
| Popup UI 渲染正常 | 截图验证 |
| 知识增强执行按钮响应 | Console 日志 |
| Studio 面板可交互 | checkbox 勾选 |
| 消息传递正确 | Service Worker 日志 |
| 测试报告完整 | 文档检查 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| chrome-extension/tests/screenshots/*.png | 截图保存 |
| collaboration/results/CHROME_EXTENSION_TEST_REPORT_2026-04-26.md | 新建 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| Extension 加载失败 | 无法测试 | 检查 manifest.json |
| Backend 未运行 | API 调用失败 | 先启动 Backend |
| 认证过期 | 知识查询失败 | 检查 NotebookLM 认证 |

---

**创建时间**: 2026-04-26T09:00:00+08:00