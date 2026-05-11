# Tasks

## 1. Implementation
- [x] 1.1 在任务契约校验中新增 `change_id` 强校验逻辑
- [x] 1.2 支持 OpenSpec active/archive 变更目录校验与白名单标签

## 2. Tests
- [x] 2.1 补齐 `tests/unit/test_state_manager.py` 的 `change_id` 正反向测试
- [x] 2.2 执行 `PYTHONPATH=. pytest -q tests/unit/test_state_manager.py tests/unit/test_cli.py tests/unit/test_task_controller_daemon.py`
- [x] 2.3 执行 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-change-id-validation-gatekeeper --strict`
