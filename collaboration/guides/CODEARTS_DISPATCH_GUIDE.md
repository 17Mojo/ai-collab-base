# CodeArts 任务派发标准流程

## 概述

本文档固化 Claude → CodeArts 任务派发的标准流程，避免重复调查和调试。

## 派发清单（Checklist）

### 1. 任务文件准备

```bash
# 任务文件位置
collaboration/tasks/TASK_*.md

# 任务文件模板
```

```markdown
# 任务：[任务名称]

**日期**: YYYY-MM-DD
**优先级**: P0/P1/P2
**执行者**: CodeArts Agent
**参考文档**: `docs/[相关文档].md`

---

## 任务背景

[任务背景描述]

## 任务列表

### Task 1: [任务标题]

**目标**: [目标描述]

**文件**: `[文件路径]`

**验收标准**:
- [ ] 标准1
- [ ] 标准2

---

## 完成后回复

\`\`\`
A.ACK|task=[任务ID]|status=ok|result=[结果描述]
\`\`\`
```

### 2. Payload 文件创建（关键！）

**必须同时创建两个格式的 payload 文件**：

#### JSON 格式（CodeArts 主要识别）

```bash
# 位置 1: collaboration/monitoring/payload_codearts_agent_latest.json
# 位置 2: collaboration/dispatch/payloads/AGENT_TRIGGER_codearts_agent_latest.json
```

```json
{
  "assignee": "codearts_agent",
  "generated_at": "YYYY-MM-DDTHH:MM:SS",
  "mode": "direct_execution",
  "task_id": "TASK_ID",
  "task_file": "collaboration/tasks/TASK_FILE.md",
  "reference_docs": ["docs/REF.md"],
  "steps": [
    {"id": 1, "title": "步骤1", "commands": ["cmd1"], "files": ["file1"]}
  ],
  "acceptance_criteria": ["标准1", "标准2"],
  "ack_format": "A.ACK|task=TASK_ID|status=ok|result=描述"
}
```

#### MD 格式（系统兼容）

```bash
# 位置: collaboration/dispatch/AGENT_TRIGGER_codearts_agent_latest.md
```

### 3. StateManager 注册

```python
from ai_collab.state_manager import StateManager

sm = StateManager()
sm.register_task(
    task_id='TASK_ID',
    ai_type='codearts_agent',
    description='任务描述',
    files=['file1', 'file2'],
    assignee='codearts_agent'
)
```

### 4. Git 提交

```bash
git add collaboration/tasks/TASK_*.md \
        collaboration/monitoring/payload_codearts_agent_latest.json \
        collaboration/dispatch/payloads/ \
        logs/collaboration_state.json

git commit -m "feat: assign TASK_ID to CodeArts"
```

## 常见问题排查

### 问题 1: CodeArts 返回 `noop`

| 原因 | 解决方案 |
|------|----------|
| payload 文件不存在 | 创建 payload 文件 |
| 文件名不包含 `payload` | 使用 `payload_codearts_agent_latest.json` |
| JSON 格式错误 | 验证 JSON 语法 |
| 任务未注册 | 调用 StateManager.register_task() |

### 问题 2: `payloads目录不存在`

```bash
mkdir -p collaboration/dispatch/payloads/
mkdir -p collaboration/monitoring/
```

### 问题 3: `无有效payload`

确保文件名匹配 CodeArts 的搜索模式：
- ✅ `payload_*.json`
- ✅ `*payload*.json`
- ❌ `AGENT_TRIGGER_*.json` (不会被识别)

## 文件位置速查表

| 文件类型 | 位置 | 必需 |
|----------|------|------|
| 任务文件 | `collaboration/tasks/TASK_*.md` | ✅ |
| JSON Payload | `collaboration/monitoring/payload_codearts_agent_latest.json` | ✅ |
| JSON Payload (备) | `collaboration/dispatch/payloads/AGENT_TRIGGER_*.json` | 推荐 |
| MD Payload | `collaboration/dispatch/AGENT_TRIGGER_*.md` | 推荐 |
| 状态文件 | `logs/collaboration_state.json` | 自动 |

## 快速派发脚本

见: `scripts/dispatch_to_codearts.py`

---

**更新时间**: 2026-04-13
**维护者**: Claude (Technical Partner)
