# Design: Restore Governance Enforcement

本文件只记录**取舍**与**立项前深调结论**。动机见 `proposal.md`，可观测行为见
`specs/governance-coverage/spec.md`，动作分解见 `tasks.md`。

## D1 · 覆盖率事实源：显式登记表，而不是推断提交与工单的关联

**选 A：append-only 登记表 + 声明命令。** 每个合并提交由执行主体在合并前显式声明
`change_id` 或豁免标签、理由、时间、主体；门禁只做「边界之后的提交集合」与「登记集合」
的差集。

**不选 B：从提交信息、分支名、文件路径推断 commit↔task 关联。**
理由：本仓 11 月 51 个合并提交的正文里 `openspec|change_id|bugfix/no-spec` 命中为 0，
说明提交信息里根本没有可靠关联字段；分支名也只能表达类别不能表达归属。推断规则一旦
有例外，就会出现「推断不出 ⇒ 当作已覆盖」的静默兜底——那正是本次要修的假绿。

**备选 C：给每个 PR 强制补建一份工单。** 否决：这是把覆盖率问题转写成文档补作业，
成本高、且仍需有人记得建；不建时门禁依旧看不见。

**代价**：A 引入一条每次合并都要执行的声明动作。缓解方式是把它并进
`governance preflight` 的开工检查与收口检查，而不是让人单独记。

## D2 · 生效边界必须与启用改动同属一个提交

`enforced_from_commit` 若由后续某次提交单独写入，会出现两个问题：门禁在边界落定前
窗口期反复翻红/翻绿（flapping）；以及边界可被事后改写以洗掉某段历史。因此边界声明与
启用覆盖率判定的代码必须原子落在同一个合并提交里，并对声明里的 sha 做 git 真值校验。

**不选**：用「最近 N 天」作为滑动边界。理由：那是观测，不是保证，有保质期；
且每次运行边界都变，脚本不幂等。

**不选**：从当前状态文件的 `last_updated` 反推边界。理由：该字段是写入时刻，不是
提交时刻，两者不同口径会造成「冻结说没事、门说过期」。

## D3 · 新信号先接通、决策先冻结

覆盖率与输入完整性都是**放行决策信号**，一旦上线就同时对全部后续工作生效，错了往往
不报错、只是安静地继续假绿或误挡。因此分两步：

- 观测期：新增信号只计算、打印、落盘「假想判定」，既有结论逐位不变；
  总闸用**模块级常量**，不用 CLI 旋钮（旋钮会被误传误用，这是发布阶段闸门而非运行时配置）。
- 翻闸：常量切换后按新判定执行，验收用「注入未登记提交 → 非零且点名 / 登记后通过 /
  边界前不引红」三场景。

**翻闸依据的修正（重要）**：仓库既有方法论原本把翻闸依据写为「人工目检新旧决策差异」，
但用户已明确无目检样板能力。本设计改为**机器可判定的差异清单 + 反向测试**：
差异清单列出会引红的提交并核对是否全为预期；反向测试从输入中移除新字段后断言既有
结论逐位不变；跑前跑后同一命令输出做哈希比对。不口头发「应该没问题」。

**不选**：直接一次性上线。理由：无法证明零行为改变，且 11 月已经因为同类
「信号恒为空却无人发现」吃过亏。

## D4 · 不修改既有并发风险评级，改为新增开工门禁消费新信号

这是本设计最容易被做错的一处。直觉做法是在并发守护里，输入不全时直接把
`risk_level` 改成 `unknown`、`allowed` 改成 `false`。**否决**，两个理由：

1. 既有能力规格 `openspec/specs/concurrent-workspace-safety/spec.md` 明确写
   「未给出期望分支时 SHALL 跳过该检测且不产生任何违规」。改 `allowed` 等于修改既有
   requirement，需要 MODIFIED delta，且会让「未配置」与「检测到违规」两种语义混在一起。
2. 把「没装探头」报成「探测到危险」，本身又是一次结论词欺骗；正确表达是
   「本门禁未装备，不能给出放行结论」。

**选 A**：并发守护报告只新增 `input_contract_complete` 布尔字段（观测期不改任何既有
字段），由新的 `governance preflight` 在开工阶段判定「是否装备」并拒绝放行。
并发守护继续只回答并发风险，治理门禁回答门禁是否可用，**职责分离**。

