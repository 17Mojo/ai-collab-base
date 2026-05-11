# Agent Dispatch Orders - Chrome Extension & 用户文档冲刺

- 生成时间: `2026-04-19T09:00:00`
- 目标: Chrome Extension 100% + 用户文档 90%
- 总任务: 12 个
- 预计天数: 6 天

---

## 一、Chrome Extension MVP 任务组

### 发送给 `Claude` (`claude_code`)

#### TASK-EXT-SETTINGS-001

```text
【执行指令 | TASK-EXT-SETTINGS-001】

优先级: P1
描述: 用户设置界面实现

1) 创建文件
chrome-extension/public/settings.html
chrome-extension/public/settings.js
chrome-extension/src/background/settings-handler.js

2) 功能要求
- 平台开关（Claude/ChatGPT/Gemini）
- 执行超时设置（默认 60s）
- 重试次数设置（默认 3）
- 日志开关

3) 验收
node -c chrome-extension/public/settings.js
node -c chrome-extension/src/background/settings-handler.js

4) 结果文件
collaboration/results/RESULT_TASK-EXT-SETTINGS-001.md

5) ACK
C.ACK|task=TASK-EXT-SETTINGS-001|status=ok
```

#### TASK-EXT-STORAGE-001

```text
【执行指令 | TASK-EXT-STORAGE-001】

优先级: P1
描述: 设置存储同步实现

1) 实现功能
- chrome.storage.sync API 集成
- 设置跨设备同步
- 默认设置初始化

2) 验收
设置变更后刷新页面，设置保持

3) 结果文件
collaboration/results/RESULT_TASK-EXT-STORAGE-001.md

4) ACK
C.ACK|task=TASK-EXT-STORAGE-001|status=ok
```

#### TASK-EXT-POPUP-ENHANCE-001

```text
【执行指令 | TASK-EXT-POPUP-ENHANCE-001】

优先级: P1
描述: Popup Pack 列表展示增强

1) 修改文件
chrome-extension/public/popup.html
chrome-extension/public/popup.js

2) 功能要求
- 已加载 Pack 列表
- Pack 执行状态显示
- 快速执行按钮

3) 验收
node -c chrome-extension/public/popup.js

4) 结果文件
collaboration/results/RESULT_TASK-EXT-POPUP-ENHANCE-001.md

5) ACK
C.ACK|task=TASK-EXT-POPUP-ENHANCE-001|status=ok
```

#### TASK-EXT-TEST-CLAUDE-001

```text
【执行指令 | TASK-EXT-TEST-CLAUDE-001】

优先级: P1
描述: Claude.ai 实际浏览器测试

1) 测试步骤
- 加载扩展到 Chrome
- 打开 claude.ai
- 测试文本注入到输入框
- 测试 Pack 执行流程
- 记录问题和修复

2) 验收
成功注入文本到 Claude.ai 输入框

3) 结果文件
collaboration/results/RESULT_TASK-EXT-TEST-CLAUDE-001.md

4) ACK
C.ACK|task=TASK-EXT-TEST-CLAUDE-001|status=ok
```

#### TASK-EXT-TEST-CHATGPT-001

```text
【执行指令 | TASK-EXT-TEST-CHATGPT-001】

优先级: P1
描述: ChatGPT 实际浏览器测试

验收: 成功注入文本到 ChatGPT 输入框

结果文件: collaboration/results/RESULT_TASK-EXT-TEST-CHATGPT-001.md

ACK: C.ACK|task=TASK-EXT-TEST-CHATGPT-001|status=ok
```

#### TASK-EXT-TEST-GEMINI-001

```text
【执行指令 | TASK-EXT-TEST-GEMINI-001】

优先级: P1
描述: Gemini 实际浏览器测试

验收: 成功注入文本到 Gemini 输入框

结果文件: collaboration/results/RESULT_TASK-EXT-TEST-GEMINI-001.md

ACK: C.ACK|task=TASK-EXT-TEST-GEMINI-001|status=ok
```

---

## 二、用户文档任务组

### 发送给 `CodeArts` (`codearts_agent`)

#### TASK-DOC-INSTALL-001

```text
【执行指令 | TASK-DOC-INSTALL-001】

优先级: P1
描述: 用户安装指南编写

1) 内容要求
- Chrome 扩展安装步骤
- 开发者模式启用
- 加载未打包扩展
- 权限说明
- 安装验证方法

2) 输出文件
docs/user-guide-install.md (约 500 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-INSTALL-001.md

4) ACK
A.ACK|task=TASK-DOC-INSTALL-001|status=ok
```

