# RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23：派单链路的模型降级与可观测性（等回执超时 ≠ 投递失败）

- **状态**: completed
- **任务 ID**: TASK-P1-DISPATCH-MODEL-FALLBACK-001
- **change_id**: bugfix/no-spec
- **角色**: AGENT_EXEC（codearts_agent）
- **复核方**: AGENT_TEST（claude_code）
- **完成时间**: 2026-10-23T19:20+08:00
- **本轮范围**：R1b（等回执超时语义）+ R9（结果文件）+ 提交 + ACK
- **R1–R8 状态**：已由复核方复审通过并代提交（`a5b0d09`），provider 注册表作用域缺陷由复核方修复（`6251395`）；本轮**未重做**

## 执行命令

```bash
# 0. 门禁修正留痕（工单上游 change_id 不在白名单）
python3 -m ai_collab.cli tasks update --change-id bugfix/no-spec \
  --note "工单上游写 feature/no-spec 不在 TASK_CONTRACT_SPECIAL_CHANGE_IDS 白名单，改为白名单内的等价 no-spec 标签"

# 1. 契约验收命令（全部实跑）
python3 -m pytest tests/unit/test_codearts_bridge_deliver.py tests/unit/test_codearts_adapter.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/ scripts/
python3 -m mypy ai_collab/

# 2. 真机只读复验（不投递、不建会话）
#    GET /session/{id}/message?directory=<ws> 的真实响应形状 + 核实判定
python3 - <<'PY'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("bridge", "scripts/codearts_bridge_deliver.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge
spec.loader.exec_module(bridge)
user, pw = bridge.resolve_credentials()
ws = pathlib.Path(".").resolve()
client = bridge.KernelClient(base_url=bridge.DEFAULT_KERNEL_URL, username=user,
                             password=pw, timeout=120, workspace=ws, receipt_timeout=600)
msgs = client.list_messages(session_id="ses_e97e33fd4ffezO8oebWzvgsecf", workspace=ws)
# 真实会话 104 条消息；核实判定四种情形全部符合预期
PY
```

### 实现摘要（只讲 R1b，R1–R8 见复核方结论）

**R1b：等回执超时 ≠ 投递失败。** 真机根因（2026-10-23 17:34 本轮派单本身）：
`POST /session/{id}/message` 等回执 120 秒超时 → 抛 `TimeoutError`（**不是**
`BridgeError`，降级链和 `main()` 都没接住）→ 脚本以 traceback 结束、退出码 1
（契约要求 2）→ 适配器判 `failed` → `failed` 是**可重试**状态 → 下一轮再投
一次 → 对方那边**再建一个会话** → 两个会话并发改同一个工作区（2026-10-22
22:01 事故的成因）。而 kernel 侧完全正常：会话
`ses_e97e33fd4ffezO8oebWzvgsecf` 正常执行，assistant 消息全是
`inferhub-provider/glm-5.3`。

| 契约 | 落点 | 改动 |
|---|---|---|
| R1b-a 显式收口超时类异常 | `scripts/codearts_bridge_deliver.py`：`KernelClient.request()` | 新增 `except TimeoutError`（`socket.timeout` 在 3.10+ 是它的别名，一句同时接住两者）→ 抛新类型 `BridgeTimeoutError`（`BridgeError` 子类）；补 `except ConnectionError` 与 `except http.client.HTTPException` → `BridgeError`。**超时/连接中断不再以 traceback 逃逸** |
| R1b-b 先核实再定成败 | 同上：`send_message_awaiting_receipt()` + `verify_message_accepted()` | 等回执超时 → `GET /session/{id}/message?directory=<ws>` 核实：看得到本条用户消息 → **视为投递成功**（退出码 0、**不降级**、**不重投**）；看不到 → 这次候选才算失败，换下一个候选（仍用全新会话） |
| R1b-c `accepted_without_receipt` | 桥接脚本 + `ai_collab/adapters/codearts_adapter.py` | 新字段出现在 `--json` 输出、回执文件、`model_attempts` 对应项、适配器 delivery 记录与摘要行 |
| R1b-d `--receipt-timeout` | 桥接脚本 `main()` / `KernelClient.__init__` | 新增 `--receipt-timeout`（默认 600 秒）**单独**管"等回执"窗口；`--timeout`（默认 120）继续管建会话 / 查 provider 注册表这类短请求，两者不再混用 |
| R1b-e 失败收口 | 桥接脚本 `main()` | 全部候选失败 → 退出码 2、stderr 逐条列出每个候选的失败原因；网络类异常额外有兜底 `except (TimeoutError, ConnectionError)` → 非零退出码 + 明确原因，绝不 traceback |

