# 任务: 治理对齐协同 Smoke 测试

**任务ID**: TASK-GOV-COLLAB-SMOKE-001  
**change_id**: update-agent-governance-handover  
**分配给**: codex  
**reviewer**: user  
**优先级**: P0

## Skill 分配

- **primary_skill**: duoai-coordinator
- **support_skills**: [api-test-pro, compliance-checker]
- **scope_in**: 验证治理口径、编排路由、规则加载、MCP 统一入口均有效
- **scope_out**: 不做业务功能迭代

## 输入

- `collaboration/tasks/TASK-GOV-ONBOARD-CLAUDE-001.md`
- `collaboration/tasks/TASK-GOV-ONBOARD-CODEARTS-001.md`
- `collaboration/configs/mcp.unified.json`

## 输出要求

- `collaboration/results/RESULT_TASK-GOV-COLLAB-SMOKE-001.md`
- 必须包含：通过项、失败项、偏差原因、纠正动作、回滚建议

## acceptance_commands

```bash
python3 scripts/sync_mcp_unified.py --workspace . --check
python3 -m ai_collab.cli status -v
python3 -m pytest -q tests/unit/test_agent_orchestrator.py tests/unit/test_session_inject.py tests/unit/test_cli.py tests/unit/test_vscode_integration.py
python3 -m pytest -q
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
