# 任务: Base receipt stability uplift

**任务ID**: TASK-TD-20260322-BASE-RECEIPT-STABILITY-UPLIFT-CLAUDE-140  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 依据 `BASE_AUTOMATION_BENEFIT_TRIAGE_2026-03-22.md`，优先处理收据自动化链路稳定性问题
  - 聚焦 `receipt error_count > 0`、收据失败与派单-收据断链率偏高的问题
  - 输出最小修复与验证证据，目标是降低收据失败率而不是重写架构
  - 允许修改 `ai_collab` 收据相关实现与对应测试
- **scope_out**:
  - 不重做收益口径设计
  - 不修改研究验证线资产
  - 不进行破坏性工作区清理

## 输入

- `collaboration/results/BASE_AUTOMATION_BENEFIT_TRIAGE_2026-03-22.md`
- `collaboration/results/RESULT_TASK-TD-20260322-BASE-AUTOMATION-BENEFIT-TRIAGE-CLAUDE-138.md`
- `logs/task_receipt_history.jsonl`
- `logs/task_receipt_report.json`
- `ai_collab/cli.py`
- `ai_collab/state_manager.py`
- `scripts/agent_receipt_bridge.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `tests/unit/test_missing_ack_monitor.py`

## 输出要求

- 资产文件: `collaboration/results/BASE_RECEIPT_STABILITY_UPLIFT_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-RECEIPT-STABILITY-UPLIFT-CLAUDE-140.md`
- 必须包含:
  - 根因定位与修复点
  - 修改文件清单
  - 验证结果
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_agent_receipt_bridge.py \
  tests/unit/test_missing_ack_monitor.py \
  tests/unit/test_cli_ack.py
python3 -m ai_collab.cli receipt --dry-run --force-workspace
test -f collaboration/results/BASE_RECEIPT_STABILITY_UPLIFT_2026-03-22.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [x] planning
- [x] implementing
- [x] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
