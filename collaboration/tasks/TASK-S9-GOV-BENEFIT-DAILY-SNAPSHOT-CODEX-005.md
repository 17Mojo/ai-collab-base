# 任务: S9 每日收益快照自动化落地

**任务ID**: TASK-S9-GOV-BENEFIT-DAILY-SNAPSHOT-CODEX-005  
**change_id**: add-benefit-daily-snapshot-runner  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 新增每日收益快照执行器 + Make/VSCode 入口 + 历史追踪
- **scope_out**: 不变更任务状态机，不自动触发 dispatch/receipt

## 输入

- `collaboration/scripts/build_automation_benefit_dashboard.py`
- `logs/bench_dispatch_history.jsonl`
- `logs/bench_receipt_history.jsonl`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-GOV-BENEFIT-DAILY-SNAPSHOT-CODEX-005.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_daily_benefit_snapshot.py
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
make benefit-daily
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dispatch-history logs/bench_dispatch_history.jsonl --receipt-history logs/bench_receipt_history.jsonl --target-ratio 3 --window 14
openspec validate add-benefit-daily-snapshot-runner --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
