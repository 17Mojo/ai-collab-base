---
name: CodeArts 派单执行的工具约束（禁 write/edit、禁派生代理、写文件用 bash heredoc）
description: 真机实测 CodeArts 会话中 write/edit 工具与派生 subagent 会卡死并中止会话；派单任务写文件一律用 bash heredoc
type: feedback
from: Agent
---

在 CodeArts（`codearts_agent`）派单执行场景下，**不要用 `write` / `edit` 工具写文件，也不要派生子代理（subagent / Task 工具）**；所有文件产出用 **bash heredoc**（`cat > file <<'EOF' … EOF`）完成。

**Why:** 2026-10-23 执行 `TASK-P0-CONSENSUS-ENGINE-001` 派单时，用户给出真机实测结论：在 CodeArts 会话中调用 `write`/`edit` 工具以及派生 subagent 会把会话**卡死并中止**（用户已实测的稳定行为，不是偶发）。用户因此指定改用 bash heredoc 写文件。

**How to apply:**
- 派单 payload（`collaboration/monitoring/AGENT_TRIGGER_*_latest.md`）驱动的执行：写文件/追加内容一律走 bash heredoc，避免 `write`/`edit` 工具调用。
- 不要为「写文件」「跑测试」等子任务派生 subagent，任务在本会话内联完成。
- 与 ACK 规范并行遵守：ACK 仍必须由 `python3 -m ai_collab.cli ack ...` 生成并原样回复，顺序为 读 payload → `A.RUN-RESET` → `A.RUN` → 生成 ACK（见 `feedback_ack_cli_generated.md`）。
- 适用于本项目一切由 CodeArts 派单/监控 payload 触发的执行；普通 Claude Code 会话不受此约束。
