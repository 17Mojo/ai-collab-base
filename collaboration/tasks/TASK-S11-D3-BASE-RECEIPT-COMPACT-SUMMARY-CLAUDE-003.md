# 任务: S11 Day3 基座任务 - Receipt 紧凑摘要输出

**任务ID**: TASK-S11-D3-BASE-RECEIPT-COMPACT-SUMMARY-CLAUDE-003  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 为 receipt 输出增加紧凑摘要视图，支撑聊天框短回报模式快速判断。
- **scope_out**: 不改变 receipt 的实际收口判定逻辑。

## 输入

- 文件: scripts/agent_receipt_bridge.py, ai_collab/cli.py, tests/unit/test_agent_receipt_bridge.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S11-D3-BASE-RECEIPT-COMPACT-SUMMARY-CLAUDE-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_receipt_bridge.py tests/unit/test_cli.py
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
