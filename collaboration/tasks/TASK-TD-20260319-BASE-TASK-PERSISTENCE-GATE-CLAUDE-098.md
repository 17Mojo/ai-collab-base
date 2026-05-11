# 任务: 基座任务落盘与工单资产完整性补齐

**任务ID**: TASK-TD-20260319-BASE-TASK-PERSISTENCE-GATE-CLAUDE-098  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 补齐“任务执行存在但 `collaboration/tasks/TASK-*.md` 实体缺失”的治理缺口
  - 为任务创建、落盘、结果回链提供稳定可追溯的最小机制
  - 补充对应 CLI / 状态管理 / 回归测试，确保任务实体链可验证
  - 在结果报告中说明本次修复对审计、归档、receipt 收口的正向收益
- **scope_out**:
  - 不改 dispatch / trigger payload 文案
  - 不做新的 ACK 协议设计
  - 不扩展新的 Agent 角色或新的工单类型

## 输入

- `ai_collab/cli.py`
- `logs/collaboration_state.json`
- `collaboration/tasks/`
- `collaboration/results/RESULT_TASK-TD-20260313-END2END-CLOSE-LOOP-CODEX-069.md`
- `collaboration/results/BASE_RESEARCH_7DAY_EXECUTION_PLAN_2026-03-19.md`
- `tests/unit/test_cli.py`
- `tests/unit/test_task_controller_daemon.py`
- `tests/unit/test_state_manager.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-TASK-PERSISTENCE-GATE-CLAUDE-098.md`
- 必须包含:
  - 缺失任务实体的根因判断
  - 新增或补齐的任务落盘机制说明
  - 结果文件与任务文件的回链方式
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_cli.py \
  tests/unit/test_task_controller_daemon.py \
  tests/unit/test_state_manager.py
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
