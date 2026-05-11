---
task_id: TASK-W9-D1-CHROME-EXTENSION-REAL-TEST-001
change_id: chrome-extension-real-browser-integration-test
status: completed
assignee: user
reviewer: user
primary_skill: chrome_extension
support_skills: ["testing", "browser_automation"]
acceptance_commands: "手动测试报告提交"
created_at: 2026-04-27T09:00:00
estimated_hours: 1.0
priority: P1
depends_on: []
---

# TASK-W9-D1-CHROME-EXTENSION-REAL-TEST-001

## 任务描述

在 Chrome Extensions 页面真实加载并测试 Extension 完整功能。

## 背景

D5 任务使用 Chrome DevTools MCP 在 popup.html 直接测试，但真实 Extension 功能需要在 `chrome://extensions/` 加载后测试。

## 详细任务

### Task 1: Extension 加载 (15min)

**操作步骤**:

1. 打开 Chrome 浏览器
2. 进入 `chrome://extensions/`
3. 开启「开发者模式」(右上角开关)
4. 点击「加载已解压的扩展程序」
5. 选择 `chrome-extension/` 目录
6. 验证 Extension ID 生成

**验证项**:
- Extension 图标显示在工具栏
- 扩展列表显示 "AI Collab Extension"
- ID 格式: `abcdefghijklmnopqrstuvwxyz123456`

---

### Task 2: Popup UI 测试 (15min)

**测试步骤**:

1. 点击 Extension 图标
2. Popup 界面打开
3. 验证 UI 元素:
   - Pack 选择下拉框
   - 刷新 Pack 列表按钮
   - 知识增强执行按钮
   - Studio 面板
   - 平台勾选框

**截图要求**:
- Popup 整体截图
- Studio 面板截图

---

### Task 3: 知识增强执行测试 (15min)

**测试步骤**:

1. 确保 Backend 运行 (`http://127.0.0.1:8000`)
2. 打开 Popup
3. 选择 Pack: `xiaohongshu_knowledge_creator`
4. 勾选平台: Claude
5. 输入 prompt: "小红书知识型博主创作原则"
6. 点击「知识增强执行」
7. 观察 Console 日志

**验证**:
- Service Worker 收到消息
- Backend API 被调用
- 知识来源标注显示

---

### Task 4: Studio 产物生成测试 (10min)

**测试步骤**:

1. 打开 Popup → Studio 面板
2. 勾选 Audio + Slides
3. 输入 Focus: "知识型博主创作方法"
4. 点击「生成 Studio 产物」
5. 观察状态变化

**验证**:
- GENERATE_STUDIO_ARTIFACTS 消息发送
- Status 显示生成状态

---

### Task 5: 测试报告提交 (5min)

**位置**: `collaboration/results/CHROME_EXTENSION_REAL_TEST_2026-04-27.md`

**内容**:
- Extension ID
- 测试场景截图
- 功能验证结果
- 发现问题汇总
- 改进建议

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| Extension 加载成功 | 扩展列表显示 |
| Popup 打开正常 | UI 渲染 |
| Pack 列表加载 | 下拉框显示 Pack |
| 知识增强执行响应 | Console 日志 |
| Studio 面板交互 | checkbox 勾选 |
| 测试报告完整 | 文档检查 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| chrome-extension/tests/screenshots/real_test_*.png | 截图保存 |
| collaboration/results/CHROME_EXTENSION_REAL_TEST_2026-04-27.md | 新建 |

---

## 前置条件

| 条件 | 检查方法 |
|------|----------|
| Backend API 运行 | `curl http://127.0.0.1:8000/health` |
| NotebookLM 认证有效 | `nlm auth status` |
| Pack 示例存在 | `ls packs/examples/*.json` |

**启动 Backend**:
```bash
cd local-backend
python -m uvicorn app.main:app --reload --port 8000
```

---

**创建时间**: 2026-04-27T09:00:00+08:00
**执行者**: User (手动测试)
