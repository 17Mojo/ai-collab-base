# RESULT-DISPATCH-ENQUEUE-2026-10-23

**任务**：`TASK-P1-DISPATCH-ENQUEUE-001`
**执行方**：Claude Code（AGENT_ARCH）
**状态**：completed
**提交**：`3ceb011 feat(dispatch): 派单即入队即送达 + 派发 prompt_pack 热度工单`

---

## 一、问题：派单到开工之间有 120s 空窗

干预队列（`ai_collab/intervention_queue.py`）原本**只有**
`ai_collab/session_health.py` 的 ACK 静默看门狗会写。也就是说
**派单本身不产生任何可投递的东西**：第一轮投递只能等下一轮
`cli sessions health` 跑起来、且看门狗判定「ACK 静默 > 120s」之后才发生。

| 环节 | 位置 | 现状 |
|---|---|---|
| 静默阈值 | `ai_collab/ack_watchdog.py` | `DEFAULT_THRESHOLD_SECONDS = 120` |
| 唯一入队方 | `ai_collab/session_health.py:426` | 只有 ACK 静默看门狗会 `enqueue_intervention` |
| 派单链路 | `cmd_dispatch` → `cmd_trigger` | 只产出 payload 文件，**从不入队** |

实测链路证实了这一点：2026-10-23 00:47 那次真机投递
（`candidate_count=1, queued_count=1`）发生在 `sessions health` 那一轮，
不是派单那一刻。

## 二、改动

### 2.1 `ai_collab/cli/_cli_main.py`

1. `_generate_trigger_payload_files()` 额外返回 `payload_files` 映射
   （assignee → payload 文件相对路径），入队时要用。
2. 新增 `_enqueue_dispatch_interventions()`：派单当场把触发 payload 挂进干预队列。
3. 新增 `_deliver_dispatch_interventions()`：入队后立刻跑一次 codearts 拉取适配器。
   **不重复实现投递逻辑** —— 会话选择、cron 兜底、失败上报、成功后翻在途
   全在适配器里，这里只做「触发一次适配器」。
4. `cmd_trigger()` 接上这两步，并把结果写进触发报告
   （新增 `dispatch_interventions` / `dispatch_delivery` 两个字段）。

### 2.2 `ai_collab/cli/__init__.py`

导出两个新函数。

## 三、两个坑（都做成了不变量测试）

### 坑 1：状态必须是 `pending_operator_delivery`，不能是 `queued_for_delivery`

`enqueue_intervention(delivery_mode="bridge")` 的默认状态是 `queued_for_delivery`，
而 `queued_for_delivery` 属于 `IN_FLIGHT_DELIVERY_STATUSES` ——
codearts adapter 的在途过滤器会**整个跳过**它。投递根本不会发生，而且不报错。

**反向验证**（把 `delivery_mode` 改回 `"bridge"` 后重跑本文件测试）：

```
FAILED test_enqueue_dispatch_intervention_uses_pending_operator_delivery
FAILED test_enqueued_dispatch_intervention_is_picked_up_by_codearts_adapter
  assert 0 == 1        # candidate_count 从 1 掉到 0
```

### 坑 2：同一 assignee 只能有一条未决干预

重复派单会开出第二条干预 → 适配器投两次 → 对方那边两个并发会话改同一个工作区
（这正是干预队列里 `IN_FLIGHT_DELIVERY_STATUSES` 那段注释描述的事故形态）。

去重键取 `(session_id, assignee, reason_code)`，`session_id` 用稳定的
`dispatch-{assignee}`，所以重复派单命中同一条。
**`failed` 不参与复用** —— 复用一条已失败的记录等于永远投不出去。

## 四、测试

`tests/unit/test_dispatch_intervention_wiring.py`（新建，10 条）：

| # | 测试 | 守住的规则 |
|---|---|---|
| 1 | `test_enqueue_dispatch_intervention_uses_pending_operator_delivery` | 状态是 `pending_operator_delivery`，且**不在**在途集合里 |
| 2 | `test_enqueued_dispatch_intervention_is_picked_up_by_codearts_adapter` | adapter 看得见它（`candidate_count=1`、`skipped_in_flight_count=0`） |
| 3 | `test_repeat_dispatch_reuses_open_intervention` | 重复派单复用同一条，不开出第二条 |
| 4 | `test_repeat_dispatch_after_failure_creates_new_intervention` | `failed` 不复用 |
| 5 | `test_dry_run_does_not_enqueue_intervention` | dry-run 只看不写 |
| 6 | `test_enqueue_covers_every_assignee` | 多个 assignee 各一条 |
| 7 | `test_generate_trigger_payload_files_exposes_payload_files` | payload 映射与文件落盘一致 |
| 8 | `test_delivery_is_skipped_in_dry_run` | dry-run 不投递 |
| 9 | `test_delivery_is_skipped_without_codearts_target` | 非 codearts 目标不触发 codearts 适配器 |
| 10 | `test_delivery_runs_adapter_for_codearts_target` | 投递后状态翻成在途，避免下一轮重复投递 |