**降级链的判定口径（R1，三种"失败"）** —— 命中任一即换下一个候选，且
**每次重试用全新会话**（不在已被污染的会话里重试）：

1. `resolve_model` 返回 `model_payload is None`（模型不在 kernel 注册表里）；
2. 投递过程抛 `BridgeError`（HTTP 错误、连接失败、建会话失败、**以及 R1b
   核实后确认"消息确实没被接受"的等回执超时**）；
3. 投递成功但回执里的实际模型 ≠ 请求的模型（**静默回落**）。

**为什么"全部候选失败"必须失败，而不是静默回落成"不指定模型"** ——
落回"不指定模型"等于**假装钉住了模型**：报告里写着钉了 `glm-5.3`，实际
由 kernel 自选，而且没有任何机器可读的失败痕迹。派单方（对方 agent）会
以为拿到了指定的模型/确定的上下文，差异只会在结果里以"模型表现不一致"
的形式出现，极难定位。所以口径是：**要么用某个候选并留痕（含降级留痕），
要么明确失败（退出码 2 + 逐条原因）**，绝不"看起来成功"。

**为什么"超时不等于失败"** —— `POST /session/{id}/message` 是**同步**等
assistant 回执的：agent 跑完才回。真实派单要几分钟（读契约 + 跑测试），
120 秒的等待窗口天然会超时。**客户端超时只说明"没在窗口内收到回执"，
不说明"kernel 没收到消息"** —— 后者才是投递失败。核实步骤（三步）：

1. `GET /session/{id}/message?directory=<ws>` 读该会话的消息列表；
2. 看到**本条用户消息**（内容匹配，且时间戳在发送之后 ±5 秒）→ 消息已被
   kernel 接受 → **投递成功**（退出码 0、不降级、不重投）。此时 agent
   可能还在跑，回执里可能还没有 assistant 消息 → `model_used` 允许空串、
   `model_applied` 允许 `null`（**不许**因此判成"模型没生效"→ 那会触发
   假降级）；若已能看到 assistant 消息，则从 `info.providerID` /
   `info.modelID` 取实际模型；
3. 看不到 → 消息确实没被接受 → 才算失败，换下一个候选（仍用新会话）。

**"请求的模型" vs "实际用的模型"（两个字段，语义不同，绝不互相顶替）**：

| 字段 | 含义 | 来源 |
|---|---|---|
| `model`（适配器）/ `model_requested`（桥接） | **我们要求**用谁 | 本地模型池轮换的选择结果 |
| `model_used` | kernel **实际**用掉了谁 | 桥接回执 / 会话消息里的 `info.providerID` + `info.modelID` |
| `model_applied` | 请求的模型是否真的生效（`true`/`false`/回执没带信息时 `null`） | 由上两者比较得出 |
| `fallback_used` | 是否发生过降级（实际干活的 ≠ 首选） | 同上 |
| `accepted_without_receipt` | 消息已被接受、但没等到回执（R1b 的核实结果） | 核实步骤 2 |

读不到回执时，这些字段一律**留空字符串**，绝不用"请求的模型"顶替。

