# 任务: Base closeout evidence harden

**任务ID**: TASK-TD-20260320-BASE-CLOSEOUT-EVIDENCE-HARDEN-CLAUDE-110  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 加强 completed/receipt 门禁对结果文件中 `acceptance_commands` 证据的匹配健壮性，避免等价多行格式或轻微 shell 格式差异导致误拦截
  - 保持显式 ACK 要求与负向信号拦截能力不回退
  - 修正 `receipt --dry-run` 与 `receipt apply` 摘要产物的保真问题，避免最新摘要被 dry-run 覆盖后误导 reviewer
  - 为上述行为补齐单测，确保 `109` 这一类真实落地任务不会再次因报告格式噪音卡住
  - 在结果报告中说明本次改动如何缩短 reviewer 收口链路
- **scope_out**:
  - 不改 Prompt Pack 产品代码
  - 不改 dispatch/trigger 派单协议
  - 不移除显式 ACK 门禁

## 输入

- `ai_collab/state_manager.py`
- `scripts/agent_receipt_bridge.py`
- `tests/unit/test_state_manager.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-REAL-CODEARTS-109.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260320-BASE-CLOSEOUT-EVIDENCE-HARDEN-CLAUDE-110.md`
- 必须包含:
  - receipt / completed 门禁行为变更摘要
  - 新增或修复的测试说明
  - `dry-run` 与 `apply` 摘要保真策略
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_state_manager.py \
  tests/unit/test_agent_receipt_bridge.py
python3 -m ai_collab.cli receipt --dry-run --force-workspace
rg -n "acceptance_commands|negative_signals|dry-run|mode=apply|mode=dry-run" \
  ai_collab/state_manager.py \
  scripts/agent_receipt_bridge.py \
  tests/unit/test_state_manager.py \
  tests/unit/test_agent_receipt_bridge.py
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
