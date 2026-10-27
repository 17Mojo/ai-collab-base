---
task_id: TASK-P1-DISPATCH-MODEL-FALLBACK-001
# 2026-10-27 修正：原值 `feature/no-spec` 不在 `TASK_CONTRACT_SPECIAL_CHANGE_IDS`
# 白名单内（`/` 也不符合 OpenSpec change id 的命名规则），会被契约校验判 invalid。
# 结果文件 §0「门禁修正留痕」已记录当时用 CLI 改成了 `bugfix/no-spec`，
# 但**工单文件本身**没跟着改——校验脚本按文件读，于是把非法值又推回了状态库。
change_id: bugfix/no-spec
status: planning
priority: P1
assignee: codearts_agent
assignee_role: AGENT_EXEC
reviewer: claude_code
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-23T18:10:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_codearts_bridge_deliver.py tests/unit/test_codearts_adapter.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/ scripts/"
result_file: collaboration/results/RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23.md
---

# TASK-P1-DISPATCH-MODEL-FALLBACK-001：派单链路的模型降级与可观测性

> **本工单由 Claude Code（AGENT_ARCH）定义契约，CodeArts（AGENT_EXEC）实现。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
> 复核方：Claude Code（AGENT_TEST）。
>
> **上一轮（Claude Code 侧）已经落地的部分，视为既有基线，不要重做：**
> 桥接脚本已有 `--model` 与 `--channel new_session`（自建会话 + 消息体带
> `model`），回执 `info.providerID`/`info.modelID` 已能取证**实际**用掉的模型，
> 输出里已有 `model_requested` / `model_used` / `model_applied`；
> 适配器已能从 `.vscode/ai-collab.json` 的 `models` / `modelPolicy` 读模型池
> 并按"钉了模型的投递次数"轮换，把 `{model}` / `{channel}` 渲染进
> `bridgeCommand`（commit `a0b6a01`）。

## 一、背景与真证

### 真证 1：模型钉死已经生效，但**没有任何降级能力**

Claude Code 侧已把「派单消息体带 model」接通（commit `a0b6a01`），
本轮派单（round 4）就是第一次**真机**使用它。但当前实现有两个**真实**的
失效面：

1. **指定模型不可用 = 派单直接失败。** 桥接脚本把模型写进消息体后，
   上游若额度耗尽 / key 失效 / 模型下线，HTTP 会报错或回执带 error。
   此时 `deliver_via_new_session` 抛 `BridgeError` → 脚本退出码 2 →
   适配器把这次投递标成 `failed` → intervention 停在 `failed`（可重试，
   不是终态）→ **任务无限期停滞**，CodeArts 那一轮白等。
2. **静默回落没人知道。** 如果上游不报错、只是换了模型（回执里的
   `info.modelID` ≠ 请求的模型），当前 `model_applied` 会是 `False`，
   但**适配器报告里记的还是"请求的模型"** —— 报告看起来是钉住了 glm-5.3，
   实际干活的是别的模型。**报告不能作为证据。**

### 真证 2：适配器记的是"请求的模型"，不是"实际用的模型"

适配器的 delivery 记录里 `model` 字段来自**本地选择**（还没投递呢），
与 kernel 回执无关。桥接脚本的 stdout 里虽然有 `model_used`，但适配器
**不解析 stdout**，所以这个证据目前被丢掉了。

### 真证 4：**超时会被误判成"投递失败"，而消息其实已被 kernel 接受**

round 4 真机派单（2026-10-23 17:36）实测到的**假失败**：

- 桥接脚本 `POST /session/{id}/message` 等待回执，**120 秒**超时（`--timeout`
  默认值）→ 抛 `TimeoutError` → 脚本退出码非 0 → 适配器把这次投递记成
  `failed`，intervention 停在 `failed`。
- 但 kernel 侧**完全正常**：会话 `ses_e97e33fd4ffezO8oebWzvgsecf` 已建立，
  用户消息已落库，**24 条 assistant 消息全部是 `inferhub-provider/glm-5.3`**，
  对方一直在正常干活。
- 也就是说：**客户端"超时"≠"投递失败"**。真实派单要几分钟（读契约、跑测试），
  120 秒的等待窗口天然会超时。
- 危险不在这一次误报，而在**它会引发重复投递**：`failed` 是可重试状态，
  下一轮适配器会再投一次 → 在对方那边**再建一个会话** → 两个会话并发改
  同一个工作区。这正是 2026-10-22 22:01 那次事故的成因。
- 降级链如果把"超时"直接判为失败并换下一个候选，会**再开一个会话**，
  同样踩这个坑。

