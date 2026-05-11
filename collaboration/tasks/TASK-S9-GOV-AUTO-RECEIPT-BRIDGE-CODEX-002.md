# 任务: S9 自动回执桥接（V2）

**任务ID**: TASK-S9-GOV-AUTO-RECEIPT-BRIDGE-CODEX-002  
**change_id**: add-agent-receipt-bridge  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 落地自动回执桥接能力（testing 候选识别、证据门禁复用、自动收口、回执审计）
- **scope_out**: 不做外部 Agent 通道自动消息发送，不改任务契约字段规范

## 输入

- 文件: ai_collab/cli.py, scripts/agent_receipt_bridge.py, collaboration/PROTOCOL.md
- OpenSpec: openspec/changes/add-agent-receipt-bridge

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-GOV-AUTO-RECEIPT-BRIDGE-CODEX-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_receipt_bridge.py tests/unit/test_cli.py
python3 -m ai_collab.cli receipt --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
openspec validate add-agent-receipt-bridge --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
