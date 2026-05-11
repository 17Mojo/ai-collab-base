# 任务: Base receipt stability implementation

**任务ID**: TASK-TD-20260322-BASE-RECEIPT-STABILITY-IMPLEMENTATION-CLAUDE-142  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `BASE_RECEIPT_STABILITY_UPLIFT_2026-03-22.md` 的诊断结果，落实最小可执行的 receipt 稳定性修复
  - 优先处理错误分类、报错可诊断性、路径解析降级和低风险重试机制
  - 允许修改 `scripts/agent_receipt_bridge.py`、`ai_collab/state_manager.py` 以及相关测试
  - 输出实际代码修改与验证证据，不停留在方案文档
- **scope_out**:
  - 不重做收益口径设计
  - 不修改研究验证线资产
  - 不进行破坏性工作区清理

## 输入

- `collaboration/results/BASE_RECEIPT_STABILITY_UPLIFT_2026-03-22.md`
- `collaboration/results/RESULT_TASK-TD-20260322-BASE-RECEIPT-STABILITY-UPLIFT-CLAUDE-140.md`
- `scripts/agent_receipt_bridge.py`
- `ai_collab/state_manager.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `tests/unit/test_missing_ack_monitor.py`
- `tests/unit/test_cli_ack.py`

## 输出要求

- 资产文件: `collaboration/results/BASE_RECEIPT_STABILITY_IMPLEMENTATION_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-RECEIPT-STABILITY-IMPLEMENTATION-CLAUDE-142.md`
- 必须包含:
  - 实际修改文件清单
  - 修复点与原因
  - 测试/验证结果
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_agent_receipt_bridge.py \
  tests/unit/test_missing_ack_monitor.py \
  tests/unit/test_cli_ack.py
python3 -m ai_collab.cli receipt --dry-run --force-workspace
test -f collaboration/results/BASE_RECEIPT_STABILITY_IMPLEMENTATION_2026-03-22.md
rg -n "错误分类|重试|路径解析|回滚|测试" collaboration/results/BASE_RECEIPT_STABILITY_IMPLEMENTATION_2026-03-22.md
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
