# Session Intervention Artifact（自动生成）

- generated_at: `2026-04-01T09:51:58.089894`
- assignee: `claude_code`
- session_id: `612d5ac4-8367-47e4-96db-dae5bce961b3`
- session_status: `active`
- reason_code: `terminal_status_mismatch`
- severity: `high`
- source_signal: `result_consistency_audit`
- recommended_action: `修复结果文件和控制面终态的一致性后再收口`
- requires_operator_delivery: `True`
- artifact_file: `/Users/raymondna/Documents/ai-collab-system/collaboration/monitoring/session_interventions/SESSION_INTERVENTION_612d5ac4-8367-47e4-96db-dae5bce961b3_terminal_status_mismatch_latest.md`

## Summary

检测到 1 个终态结果一致性问题（terminal_status_mismatch）。

## Exact Forward Message

```text
检测到 `claude_code` 的控制面终态与结果文件状态头不一致。
请修正结果文件中的顶层状态头，使其与控制面终态一致后再继续收口。
```

## Tasks

- `TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146`
