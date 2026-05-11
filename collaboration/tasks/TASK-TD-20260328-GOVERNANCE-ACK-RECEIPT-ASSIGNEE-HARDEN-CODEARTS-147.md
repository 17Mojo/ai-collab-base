# 任务: Governance ACK + receipt assignee hardening

**任务ID**: TASK-TD-20260328-GOVERNANCE-ACK-RECEIPT-ASSIGNEE-HARDEN-CODEARTS-147  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 在 merged `main` 基线上，为 `receipt/ack + result consistency` 做第二批硬化
  - 聚焦显式 ACK 证据判定、assignee 一致性、receipt dry-run 摘要可诊断性
  - 允许修改 `ai_collab/ack_protocol.py`、`ai_collab/ack_remediation.py`、`ai_collab/missing_ack_monitor.py`、`ai_collab/result_consistency_audit.py`、`scripts/agent_receipt_bridge.py` 及对应测试
  - 产出实际代码修复与验证，不停留在分析文档
- **scope_out**:
  - 不修改 `ai_collab/cli.py`
  - 不修改 `ai_collab/state_manager.py`
  - 不做主工作区清理或手工编辑 `logs/collaboration_state.json`

## 输入

- `ai_collab/ack_protocol.py`
- `ai_collab/ack_remediation.py`
- `ai_collab/missing_ack_monitor.py`
- `ai_collab/result_consistency_audit.py`
- `scripts/agent_receipt_bridge.py`
- `tests/unit/test_ack_remediation.py`
- `tests/unit/test_missing_ack_monitor.py`
- `tests/unit/test_result_consistency_audit.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `tests/unit/test_reconcile_state_drift.py`
- `collaboration/results/GOVERNANCE_POST_MERGE_MAINLINE_VERIFICATION_CHECKLIST_2026-03-28.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260328-GOVERNANCE-ACK-RECEIPT-ASSIGNEE-HARDEN-CODEARTS-147.md`
- 必须包含:
  - 实际修改文件清单
  - 显式 ACK / assignee 判定修复点
  - receipt / result consistency 验证结果
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_ack_remediation.py \
  tests/unit/test_missing_ack_monitor.py \
  tests/unit/test_result_consistency_audit.py \
  tests/unit/test_agent_receipt_bridge.py \
  tests/unit/test_reconcile_state_drift.py
python3 -m ruff check \
  ai_collab/ack_protocol.py \
  ai_collab/ack_remediation.py \
  ai_collab/missing_ack_monitor.py \
  ai_collab/result_consistency_audit.py \
  scripts/agent_receipt_bridge.py
python3 -m ai_collab.cli receipt --dry-run --force-workspace
python3 -m ai_collab.cli tasks audit-result-consistency --strict
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
