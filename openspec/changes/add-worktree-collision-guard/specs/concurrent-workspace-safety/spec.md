## ADDED Requirements

### Requirement: 工作树分支冲突检测

系统 SHALL 检测「同一分支被两个及以上工作树同时签出」这一状态，并把它作为独立的并发风险信号
提供给门禁使用。检测 MUST 为只读：不得修改任何工作树的 HEAD、索引或工作树文件。

detached HEAD 的工作树没有分支归属，MUST NOT 参与冲突计数；但它也 MUST NOT 掩盖真实冲突。

#### Scenario: 同一分支被两个工作树签出

- **WHEN** `git worktree list --porcelain` 输出中两个及以上工作树带同一个 `branch refs/heads/X`
- **THEN** 检测结果为冲突，`collisions` 至少含一条记录，其中的 `branch` 为 `X`、`paths` 为这些工作树路径
- **AND** 该信号的 `severity` 为 `high`

#### Scenario: 各工作树分支互不相同

- **WHEN** 每个工作树签出不同分支
- **THEN** `collisions` 为空
- **AND** 该信号的 `severity` 为 `none`
- **AND** `worktree_count` 仍如实反映参与统计的工作树数量

#### Scenario: detached HEAD 的工作树

- **WHEN** 某工作树处于 detached HEAD（porcelain 输出中无 `branch` 行）
- **THEN** 该工作树不计入任何分支的冲突分组
- **AND** 不得因为它存在而漏报其他工作树的真实冲突

#### Scenario: git 不可用或命令失败

- **WHEN** `git worktree list --porcelain` 返回非零退出码
- **THEN** 检测返回空冲突列表并带上 `error` 说明
- **AND** MUST NOT 把「查不到」当成「无冲突」以外的任何结论（不得据此判违规）

### Requirement: 工作树冲突的门禁定级与降级

该信号 SHALL 默认作为硬门禁：进入违规列表、`risk_level` 为 `high`、`allowed` 为假。
系统 SHALL 提供配置开关 `concurrentGuard.worktreeCollisionSeverity`，取值为 `warning` 时
降级为软警告。

降级后 MUST 仍把该信号写入 `warnings`，不得静默丢弃——降级的语义是「不阻断」，不是「不存在」。

#### Scenario: 默认状态下冲突阻断

- **WHEN** 存在工作树分支冲突且未配置降级
- **THEN** 评估结果 `allowed` 为假、`risk_level` 为 `high`
- **AND** `violations` 中含可辨识的冲突描述
- **AND** CLI 退出码为 `2`

#### Scenario: 配置降级为警告

- **WHEN** 存在工作树分支冲突且 `worktreeCollisionSeverity` 为 `warning`
- **THEN** `allowed` 为真
- **AND** `warnings` 中仍含该冲突描述
- **AND** `thresholds` 中如实记录本次生效的等级

#### Scenario: 无冲突时不产生噪音

- **WHEN** 不存在冲突
- **THEN** 不向 `violations` 或 `warnings` 写入任何与工作树冲突相关的内容
- **AND** 现有 G1 / G2 / G3 的判定结果不受影响

### Requirement: 冲突的处置指引

CLI 在因工作树冲突而阻断时 SHALL 给出可执行的修法，并 MUST 明确说明「用覆盖开关绕过不是解法」。

理由：该状态会让被牵连工作树的 `git status` 失真（把基线漂移报成改动，含 D 型「删除」假象），
覆盖门禁只会让失真继续存在而无人察觉。

#### Scenario: 阻断时给出修法

- **WHEN** 因工作树冲突阻断
- **THEN** 输出中包含让多余工作树脱离该分支的做法（`checkout --detach`）或只移动引用的做法（`update-ref`）
- **AND** 输出中说明该冲突不能靠 `--force-workspace` 解决

#### Scenario: 未阻断时也可见

- **WHEN** 门禁放行
- **THEN** 输出中仍显示工作树数量与冲突计数（无冲突时显示 `collisions: none`）
- **AND** 不因放行而隐藏该信号