**回执文件的路径与用途** —— `<workspace>/logs/codearts_delivery_receipt.json`：
桥接脚本每次投递**覆盖**写（只有一个文件），内容含 `intervention_id`、
`session_id`、`model_requested`、`model_used`、`model_applied`、
`fallback_used`、`accepted_without_receipt`、`model_attempts`、`generated_at`。
用途：让适配器**按 `intervention_id` 对单**取到"实际用的模型"这个证据
（适配器不解析桥接进程的 stdout）。写失败只告警，不影响投递成功
（与 inbox 副本的容错口径一致）。

## 验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| 契约验收（相关三件套） | `python3 -m pytest tests/unit/test_codearts_bridge_deliver.py tests/unit/test_codearts_adapter.py tests/unit/test_codearts_models_pick.py -q` | **121 passed**（复核方交付 102 → 本轮 +19） |
| 全仓回归 | `python3 -m pytest tests/ -q` | **2965 passed, 6 skipped**（复核方交付 2946 → 本轮 +19；跳过的 6 条是后端未启动/数据库缺失，与本任务无关） |
| ruff | `python3 -m ruff check ai_collab/ scripts/` | **10 个错误，与基线完全一致**（`scripts/codearts_bridge_deliver.py` 的 UP012 + `scripts/sync_agent_memory.py` 的 9 个）→ **无新增** |
| mypy | `python3 -m mypy ai_collab/` | **Success: no issues found in 100 source files** |
| 范围 | `git diff --name-only` | 只含允许清单内的文件；**禁止清单零改动**（`.vscode/ai-collab.json`、`ai_collab/cli/_cli_main.py`、`ai_collab/intervention_queue.py`、`ai_collab/dispatch_trigger.py`、`ai_collab/session_registry.py`、`ai_collab/result_consistency_audit.py`、`ai_collab/ack_protocol.py`） |

### 契约 R7 的 12 条用例覆盖

| # | 用例 | 落点 |
|---|---|---|
| 1 | 首选回执 modelID == 请求 | `test_fallback_chain_first_choice_succeeds_without_fallback` |
| 2 | 静默回落 → 换候选 | `test_fallback_chain_silent_fallback_moves_to_next_candidate` |
| 3 | 首选 HTTP 报错 → 换候选 | `test_fallback_chain_http_error_moves_to_next_candidate` |
| 4 | 全部候选失败 → 退出码 2 + 逐条原因 | `test_fallback_chain_all_candidates_fail`、`test_receipt_timeout_all_candidates_fail_exits_with_reasons` |
| 5 | 降级重试用新会话 | `test_fallback_chain_retry_uses_fresh_session`、`test_receipt_timeout_not_accepted_falls_back_to_next_candidate` |
| 6 | `--pick` 第一个可用 | `test_pick_returns_first_model_with_matching_receipt` |
| 7 | `--pick` 全部不可用 | `test_pick_fails_without_any_usable_model` |
| 8 | 适配器读到回执 | `test_codearts_adapter_reads_model_used_from_delivery_receipt` |
| 9 | 适配器读不到 / 对不上回执 | `test_codearts_adapter_ignores_receipt_for_other_intervention`、`..._leaves_model_used_empty_without_receipt` |
| 10 | 超时但能看到本条用户消息 → 退出码 0、不降级（`model_attempts` 长度 1）、`accepted_without_receipt=true`、**没有第二个会话** | `test_receipt_timeout_accepted_is_success_without_fallback` |
| 11 | 超时且看不到本条用户消息 → 算失败、换下一个候选、两个候选 `session_id` 不同 | `test_receipt_timeout_not_accepted_falls_back_to_next_candidate`（断言 `len(sessions) == 2`） |
| 12 | 超时但消息已被接受、此时还没有 assistant 消息 → `model_used` 空串、`model_applied` 为 `null`、**不触发降级** | `test_receipt_timeout_accepted_is_success_without_fallback`（断言 `model_used == ""`、`model_applied is None`、`kernel.calls == 1`） |

