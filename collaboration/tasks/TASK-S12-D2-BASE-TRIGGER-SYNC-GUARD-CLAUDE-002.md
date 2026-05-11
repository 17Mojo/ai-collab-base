# 任务: S12 Day2 基座任务 - Trigger 同步守卫

**任务ID**: TASK-S12-D2-BASE-TRIGGER-SYNC-GUARD-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 加固 trigger 文件刷新与派单状态的一致性，避免“有任务但 trigger 显示无任务”。
- **scope_out**: 不引入外部服务，不改任务契约字段。

## 输入

- 文件: ai_collab/cli.py, ai_collab/dispatch_trigger.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S12-D2-BASE-TRIGGER-SYNC-GUARD-CLAUDE-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_agent_dispatch_bridge.py
python3 -m ai_collab.cli trigger --phrase "2X DISPATCH" --include-pending --dry-run
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