### 真证 3：模型可用性探测脚本已经存在，但只能"全测"不能"选一个"

`scripts/check_codearts_models.py`（Claude Code 侧，commit `2d921d6`）
能对每个候选做**一次真实推理**并用回执 `info.modelID` 取证（防静默回落），
但没有"按候选顺序挑第一个真能用的"这个能力。

## 二、目标

1. **钉死的模型不可用时自动降级**，派单不中断（降级链的下一个候选顶上）；
2. **降级必须留痕**：报告/摘要里能一眼看出「请求的模型 / 实际用的模型 /
   是否降级 / 每个候选的成败」；
3. 全程**不许静默**：请求 A 实际 B、候选全挂、降级发生，都必须落到
   机器可读字段与报告里；
4. **假失败不得造成重复投递**：等回执超时 ≠ 投递失败（真证 4）—— 消息已被
   kernel 接受时必须按成功处理，不许降级、不许重投（否则两个会话并发改
   同一个工作区）。

## 三、详细契约（逐条实现，不要自行发挥）

### R1 桥接脚本：模型降级链

新增 `--model-fallback`（逗号分隔的候选模型列表，形如
`glm-5.3,deepseek-v4.1-flash,kimi-k3`）。

语义（**逐条照做**）：

- 候选序列 = `[--model 的值]` + `--model-fallback` 列表里**尚未尝试过**的项，
  按给定顺序（去重、保持原序）。
- 依次尝试：对每个候选，走**既有**的 `resolve_model` → `new_session` 通道
  （自建会话 + 消息体带 model）。
- 某个候选"失败"的判定（三者任一）：
  1. `resolve_model` 返回 `model_payload is None`（模型不在 kernel 注册表里）；
  2. 投递过程抛 `BridgeError`（HTTP 错误、连接失败、创建会话失败等）
     —— **注意区分"消息还没被接受"和"已接受但回执没等到"，见 R1b**；
  3. 投递成功但回执里的实际模型 **≠** 请求的模型（静默回落）。
- 判定为"失败"时，**换下一个候选**，并且**用新会话**（不要在已经发过消息的
  会话里重试 —— 那个会话已经被污染了）。
- 全部候选都失败 → **明确失败**：退出码 2，stderr 列出每个候选的失败原因。
  **不许**在没有模型可用时静默降级成"不指定模型"（那等于假装钉住了）。
- 只有一个候选（没给 `--model-fallback`）时，行为与现在**完全一致**：
  失败就是失败（退出码 2），不做任何自动降级。

### R1b 桥接脚本：**超时 ≠ 投递失败**（真证 4 的直接对策）

这是本轮**最容易做错**的一条，务必照做：

- **等待回执超时**（`TimeoutError` / `socket.timeout` / 连接被重置，且发生在
  `POST /session/{id}/message` **已发出**之后）**不得**直接判为"投递失败"。
  真证 4：这种超时下消息**已被 kernel 接受并正在执行**，判失败会造成重复投递
  → 在对方那边再建一个会话 → 两个会话并发改同一个工作区（2026-10-22 事故复现）。
- 超时后的**核实步骤**（必须做）：
  1. `GET /session/{id}/message?directory=<ws>` 读该会话的消息列表；
  2. 若能看到**本条用户消息**（或其后已有 assistant 消息）→ **消息已被接受**：
     - 视为**投递成功**（退出码 0），不降级、不重投；
     - `model_used` 取回执里的实际模型；此时 agent 可能还在跑，回执里可能还
       没有 assistant 消息 → `model_used` 允许为空串、`model_applied` 允许为
       `null`（**不许**因此判成"模型没生效"→ 那会触发假降级）；
     - 在 `model_attempts` 里记一条 `ok=true`、`error=""`，并额外记
       `accepted_without_receipt=true`（新增字段，说明"接受但没等到回执"）。
  3. 若**看不到**本条用户消息 → 消息确实没被接受 → 才算"失败"，换下一个候选。
- 等待回执的超时窗口要**单独可配**（新增 `--receipt-timeout`，默认建议
  **600 秒**；`--timeout` 继续管"建会话/解析模型"这类短请求）。
  120 秒对真实派单（读契约 + 跑测试）**必然**超时。
- 同样口径适用于**投递前**的失败（建会话失败、`resolve_model` 失败）：
  那些发生在消息发出之前，不涉及"已被接受"的歧义，按普通失败处理。

### R2 桥接脚本：降级留痕字段

投递结果（`--json` 的输出、以及 `write_inbox_copy` 落的那份 payload）里必须有：

