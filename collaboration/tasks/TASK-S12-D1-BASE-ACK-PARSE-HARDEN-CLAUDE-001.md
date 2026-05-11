# 任务: S12 Day1 基座任务 - ACK 解析容错加固

**任务ID**: TASK-S12-D1-BASE-ACK-PARSE-HARDEN-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 强化 ACK 判定逻辑，支持“ACK 行 + 额外文本”的容错识别，减少误报 reset。
- **scope_out**: 不改任务状态机，不改外部 Agent 协议关键词。

## 输入

- 文件: ai_collab/cli.py, scripts/agent_receipt_bridge.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S12-D1-BASE-ACK-PARSE-HARDEN-CLAUDE-001.md`
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
