# 任务: 基座运行态契约探针与门禁压测

**任务ID**: TASK-S5-BASE-RUNTIME-PROBE-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 对现有契约门禁与 controller 观测链路做运行态探针验证，并输出问题清单
- **scope_out**: 不新增非必要功能，不改业务逻辑

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 在 S5 时间窗内提交结果
- **CTQ-2 质量门禁**: acceptance_commands 全部通过
- **CTQ-3 漂移控制**: 无越界改动
- **DPMO 记录**: 0/6

## 输入

- 文件: ai_collab/state_manager.py, scripts/task_controller_daemon.py, tests/unit/test_state_manager.py, tests/unit/test_task_controller_daemon.py
- 上下文: S1~S4 已完成，目标是验证“运行态稳定性”
- 依赖: TASK-S4-CHANGE-ID-VALIDATION-GATEKEEPER-001

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S5-BASE-RUNTIME-PROBE-CLAUDE-001.md`
- 必须包含: 变更摘要、执行命令、测试结论、风险与回滚点

## acceptance_commands（必填）

```bash
PYTHONPATH=. pytest -q tests/unit/test_state_manager.py tests/unit/test_task_controller_daemon.py
python3 -m ai_collab.cli controller --once --dry-run
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
