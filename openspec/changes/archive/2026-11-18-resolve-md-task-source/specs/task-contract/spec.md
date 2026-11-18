## ADDED Requirements

### Requirement: md 工单身份可同步进账本

系统 SHALL 提供从 `collaboration/tasks/TASK-*.md` 向当前工作树账本同步身份的显式入口。
同步后，身份审计覆盖的工单集合 SHALL 等于磁盘上的 md 工单集合，与账本此前的内容无关。

理由：账本是 per-worktree 的本机状态（gitignored），新检出上为空。以账本为输入的审计，
在没同步过的工作树上天然看到 0 条历史工单，该结果不能解释为「没有历史欠账」。

#### Scenario: 在空账本上同步

- **WHEN** 在一个账本为空的新工作树上执行同步
- **THEN** 账本工单数等于磁盘 md 工单数
- **AND** 每个 md 的 `task_id` 在账本中恰好对应一条记录

#### Scenario: 同步是显式的

- **WHEN** 用户只运行身份审计而未运行同步
- **THEN** 审计仍只读账本，不自动触发同步
- **AND** 输出显式说明「未同步过 md」，让覆盖范围可被解释

### Requirement: 同步不得推导或编造身份

同步 SHALL 只写 md frontmatter 中**已经声明**的字段。md 未声明的字段 SHALL 在账本中保持为空，
由身份判定逻辑按时间切点给出 `legacy` 或 `missing`，MUST NOT 填充任何推测值。

这条约束与「迁移函数顺手补身份」的设计错误同源：历史会话多数已结束，注册表无事实可依，
任何填充都是编造。

#### Scenario: 只声明了一个身份字段

- **WHEN** 某 md 只写了 `session_id` 而没有 `model_id`
- **THEN** 同步后账本中 `model_id` 为空
- **AND** 该工单判为 `partial`，原因点名缺失 `model_id`
- **AND** 不得从 `session_id` 或其他字段推导 `model_id`

#### Scenario: 历史工单没有身份字段

- **WHEN** 切点之前创建的 md 没有任何身份字段
- **THEN** 同步后账本中两个身份字段均为空
- **AND** 该工单判为 `legacy` 并被计数
- **AND** 不得判为 `invalid` 或 `missing`

#### Scenario: 同步方向单向

- **WHEN** 账本中某工单后来补了路由键，而 md 中没有该字段
- **THEN** 再次同步不把账本值写回 md
- **AND** 同步前后所有 md 文件的内容哈希不变

### Requirement: 审计输出披露输入覆盖范围

身份审计 SHALL 在输出中给出判定所依据的工单来源与条数，MUST NOT 让一个工作树内的条数
看起来像全仓全量。

#### Scenario: 同步过 md

- **WHEN** 账本记录了最近一次 md 同步
- **THEN** 审计输出给出同步时间与同步条数
- **AND** 输出中的 `total` 与同步条数不一致时，两者同时可见，便于发现差异

#### Scenario: 未同步过 md

- **WHEN** 账本没有 md 同步记录
- **THEN** 审计输出明确写「未同步过 md」
- **AND** 不得因为 `total=0` 而输出「无历史欠账」

### Requirement: 登记路径不得丢失已有身份字段

从 md 登记工单进账本的各条路径 SHALL 传递 md 中已声明的 `session_id` 与 `model_id`。

理由：登记函数支持这两个字段且会写入账本；丢失发生在调用点。缺失时，把 md 全量登记进账本
仍会得到全 `legacy` 的审计结果，被误读成迁移失败。

#### Scenario: 新登记

- **WHEN** 一个带完整身份的 md 首次被登记进账本
- **THEN** 账本中该工单的两个身份字段与 md 一致

#### Scenario: 已登记工单更新

- **WHEN** 一个已登记工单的 md 后来加了身份字段，再次走登记路径
- **THEN** 账本中该工单的身份字段被更新为 md 的值
- **AND** 不重复创建新工单