**代价**：多一个 CLI 子命令和一条开工动作；收益是既有 spec 与 5442 行守护测试不被
语义改动波及。

## D5 · 立项前深调新增：账本写入必须先统一到互斥原子入口

**范围修正**：上一版恢复方案只有两项 P0。按用户要求在立项前深入调研工单系统后，
发现第三处必须先修的前置问题，因此纳入本 change。

磁盘证据：

- 正确的一侧：`ai_collab/state_manager.py:772` `_file_lock` 用
  `os.open(..., O_CREAT|O_EXCL|O_WRONLY)` 建锁文件提供跨进程互斥；
  `:847` `_commit_state_transaction` 在锁内**重读最新状态**再 mutate；
  `:649` `_atomic_write_json` 用 `mkstemp + fsync + os.replace` 原子落盘。
  这一套对多执行主体并发是安全的。
- 缺失的一侧：`ai_collab/ack_protocol.py:46` 与
  `scripts/agent_receipt_bridge.py:129` 的写入是裸 `path.write_text`；
  `record_ack_bridge`（`ack_protocol.py:334`）是 load → upsert → write 的
  read-modify-write，无锁；`scripts/agent_receipt_bridge.py:326–327` 更直接覆写
  `logs/collaboration_state.json` 与 `logs/agent_ack_bridge_state.json`，
  **绕过状态机的锁与状态合并**。

**风险**：多会话并发 ACK 会 lost update；直写会把状态回退到旧快照；
`write_text` 非原子，中断会留下半截 JSON 被门禁读取。

**选 A**：所有账本写入收口到统一入口，复用既有跨进程锁 + 原子替换，并加一致性校验
检测「绕过入口的直写路径」。**不选 B**：给每个写方各加一把自己的锁（锁不统一等于没锁）。
**不选 C**：靠「多会话错峰执行」的流程约定（那是观测，不是保证）。

**容量边界**：`_file_lock` 默认 5s 超时、120s stale。会话数增多会争用超时，属已知上限，
需在多会话试点中观测，不在本 change 里扩大阈值（改阈值等于放宽门禁，须另附实测）。

## D6 · 「会话代替 Agent 框架平台」可行性裁定（用户指定探讨项）

### D6.1 工单系统实际是三层，不是一整块

立项前深调把工单系统拆成三层，这是判定的基础：

| 层 | 事实源 / 实现 | 平台依赖 |
|---|---|---|
| **记录层** | `logs/collaboration_state.json`（20 字段任务对象）、`logs/agent_ack_bridge_state.json`、`logs/agent_receipt_state.json`、`logs/agent_dispatch_state.json`、`logs/session_intervention_state.json` | **无**：普通 JSON 文件 + 标准库，跨进程锁，原子替换 |
| **门禁层** | 契约校验、结果四段门禁、显式 ACK 判定、缺失 ACK 监控、ACK 看门狗、干预队列、状态漂移核对 | **基本无**：判定基于字段名、字符串、文件路径；ACK 证据只看账本里 `source` 是否以 `cli-ack`/`chat-ack` 开头，**从不校验是哪个模型发的** |
| **派发 / 传输层** | `adapters/codearts_adapter.py` 硬编码 `assignee="codearts_agent"`；`.vscode/ai-collab.json` 的 `bridgeCommand` → `scripts/codearts_bridge_deliver.py`（外部 kernel）；`session_inject.py` / `stop_check.py` / `pre_compact.py` 的宿主 hook 契约；`2X` 暗语 | **强绑定**：绑定具体平台会话与宿主 hook |

一个容易搞错的事实：`collaboration/tasks/*.md` **不是门禁的事实源**。
`scripts/verify_task_file_contracts.py:6-9` 自述「工单文件写好了不等于工单过了门禁」，
严格契约校验读的是 `logs/collaboration_state.json`；Markdown 只是源文件，靠该脚本单向
同步进状态库。所以「工单系统」的真实形态是**磁盘文件协议 + CLI**，不是某个平台服务。

另一个事实：`config/agent-orchestration.json` 里的 `roles[].binding.provider` 读出来后
**从未被用于决定谁执行**。`ai_collab/orchestration.py:596` 的 `get_role_for_provider()`
无生产调用点；该绑定只用于派生 ACK/RUN 前缀字母、新工单默认角色元数据、CLI 展示与
冷启动记录。真正决定执行对象的是工单的 `assignee` 字段、`.vscode/ai-collab.json` 的
`enabledAIs` / `activationKeyword`，以及那条硬编码到 CodeArts kernel 的投递通道。
⇒ **「代替 Agent 框架平台」的代价比直觉小：真正要重做的是投递通道，不是编排配置。**

