# Agent Dispatch Orders - Week 7

**生成时间**: `2026-04-25T10:00:00`
**派发者**: Claude Code (主执行者)
**待派发任务数**: `2`

---

## 发送给 `CodeArts Agent` (`codearts_agent`)

### TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002

**优先级**: P1
**预估工时**: 2.0h

```text
【执行指令 | TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002】

1) 切换状态为 implementing
更新 collaboration/tasks/TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002.md
status: implementing

2) 执行任务内容
- Task 1: Popup UI Studio 面板 (40min)
  文件: chrome-extension/public/popup.html, chrome-extension/public/popup.js
  新增 Studio 产物生成面板 UI

- Task 2: Service Worker 消息处理 (30min)
  文件: chrome-extension/src/background/service-worker.js
  新增 GENERATE_STUDIO_ARTIFACTS 消息类型

- Task 3: Bridge 真实调用实现 (40min)
  文件: chrome-extension/src/background/notebooklm-packexecutor-bridge.js
  完善 generateArtifact() 真实调用逻辑

- Task 4: 集成测试 (30min)
  文件: tests/integration/test_studio_integration.py
  新建集成测试文件

3) 执行验收命令
pytest tests/integration/test_studio_integration.py -v

4) 创建结果文件
collaboration/results/RESULT_TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002.md
格式参照: collaboration/results/RESULT_TASK-W6-D1-INTEGRATION-EXPANSION-001.md

5) 更新任务状态为 testing
status: testing

6) 生成 ACK
回复本文件确认任务已接收
```

---

### TASK-W7-D4-CICD-INTEGRATION-004 (依赖 D1 + D2 完成)

**优先级**: P3
**预估工时**: 3.0h
**状态**: 等待前置任务完成

---

## 前置依赖说明

| 任务 | 依赖 | 说明 |
|------|------|------|
| TASK-W7-D4 | D1 + D2 | CI/CD 需要分支逻辑和 Studio 集成完成后再部署 |

---

## 执行约束

1. **禁止绕过验收命令**: 必须执行 pytest 验证
2. **禁止跳过结果文件**: 必须创建 RESULT_*.md
3. **禁止直接修改 main 分支**: 使用 feature 分支开发
4. **遇阻塞立即回报**: 在任务文件中记录 blocker

---

## ACK 协议

CodeArts Agent 接收任务后，请回复：

```
【ACK | TASK-W7-D2-STUDIO-CHROME-INTEGRATION-002】
status: received
timestamp: {ISO时间}
note: {简短备注}
```

---

**派发完成**