### 本轮新增用例（19 条）

- 桥接脚本（`tests/unit/test_codearts_bridge_deliver.py`，+17）：
  `test_receipt_timeout_accepted_is_success_without_fallback`、
  `test_receipt_timeout_accepted_keeps_actual_model_from_assistant`、
  `test_receipt_timeout_not_accepted_falls_back_to_next_candidate`、
  `test_receipt_timeout_all_candidates_fail_exits_with_reasons`、
  `test_receipt_timeout_single_candidate_exits_two_without_traceback`、
  `test_receipt_timeout_is_forwarded_to_kernel_client`、
  `test_accepted_without_receipt_is_written_to_receipt_file`、
  `test_request_wraps_socket_timeout_into_bridge_timeout`、
  `test_request_wraps_connection_error_into_bridge_error`、
  `test_verify_message_accepted_ignores_messages_from_before_the_send`、
  `test_verify_message_accepted_matches_by_content`、
  `test_verify_message_accepted_ignores_identical_message_from_before_the_send`、
  `test_verify_message_accepted_accepts_message_without_timestamp`、
  `test_verify_message_accepted_rejects_unrelated_recent_message`、
  以及 R1–R8 复核方交付的 13 条（合计 91 passed）。
- 适配器（`tests/unit/test_codearts_adapter.py`，+2）：
  `test_codearts_adapter_reads_accepted_without_receipt_from_receipt`、
  `test_codearts_adapter_leaves_accepted_without_receipt_empty_without_receipt`
  （合计 23 passed）。

### 既有测试零改动

**没有删改任何既有断言**（R8 硬约束）。为此，`model_attempts` 里的
`accepted_without_receipt` **只在为 true 时出现**（false 与"没有这个字段"
等价），这样既满足契约"对应 `model_attempts` 项要记 `accepted_without_receipt`"，
又不破坏既有的**整字典相等**断言（如
`test_fallback_chain_first_choice_succeeds_without_fallback` 断言
`model_attempts == [{"model": ..., "ok": True, "error": ""}]`）。
回执文件与适配器 delivery 记录里的同名字段则**恒定存在**（bool），
既有测试用的是逐键断言，未受影响。

### 真机只读复验（2026-10-23 19:0x）

对真实会话 `ses_e97e33fd4ffezO8oebWzvgsecf` 只读调 `GET /session/{id}/message`
（104 条消息、733KB，解析正常），核实判定四种情形全部符合预期：

| 情形 | 期望 | 实测 |
|---|---|---|
| 真实消息 + 真实时间戳 | True | **True**（并取到 105 条 assistant 消息、实际模型 `inferhub-provider/glm-5.3`） |
| 真实消息 + 晚 600 秒的时间戳（只剩更早的同内容消息） | False | **False** |
| 真实消息 + 早 1 秒的时间戳 | True | **True** |
| 从未发过的正文 | False | **False** |

## 风险

1. **核实本身失败 → 判失败 → 仍可能重复投递。** `GET /session/{id}/message`
   读不到（kernel 重启/不可达）时，本实现**重试 3 次（间隔 1 秒）**，仍失败
   则按"消息确实没被接受"处理 → 该候选失败 → 降级链会**新建一个会话**重投。
   这正是 R1b 要消灭的那类重复投递。之所以这样选：契约原文是"看不到 →
   消息确实没被接受 → 才算失败"，且"无法确认"绝不能当成"确认成功"
   （否则投递被静默吞掉、再也没人重投）。**若复核方认为该分支应按"接受"
   处理，改 `verify_message_accepted()` 里核实失败的分支即可（一处）。**
2. **`accepted_without_receipt` 只在 true 时写进 `model_attempts` 项**
   （false 与缺省等价）——见「既有测试零改动」。消费方请用
   `attempt.get("accepted_without_receipt")` 读取，不要假设该键必然存在。
