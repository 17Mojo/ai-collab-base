# Tasks

## 1. Implementation
- [x] 1.1 新增自动化收益看板脚本（按天聚合 dispatch/receipt 历史、计算效率比与达标状态）
- [x] 1.2 在 CLI 增加 `benefit` 命令，支持配置默认值与参数覆盖
- [x] 1.3 在初始化配置中增加 `benefit` 默认配置段
- [x] 1.4 补齐单元测试（脚本行为、CLI 命令与路由）

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_automation_benefit_dashboard.py tests/unit/test_cli.py`
- [x] 2.2 `python3 -m ai_collab.cli benefit --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-automation-benefit-dashboard --strict`
