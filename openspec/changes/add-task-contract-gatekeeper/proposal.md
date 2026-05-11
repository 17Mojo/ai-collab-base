# 增加工单契约守卫（Task Contract Gatekeeper）

## Why

当前协作流程已要求工单必须声明 `change_id`、`primary_skill`、`support_skills` 与 `acceptance_commands`，但缺少自动化守卫，仍存在“人工漏填导致执行漂移”的风险。

## What Changes

- 新增工单契约校验能力，至少覆盖：
  - `task_id`
  - `change_id`
  - `assignee`
  - `reviewer`
  - `primary_skill`
  - `support_skills`
  - `acceptance_commands`
  - `result_file`
- 在 CLI/脚本层提供可执行检查入口，便于控制器与人工巡检复用。
- 将校验结果纳入结果文件模板，形成可追溯证据。

## Impact

- Affected specs: `task-governance`
- Affected code: `ai_collab/cli.py`, `ai_collab/state_manager.py`, `scripts/*`, `tests/unit/*`
- 风险: 旧任务历史文件可能不满足新契约，需要兼容“历史任务忽略/白名单”策略。
