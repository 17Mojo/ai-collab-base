# 任务: S14 Day1 基座任务 - ACK 超时守卫加固

**任务ID**: TASK-S14-D1-BASE-ACK-TIMEOUT-GUARD-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 优化 ACK 超时与状态推进联动判断，减少误触发 reset。
- **scope_out**: 不修改任务状态机定义，不新增外部依赖。

## 输入

- 文件: ai_collab/cli.py, scripts/agent_receipt_bridge.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S14-D1-BASE-ACK-TIMEOUT-GUARD-CLAUDE-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_agent_receipt_bridge.py
python3 -m ai_collab.cli receipt --dry-run
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