| 字段 | 含义 |
|---|---|
| `model_requested` | 首选模型（`provider/model`）—— 已有，语义不变 |
| `model_used` | kernel 回执里**实际**用掉的模型 —— 已有，语义不变 |
| `model_applied` | 请求的模型是否真的生效（`true`/`false`/回执没带信息时 `null`）—— 已有，语义不变 |
| `fallback_used` | **新增**：`true` = 发生过降级（不是首选模型干的活） |
| `model_attempts` | **新增**：列表，每项 `{"model": "provider/model", "ok": true/false, "error": "失败原因"}`，按尝试顺序 |
| `accepted_without_receipt` | **新增**：`true` = 消息已被 kernel 接受，但没等到回执（R1b 的超时核实结果） |

`model_attempts` 里的 `error` 为空串表示该候选成功。

### R3 `scripts/check_codearts_models.py`：新增 `--pick`

- `--pick` 与 `--models` 一起用：按 `--models` 的顺序逐个**真实探测**
  （复用现有的 `probe_model`，它已经用回执 `info.modelID` 取证），
  返回**第一个"实际模型 == 请求模型"**的候选。
- 输出（`--json` 时放进 JSON 字段 `picked`）：`providerID/modelID`。
- 一个都不可用时：**退出码 1**，且**不输出**任何模型 id（不许回落到
  kernel 默认模型来充数）。
- `--pick` 与 `--watch` 互斥（同时给 → 退出码 2，报错说明）。

### R4 桥接脚本：落投递回执文件

投递成功后，把本次投递的关键信息写成 JSON 文件：

```
<workspace>/logs/codearts_delivery_receipt.json
```

内容至少包含：`intervention_id`、`session_id`、`model_requested`、`model_used`、
`model_applied`、`fallback_used`、`model_attempts`、`generated_at`。

- 每次投递**覆盖**写（只有一个文件）。
- `intervention_id` 用来让调用方把回执对到具体哪一单。
- 写文件失败**只告警不影响投递成功**（与现有 inbox 副本的容错口径一致）。

### R5 适配器：把"实际用的模型"写进报告

`ai_collab/adapters/codearts_adapter.py`：

- 投递成功（returncode == 0）后，读 `<workspace>/logs/codearts_delivery_receipt.json`，
  **按 `intervention_id` 匹配**（对不上就当没有回执）。
- 把 `model_used` / `model_applied` / `fallback_used` 写进该条 delivery 记录
  （字段名与 R2 一致），并写进报告与摘要。
- **对不上或读不到时，这些字段留空字符串** —— **绝对不许**拿"请求的模型"
  冒充"实际用的模型"。
- 现有的 `model` 字段（请求的模型）**保留**，语义不变：它是"我们要求用谁"。

### R6 适配器：把降级链渲染进 bridgeCommand

- `.vscode/ai-collab.json` 的 `bridgeCommand` 里会多一个 `{model_fallback}`
  占位符 —— **该文件由复核方在你交付复审通过后改，你不要动**。
  在你交付之前该占位符不存在，此时适配器渲染它是无害的 no-op
  （`command.format()` 对模板里没有的占位符直接忽略）。
- 适配器渲染时：`{model_fallback}` = 模型池里**除本单选中模型之外**的其余模型，
  按池内顺序用逗号连接（例：选中 `glm-5.3` → `deepseek-v4.1-flash,kimi-k3`）。
- `{model_fallback}` 为空时渲染成空串（模板里带引号，argparse 收到空值）。
- **不要**自己往 `.vscode/ai-collab.json` 里加占位符：在桥接脚本还不认
  `--model-fallback` 时，模板里出现该占位符会让**每一次派单都因 argparse
  报错而失败**。占位符与桥接支持必须同时生效，由复核方统一落地。

### R7 测试（新建或扩展）

必须覆盖（**用真进程或真实 HTTP 形状的桩，不要只测函数返回值**）：

