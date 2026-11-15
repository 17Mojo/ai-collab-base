# Change Proposal: Migrate Session Identity

## Why

`PROTOCOL §12` 早在治理阶段就把「硬编码特定 Agent 提供商名称」列为废弃，但**规则与代码至今互相
矛盾**，而且是往坏的方向矛盾：

1. **契约要求的是厂商名，不是身份。**
   `§7.3` 要求每个工单声明 `assignee_provider`（实际提供商）。可 26 个现存工单里写的是
   `claude_code` / `codearts_agent` / `codex` 这类**厂商标签**——它回答「哪家的 Agent」，
   不回答「哪个会话、哪个模型」。多会话多模型并行时，同一个 `claude_code` 可能同时对应
   3 个会话，工单上的这个字段因此**无法定位到执行主体**。上一轮 `PROTOCOL` 已被指出这一点，
   但规则文本没改，工单仍按旧口径填。

2. **代码把废弃口径固化成了白名单。**
   `ai_collab/ack_protocol.py:9` 的 `SUPPORTED_ASSIGNEES = {"claude_code", "codearts_agent", "codex"}`
   被 9 个模块引用（ack / 干预队列 / 缺失 ACK 监控 / 看门狗 / 会话健康 / 自动注册 / hooks / CLI）。
   也就是说：§12 宣布废弃的东西，在代码里是**强校验**。新接入任何执行主体都要先改这个常量，
   与「不可动态调整的角色分工规则应废弃」直接冲突。

3. **迁移会失败，因为没人能证明「当时是谁」。**
   直接给 26 个历史工单补 `session_id` 就是编造事实——那些会话早已结束，注册表里没有记录。
   而「把没做的补齐」正是本项目反复拒绝的那类假绿。

结论：不是补几个字段，而是要把**身份**和**路由**拆开，并给历史工单一条不造假的处理路径。

## What Changes

### 规则层（这是本 change 的主要交付物）

| 位置 | 改动 |
|------|------|
| `PROTOCOL §7.3` | 绑定规则改为 `change_id` + `assignee_role` + **`session_id` + `model_id`**；`assignee_provider` 降级为「过渡期路由键」，仅历史工单沿用 |
| `PROTOCOL` 新增 §7.5 | 新增原则「身份与路由分离」：身份回答「谁在哪个模型上做的」，路由回答「消息发给谁」；同一身份可换路由，同一路由可承载多身份 |
| `PROTOCOL §12` | 把 `SUPPORTED_ASSIGNEES` 明确为**过渡兼容白名单**，并写出淘汰条件（不是「以后再说」，而是可判定的完成条件） |
| `AI-COLLABORATION-STANDARDS §2.1` | 开工检查清单加入「确认工单身份字段（session_id / model_id）」，与 `2X` 激活词并列 |

### 契约层

| 产物 | 内容 |
|------|------|
| `ai_collab/identity.py` | 身份规范化（`session_id` / `model_id` 格式）、`resolve_identity()` 三态判定（declared / legacy / missing）、按会话注册表反查 assignee 的桥接 |
| 契约字段 | `session_id` / `model_id` 进入工单契约；**时间切点**之后的工单缺失即 `invalid`，切点之前的判定为 `legacy` 并计数，不判错 |
| `tasks register/update` | 新增 `--session-id` / `--model-id`；只给 `session_id` 时，可从会话注册表反查 `assignee` 完成路由字段，避免「身份有了但路由断了」 |
| `tasks migrate-identity` | 迁移审计：逐条报告「有身份 / 可反查 / 不可反查（历史）」。**不编造**：反查不到的保持 legacy，只统计不填充 |

## Non-goals（明确划界，避免假完成）

- **不改运行时路由。** ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康这 5 个模块仍按
  `assignee` 过滤。理由：改成按 `session_id` 路由，需要 `assignee → session_id → transport`
  的完整映射与投递侧改造，牵动桥接脚本，属独立风险面。本 change 只做到「身份可声明、可核验、
  可反查路由」，并把淘汰条件写进 §12。
- **不给历史工单补身份。** 编造 `session_id` 比缺字段更坏。
- **不动 `provider_registry` 的配置结构**（角色编排仍按 provider 绑定角色，属路由层）。
- 不改 `quickfix/no-ticket` 轻量通道（已在 `TASK_CONTRACT_SPECIAL_CHANGE_IDS` 内，行为不变）。

## Impact

- 新增工单缺 `session_id` / `model_id` 会被严格校验判错（时间切点之后）。
- 历史工单不会被判错，但会在 `validate-contract` 输出里以 `legacy_identity=N` 显式计数，
  不再沉默。
- `PROTOCOL §7.3` 的表述变化会让引用旧条款的文档需要更新（`§7.4` 的勘误段已指向本节，
  本次一并校正交叉引用）。
- 规则文本改动需要与代码**同 commit** 落盘，否则出现「规则说要求、代码不校验」的第四类假绿。
