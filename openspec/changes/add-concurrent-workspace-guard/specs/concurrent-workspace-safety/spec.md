## Purpose

在并行协作者共享同一个 git 工作区时，于提交/派单前给出可判定的并发风险结论：分支是否漂移、基线是否过期、工作区是否混入他人未提交改动，并把结论落盘留痕。

## ADDED Requirements

### Requirement: 工作区 git 上下文采集

系统 SHALL 提供只读的 git 上下文采集能力，返回当前分支名、HEAD commit、上游分支、领先/落后提交数，以及工作区脏文件总数与脏文件路径列表（最多 50 条）。当处于 detached HEAD 状态时分支名 SHALL 为空值而非字符串 `HEAD`。

#### Scenario: 在有上游的常规分支上采集

- **WHEN** 工作区位于分支 `feat/x`，且该分支跟踪上游 `origin/feat/x`，领先 3 个提交
- **THEN** 采集结果中分支为 `feat/x`，上游为 `origin/feat/x`，领先数为 3
- **AND** 脏文件路径列表与 `git status --porcelain=v1 --untracked-files=all` 的输出条数一致

#### Scenario: 处于 detached HEAD

- **WHEN** 工作区的 HEAD 指向某个 commit 而非分支
- **THEN** 采集结果中分支为空值，且不出现字符串 `HEAD`

#### Scenario: 重命名条目的路径归一化

- **WHEN** `git status` 输出某条重命名记录 `old.py -> new.py`
- **THEN** 脏文件路径列表中记录的是重命名后的路径 `new.py`

### Requirement: 分支漂移检测

系统 SHALL 在给出期望分支时检测当前分支是否与期望分支不一致，并将其标记为高危违规。未给出期望分支时 SHALL 跳过该检测且不产生任何违规。

#### Scenario: 当前分支与期望分支一致

- **WHEN** 期望分支为 `main`，当前分支为 `main`
- **THEN** 检测结果为未漂移，severity 为 `none`
- **AND** 总体结论中不包含分支漂移违规

#### Scenario: 当前分支与期望分支不一致

- **WHEN** 期望分支为 `main`，当前分支为 `refactor/slimming`
- **THEN** 检测结果为已漂移，severity 为 `high`
- **AND** 总体结论的违规列表中出现一条指明期望值与实际值的分支漂移记录

#### Scenario: 未声明期望分支

- **WHEN** 调用方未提供期望分支
- **THEN** 检测结果为未漂移，且总体结论中不产生分支漂移违规

### Requirement: 基线过期检测

系统 SHALL 在同时提供基线 commit 与受监视路径时，统计 `基线..HEAD` 区间内这些路径上的提交数，任一路径计数大于 0 即判定基线过期并记为高危违规。缺少基线 commit 或受监视路径为空时 SHALL 跳过该检测。

#### Scenario: 受监视路径在基线之后被改动

- **WHEN** 基线为 `81a02c5`，受监视路径含 `ai_collab/`，且 `81a02c5..HEAD` 区间内 `ai_collab/` 下有 2 个提交
- **THEN** 检测结果为已过期，severity 为 `high`
- **AND** 总体结论的违规列表中指明基线与当前 HEAD 之间的过期事实

#### Scenario: 受监视路径自基线以来未变

- **WHEN** 基线为 `81a02c5`，受监视路径含 `docs/`，且该区间内 `docs/` 下无提交
- **THEN** 检测结果为未过期，severity 为 `none`

#### Scenario: 基线 commit 不存在

- **WHEN** 基线 commit 无法被 git 解析
- **THEN** 该路径的检测条目记录错误信息且提交数为空值
- **AND** 该路径本身不构成过期违规

### Requirement: 归属不明改动检测

系统 SHALL 在提供会话开始时间后，识别工作区中修改时间早于会话开始时刻的未提交文件（含未跟踪文件），并按配置决定其严重级别。未提供会话开始时间时 SHALL 跳过该检测。

#### Scenario: 存在早于会话开始的他人改动

- **WHEN** 会话开始时间为 `2026-09-26T10:00:00`，工作区有一个未提交文件的修改时间为 `2026-09-26T09:30:00`
- **THEN** 该文件被计入归属不明改动数量
- **AND** 当严重级别配置为 `warning` 时，该事实只出现在警告列表中，总体结论仍然放行

#### Scenario: 严重级别配置为 high

