# 任务: M1 产出 RC 交付清单与运行摘要

**任务ID**: TASK-S8-BASE-RC-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 产出本轮 RC 交付清单、运行摘要、已知限制
- **scope_out**: 不新增治理能力、不改控制器策略

## 输入

- 文件: collaboration/monitoring/S8_DELIVERY_DEADLINE_PLAN_2026-03-03.md, ai_collab/cli.py, scripts/task_controller_daemon.py
- 截止时间: 2026-03-04 12:00（北京时间）

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S8-BASE-RC-CLAUDE-001.md`
- 必须包含: 交付清单、运行摘要、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli status -v
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli controller --once --dry-run
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
