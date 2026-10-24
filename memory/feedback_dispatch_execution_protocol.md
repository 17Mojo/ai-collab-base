---
name: CodeArts 派单执行全流程规范（新鲜度 → RUN-RESET → RUN → 结果文件 → CLI ACK）
description: 派单流程硬性规范——payload 先校验新鲜度（≤5 分钟）、系统级 RUN 只许单条 cli run、ACK/receipt 禁手写须用 cli ack 生成、结果文件须含 PROTOCOL §7.4 四段+可解析状态行+测试结论小节、终态收口 completed
type: feedback
from: Agent
---

## 常规派单入口的固定顺序

1. **新鲜度校验是第一动作，不是直接干活**：读 `logs/task_dispatch_report.json` 的 `generated_at`，与 payload 的 `GeneratedAt` 比对，**时间差 ≤ 5 分钟才算新鲜**；过期必须**立即停止执行**，改用 `python3 -m ai_collab.cli trigger --phrase '<trigger phrase>' --target <agent>` 一键重生成 payload，再基于新 payload 继续。
2. **系统级 RUN 只允许单条 `python3 -m ai_collab.cli run`**（该命令自带工作区门禁），**禁止**改写为 `python3 -m ai_collab.cli dispatch && python3 -m ai_collab.cli receipt && python3 -m ai_collab.cli benefit` 这类全局串联。收到 `A.RUN` 后必须先完整读完 payload 再执行任务块。
3. **读任务工单 → 翻状态 → 实现 → 验收 → 结果文件 → 复验 → 收口 → ACK**：
   `python3 -m ai_collab.cli tasks update --task-id <ID> --ai <agent> --status implementing` → 实现 → 跑验收命令 → 写结果文件 → 复验契约与审计 → 状态收口 `completed` → 生成 ACK。
4. **ACK**：`A.RUN|task=<ids>|status=<ok/blocked/noop>|result=<paths>`，必须由 `python3 -m ai_collab.cli ack ...` 生成并**原样**回复。

## 静默告警入口（RUN 后未返回 ACK / receipt）

收到「未返回 ACK / receipt」类派单指令时，不要自己拼 ACK 文本，也不要跳回 RUN 起点重跑；顺序固定为 **读 payload → `A.RUN-RESET` → `A.RUN` → 用 CLI 生成 ACK 并原样回复**。先 RUN-RESET 是因为静默态下会话健康度/门禁状态未复位，直接重跑 RUN 仍会卡在同一状态。

## 结果文件的结构契约

写结果文件（`collaboration/results/RESULT-*.md`）时按「**四段标题 → 每条验收命令的真实输出 → 测试结论小节 → 状态行**」的顺序一次写全，写完立刻复验：

1. **契约校验**（`python3 -m ai_collab.cli tasks validate-contract`）：正文需含 PROTOCOL §7.4 四段标题 `## 执行命令` / `## 验证结果` / `## 风险` / `## 回滚`；仅标题齐备**仍可能不合格**——需在「验证结果」段内补出每条验收命令的真实输出与测试结论小节（校验按章节结构统计 checked 项）。
2. **一致性审计**：会**解析结果文件中的状态行**，并据此核对任务终态；工单状态必须收口到 `completed` 且结果文件在位，否则审计不通过。状态行格式与既有同日期 RESULT 文件保持一致（可先读一份对齐）。

**Why:**
- **新鲜度**：payload 携带任务描述、涉及文件、验收命令与结果文件路径，均由上游生成时刻固化；过期 payload 会让执行基于已变更的任务契约（验收命令/口径已漂移）而「完成」了错的东西。拆成串联命令会绕过 `cli run` 内置的工作区门禁，让越权或脏工作区的执行不被拦截。
- **ACK**：该协作控制面由 `ai_collab/ack_watchdog.py` 监控 ACK 静默；手写的 ACK 与 CLI 生成的 receipt 在格式/会话标识上不一致，会被 watchdog 判为未回执，从而再次触发「RUN 后未按预期返回 ACK」的干预工单（例：`SESSION_INTERVENTION_codearts-agent-bridge_ack_silence_after_run_latest.md`）。
- **结果文件**：2026-10-23 执行 `TASK-P1-CLI-EXITCODE-001` 时，结果文件起初只写四段标题，契约校验的 checked 统计不达标；补齐「测试结论」小节并复跑 `validate-contract` + 一致性审计后才转绿。说明校验器看的是「段落 + 结论」的结构，不是「有没有这四个字」。

**How to apply:**
- 收尾顺序：任务状态 `implementing` → 实现 → 跑验收命令 → 写结果文件 → 复验契约与审计 → 状态收口 `completed` → `python3 -m ai_collab.cli ack ...` 生成一行 ACK 原样回复。
- 写文件本身遵守 `feedback_codearts_tooling_constraints.md`（用 bash heredoc，禁 write/edit、禁派生 subagent）。
- 结果文件路径按任务块指定的日期化命名。
- 适用于本项目一切由派单/监控 payload 触发的 CodeArts 会话；普通人工会话不适用。
