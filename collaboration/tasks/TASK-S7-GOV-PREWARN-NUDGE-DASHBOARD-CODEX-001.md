# 任务: S7 自动催办消息模板与控制器趋势看板落地

**任务ID**: TASK-S7-GOV-PREWARN-NUDGE-DASHBOARD-CODEX-001  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 提供自动催办模板生成与趋势看板，支撑预警阶段的运营闭环
- **scope_out**: 不改业务模块，不引入外部依赖

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 当日内完成并可复跑
- **CTQ-2 质量门禁**: acceptance_commands 全绿
- **CTQ-3 漂移控制**: 无越界改动
- **DPMO 记录**: 0/6

## 输入

- 文件: scripts/task_controller_daemon.py, ai_collab/cli.py, collaboration/scripts/*.py, collaboration/monitoring/*.md
- 上下文: S6 已落地 prewarning 机制，S7 需补齐运营动作与可视化
- 依赖: TASK-S6-BASE-PREWARN-GATEKEEPER-CODEX-001

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S7-GOV-PREWARN-NUDGE-DASHBOARD-CODEX-001.md`
- 必须包含: 变更摘要、执行命令、测试结论、风险与回滚点

## acceptance_commands（必填）

```bash
PYTHONPATH=. pytest -q tests/unit/test_state_manager.py tests/unit/test_task_controller_daemon.py tests/unit/test_cli.py
python3 -m ai_collab.cli controller --once --dry-run
python3 collaboration/scripts/generate_agent_nudge_messages.py --workspace .
python3 collaboration/scripts/build_controller_trend_dashboard.py --workspace . --window 20
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
