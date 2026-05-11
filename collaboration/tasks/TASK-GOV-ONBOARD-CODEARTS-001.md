# 任务: CodeArts 上岗前治理对齐与自改造

**任务ID**: TASK-GOV-ONBOARD-CODEARTS-001  
**change_id**: update-agent-governance-handover  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P0

## Skill 分配

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 按“执行辅助者”新角色完成规则、配置、协同测试对齐
- **scope_out**: 不承担全局治理任务，不修改产品路线决策

## 输入

- `collaboration/PROTOCOL.md`
- `rules/agent_governance_quickstart.md`
- `rules/codearts_agent_rules.md`
- `collaboration/configs/mcp.unified.json`

## 输出要求

- `collaboration/results/RESULT_TASK-GOV-ONBOARD-CODEARTS-001.md`
- 记录：规则加载结果、MCP 配置核对、协同 smoke 参与证据

## acceptance_commands

```bash
python3 -m ai_collab.cli activate --ai codearts_agent --mode command --input "2X governance onboarding"
python3 scripts/sync_mcp_unified.py --workspace . --check
python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_session_inject.py
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
