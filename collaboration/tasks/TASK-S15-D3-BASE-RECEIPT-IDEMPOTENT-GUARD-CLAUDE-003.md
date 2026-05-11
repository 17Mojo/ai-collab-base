# 任务: S15 Day3 基座任务 - 回执幂等收口守卫

**任务ID**: TASK-S15-D3-BASE-RECEIPT-IDEMPOTENT-GUARD-CLAUDE-003  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 强化 receipt 幂等收口与重复 ACK 场景防抖，降低重复收口干扰。
- **scope_out**: 不改任务定义格式，不改外部 Agent 协议关键字。

## 输入

- 文件: scripts/agent_receipt_bridge.py, ai_collab/cli.py, tests/unit/test_agent_receipt_bridge.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S15-D3-BASE-RECEIPT-IDEMPOTENT-GUARD-CLAUDE-003.md`
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
