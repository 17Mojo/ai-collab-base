# 任务: 结果文件门禁与 receipt 收口契约补齐

**任务ID**: TASK-TD-20260319-BASE-RECEIPT-RESULT-CONTRACT-CLAUDE-101  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 基于 `098/099` 的实际回传，补齐结果文件门禁与 receipt 收口契约之间的兼容性
  - 降低因标题命名、命令回写格式差异导致的 `testing -> completed` 收口失败
  - 为结果文件必填 section、acceptance_commands 追踪与 receipt closeout 增加回归保护
  - 在结果报告中说明本次修复如何减少“结果已回传但无法自动收口”的状态漂移
- **scope_out**:
  - 不改 dispatch trigger 暗语协议
  - 不新增 Agent 角色
  - 不做新的 benefit/dashboard 统计能力

## 输入

- `ai_collab/state_manager.py`
- `ai_collab/cli.py`
- `tests/unit/test_state_manager.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `logs/task_receipt_report.json`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-TASK-PERSISTENCE-GATE-CLAUDE-098.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-STATE-SYNC-AUTOMATION-CODEARTS-099.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-RECEIPT-RESULT-CONTRACT-CLAUDE-101.md`
- 必须包含:
  - 触发本次修复的真实 closeout 问题摘要
  - 门禁/兼容性补齐点清单
  - 回归测试结果
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_state_manager.py \
  tests/unit/test_cli.py \
  tests/unit/test_agent_receipt_bridge.py
python3 -m ai_collab.cli receipt --dry-run
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