| # | 用例 | 断言 |
|---|---|---|
| 1 | 首选模型回执 modelID 与请求一致 | 成功；`model_applied` 为 `true`；`fallback_used` 为 `false`；`model_attempts` 长度 1 |
| 2 | 首选模型回执 modelID **不同**（静默回落） | 自动换下一个候选；最终 `model_used` == 第二个候选；`fallback_used` 为 `true`；`model_attempts` 长度 2，第一项 `ok=false` |
| 3 | 首选模型 HTTP 报错 | 同上，换候选 |
| 4 | 全部候选失败 | 退出码 2；stderr 里能看到每个候选的失败原因；**没有**任何一次"不指定模型"的投递 |
| 5 | 降级重试必须用**新会话** | 两次尝试的 `session_id` 不同 |
| 6 | `--pick` 第一个可用 | 输出该候选；退出码 0 |
| 7 | `--pick` 全部不可用 | 退出码 1；输出里没有模型 id |
| 8 | 适配器读到回执 | delivery 记录里 `model_used` 是**回执里的**值，不是请求值 |
| 9 | 适配器读不到/对不上回执 | `model_used` 为空串（不许用请求值顶替） |
| 10 | 等待回执**超时**，但 `GET /session/{id}/message` 能看到本条用户消息 | 退出码 **0**；**不降级**（`model_attempts` 长度 1）；`accepted_without_receipt` 为 `true`；没有创建第二个会话 |
| 11 | 等待回执**超时**，且 `GET /session/{id}/message` **看不到**本条用户消息 | 算失败；换下一个候选；两个候选的 `session_id` 不同 |
| 12 | 超时但消息已被接受、此时回执里还没有 assistant 消息 | `model_used` 允许为空串、`model_applied` 为 `null`，**且不得**因此触发降级 |

### R8 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---|---|
| `scripts/codearts_bridge_deliver.py` | `.vscode/ai-collab.json`（**复核方改**，你只按 R6 渲染占位符） |
| `scripts/check_codearts_models.py` | `ai_collab/cli/_cli_main.py`（CLI 入口归复核方） |
| `ai_collab/adapters/codearts_adapter.py` | `ai_collab/intervention_queue.py`、`ai_collab/dispatch_trigger.py`、`ai_collab/session_registry.py` |
| `tests/unit/test_codearts_bridge_deliver.py` | 既有测试**一行都不许删改断言**；要改就逐条写进结果文件 |
| `tests/unit/test_codearts_adapter.py`（可新建 `tests/unit/test_codearts_models_pick.py`） | `ai_collab/result_consistency_audit.py`、`ai_collab/ack_protocol.py` |
| `collaboration/results/RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23.md` | 上一轮已交付的 `TASK-P1-CLI-EXITCODE-001` 相关文件 |

**既有测试零改动**：既有测试文件**不许删改断言**。若某条既有用例因新语义
必须修改：**逐条在结果文件里说明改了什么、为什么**。

### R9 文档与口径

- 结果文件**头部**必须有一行可机读的状态（**前 40 行内**）：

  ```markdown
  - **状态**: completed
  ```

- 结果文件必须写清：
  - 降级链的判定口径（三种"失败"）；
  - **超时为什么不等于失败**（R1b），以及核实步骤；
  - 为什么"全部候选失败"要**失败**而不是静默回落；
  - 回执文件的路径与用途；
  - 适配器里"请求的模型"与"实际用的模型"两个字段的区别；
  - **回滚**方式（`git checkout --` 三个文件即可）；
  - 若你发现还有别的地方会记错模型（例如 CLI 输出），**不要改** —— 写进结果文件
    「风险」段，由复核方决定。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_codearts_bridge_deliver.py tests/unit/test_codearts_adapter.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check ai_collab/ scripts/` 无**新增**问题
      （注意：`scripts/codearts_bridge_deliver.py:531` 有一条**基线**已有的
      `UP012`，不算你的问题，也**不要顺手改**它）
- [ ] `git diff --name-only` **不含** R8 禁止清单里的任何文件
- [ ] 结果文件含「执行命令 / 验证结果 / 风险 / 回滚」四段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] 结果文件头部的 `- **状态**: completed` 在**前 40 行内**

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**（手写 ACK 会被回执桥接判为「非显式 ACK」而拒绝收口）：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-DISPATCH-MODEL-FALLBACK-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23.md
```

把该命令**原样输出**的一行回复回来（形如
`A.ACK|task=TASK-P1-DISPATCH-MODEL-FALLBACK-001|status=ok|result=collaboration/results/RESULT-P1-DISPATCH-MODEL-FALLBACK-2026-10-23.md`）。

## 六、参考

- 本轮基线（Claude Code 侧已落地）：`scripts/codearts_bridge_deliver.py`
  （`--model` / `--channel new_session` / `model_used` 取证）、
  `ai_collab/adapters/codearts_adapter.py`（模型池轮换）、
  `.vscode/ai-collab.json`（`models` / `modelPolicy`）
- 模型可用性探测：`scripts/check_codearts_models.py`
- 上一轮契约与交付：`collaboration/tasks/TASK-P1-CLI-EXITCODE-001.md`、
  `collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
