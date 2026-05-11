# 任务: S10 Day1 基座任务 - 研究指标同步到收益看板

**任务ID**: TASK-S10-D1-BASE-RESEARCH-METRIC-SYNC-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 将研究项目结果质量指标映射到收益看板可读字段，支撑跨日稳定性追踪。
- **scope_out**: 不修改业务域逻辑，不引入新外部依赖。

## 输入

- 文件: collaboration/scripts/build_automation_benefit_dashboard.py, collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md, ai_collab/cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S10-D1-BASE-RESEARCH-METRIC-SYNC-CLAUDE-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_automation_benefit_dashboard.py tests/unit/test_cli.py
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
