---
name: ACK/receipt 必须由 CLI 生成且先 RUN-RESET 再 RUN
description: 派单流程硬性规范——ACK/receipt 禁止手写，须用 python3 -m ai_collab.cli ack ... 生成并原样回复；RUN 静默无 ACK 时先 A.RUN-RESET 再 A.RUN
type: feedback
from: Agent
---

在 AI Collaboration System 的派单执行中，**ACK/receipt 绝对不能手写**。正确做法是执行任务块中给出的 `python3 -m ai_collab.cli ack ...` 命令，把命令生成的 ACK 内容**原样**回给用户。若 `codearts_agent` 在 RUN 后未按预期返回 ACK 或 receipt，标准处理顺序是：先完整读取派单 payload（`collaboration/monitoring/AGENT_TRIGGER_<agent>_latest.md`），再执行 `A.RUN-RESET`，然后重新执行 `A.RUN`。

**Why:** 该协作控制面由 `ai_collab/ack_watchdog.py` 监控 ACK 静默，手写的 ACK 与 CLI 生成的 receipt 在格式/会话标识上不一致，会被 watchdog 判为未回执，从而再次触发「RUN 后未按预期返回 ACK」的干预工单（例：`SESSION_INTERVENTION_codearts-agent-bridge_ack_silence_after_run_latest.md`）。先 RUN-RESET 是因为静默态下会话健康度/门禁状态未复位，直接重跑 RUN 仍会卡在同一状态。

**How to apply:** 收到「未返回 ACK / receipt」类派单指令时，不要自己拼 ACK 文本，也不要跳回 RUN 起点重跑；顺序固定为 读 payload → `A.RUN-RESET` → `A.RUN` → 用 CLI 生成 ACK 并原样回复。相关任务 ID（如 `TASK-P0-CONSENSUS-ENGINE-001`）以 payload 任务块为准。
