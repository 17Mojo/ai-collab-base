# 任务: Base ACK anomaly close loop

**任务ID**: TASK-TD-20260320-BASE-ACK-ANOMALY-CLOSE-LOOP-CLAUDE-112  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 加强 `ACK watchdog / remediation / missing_ack_monitor` 的闭环规则，降低“完成但未显式 ACK”继续依赖人工补桥的概率
  - 明确 `completed but no explicit ACK`、`testing 卡住`、`历史 bridge 残留` 三类异常的自动化处理边界
  - 为异常状态到摘要/告警文档的映射补齐验证，确保 reviewer 能快速看到问题而不是翻状态文件
  - 为上述行为补齐或修正单测，避免 ACK 自愈链路回退
  - 在结果报告中说明本次改动如何继续减少人工胶水动作
- **scope_out**:
  - 不改 dispatch/trigger 派单协议
  - 不改 Prompt Pack 产品代码
  - 不移除显式 ACK 要求

## 输入

- `ai_collab/ack_watchdog.py`
- `ai_collab/ack_remediation.py`
- `ai_collab/missing_ack_monitor.py`
- `ai_collab/cli.py`
- `tests/unit/test_ack_watchdog.py`
- `tests/unit/test_ack_remediation.py`
- `tests/unit/test_missing_ack_monitor.py`
- `tests/unit/test_cli_ack.py`
- `tests/unit/test_reconcile_state_drift.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260320-BASE-ACK-ANOMALY-CLOSE-LOOP-CLAUDE-112.md`
- 必须包含:
  - ACK 异常闭环行为变更摘要
  - 新增/修正的测试说明
  - 异常状态到摘要/告警文档的映射说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_cli_ack.py \
  tests/unit/test_ack_remediation.py \
  tests/unit/test_ack_watchdog.py \
  tests/unit/test_missing_ack_monitor.py \
  tests/unit/test_reconcile_state_drift.py
python3 -m ai_collab.cli ack-remediation --dry-run
python3 -m ai_collab.cli receipt --dry-run --force-workspace
rg -n "watchdog|remediation|missing ack|explicit ACK|closeout_eligible" \
  ai_collab/ack_watchdog.py \
  ai_collab/ack_remediation.py \
  ai_collab/missing_ack_monitor.py \
  ai_collab/cli.py \
  tests/unit/test_ack_watchdog.py \
  tests/unit/test_ack_remediation.py \
  tests/unit/test_missing_ack_monitor.py \
  tests/unit/test_cli_ack.py
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
