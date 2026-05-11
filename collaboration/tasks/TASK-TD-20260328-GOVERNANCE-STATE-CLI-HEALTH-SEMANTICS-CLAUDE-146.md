# 任务: Governance state + CLI health semantics hardening

**任务ID**: TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 merged `main` 基线上，为 `state_manager + cli control plane` 做第二批收口
  - 聚焦 operator 可读性与控制面确定性，不做大改
  - 允许修改 `ai_collab/state_manager.py`、`ai_collab/cli.py`、`ai_collab/daily_report.py` 及对应测试
  - 优先处理任务/状态输出的稳定排序、`status` 报告健康语义、低活跃工作区下的误报/歧义
- **scope_out**:
  - 不修改 `receipt/ack/result consistency` 核心实现
  - 不修改 `scripts/agent_receipt_bridge.py`
  - 不做工作区清理或主工作区同步

## 输入

- `ai_collab/state_manager.py`
- `ai_collab/cli.py`
- `ai_collab/daily_report.py`
- `tests/unit/test_state_manager.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_daily_report.py`
- `collaboration/results/GOVERNANCE_POST_MERGE_MAINLINE_VERIFICATION_CHECKLIST_2026-03-28.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146.md`
- 必须包含:
  - 实际修改文件清单
  - 为什么这次修改能降低 operator 误判
  - 测试/验证结果
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_state_manager.py \
  tests/unit/test_cli.py \
  tests/unit/test_daily_report.py
python3 -m ruff check ai_collab/state_manager.py ai_collab/cli.py ai_collab/daily_report.py tests/unit/test_state_manager.py
python3 -m ai_collab.cli status
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
