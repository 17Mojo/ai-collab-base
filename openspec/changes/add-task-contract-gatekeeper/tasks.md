# Tasks

## 1. Implementation
- [x] 1.1 定义工单契约字段与校验规则（含历史任务兼容策略）
- [x] 1.2 提供可执行校验入口（CLI 子命令或脚本）
- [x] 1.3 将校验结果接入控制器巡检与结果文件模板
- [x] 1.4 补齐单元测试与异常场景测试
- [x] 1.5 更新协作文档与使用示例

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_cli.py tests/unit/test_state_manager.py`
- [x] 2.2 `python3 -m ai_collab.cli status -v`
- [x] 2.3 `python3 -m ai_collab.cli controller --once --dry-run`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-task-contract-gatekeeper --strict`
