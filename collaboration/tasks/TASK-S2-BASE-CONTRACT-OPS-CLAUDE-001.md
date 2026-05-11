# 任务: 基座契约化派单作业手册（Ops）

**任务ID**: TASK-S2-BASE-CONTRACT-OPS-CLAUDE-001  
**change_id**: add-task-contract-gatekeeper  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 沉淀契约化派单操作手册并更新任务模板示例
- **scope_out**: 不修改业务逻辑

## 输入

- `ai_collab/cli.py`
- `ai_collab/state_manager.py`
- `collaboration/templates/TASK_TEMPLATE_SKILL_GATED.md`

## 输出要求

- `collaboration/guides/TASK_CONTRACT_OPS_PLAYBOOK.md`
- `collaboration/results/RESULT_TASK-S2-BASE-CONTRACT-OPS-CLAUDE-001.md`

## acceptance_commands

```bash
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
pytest -q tests/unit/test_cli.py
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
