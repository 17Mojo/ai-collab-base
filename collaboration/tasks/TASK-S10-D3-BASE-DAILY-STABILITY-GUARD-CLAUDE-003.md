# 任务: S10 Day3 基座任务 - 跨日稳定性守护与告警

**任务ID**: TASK-S10-D3-BASE-DAILY-STABILITY-GUARD-CLAUDE-003  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 强化 daily snapshot 跨日连续样本检测与异常提示，确保 >3 指标连续可复现。
- **scope_out**: 不改历史数据结构，不清理历史样本。

## 输入

- 文件: collaboration/scripts/run_daily_benefit_snapshot.py, tests/unit/test_daily_benefit_snapshot.py, logs/automation_benefit_daily_history.jsonl

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S10-D3-BASE-DAILY-STABILITY-GUARD-CLAUDE-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_daily_benefit_snapshot.py tests/unit/test_automation_benefit_dashboard.py
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
