# 任务: S6 控制器超时前预警能力落地与模板固化

**任务ID**: TASK-S6-BASE-PREWARN-GATEKEEPER-CODEX-001  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 新增 controller prewarning（超时前提醒）并固化到模板/规则/配置
- **scope_out**: 不改任务核心契约字段，不改业务功能模块

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 当日完成并收口（Y）
- **CTQ-2 质量门禁**: acceptance_commands 全部通过（Y）
- **CTQ-3 漂移控制**: 无越界改动（Y）
- **DPMO 记录**: 0/6

## 输入

- 文件: scripts/task_controller_daemon.py, ai_collab/cli.py, .vscode/ai-collab.json, collaboration/templates/TASK_TEMPLATE_SKILL_GATED.md
- 上下文: S5 已建立 stale 管控，需要在 stale 前发预警降低被动 blocked
- 依赖: TASK-S5-GOV-REVIEW-CODEX-001

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S6-BASE-PREWARN-GATEKEEPER-CODEX-001.md`
- 必须包含: 变更摘要、执行命令、测试结论、风险与回滚点

## acceptance_commands（必填）

```bash
PYTHONPATH=. pytest -q tests/unit/test_state_manager.py tests/unit/test_task_controller_daemon.py tests/unit/test_cli.py
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
