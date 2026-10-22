# Session Health Summary（自动生成）

- 生成时间: `2026-10-22T23:59:18.420660`
- 模式: `apply`
- session_count: `8`
- healthy: `7`
- unhealthy: `1`
- unregistered: `0`
- incidents: `1`
- interventions: `1`
- open_interventions: `1`
- claude_push_report: `logs/claude_adapter_report.json`
- codearts_pull_report: `logs/codearts_adapter_report.json`
- codex_native_report: `logs/codex_adapter_report.json`

## Sessions

- `0099ee6f-b599-472d-9dcc-143752ce6b56` assignee=`claude_code` health=`healthy` reasons=``
- `03cc6ad2-c943-4288-a673-2b22277b83e0` assignee=`claude_code` health=`healthy` reasons=``
- `1b502113-ed3a-40c2-a781-59e576cb80e1` assignee=`claude_code` health=`healthy` reasons=``
- `28cec864-28ac-4322-814a-ff7154e7cdc6` assignee=`claude_code` health=`healthy` reasons=``
- `9fb00703-fc35-48fb-9de0-109f669e852f` assignee=`claude_code` health=`healthy` reasons=``
- `cccfe573-6e74-4751-a828-41f3190b70cd` assignee=`claude_code` health=`healthy` reasons=``
- `f43b2192-faed-4d34-84e7-83e2c5786446` assignee=`claude_code` health=`healthy` reasons=``
- `codearts-agent-bridge` assignee=`codearts_agent` health=`unhealthy` reasons=`ack_silence_after_run`

## Incidents

- assignee=`codearts_agent` session=`codearts-agent-bridge` reason=`ack_silence_after_run` severity=`high`
  artifact: `collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts-agent-bridge_ack_silence_after_run_latest.md`
