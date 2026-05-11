# 任务: Claude 上岗前治理对齐与自改造

**任务ID**: TASK-GOV-ONBOARD-CLAUDE-001  
**change_id**: update-agent-governance-handover  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 按最新治理口径完成 Claude 执行链路对齐（规则理解、激活验证、协同测试参与）
- **scope_out**: 不改业务功能，不新增架构级能力

## 输入

- `collaboration/PROTOCOL.md`
- `rules/agent_governance_quickstart.md`
- `rules/claude_code_memory.md`
- `collaboration/monitoring/GOVERNANCE_ONBOARDING_CONTROL_PLAN_2026-03-03.md`

## 输出要求

- `collaboration/results/RESULT_TASK-GOV-ONBOARD-CLAUDE-001.md`
- 记录：`rules_loaded`、执行命令、验证结论、偏差与纠正措施

## acceptance_commands

```bash
python3 -m ai_collab.cli activate --ai claude --mode command --input "2X governance onboarding"
python3 -m ai_collab.cli status -v
python3 -m pytest -q tests/unit/test_agent_orchestrator.py tests/unit/test_session_inject.py
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
