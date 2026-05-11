# 增加显式 ACK 闭环门禁（Explicit ACK Closeout Gate）

## Why

当前运行时已经收紧为：`claude_code` 任务必须先形成显式 ACK 证据，才允许进入正式闭环。但 OpenSpec 仍未把这条规则写成能力级要求，导致：

- 代码、治理文档与 OpenSpec 基线之间存在漂移风险
- `missing_ack_monitor` / `receipt` / `state_drift` 的“为什么对 Claude 失败”缺少统一规范口径
- 历史状态中仍保留 `9` 条 `claude_code` 的 fallback ACK bridge 记录，监控需要明确区分“旧残留”与“当前有效 ACK”

需要把显式 ACK 闭环门禁正式纳入 `task-governance`，并定义历史残留的审计/可见性要求。

## What Changes

- 为 `task-governance` 增加 `claude_code` 显式 ACK 闭环要求：
  - 仅 `cli-ack` / `chat-ack` 视为有效显式 ACK 证据
  - `receipt` / `reconcile_state_drift` / `missing_ack_monitor` 不得替代 Claude 显式 ACK
  - Stop Hook 在缺失显式 ACK 时必须阻止退出并给出精确 `cli ack` 指令
- 增加监控与审计要求：
  - 监控必须把历史 fallback bridge 识别为“显式 ACK 缺口/残留”
  - 不得把历史 fallback bridge 继续当作 Claude 的有效闭环证据
- 为后续清理历史残留 bridge 记录预留治理路径

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/ack_protocol.py`
  - `ai_collab/cli.py`
  - `ai_collab/hooks/stop_check.py`
  - `ai_collab/missing_ack_monitor.py`
  - `scripts/agent_receipt_bridge.py`
  - `scripts/reconcile_state_drift.py`
  - `collaboration/monitoring/*ACK*`
- 风险控制：
  - 仅对 `claude_code` 强制显式 ACK；`codearts_agent` / `codex` 现有闭环行为保持不变
  - 不自动伪造历史 `chat-ack`
  - 历史 fallback bridge 先标记为残留，不做隐式删除