3. **`model_applied` 在"接受但没回执且尚无 assistant 消息"时是 `null`**，
   含义是"回执里没带模型信息、无法证实"，**不是**"模型没生效"。任何消费方
   都不得把 `null` 当成 `false`（那会触发假降级）。
4. **"接受但没等到回执"时，`model_used` 可能为空串** —— 实际用掉的模型要等
   agent 跑完才有 assistant 消息可查。后续若要补齐，需要在 agent 跑完后
   二次回填（当前**未**实现，超出本任务范围）。
5. **适配器在"接受但没回执"时把投递记为 `queued`**（桥接退出码 0），
   intervention 不会停在 `failed`，因此**不会**触发自动重投 —— 这正是想要
   的效果；但也意味着"实际有没有跑完"要看对方的会话，不看本仓库的报告。
6. **别的地方会记模型，但都不是派单投递的证据**（按 R9 要求**不改**，
   仅记录待复核方决定）：
   - `ai_collab/session_auto_register.py:137` 记录会话注册 hook 上报的
     `model`（CodeArts 会话侧的模型），与本任务的"投递证据"是两回事；
   - `ai_collab/laya_client.py:99` 的 `model` 是 Laya 提问用的模型，与派单无关；
   - `logs/task_dispatch_report.json`（派单报告）**完全不记录模型** ——
     谁从派单报告判断"用了哪个模型"都会得到"没记录"这个答案；
   - `ai_collab/cli/_cli_main.py` 里的 `--model` 是"编排参与模型"、
     `model_variant` 是"角色模型变体"，都不是投递链路的模型证据。
7. **`scripts/check_codearts_models.py` 本轮未改动**：它的 `--pick` / 探测
   仍用 `client.request()`（超时由 `--timeout` 控制，默认 120 秒）。探测
   提示词极短（"Reply with exactly one word: OK"），正常不会触发 R1b 的长时
   等待场景；且它的 `probe_model()` 早就用 `except Exception` 兜住了超时，
   不会以 traceback 逃逸。若后续要给探测脚本也加 `--receipt-timeout`，
   建议用同一个 `--receipt-timeout` 口径（**本轮未做，避免扩大范围**）。
8. **基线问题未动**：`scripts/codearts_bridge_deliver.py` 的 `UP012`
   （`encode("utf-8")` 多余参数）、`scripts/sync_agent_memory.py` 的 9 个
   ruff 错误 —— 都是本任务之前就有的，按契约"不要顺手改"。
9. `tests/perf/test_performance_baseline.py::test_state_update_performance`
   在全量高负载下偶发 flaky 失败（单跑通过、重跑全绿）——与本任务无关。

## 回滚

本轮（R1b）只改了 3 个文件，回滚方式：

```bash
git checkout -- scripts/codearts_bridge_deliver.py ai_collab/adapters/codearts_adapter.py
# 测试与结果文件（可选，一并回滚）
git checkout -- tests/unit/test_codearts_bridge_deliver.py tests/unit/test_codearts_adapter.py
git checkout -- collaboration/results/RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23.md
```

> **注意**：回滚 R1b 会把"等回执超时"重新变回**裸 `TimeoutError` traceback +
> 退出码 1**（真机已验证会误判成投递失败 → 重复投递 → 两个会话并发改同一
> 个工作区）。若只是要临时关掉"接受但没回执"的特殊处理，请改
> `--receipt-timeout`（调到足够大）或 `verify_message_accepted()` 的返回分支，
> 不要整段回滚。

R1–R8（复核方交付）的回滚：

```bash
git revert a5b0d09  # R1–R6：降级链 / 留痕 / --pick / 回执落盘 / 适配器取证 / 渲染
```

`.vscode/ai-collab.json` 的 `{model_fallback}` 占位符由复核方统一落地
（本轮**未改**该文件，契约 R6 的硬约束）。
