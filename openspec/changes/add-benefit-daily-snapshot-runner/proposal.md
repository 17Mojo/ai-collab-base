# 增加每日收益快照执行器（Daily Benefit Snapshot Runner）

## Why

当前已具备 `benefit` 看板能力，但仍需人工触发，无法保证每日稳定留痕，不利于连续 3 天的稳定性验证。

需要新增“每日快照执行器”，将收益报告按日期固化并生成稳定性追踪台账。

## What Changes

- 新增每日收益快照脚本：
  - 调用收益聚合逻辑生成当日看板与报告（按日期命名）
  - 维护 `automation_benefit_daily_history.jsonl`
  - 输出最新看板 + 日期快照，支持 dry-run
- 增加 Makefile 与 VSCode 任务入口，便于定时执行与手动触发。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `collaboration/scripts/run_daily_benefit_snapshot.py`
  - `tests/unit/test_daily_benefit_snapshot.py`
  - `Makefile`
  - `.vscode/tasks.json`
- 风险控制：
  - 仅做报表落盘，不修改任务状态
  - 对无数据场景输出空统计结果并保持历史结构稳定
