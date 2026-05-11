---
task_id: TASK-FIX-CONTEXT-IMPORT-001
change_id: add-session-orchestration-control-plane
status: completed
assignee: codearts_agent
reviewer: claude
primary_skill: unittest
support_skills: ["testing", "coding"]
acceptance_commands: "python3 -m pytest tests/unit/context/test_scenario.py tests/unit/context/test_schema.py -v"
result_file: collaboration/results/RESULT_TASK-FIX-CONTEXT-IMPORT-001.md
created_at: 2026-04-04T14:00:00
completed_at: 2026-04-04T14:40:00
priority: P0
---

# TASK-FIX-CONTEXT-IMPORT-001

## 任务描述

修复 context 测试文件中的导入错误。

## 问题

测试文件使用了错误的导入路径 `from ai_collab.context`，但 context 模块实际位于 `src/ai_collab/context`。

## 修复内容

1. **tests/unit/context/test_scenario.py** - 修复导入路径
2. **tests/unit/context/test_schema.py** - 修复导入路径

## 验收结果

- ✅ 53 个测试全部通过
- ✅ 代码质量检查通过
- ✅ 无导入错误
