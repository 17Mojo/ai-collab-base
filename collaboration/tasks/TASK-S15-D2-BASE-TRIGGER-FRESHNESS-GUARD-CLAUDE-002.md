# 任务: S15 Day2 基座任务 - Trigger 新鲜度守卫

**任务ID**: TASK-S15-D2-BASE-TRIGGER-FRESHNESS-GUARD-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 增强 trigger 文件 freshness 校验，避免旧 payload 被误执行。
- **scope_out**: 不改派单策略，不改 AI 路由策略。

## 输入

- 文件: ai_collab/dispatch_trigger.py, ai_collab/cli.py, tests/unit/test_dispatch_trigger.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S15-D2-BASE-TRIGGER-FRESHNESS-GUARD-CLAUDE-002.md`
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