## 执行命令

```bash
# 验收命令（与工单 acceptance_commands 逐字一致）
python3 -m pytest tests/unit/test_dispatch_intervention_wiring.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/

# 补充验证
python3 -m mypy ai_collab/
python3 -m ai_collab.cli 2x codearts --dry-run
```

## 测试结论

| 项 | 结果 |
|---|---|
| 本任务新增测试 | **10 passed** |
| 全量测试 | **2845 passed, 6 skipped**（= 改动前 2835 + 新增 10；6 条 skip 全是「本地后端/数据库未启动」的环境性跳过，与本次改动无关） |
| ruff（`ai_collab/` + 新测试文件） | **All checks passed**（无新增问题） |
| mypy（`ai_collab/`） | **Success: no issues found in 100 source files** |
| 反向验证 | 把 `delivery_mode` 改回 `"bridge"` → **2 failed**，`candidate_count` 由 1 掉到 0 |
| 行为级复验 | `2x codearts --dry-run` 正常产出 payload 且**不**入队（dry-run 只看不写） |
| 工单契约校验 | `checked=1 skipped=0 invalid=0` |

## 风险

| 风险 | 影响 | 处置 |
|---|---|---|
| 派单即投递 ⇒ 一次派单可能在对方开出**新会话** | 对方会话数量增长 | 去重键保证同一 assignee 同时只有一条未决干预；投递成功后状态翻成在途，适配器下一轮跳过 |
| `session_id` 用的是合成值 `dispatch-{assignee}`，不是 kernel 的 `ses_` 形态 | bridge 的 `resolve_direct_session` 认不出，会落到 cron 通道新建会话 | 这是**期望行为**：新任务应当开新会话，而不是续跑上一个任务的会话。若要续跑，把 `session_id` 换成真实 `ses_` ID 即可 |
| `cmd_trigger` 现在会触发一次 codearts 适配器 | 派单命令的网络/副作用变多 | 只在 target 含 `codearts_agent` 时触发；dry-run 完全跳过；投递失败只打印 `投递失败:`，不改变命令退出码 |
| 干预队列里已有其他来源的未决干预 | 本次投递会**连带**投出去 | 这是适配器的既有语义（按 assignee 拉取全部未决项），不是本次引入的行为；dry-run 模式可先看 `candidate_count` |
| 触发的干预只发 `payload_files` 里当前 assignee 的 payload | 多个 assignee 时各投各自的 | 每个 assignee 一条独立干预，artifact 指向自己的 payload 文件 |

## 回滚

```bash
# 回滚本任务全部改动
git revert 3ceb011

# 若只回滚接线、保留工单（工单是独立文件，可单独保留）
#   - ai_collab/cli/_cli_main.py：删掉 cmd_trigger 里的两处调用，
#     以及 _enqueue_dispatch_interventions / _deliver_dispatch_interventions
#   - ai_collab/cli/__init__.py：删掉两个导出
#   - tests/unit/test_dispatch_intervention_wiring.py：删除
```

回滚后干预队列会回到「只有 ACK 静默看门狗会写」的状态，
即派单到开工重新变成最长 120s 的空窗 —— 预期行为。

---

## 配套产出

| 产出 | 位置 |
|---|---|
| 任务工单 | `collaboration/tasks/TASK-P1-DISPATCH-ENQUEUE-001.md` |
| 新增测试 | `tests/unit/test_dispatch_intervention_wiring.py`（10 条） |
| 改动 | `ai_collab/cli/_cli_main.py`、`ai_collab/cli/__init__.py` |
| 开发日志 | `logs/claude-code/2026-10/2026-10-22_codearts-collab-wiring.md` §20 |
| 同批派出的工单 | `collaboration/tasks/TASK-P1-PROMPT-TRENDING-001.md`（派给 CodeArts / AGENT_EXEC） |
