---
name: 投递结果判定口径——等回执超时≠投递失败
description: 派单投递中「等回执超时」不得直接判失败；必须先向 kernel 核实消息是否被接受，否则误报 failed 会触发重投并在对方新开会话，造成双会话并发改同一工作区
type: feedback
from: Agent
---

## 规则

判定一次派单投递的成败时，必须区分两种状态：**「消息没被接受」** 与 **「被接受了但没等到回执」**。后者**不是失败**。

具体要求：

- 等回执期的 `TimeoutError` / `socket.timeout` / `ConnectionError` 必须**显式捕获**，不许以 traceback 逃逸（逃逸会让退出码变成 1，绕过降级链与主流程的收口）。
- 超时后**先核实再定成败**：`GET /session/{id}/message?directory=<工作区>`。
  - 能看到本条用户消息（或其后已有 assistant 消息）→ 消息**已被 kernel 接受** → 视为投递成功：退出码 0、**不降级**、**不重投**。
  - 看不到 → 消息确实没被接受 → 才算失败，换下一个候选（重试仍用新会话）。
- 接受但没等到回执时，agent 可能还在跑，回执里可能还没有 assistant 消息 → `model_used` 允许空串、`model_applied` 允许 `null`；**不许因此判成「模型没生效」**——那会触发假降级。
- 所有候选都失败 → 退出码 2，stderr **逐条列出每个候选的失败原因**（不要 traceback）。
- 等待回执的窗口**单独可配**（如 `--receipt-timeout`，默认 600 秒）；`--timeout` 继续只管建会话/解析模型这类短请求。

**Why:** 2026-10-23 17:34 那一轮派单本身就把该缺陷跑出来了：桥接脚本 `POST /session/{id}/message` 等回执 120 秒超时 → 抛 `TimeoutError`（**不是 `BridgeError`**，既没被降级链捕获、也没被 `main()` 捕获）→ 脚本以 traceback 结束、**退出码 1**（契约要求 2）→ 适配器把这次投递判成 `failed` → intervention 停在 failed（可重试状态）。而 **kernel 侧完全正常**：会话 `ses_e97e33fd4ffezO8oebWzvgsecf` 正常执行，24 条 assistant 消息全部是 `inferhub-provider/glm-5.3`。真实派单要几分钟（读契约 + 跑测试），120 秒必然超时。

误报的后果比故障本身更严重：`failed` 是**可重试**状态 → 下一轮适配器会再投一次 → 在对方那边**再建一个会话** → 两个会话并发改同一个工作区（**2026-10-22 22:01 事故的成因**）。降级链若把超时直接判失败并换候选，同样会再开一个会话。

**How to apply:**
1. 改派单投递/适配器状态机时，先确认「没收到 assistant 回执」没有被当成「投递失败」或「模型没生效」。
2. 涉及失败收口的实现，退出码语义要对齐契约（全失败 = 2，而不是 1），且 stderr 输出要能让复核方逐条读懂。
3. 派单耗时量级与回执窗口要匹配：分钟级任务不能用分钟级以内的回执超时。
4. 与 `project_dispatch_model_fallback.md`（降级链目标）、`project_intervention_delivery_states.md`（投递状态语义）配套使用。
