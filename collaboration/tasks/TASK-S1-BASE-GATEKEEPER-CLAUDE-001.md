# 任务: 基座工单契约守卫实现

**任务ID**: TASK-S1-BASE-GATEKEEPER-CLAUDE-001  
**change_id**: add-task-contract-gatekeeper  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 实现并接入工单契约校验能力（字段完整性 + 兼容策略 + 可执行入口 + 回归测试）
- **scope_out**: 不改 Prompt Pack 业务功能，不修改发布流程

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 当日提交结果文件（Y/N）
- **CTQ-2 质量门禁**: acceptance_commands 全部通过（Y/N）
- **CTQ-3 漂移控制**: 无越界文件改动（Y/N）
- **DPMO 记录**: 0/6（目标）

## 输入

- 文件: `openspec/changes/add-task-contract-gatekeeper/*`, `ai_collab/cli.py`, `ai_collab/state_manager.py`, `collaboration/templates/TASK_TEMPLATE_SKILL_GATED.md`
- 上下文: 协作工单需强制 `change_id+skill+acceptance` 字段，防止执行漂移
- 依赖: 无

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S1-BASE-GATEKEEPER-CLAUDE-001.md`
- 必须包含: 变更摘要、执行命令、测试结论、风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_state_manager.py
python3 -m ai_collab.cli controller --once --dry-run
openspec validate add-task-contract-gatekeeper --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
