# 任务: S9 自动化收益看板落地（持续 >3 追踪）

**任务ID**: TASK-S9-GOV-BENEFIT-DASHBOARD-CODEX-004  
**change_id**: add-automation-benefit-dashboard  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 新增收益看板脚本与 CLI 命令，按日追踪 dispatch/receipt 效率比
- **scope_out**: 不改变任务状态机，不自动调整派单策略

## 输入

- 依赖文件: `logs/task_dispatch_history.jsonl`, `logs/task_receipt_history.jsonl`
- 实测文件: `logs/bench_dispatch_history.jsonl`, `logs/bench_receipt_history.jsonl`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-GOV-BENEFIT-DASHBOARD-CODEX-004.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_automation_benefit_dashboard.py tests/unit/test_cli.py
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli benefit --dispatch-history logs/bench_dispatch_history.jsonl --receipt-history logs/bench_receipt_history.jsonl --report logs/bench_automation_benefit_report.json --output collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_bench.md
openspec validate add-automation-benefit-dashboard --strict
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
