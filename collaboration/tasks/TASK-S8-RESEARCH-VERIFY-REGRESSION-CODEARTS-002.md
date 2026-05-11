# 任务: S8 后续复核 - 回归修复验证（CodeArts）

**任务ID**: TASK-S8-RESEARCH-VERIFY-REGRESSION-CODEARTS-002  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 复核 Claude 修复结果并产出回归复核报告
- **scope_out**: 不新增功能，不改治理策略

## 输入

- 文件: collaboration/results/RESULT_TASK-S8-BASE-TEST-STABILIZATION-CLAUDE-002.md, tests/unit/test_reconcile_state_drift.py, tests/unit/test_stop_check.py
- 截止时间: 2026-03-04 16:00（北京时间）

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S8-RESEARCH-VERIFY-REGRESSION-CODEARTS-002.md`
- 必须包含: 执行命令、测试结论、风险说明

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_reconcile_state_drift.py::test_apply_reconciles_task_and_patch
python3 -m pytest -q tests/unit/test_stop_check.py::TestMain::test_main_with_invalid_input
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
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