- **WHEN** 存在归属不明改动，且严重级别配置为 `high`
- **THEN** 该事实出现在违规列表中，总体结论不放行，风险级别为 `high`

#### Scenario: 会话开始时间不是合法 ISO 时间

- **WHEN** 会话开始时间无法被解析
- **THEN** 检测结果中记录错误信息，归属不明改动数量为 0
- **AND** 该错误不产生违规，总体结论不因此被阻断

#### Scenario: 调用方声明自己跟踪的路径

- **WHEN** 调用方声明某路径由本会话跟踪，且该路径恰好早于会话开始时间
- **THEN** 该路径不被计入归属不明改动

### Requirement: 并发风险评级与放行判定

系统 SHALL 综合上述三类信号得出风险级别与是否放行：存在违规时风险级别为 `high` 且不放行；仅有警告时为 `medium` 且放行；无违规无警告时为 `low`。当工作区领先上游的提交数超过配置的阈值时 SHALL 追加一条警告。

#### Scenario: 仅有警告时放行

- **WHEN** 三类检测均无违规，但存在警告
- **THEN** 风险级别为 `medium`，放行结论为真

#### Scenario: 存在违规时阻断

- **WHEN** 任一检测产生违规
- **THEN** 风险级别为 `high`，放行结论为假

#### Scenario: 领先上游超过阈值

- **WHEN** 工作区领先上游 25 个提交，且阈值为 20
- **THEN** 警告列表中出现领先提交数与阈值的记录，且放行结论不受该警告影响

### Requirement: 检测结论落盘留痕

系统 SHALL 将每次检测的结论写入最新报告文件，并向历史文件追加一行 JSON 记录。报告与历史的落点路径 SHALL 可配置，相对路径 SHALL 相对于被治理的工作区解析。报告 SHALL 包含生成时间、工作区路径、放行结论、风险级别、git 上下文、各类信号、违规列表、警告列表与生效的阈值。

#### Scenario: 默认落点

- **WHEN** 未配置报告路径与历史路径
- **THEN** 最新报告写入 `<工作区>/logs/workspace_forensics/concurrent_guard_latest.json`，历史追加到同目录的 `concurrent_guard_history.jsonl`

#### Scenario: 每次运行追加一条历史

- **WHEN** 在同一工作区连续运行两次检测
- **THEN** 历史文件包含两行，且每行都是可解析的 JSON 结论对象

#### Scenario: 报告落点可覆盖

- **WHEN** 配置了自定义的报告与历史相对路径
- **THEN** 结论写入该自定义路径，且仍位于被治理工作区内部

### Requirement: CLI 门禁

系统 SHALL 提供 `concurrent guard` 子命令执行检测并输出人可读结论。当放行结论为假时 SHALL 以非零退出码结束，当放行结论为真时 SHALL 以零退出码结束。配置的取值 SHALL 遵循「命令行参数优先于项目配置文件」的顺序。

#### Scenario: 检出分支漂移时门禁失败

- **WHEN** 以期望分支 `main` 运行 `concurrent guard`，而工作区当前分支为其它分支
- **THEN** 命令输出包含并发门禁结论的诊断段落
- **AND** 进程退出码为 2

#### Scenario: 无违规时门禁放行

- **WHEN** 运行 `concurrent guard` 且未检出任何违规
- **THEN** 进程退出码为 0

#### Scenario: 强制模式

- **WHEN** 以强制模式运行 `concurrent guard`，即使检出违规
- **THEN** 进程退出码为 0，且结论中标注该次运行处于强制状态

#### Scenario: 期望分支优先于项目配置

- **WHEN** 项目配置中声明了期望分支，但命令行同时传入另一个期望分支
- **THEN** 以命令行传入的期望分支为准

#### Scenario: 声明需要基线但未提供基线

- **WHEN** 项目配置要求提供基线 commit，而本次调用未提供
- **THEN** 该情况以警告形式提示，且不阻断门禁

### Requirement: 与被治理仓库解耦

系统 SHALL 能在与本仓库无关的任意 git 工作区上运行检测，结论与报告 SHALL 落位于该被治理工作区内部，不得写入其它工作区。

#### Scenario: 在外部工作区上运行检测

- **WHEN** 在一个与本仓库无关的 git 工作区上运行检测
- **THEN** 报告写入该工作区内部，其记录的 workspace 指向该工作区
- **AND** 本仓库的报告文件未被本次运行改写