#### TASK-DOC-QUICKSTART-001

```text
【执行指令 | TASK-DOC-QUICKSTART-001】

优先级: P1
描述: 快速上手教程编写

1) 内容要求
- 首次使用流程
- 平台检测说明
- 第一个 Pack 执行示例
- 基础操作截图说明

2) 输出文件
docs/user-guide-quickstart.md (约 1000 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-QUICKSTART-001.md

4) ACK
A.ACK|task=TASK-DOC-QUICKSTART-001|status=ok
```

#### TASK-DOC-PACK-001

```text
【执行指令 | TASK-DOC-PACK-001】

优先级: P1
描述: Pack 使用教程编写

1) 内容要求
- Pack 是什么
- 如何加载 Pack
- 如何执行 Pack
- Pack 执行结果查看

2) 输出文件
docs/user-guide-pack.md (约 600 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-PACK-001.md

4) ACK
A.ACK|task=TASK-DOC-PACK-001|status=ok
```

#### TASK-DOC-PACK-CREATE-001

```text
【执行指令 | TASK-DOC-PACK-CREATE-001】

优先级: P2
描述: Pack 创建指南编写

1) 内容要求
- Pack Schema v2.0 介绍
- Step 类型说明 (6种)
- Pack 编写示例
- Pack 测试方法
- Pack 发布流程

2) 输出文件
docs/user-guide-pack-create.md (约 1500 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-PACK-CREATE-001.md

4) ACK
A.ACK|task=TASK-DOC-PACK-CREATE-001|status=ok
```

#### TASK-DOC-FAQ-001

```text
【执行指令 | TASK-DOC-FAQ-001】

优先级: P2
描述: FAQ 编写

1) 内容要求 (10-15 个常见问题)
- 扩展无法加载？
- 文本注入失败？
- 平台不识别？
- Pack 执行报错？
- 设置如何保存？
- ...

2) 输出文件
docs/faq.md (约 800 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-FAQ-001.md

4) ACK
A.ACK|task=TASK-DOC-FAQ-001|status=ok
```

#### TASK-DOC-TRoubleshooting-001

```text
【执行指令 | TASK-DOC-TROUBLESHOOTING-001】

优先级: P2
描述: 常见问题排查指南编写

1) 内容要求
- 问题排查流程
- 日志查看方法
- 常见错误代码说明
- 解决方案列表

2) 输出文件
docs/troubleshooting.md (约 600 字)

3) 结果文件
collaboration/results/RESULT_TASK-DOC-TROUBLESHOOTING-001.md

4) ACK
A.ACK|task=TASK-DOC-TROUBLESHOOTING-001|status=ok
```

---

## 三、任务分配汇总

| 任务组 | Claude Code | CodeArts Agent |
|--------|-------------|----------------|
| Chrome Extension | 6 个 | 0 个 |
| 用户文档 | 0 个 | 6 个 |
| **总计** | **6** | **6** |

## 四、执行顺序

### Claude Code 执行顺序
1. TASK-EXT-SETTINGS-001 (设置界面)
2. TASK-EXT-STORAGE-001 (存储同步)
3. TASK-EXT-POPUP-ENHANCE-001 (Popup 增强)
4. TASK-EXT-TEST-CLAUDE-001 (Claude 测试)
5. TASK-EXT-TEST-CHATGPT-001 (ChatGPT 测试)
6. TASK-EXT-TEST-GEMINI-001 (Gemini 测试)

### CodeArts Agent 执行顺序
1. TASK-DOC-INSTALL-001 (安装指南)
2. TASK-DOC-QUICKSTART-001 (快速上手)
3. TASK-DOC-PACK-001 (Pack 使用)
4. TASK-DOC-PACK-CREATE-001 (Pack 创建)
5. TASK-DOC-FAQ-001 (FAQ)
6. TASK-DOC-TROUBLESHOOTING-001 (排查指南)

## 五、验收标准

### Chrome Extension MVP 100%
- [ ] 用户设置界面可用
- [ ] 设置跨设备同步
- [ ] Popup 显示 Pack 列表
- [ ] Claude.ai 实测通过
- [ ] ChatGPT 实测通过
- [ ] Gemini 实测通过

### 用户文档 90%
- [ ] 安装指南完成
- [ ] 快速上手教程完成
- [ ] Pack 使用教程完成
- [ ] Pack 创建指南完成
- [ ] FAQ 完成
- [ ] 常见问题排查完成