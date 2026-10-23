---
name: project-intervention-delivery-states
description: 干预队列的投递状态语义——入队必须用 delivery_mode="manual"（pending_operator_delivery），用 "bridge" 会被在途过滤器静默跳过，投递根本不会发生且不报错
type: project
from: Agent
---

干预队列（`ai_collab/intervention_queue.py`）里的 `delivery_status` 决定
「这条干预会不会被适配器投出去」，而**投不出去时没有任何报错** —— 这是个静默失败。

**Why:** `enqueue_intervention()` 的默认状态按投递模式推导：

| `delivery_mode` | 默认 `delivery_status` | 会被 codearts adapter 投吗 |
|---|---|---|
| `"manual"` | `pending_operator_delivery` | **会**（不在在途集合里） |
| `"bridge"` | `queued_for_delivery` | **不会** —— 属于 `IN_FLIGHT_DELIVERY_STATUSES`，被在途过滤器整个跳过 |

在途过滤器的本意是防止「每轮轮询都重投，在对方开出两个并发会话改同一个工作区」，
但它把「刚入队、还没投」和「已经投了、等 ACK」两种状态混成了同一个值。
2026-10-23 派单接线时踩了这个坑：反向验证实测把 `delivery_mode` 从
`"manual"` 改成 `"bridge"` 后，适配器的 `candidate_count` 由 **1 掉到 0** ——
干预既没被投出去，也没有任何失败记录。

**How to apply:**

- 新写任何 `enqueue_intervention()` 调用：**入队一律用 `delivery_mode="manual"`**
  （状态 = `pending_operator_delivery`）。投出去之后由适配器自己
  `ack_intervention(delivery_status="queued_for_delivery")` 翻成在途。
- 「入队」和「投递」是两件事：入队只是把东西挂上队列，真正投出去靠
  适配器轮询（`run_codearts_pull_adapter` 等）或本仓的派单即送达接线
  （`cmd_trigger` → `_enqueue_dispatch_interventions` → `_deliver_dispatch_interventions`）。
- 同一 assignee 只能留**一条**未决干预：重复入队会让适配器投两次，
  在对方开出两个并发会话。去重键取 `(session_id, assignee, reason_code)`；
  `failed` 不参与复用（复用一条已失败的记录等于永远投不出去）。
- 派单派发前先 `python3 -m ai_collab.cli dispatch --dry-run` 核对候选任务清单 ——
  历史上 `--redispatch` 会把已 completed 的历史任务一起塞进 payload
  （已于 2026-10-23 加终态守卫修掉，但派单前核对仍是便宜的习惯）。

相关：[[codearts-kernel-cron-residue]]、[[codearts-delivery-verification]]
