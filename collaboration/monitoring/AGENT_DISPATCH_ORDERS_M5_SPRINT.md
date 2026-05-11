# Agent Dispatch Orders - M5 里程碑冲刺

- 生成时间: `2026-04-18T16:30:00`
- 目标: M5 Chrome Extension MVP (2026-04-30)
- 当前进度: 60%

## 一、技术债务清理

### TASK-FIX-FAILED-001 (P0)

```text
【执行指令 | TASK-FIX-FAILED-001】

任务: 修复 failed 任务 TASK-TD-20260318-SPAWN-AGENT-CLI-DIAGNOSTICS

1) 分析失败原因
cat collaboration/results/RESULT_TASK-TD-20260318-SPAWN-AGENT-CLI-DIAGNOSTICS*.md 2>/dev/null || echo "无结果文件"

2) 检查相关代码
grep -r "spawn-agent-guard" ai_collab/ --include="*.py" | head -5

3) 实施修复并创建结果文件
collaboration/results/RESULT_TASK-FIX-FAILED-001.md

4) ACK
C.ACK|task=TASK-FIX-FAILED-001|status=ok
```

## 二、Chrome Extension MVP 完成

### TASK-CHROME-PACK-EXEC-001 (P1)

```text
【执行指令 | TASK-CHROME-PACK-EXEC-001】

任务: Pack 执行功能测试和优化

文件:
- chrome-extension/src/background/pack-executor.js
- chrome-extension/tests/pack-executor.test.js (新建)

验收:
node -c chrome-extension/src/background/pack-executor.js
npm test --prefix chrome-extension (如已配置)

结果文件: collaboration/results/RESULT_TASK-CHROME-PACK-EXEC-001.md
```

### TASK-CHROME-MESSAGE-INJECT-001 (P1)

```text
【执行指令 | TASK-CHROME-MESSAGE-INJECT-001】

任务: 跨平台消息注入验证

文件:
- chrome-extension/src/content/content-script.js
- chrome-extension/src/platforms/*.js

验收:
node -c chrome-extension/src/content/content-script.js
验证消息注入到 Claude.ai/ChatGPT/Gemini 的 DOM 选择器

结果文件: collaboration/results/RESULT_TASK-CHROME-MESSAGE-INJECT-001.md
```

### TASK-CHROME-SETTINGS-001 (P2)

```text
【执行指令 | TASK-CHROME-SETTINGS-001】

任务: 用户设置界面实现

文件:
- chrome-extension/public/settings.html (新建)
- chrome-extension/public/settings.js (新建)
- chrome-extension/src/background/settings-handler.js (新建)

验收:
node -c chrome-extension/public/settings.js

结果文件: collaboration/results/RESULT_TASK-CHROME-SETTINGS-001.md
```

### TASK-CHROME-MARKET-001 (P2)

```text
【执行指令 | TASK-CHROME-MARKET-001】

任务: Pack 市场集成基础

文件:
- chrome-extension/src/background/market-client.js (新建)

验收:
node -c chrome-extension/src/background/market-client.js

结果文件: collaboration/results/RESULT_TASK-CHROME-MARKET-001.md
```

## 三、商业化准备

### TASK-COMMERCIAL-MVP-001 (P2)

```text
【执行指令 | TASK-COMMERCIAL-MVP-001】

任务: MVP 商业化验证准备

1) 检查商业化指南
cat collaboration/docs/PROJECT_COMMERCIAL_GUIDE_2026-04-18.md | head -50

2) 创建 MVP 发布清单
docs/mvp-release-checklist.md (新建)

结果文件: collaboration/results/RESULT_TASK-COMMERCIAL-MVP-001.md
```

## 分配表

| 任务 | 优先级 | 执行者 |
|------|--------|--------|
| TASK-FIX-FAILED-001 | P0 | Claude Code |
| TASK-CHROME-PACK-EXEC-001 | P1 | Claude Code |
| TASK-CHROME-MESSAGE-INJECT-001 | P1 | Claude Code |
| TASK-CHROME-SETTINGS-001 | P2 | CodeArts Agent |
| TASK-CHROME-MARKET-001 | P2 | CodeArts Agent |
| TASK-COMMERCIAL-MVP-001 | P2 | Claude Code |