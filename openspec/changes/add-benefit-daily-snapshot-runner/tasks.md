# Tasks

## 1. Implementation
- [x] 1.1 新增每日收益快照脚本（latest + dated + history）
- [x] 1.2 增加 Makefile 入口 `benefit-daily`
- [x] 1.3 增加 VSCode 任务入口 `AI Collab: Daily Benefit Snapshot`
- [x] 1.4 补齐单元测试

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_daily_benefit_snapshot.py`
- [x] 2.2 `python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run`
- [x] 2.3 `make benefit-daily`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-benefit-daily-snapshot-runner --strict`
