# 任务: S8 后续修复 - 回归失败用例稳定化（Claude）

**任务ID**: TASK-S8-BASE-TEST-STABILIZATION-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 修复 2 个失败用例，确保局部测试可稳定通过
- **scope_out**: 不新增治理能力，不扩展业务范围

## 输入

- 文件: tests/unit/test_reconcile_state_drift.py, tests/unit/test_stop_check.py, scripts/reconcile_state_drift.py, ai_collab/hooks/stop_check.py
- 依赖: RESULT_TASK-S8-RESEARCH-REGRESSION-CODEARTS-001.md 中的失败案例
- 截止时间: 2026-03-04 12:00（北京时间）

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S8-BASE-TEST-STABILIZATION-CLAUDE-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_reconcile_state_drift.py::test_apply_reconciles_task_and_patch
python3 -m pytest -q tests/unit/test_stop_check.py::TestMain::test_main_with_invalid_input
python3 -m pytest -q tests/unit/test_reconcile_state_drift.py tests/unit/test_stop_check.py
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
