# 任务: S10 Day2 基座任务 - 回执质量门禁加固

**任务ID**: TASK-S10-D2-BASE-RECEIPT-QUALITY-GATE-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 对 receipt 收口链路增加结果质量门禁一致性校验，降低误收口风险。
- **scope_out**: 不新增外部服务，不改变任务契约字段定义。

## 输入

- 文件: scripts/agent_receipt_bridge.py, ai_collab/cli.py, tests/unit/test_agent_receipt_bridge.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S10-D2-BASE-RECEIPT-QUALITY-GATE-CLAUDE-002.md`
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
