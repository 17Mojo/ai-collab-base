---
name: CodeArts 会话工具约束（禁 write/edit、禁派生子代理；并行 bash 改单条逐个执行）
description: 真机实测 CodeArts 会话中 write/edit 与派生 subagent 会卡死并中止会话，写文件一律用 bash heredoc；并行批次中单条命令失败可致整批 abort，校验多路径改用单条逐个执行
type: feedback
from: Agent
---

## 约束一：写文件一律用 bash heredoc——不用 write/edit，不派生子代理

在 CodeArts（`codearts_agent`）派单执行场景下，**不要用 `write` / `edit` 工具写文件，也不要派生子代理（subagent / Task 工具）**；所有文件产出用 **bash heredoc**（`cat > file <<'EOF' … EOF`）完成，任务在本会话内联完成。

**Why:** 2026-10-23 执行 `TASK-P0-CONSENSUS-ENGINE-001` 派单时，用户给出真机实测结论：在 CodeArts 会话中调用 `write`/`edit` 工具以及派生 subagent 会把会话**卡死并中止**（用户已实测的稳定行为，不是偶发）。用户因此指定改用 bash heredoc 写文件。

**How to apply:**
- 派单 payload（`collaboration/monitoring/AGENT_TRIGGER_*_latest.md`）驱动的执行：写文件/追加内容一律走 bash heredoc。
- 不要为「写文件」「跑测试」等子任务派生 subagent。
- 适用范围：CodeArts 派单/监控 payload 触发的执行；普通 Claude Code 会话不受 write/edit 约束。

## 约束二：可能失败的命令不要放进并行批次

并行 bash 调用中，若其中一条命令对不存在的目录/路径报错（如 `ls src/ai_collab/`），或 glob 不匹配（如 `ls config/*.schema.json`），可能**导致整批并行调用被 abort**（`Tool execution aborted`），即使其他命令本可成功。**校验多个路径或执行可能失败的命令时，改用单条命令逐个执行。**

**Why:** 2026-09-19 两次复现：
1. 并行发出 3 条命令（2 条 bash + 1 条 grep），其中 `ls src/ai_collab/` 因目录不存在报错 → 前两条 bash 调用被中断，仅第三条 grep 成功；
2. gap analysis 时并行批次中 `ls config/*.schema.json` glob 不匹配 → ls 退出码 2 → 整批 abort，连本可成功的 bash 1 也被中断。用户追问「为什么总是卡住」后定位到同一根因。

**How to apply:**
- 含可能失败命令（ls 不确定路径、glob 可能无匹配、grep 可能无匹配）时，拆分为单条逐个执行；
- 路径存在性校验命令不要与正常工作命令混在同一并行批次；
- 若必须并行，先用一条安全命令确认路径存在，再并行执行后续操作；
- 目录不存在与 glob 不匹配都会让 ls 退出码 2，二者均会触发整批 abort。
- 适用场景不限 CodeArts：路径校验、目录探测、glob 探测、不确定是否存在的文件读取等。
