# 增加历史任务契约迁移命令并移除 legacy 分支

## Why

S2 已建立工单契约守卫，但历史任务仍依赖 legacy 跳过逻辑，导致全量校验无法严格执行。  
当前状态里大量历史任务缺少契约字段，`validate-contract --scope all` 只能通过 `--include-legacy` 暴露问题，不利于统一治理和自动化门禁。

## What Changes

- 新增可执行命令：`python3 -m ai_collab.cli tasks migrate-contract --scope all|active [--dry-run]`
- 在状态管理器中实现历史任务契约迁移：补齐缺失字段、设置 `contract_required=true`
- 取消 CLI 层 legacy 分支参数：
  - 移除 `tasks register --legacy-task`
  - 移除 `tasks validate-contract --include-legacy`
- 契约校验逻辑统一为“按 scope 全量检查，不再按 legacy 跳过”

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/state_manager.py`
  - `ai_collab/cli.py`
  - `scripts/task_controller_daemon.py`
  - `tests/unit/test_state_manager.py`
  - `tests/unit/test_cli.py`
  - `collaboration/guides/TASK_CONTRACT_OPS_PLAYBOOK.md`
- 风险:
  - 一次性迁移会写入历史任务默认字段，需要在结果中保留可追溯迁移标记
