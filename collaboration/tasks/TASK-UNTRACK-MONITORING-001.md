---
task_id: TASK-UNTRACK-MONITORING-001
change_id: untrack-monitoring-snapshots
status: pending
priority: P2
session_id: sess-untrack-monitoring-20261116
model_id: deepseek/v4.1-flash
assignee: claude_code
assignee_role: AGENT_EXEC
assignee_provider: claude_code
reviewer: codearts_agent
primary_skill: governance-engineering
support_skills: [testing, documentation]
created_at: 2026-11-16T06:21:00+08:00
acceptance_commands:
  - "openspec validate untrack-monitoring-snapshots --strict"
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 -m ai_collab.cli governance preflight"
  - "git ls-files collaboration/monitoring/ | wc -l"
  - "python3 -m pytest tests/unit/test_automation_benefit_dashboard.py tests/unit/test_ack_remediation.py tests/unit/test_dispatch_intervention_wiring.py -q"
  - "python3 -m ruff format --check . && python3 -m ruff check ."
result_file: collaboration/results/RESULT-UNTRACK-MONITORING-001.md
---

# TASK-UNTRACK-MONITORING-001 · 把本机监控摘要逐出索引

## 状态说明

- 权威状态落在协作台账（`logs/collaboration_state.json`，gitignored），由
  `python3 -m ai_collab.cli tasks update --status ...` 变更，**不手改台账**。
- 本文件 frontmatter 的 `status` 只是镜像，用于人读一致性；两者不一致时以台账为准。
- 注意：台账是**每个工作树各一份**的本机状态（`logs/` 被 gitignore），因此同一工单在不同
  工作树里的台账可见性不相同。本工单由
  `tasks register --session-id ... --model-id ...` 在本工作树注册，路由键 `assignee=claude_code`
  由注册表反查得到，未手工指定。

## 背景

`collaboration/monitoring/` 下的摘要由 CLI 自动生成，数据源是 gitignored 的本机状态。
它们被跟踪进库，导致任何人在自己机器上跑一次 `sessions register` / `tasks validate-contract`
就把库里的团队会话总览覆写成单机视图，而 diff 形如正常刷新。

登记于 `known_gaps.json` **N27**（P2 / open）。本工单执行其修法第一条：
`gitignore` + `git rm --cached`。

## 范围

- 改 `.gitignore`：monitoring 区块的 9 条逐条列举换成 3 条通配。
- `git rm --cached` 全部 13 个已跟踪摘要（11 个 `*_latest.md` + 2 个 `*_test.md`）。
- 工作区文件保留（`--cached`），生成器不动。

## 不在范围

- 团队级总览的替代方案（改由汇总侧生成、换跨会话聚合口径）。
- N26（审计输入只读账本）：同属口径类缺口，需先裁定任务事实源归属，独立处理。
