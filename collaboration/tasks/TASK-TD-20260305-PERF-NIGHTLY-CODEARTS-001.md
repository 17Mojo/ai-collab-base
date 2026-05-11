# 任务: 技术债工单 - Perf Nightly 基线流水线建设

**任务ID**: TASK-TD-20260305-PERF-NIGHTLY-CODEARTS-001  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: performance-expert
- **support_skills**: [devops-architect, planning-with-files]
- **scope_in**: 增加 nightly/perf workflow，固化性能 smoke 与基线产物输出。
- **scope_out**: 不改线上发布流程，不修改业务功能实现。

## 输入

- 文件: .github/workflows/, scripts/pre_release_check.sh, scripts/longrun_harness.py, tests/unit/test_longrun_harness.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-PERF-NIGHTLY-CODEARTS-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_longrun_harness.py
RUN_PERF_SMOKE=1 bash scripts/pre_release_check.sh --workspace . --quick
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
