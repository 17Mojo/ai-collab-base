# 任务: S11 Day2 基座任务 - 派发前置清单守卫

**任务ID**: TASK-S11-D2-BASE-DISPATCH-CHECKLIST-GUARD-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 强化“可派发/可收口/无任务”三态提示，减少操作歧义与空转。
- **scope_out**: 不改变 dispatch/receipt 现有状态流转规则。

## 输入

- 文件: ai_collab/cli.py, scripts/agent_dispatch_bridge.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S11-D2-BASE-DISPATCH-CHECKLIST-GUARD-CLAUDE-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_agent_dispatch_bridge.py
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
