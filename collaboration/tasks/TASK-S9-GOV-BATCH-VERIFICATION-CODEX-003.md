# 任务: S9 自动化批处理实测（dispatch + receipt）

**任务ID**: TASK-S9-GOV-BATCH-VERIFICATION-CODEX-003  
**change_id**: add-agent-receipt-bridge  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 对现有自动派单与自动回执能力进行真实批处理实测并产出量化收益结论
- **scope_out**: 不新增运行时能力，不改任务契约字段

## 输入

- 依赖能力: `dispatch`（S9-1）、`receipt`（S9-2）
- 样本任务: `TASK-S9-BENCH-AUTOFLOW-001..006`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-GOV-BATCH-VERIFICATION-CODEX-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli dispatch --report logs/bench_dispatch_report.json --history logs/bench_dispatch_history.jsonl --state logs/bench_dispatch_state.json --orders collaboration/monitoring/AGENT_DISPATCH_ORDERS_bench.md
python3 -m ai_collab.cli receipt --report logs/bench_receipt_report.json --history logs/bench_receipt_history.jsonl --state logs/bench_receipt_state.json --summary collaboration/monitoring/AGENT_RECEIPT_SUMMARY_bench.md
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli status -v
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
