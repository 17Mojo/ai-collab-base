# 任务: S14 Day2 基座任务 - Trigger 一致性检查

**任务ID**: TASK-S14-D2-BASE-TRIGGER-CONSISTENCY-CHECK-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 校验 trigger 输出与 dispatch orders 在单目标/双目标分支的一致性。
- **scope_out**: 不修改收益计算逻辑，不新增状态字段。

## 输入

- 文件: ai_collab/dispatch_trigger.py, ai_collab/cli.py, tests/unit/test_dispatch_trigger.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S14-D2-BASE-TRIGGER-CONSISTENCY-CHECK-CLAUDE-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_dispatch_trigger.py tests/unit/test_cli.py
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
