# 任务: S11 Day1 基座任务 - Trigger 载荷完整性加固

**任务ID**: TASK-S11-D1-BASE-TRIGGER-PAYLOAD-INTEGRITY-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 为 Agent Trigger 文档增加可校验的完整性标记，降低聊天框粘贴丢段/错位风险。
- **scope_out**: 不引入外部服务，不改变任务状态机。

## 输入

- 文件: scripts/agent_dispatch_bridge.py, ai_collab/dispatch_trigger.py, tests/unit/test_agent_dispatch_bridge.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S11-D1-BASE-TRIGGER-PAYLOAD-INTEGRITY-CLAUDE-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_cli.py
python3 -m ai_collab.cli dispatch --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [x] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
