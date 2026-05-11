# 任务: Day2 真实任务 - TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007

**任务ID**: TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files]
- **scope_in**: 固化 Day2/Day3 收益追踪 Runbook（执行窗口、命令顺序、失败回滚）
- **scope_out**: 不做未授权架构重写，不跳过契约与结果门禁

## 输入

- 文件: collaboration/monitoring/S9_BENEFIT_STABILITY_PLAN_2026-03-03.md, collaboration/PROTOCOL.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
python3 -m ai_collab.cli benefit --dry-run
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
