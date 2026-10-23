---
name: 派单 payload 必须先校验新鲜度，系统级 RUN 只允许单条 cli run
description: 收到派单 payload 后先比对 logs/task_dispatch_report.json 的 generated_at（≤5 分钟），过期用 cli trigger 一键重生成；系统级 RUN 只许 python3 -m ai_collab.cli run，禁止拆成 dispatch/receipt/benefit 串联
type: feedback
from: Agent
---

在 CodeArts 派单执行中，**收到 payload 后的第一动作是新鲜度校验，而不是直接干活**：读 `logs/task_dispatch_report.json` 的 `generated_at`，与 payload 的 `GeneratedAt` 比对，**时间差 ≤ 5 分钟才算新鲜**；过期必须**立即停止执行**，改用一键修复命令重新生成 payload，再基于新 payload 继续。

同时，**系统级 RUN 只允许执行单条 `python3 -m ai_collab.cli run`**（该命令自带工作区门禁），**禁止**改写为 `python3 -m ai_collab.cli dispatch && python3 -m ai_collab.cli receipt && python3 -m ai_collab.cli benefit` 这类全局串联。收到 `A.RUN` 后必须先完整读完 payload 再执行任务块。

**Why:** payload 携带任务描述、涉及文件、验收命令与结果文件路径，均由上游生成时刻固化；过期 payload 会让执行基于已变更的任务契约（验收命令/口径已漂移）而"完成"了错的东西。拆成串联命令会绕过 `cli run` 内置的工作区门禁，让越权或脏工作区的执行不被拦截。

**How to apply:**
- 顺序固定：校验新鲜度 → （必要时 `python3 -m ai_collab.cli trigger --phrase '<trigger phrase>' --target <agent>` 重生成）→ 读任务工单 → `python3 -m ai_collab.cli tasks update --task-id <ID> --ai <agent> --status implementing` → 实现 → 跑验收命令 → 写结果文件 → 一行 ACK（`A.RUN|task=<ids>|status=<ok/blocked/noop>|result=<paths>`，由 `python3 -m ai_collab.cli ack ...` 生成，禁手写）。
- 结果文件路径写在任务块里，按任务块指定的日期化命名；正文按 PROTOCOL §7.3 四段契约：`## 执行命令` / `## 验证结果` / `## 风险` / `## 回滚`。
- 适用于本项目一切由派单/监控 payload 触发的 CodeArts 会话；普通人工会话不适用。
