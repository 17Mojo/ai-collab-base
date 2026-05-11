# 任务: Day3 加速任务 - TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009

**任务ID**: TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging]
- **scope_in**: Day3: 执行收益链路回归测试，覆盖 dispatch/receipt/benefit/daily snapshot。
- **scope_out**: 不绕过门禁，不进行未授权架构变更

## 输入

- 文件: tests/unit/test_agent_dispatch_bridge.py, tests/unit/test_agent_receipt_bridge.py, tests/unit/test_automation_benefit_dashboard.py, tests/unit/test_daily_benefit_snapshot.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_agent_receipt_bridge.py tests/unit/test_automation_benefit_dashboard.py tests/unit/test_daily_benefit_snapshot.py
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
