## Context

运行时已经实施了 `claude_code` 显式 ACK 闭环门禁，但当前 OpenSpec 基线仍停留在“receipt 可以对 testing 任务自动收口”的宽口径。

刷新运行面证据后，当前状态是：

- `receipt --dry-run`：`candidate_count=0`
- `reconcile_state_drift --fail-on-drift`：`drift_count=0`
- `ACK_WATCHDOG_SUMMARY_latest.md`：无静默任务
- `MISSING_ACK_SUMMARY_latest.md`：存在 `9` 条历史 `claude_code` fallback bridge 残留，被正确标记为 `explicit ACK required`

这说明新行为已经生效，但规范与历史数据口径尚未完全收敛。

## Goals

- 把 `claude_code` 显式 ACK 要求纳入 `task-governance` 的正式能力定义
- 让 receipt / drift / missing-ack / stop-hook 的闭环边界具备统一判定口径
- 让监控能区分“真实缺 ACK”、“历史 fallback 残留”和“已满足显式 ACK”的状态

## Non-Goals

- 不重写 `codearts_agent` / `codex` 的 ACK 闭环规则
- 不自动伪造或回填历史 `chat-ack`
- 不在本变更里做大规模状态重建或历史任务清洗

## Decisions

### 1. 显式 ACK 的有效来源

`claude_code` 的有效闭环证据只接受：

- `source=cli-ack*`
- `source=chat-ack*`

其他来源，包括 `missing_ack_monitor*`、`receipt_bridge*`、`completed_state_fallback`，都不能替代显式 ACK。

### 2. 闭环门禁适用面

以下链路都必须读取同一显式 ACK 判定：

- `ai_collab.cli ack`
- `ai_collab/hooks/stop_check.py`
- `scripts/agent_receipt_bridge.py`
- `scripts/reconcile_state_drift.py`
- `ai_collab/missing_ack_monitor.py`

### 3. 历史残留的处理方式

历史 `claude_code` fallback bridge 记录先保留，但在监控和报告里明确显示为：

- 非显式 ACK
- 不可用于自动闭环
- 需要人工审查或后续 remediation