### D6.2 一个必须写进来的矛盾：现状实现违反协议自己的废弃声明

`PROTOCOL §3.1` 原文：「系统使用**语义化角色代号**，不绑定具体 Agent 提供商」。
`PROTOCOL §12 废弃声明` 更把「硬编码特定 Agent 提供商名称的协议条款」与
「固定的 Claude Code + Codex + CodeArts 架构描述」列为**废弃**。

但实现里 `ai_collab/ack_protocol.py:9` 是
`SUPPORTED_ASSIGNEES = {"claude_code", "codearts_agent", "codex"}`，
且这张白名单被 `missing_ack_monitor.py:118`、`ack_watchdog.py:113`、
`intervention_queue.py:439`、`stop_check.py:86`、`external_closeout_queue.py:135`
等处用作闸门；`_ACK_PREFIX`、`TASK_CONTRACT_DEFAULT_ROLE_BY_ASSIGNEE`
（`state_manager.py:330`）、`stop_check.py:36` 的模型名映射、
`external_closeout_queue.py:18` 的常量，全是硬编码厂商名。

⇒ **用户提出的「用会话代替框架平台」，方向上不是标新立异，而是把实现拉回协议原意。**
这是本次探讨最重要的结论，也是后续立法 change 的立论依据。

### D6.3 两种解读，一个可行一个不可行

**解读 A（不可行）：用宿主原生的会话 / 任务列表完全替代 `ai_collab` 工单系统。**
理由：原生任务列表不落盘成 `collaboration/tasks/TASK_*.md` +
`logs/collaboration_state.json`，无法满足 `PROTOCOL §7.3` 绑定声明与 `§7.4` 四段结果契约，
也无法满足跨会话复测与磁盘真值对账；还会丢掉已有的 20 字段状态机、跨进程锁、ACK 账本、
receipt / 监控 / 干预队列。**放弃这个解读。**

**解读 B（可行，推荐）：多会话 + 多模型作为执行载体，工单系统仍用仓库文件协议。**
正确关系是「**上层编排用会话，下层落账用 CLI**」：

- 会话 = 执行主体，不同会话可选不同模型 / 专家；
- `AGENT_EXEC / AGENT_ARCH / AGENT_TEST` = 会话认领的**职责**，不再绑定厂商名；
- `assignee` = 会话标识（启动时注册），`assignee_provider` 语义迁移为
  `session_id + model_id`，仍满足可追溯；
- 工单、结果、日志、ACK 全部仍落盘到既有文件协议，门禁不变。

支持证据：记录层与门禁层天然平台无关；`CODEX_SPAWN_AGENT_USAGE_GUIDELINES.md`
「子代理不单独产出正式 ACK、正式闭环由主线程落账」的治理规则，
恰好天然适配「多个独立会话 + 每会话一个主线程负责跑 `cli ack`」。

### D6.4 会话化必须解决的四个断点（否则静默失效）

1. **`SUPPORTED_ASSIGNEES` 硬编码白名单**：新会话名会在监控 / 看门狗 / 干预队列 /
   Stop 门禁里被静默跳过，不派单、不生成 ACK、不落账本。
   ⇒ 改为 append-only 会话注册表 + 会话启动声明，白名单改为「是否已注册」查询。
2. **宿主 hook 绑定**：`session_inject` / `stop_check` / `pre_compact` 依赖特定宿主的
   hook 契约，换载体后不触发，激活、上下文注入、ACK 缺失门禁、压缩快照全失效。
   ⇒ 改为会话启动 / 收尾的显式 CLI 调用（`preflight`、`declare-commit`、`cli ack`、
   `sessions handoff`），不依赖 hook 注入。
3. **模型名 → 厂商名的身份推断失效**：`stop_check.py:95-129` 靠模型名猜 assignee，
   多会话使用同一模型时 `len(inferred) != 1` 返回空串，而
   `_task_belongs_to_agent`（`:132-135`）在空值时返回 True ⇒ 把**全部**任务算到当前
   会话头上，可能误拦。⇒ 废弃推断，改显式声明会话身份。
