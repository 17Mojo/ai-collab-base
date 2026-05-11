# 任务: S15 Day1 基座任务 - ACK 单行输出契约守卫

**任务ID**: TASK-S15-D1-BASE-ACK-OUTPUT-CONTRACT-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 收敛 C.ACK/A.ACK 输出为单行协议，降低会话噪声导致的收口失败。
- **scope_out**: 不改任务状态机，不引入外部依赖。

## 输入

- 文件: ai_collab/dispatch_trigger.py, ai_collab/cli.py, tests/unit/test_agent_dispatch_bridge.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S15-D1-BASE-ACK-OUTPUT-CONTRACT-CLAUDE-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_cli.py
python3 -m ai_collab.cli trigger --phrase "2X DISPATCH CLAUDE" --dry-run
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
