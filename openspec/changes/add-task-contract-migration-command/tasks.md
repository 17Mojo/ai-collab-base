# Tasks

## 1. Implementation
- [x] 1.1 在 `StateManager` 增加历史任务契约迁移方法（支持 dry-run）
- [x] 1.2 在 `ai_collab.cli tasks` 新增 `migrate-contract` 子命令
- [x] 1.3 移除 `--legacy-task` / `--include-legacy` 入口并统一校验分支
- [x] 1.4 更新控制器调用与运维手册

## 2. Tests
- [x] 2.1 补齐迁移命令与状态管理器迁移单元测试
- [x] 2.2 执行 `pytest -q tests/unit/test_cli.py tests/unit/test_state_manager.py tests/unit/test_task_controller_daemon.py`
- [x] 2.3 执行 `python3 -m ai_collab.cli tasks migrate-contract --scope all --dry-run`
- [x] 2.4 执行 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-task-contract-migration-command --strict`
