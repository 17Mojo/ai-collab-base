# 任务: S10 Day3 研究任务 - 多样本连续复核

**任务ID**: TASK-S10-D3-RESEARCH-MULTI-SAMPLE-VERIFY-CODEARTS-003  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files]
- **scope_in**: 复核 bench/day2/day3 多样本收益数据一致性，输出跨样本稳定性结论。
- **scope_out**: 不修改已归档结果文件内容，不手工篡改历史日志。

## 输入

- 文件: logs/bench_automation_benefit_report.json, logs/day2_accel_automation_benefit_report.json, logs/day3_accel_automation_benefit_report.json

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S10-D3-RESEARCH-MULTI-SAMPLE-VERIFY-CODEARTS-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli benefit --dispatch-history logs/bench_dispatch_history.jsonl --receipt-history logs/bench_receipt_history.jsonl --dry-run
python3 -m ai_collab.cli benefit --dispatch-history logs/day3_accel_dispatch_history.jsonl --receipt-history logs/day3_accel_receipt_history.jsonl --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [x] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
