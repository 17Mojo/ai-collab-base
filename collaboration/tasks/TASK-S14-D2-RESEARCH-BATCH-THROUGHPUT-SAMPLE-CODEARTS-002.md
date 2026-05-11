# 任务: S14 Day2 研究任务 - 批次吞吐样本扩展

**任务ID**: TASK-S14-D2-RESEARCH-BATCH-THROUGHPUT-SAMPLE-CODEARTS-002  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files]
- **scope_in**: 扩展日内吞吐样本并对比 dispatch/receipt 比值稳定性。
- **scope_out**: 不篡改历史样本，不修改 benefit 计算公式。

## 输入

- 文件: logs/task_dispatch_history.jsonl, logs/task_receipt_history.jsonl, logs/automation_benefit_daily_history.jsonl

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S14-D2-RESEARCH-BATCH-THROUGHPUT-SAMPLE-CODEARTS-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli benefit --dry-run
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
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
