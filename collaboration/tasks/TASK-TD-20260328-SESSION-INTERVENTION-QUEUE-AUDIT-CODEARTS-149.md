# 任务: Session intervention queue + audit baseline

**任务ID**: TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149  
**change_id**: add-session-orchestration-control-plane  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 为 `session-orchestration` 建立 V1 的 `session incident / intervention queue` 数据模型
  - intervention 记录至少覆盖 `intervention_id`、`session_id`、`assignee`、`reason_code`、`severity`、`message_artifact`、`delivery_mode`、`delivery_status`、`created_at`、`resolved_at`
  - 默认仅支持 `manual` 传输模式下的 `pending_operator_delivery` 基线，不提前实现 vendor adapter
  - 采用当前项目成熟的 latest JSON / history JSONL / markdown summary 三联输出模式
  - 补齐单测，覆盖创建、状态迁移、汇总输出与审计记录
- **scope_out**:
  - 不实现 Claude Channels push
  - 不实现 CodeArts MCP pull adapter
  - 不做 session health aggregation 的全量信号接入
  - 不削弱现有显式 ACK / receipt / result consistency 门禁

## 输入

- `openspec/changes/add-session-orchestration-control-plane/design.md`
- `openspec/changes/add-session-orchestration-control-plane/tasks.md`
- `collaboration/results/SESSION_ORCHESTRATION_EXTERNAL_RESEARCH_AND_ADAPTER_STRATEGY_2026-03-28.md`
- `collaboration/results/SESSION_ORCHESTRATION_V1_IMPLEMENTATION_SLICES_2026-03-28.md`
- `ai_collab/ack_protocol.py`
- `ai_collab/missing_ack_monitor.py`
- `scripts/agent_receipt_bridge.py`
- `ai_collab/hooks/pre_compact.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149.md`
- 必须包含:
  - 实际修改文件清单
  - intervention queue 字段说明
  - latest/history/summary 产物说明
  - 测试/验证结果
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_intervention_queue.py \
  tests/unit/test_session_intervention_summary.py
python3 -m ruff check \
  ai_collab/intervention_queue.py \
  tests/unit/test_intervention_queue.py \
  tests/unit/test_session_intervention_summary.py
python3 -m ai_collab.cli sessions inspect
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
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
