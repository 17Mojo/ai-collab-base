# 任务: Day2 真实任务 - TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008

**任务ID**: TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files]
- **scope_in**: 提升 daily snapshot 可用性：补充命令注释与输出说明，降低执行歧义
- **scope_out**: 不做未授权架构重写，不跳过契约与结果门禁

## 输入

- 文件: collaboration/scripts/run_daily_benefit_snapshot.py, README.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_daily_benefit_snapshot.py
make benefit-daily
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
