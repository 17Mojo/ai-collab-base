# Change Proposal: Untrack Monitoring Snapshots

## Why

`collaboration/monitoring/` 下的摘要文件由 CLI 自动生成，数据源是 **gitignored 的本机状态**
（`logs/session_registry_state.json`、`logs/collaboration_state.json`）。它们被跟踪进库后，
任何人在自己的机器上跑一次 `sessions register` 或 `tasks validate-contract`，都会把库里的
「团队会话总览」覆写成「我这台机器的视图」，而 diff 看起来像一次正常刷新。

2026-11-16 在 `migrate-session-identity` 收口阶段实测到该覆盖：

```
-生成时间: 2026-10-24T19:06:17
-会话数: 8
+会话数: 1
```

8 条 `assignee=claude_code` 的真实会话行被整段删除，只留本机唯一会话
`sess-migrate-identity-20261116`。该改动由 CLI 自动触发，非人为编辑。

当时把它登记为 `known_gaps.json` 的 **N27**（P2 / open），修法写了两条：`gitignore` +
`git rm --cached`；若要保留团队级总览，改由汇总侧生成。本 change 执行第一条。

### 范围比台账登记的更大

N27 只点名了两个文件（`SESSION_REGISTRY_SUMMARY_latest.md`、
`TASK_RESULT_CONSISTENCY_SUMMARY_latest.md`）。实际清点受跟踪集合共 **13 个**：

```
$ git ls-files collaboration/monitoring/ | wc -l
13
```

`.gitignore` 的 monitoring 区块（第 77–92 行）确实在忽略一批同类产物
（`AGENT_DISPATCH_ORDERS_*`、`DAILY_REPORT_latest.md`、`NOOP_PENDING_CONFLICT_SUMMARY_latest.md`、
若干运行时目录），但那是**逐条列举**，新增的摘要文件从来没被补进去。结果是同一类自动产物里，
一部分被忽略、一部分被跟踪，规则不完整而非个别遗漏。

其中 11 个 `*_latest.md` 头部均带「生成时间」或 `generated_at`，是本机快照；
2 个 `*_test.md` 是空结果 JSON。

### 方法论更正：`git check-ignore` 不适用于已跟踪文件

本 change 初期用 `git check-ignore` 逐个判定 13 个受跟踪文件，得到「13 个全部未命中规则」，
并据此写下「规则完全没覆盖它们」。**该结论是用错工具得出的。**

`git check-ignore` 默认**跳过已跟踪文件**（除非加 `--no-index`），因此对受跟踪集合执行它必然
全部返回未命中——它回答不了「规则是否覆盖了这个路径」，只回答「这个未跟踪文件会被忽略吗」。

改用 `--no-index` 重做后可见，13 个路径在新规则下**全部命中**：

```
$ for f in $(git ls-files collaboration/monitoring/); do
    git check-ignore --no-index -q "$f" && echo "命中  $(basename $f)" || echo "未命中 $f"
  done | sort | uniq -c -w3
  13 命中
```

修正后的事实：**原有规则覆盖了一部分同类产物，但 13 个已跟踪文件无一在其中**（这一点结论不变），
而规则完备性的判定必须以 `--no-index` 为准。

### 改规则时抓到的回归

把逐条列举换成通配后，`AGENT_DISPATCH_ORDERS_test.md` **失去了忽略**：原第 80 行是为它单独写的
（后缀是 `_test` 而非 `_latest`），`*_latest.md` 与 `*_20*.md` 都不覆盖它。若不补 `*_test.md`，
这个原本被忽略的文件会变成未跟踪可见——改规则反而放宽了排除面。

补 `*_test.md` 后 9 个原规则实例逐个复核，全部仍为忽略，零回归。


### 为什么 untrack 是安全的

清点读取点后确认：代码里对 `collaboration/monitoring/` 的全部引用都是**输出路径**
（`DEFAULT_SUMMARY_PATH = ...`、`--summary` 默认值、CLI 打印的 `cat` 提示），
没有一处把它们当作输入读回。单测引用这些文件名时，走的都是 `tmp_path` 临时工作区
（`tests/unit/test_ack_remediation.py`、`tests/unit/test_dispatch_intervention_wiring.py`），
读写的是自己刚生成的文件，与仓库里的副本无关。

`ai_collab/workspace_guard.py` 已把 `collaboration/monitoring/` 归入 `OPS_PREFIXES`
（运维产物），与「必须干净的源码」分开对待。untrack 与该分类一致：它本来就是 ops 类产物。

## What Changes

- `.gitignore` 的 monitoring 区块把逐条列举换成三条通配：`*_latest.md` / `*_20*.md` / `*_test.md`，
  覆盖该类产物的**全部**实例（含未来新增），不再依赖逐条维护。
- `git rm --cached` 全部 13 个已跟踪摘要。**只从索引移除，工作区文件保留**（`--cached`），
  本机现有快照不丢——实测移除后 13 个文件仍在原位、内容未变。
- 生成器不动。文件照旧生成到原路径，只是不再进版本库。

## 明确不在本 change 范围

- **团队级总览的替代方案**：N27 修法第二条是「改由 CI/汇总侧生成，数据源换成跨会话聚合口径」。
  这需要先确定聚合口径由谁产、产在哪，属独立设计，本 change 只先止血（不再污染库）。
  代价是：**untrack 之后，仓库里不再有团队会话总览的副本**，需要看总览的人得在自己机器上现跑。
- **运行时事件目录**（`codearts_pull_events/` 等）已经在 ignore 列表内，不动。
- **已提交的历史快照内容**：本 change 不回写、不改写任何一份已有摘要的内容，
  只改变它是否被跟踪。历史提交里的那 13 份旧副本仍在 git 历史中可查。
- **N26**（审计输入只读账本、磁盘 26 个任务文件未计入）：同属口径类缺口，但落在
  「任务事实源归属」这个需要裁定的问题上，独立处理。