4. **`2X` 暗语**：绑在「在某会话输入 2X」的触发上，多会话下没有统一触发点。
   ⇒ 废弃，由会话启动即注册 + `preflight` 取代。

### D6.5 前置条件与依赖顺序

会话化**不是零成本切换**。硬前置依次是：

1. 本 change 的 P0-3（账本写入互斥与原子性）——不修就多会话并发写坏状态；
2. 本 change 的 P0-1 / P0-2（覆盖率与输入完整性）——不修就多会话照样能绕过门禁；
3. 会话注册表 + 显式身份声明（后续 change）；
4. 规则文本变更（`PROTOCOL §7.3` 的 `assignee_provider` 语义、`§8.1` 派发、
   `AI-COLLABORATION-STANDARDS §2.1` 的 `2X`），以及 `quickfix/no-ticket` 轻量通道立法；
5. 最后才停用 `codearts_adapter` + `bridgeCommand` 那条自动投递通道。

⇒ **本 change 明确不实施会话化改造**，只交付它依赖的机制；`design.md` 本节作为后续
change 的立论与依赖记录。这也避免了在阶段 0 规划轮里把范围膨胀到规则重写。

## D7 · `2X` 方向的裁定建议（不写入本 change 的规则文本）

用户未要求现在立法，只要求探讨。三选项评估：

- **A 强制全套工单**：每次会话首条指令即视为激活。**不推荐**——与「短指令直改」的
  实际工作方式冲突，11 月 51/51 绕过已证它跑不起来。
- **B 轻量通道合法化（推荐）**：新增 `quickfix/no-ticket` 白名单，最低义务 =
  登记表一行 + 结果摘要 + 开发日志；较大安全 / 架构 / 新能力改动仍强制走 OpenSpec。
  理由：治理断流根因是**流程成本与工作方式不匹配**，不是纪律问题；让合规覆盖全部工作
  而不是只覆盖走全套的那部分，覆盖率门禁才有意义。
- **C 仅 PR 模板加必填字段**：**不推荐**——不填照样能合并，仍是绕过。

本 change 只提供 B 所需的机器机制（登记表、开工检查），不修改规则文本、不新增标签语义。

## D8 · 已被实测推翻的假设（就地标注，保留证据位置）

| 旧假设 | 实测结论 | 证据 |
|---|---|---|
| 运行时项目配置读 `config/agent-orchestration.json` | 实际读 `.vscode/ai-collab.json`；前者是角色编排配置 | 归档 `add-concurrent-workspace-guard/design.md` D3；`integrations/vscode.py` |
| `roles[].binding.provider` 决定由谁执行 | 从未被派发代码读取用于决定执行；只影响前缀字母与工单元数据 | `orchestration.py:596` 无生产调用；派单目标来自工单 `assignee`（`scripts/agent_dispatch_bridge.py:75`） |
| 状态文件并发写入是安全的 | **部分推翻**：`state_manager` 有跨进程锁与原子写，但 ACK / receipt 账本裸写，且 receipt 直写状态文件绕过锁 | `state_manager.py:772,847,649` vs `ack_protocol.py:46,334`、`scripts/agent_receipt_bridge.py:129,326` |
| 「契约校验通过」等于合规 | 只覆盖已登记任务，未登记提交不可见 | `state_manager.py:1968–2018` 只遍历 `get_all_tasks()`；实跑 `checked=18 invalid=0` |
| 冷启动每轮都要跑 | 只在 `binding_status == "uninitialized"` 触发，当前 `active`，不跑不违规 | `PROTOCOL §4.1`；`config/agent-orchestration.json` |

## D9 · 回滚与幂等

- 观测期把模块级总闸翻回关闭即完全恢复旧行为；正式改动每个 PR 独立可 `git revert`。
- 登记表只追加，不删除、不改写生效边界声明（改边界等于篡改判定范围）。
- 自动生成的报告去掉 `generated_at` 等纯时间戳字段后再比对实质差异，避免
  「只有时间戳变化」的重复提交；脚本跑第二遍应无新提交、无新移动。
- 所有 `git add` / `git commit` 必须带 pathspec；主工作区另有 153 项在途改动，
  索引里他人的 WIP 不得被一起提交。
- 不做自动回滚；保留选择权给使用者。
