# RESULT — TASK-UNTRACK-MONITORING-001 · 把本机监控摘要逐出索引

- **状态**: completed
- 日期：2026-11-16 · change_id：`untrack-monitoring-snapshots`
- 执行者：`sess-untrack-monitoring-20261116`（`deepseek/v4.1-flash`，AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/private/tmp/wt-g11`（分支 `fix/untrack-monitoring-snapshots-2026-11-16`，基线 `origin/main @ e2af634`）
- 范围：关掉 `known_gaps.json` **N27**——监控摘要被跟踪导致提交覆写共享快照

> **口径声明**：本 change 只做两件事——补忽略规则、把文件移出索引。**不删内容**
> （`--cached` 保留工作区文件）、**不改生成器**、**不动任何已有摘要的文字**。
> 代价照实写：untrack 之后仓库里不再有团队会话总览的副本，需要看的人得在自己机器上现跑。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate untrack-monitoring-snapshots --strict
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli governance preflight
git ls-files collaboration/monitoring/ | wc -l
python3 -m pytest tests/unit/test_automation_benefit_dashboard.py tests/unit/test_ack_remediation.py tests/unit/test_dispatch_intervention_wiring.py -q
python3 -m ruff format --check . && python3 -m ruff check .
```

同一工作区内的附加命令：

```
for f in $(git ls-files collaboration/monitoring/); do git check-ignore --no-index -q "$f" && echo 命中 || echo 未命中; done
git rm --cached -q collaboration/monitoring/*_latest.md collaboration/monitoring/*_test.md
PYTHONPATH=/tmp/noshim python3 -m pytest -q                                    # 改动侧全量
git worktree add /tmp/wt-baseline e2af634 --detach && cd /tmp/wt-baseline && PYTHONPATH=/tmp/noshim python3 -m pytest -q
git add -A --dry-run | grep "collaboration/monitoring/"
```

## 验证结果

### 1 · 问题不在「个别文件漏了」，而在规则是逐条维护的

N27 只点名两个文件。实际受跟踪集合是 **13 个**，而 `.gitignore` 的 monitoring 区块采用的是
逐条列举（9 条），新增摘要从来没被补进去。这种规则的失效方式是静默的：不报错，只是漏掉；
等到有人 `git add -A` 才发现，那时库里的共享快照已经被覆写了。

所以本 change 没有去「补上漏掉的那两条」，而是把逐条列举换成三条通配
（`*_latest.md` / `*_20*.md` / `*_test.md`），让规则对**全部实例**成立，包括将来新增的。

### 2 · 三个必须记录的过程事实

**① 改规则时抓到了一个回归。**
`AGENT_DISPATCH_ORDERS_test.md` 原本由第 80 行**单独**忽略（后缀是 `_test` 而非 `_latest`）。
换成 `*_latest.md` / `*_20*.md` 之后它失去了忽略——**改规则反而缩小了排除面**。
补 `*_test.md` 后恢复，并对 9 条原规则覆盖的实例逐个复核，全部仍为忽略。

这条说明：把逐条改成通配时，「通配看起来更宽」不能替代逐实例复核。已验证的 9 条里有 1 条是反例。

**② 我自己先用错了判定工具。**
初期用 `git check-ignore` 逐个判定 13 个文件，得到「13 个全部未命中规则」，并据此写下
「规则完全没覆盖它们」。**这是错的**：`git check-ignore` 默认跳过已跟踪文件，对受跟踪集合
调用必然全部返回未命中，它回答不了「规则是否覆盖该路径」。改用 `--no-index` 才能回答。

结论方向没变（旧规则下 13 个确实无一命中），但方法必须更正，已写进 `spec.md` 的核验场景，
避免下一个人用同一个错误方法得出不同结论。

**③ `_test.md` 为什么一并处理。**
最初按「不含生成时间戳 → 不算本机快照」把两个 `_test.md` 划出范围。但 `AGENT_DISPATCH_ORDERS_test.md`
本来就在忽略列表里，说明 `_test` 后缀同属这类自动产物。若只忽略不 untrack，会出现
「被忽略但仍被跟踪」——git 里最难解释的状态之一。故 13 个一并 untrack。
`spec.md` 相应补了判定口径：**依据产出机制与落点，不依据单次内容**（某次输出为空结果不代表它不是同一机制产物）。

### 3 · 效果实证：文件被真实改写，而 git 完全没报告

这是本 change 最直接的证据链。先记录改动前状态，然后跑一次真实会刷新摘要的命令：

```
改动前： sha256 292699c5…  生成时间 2026-10-24T19:06:17  会话数 8
执行：   sessions register --session-id sess-untrack-monitoring-20261116
改动后： sha256 2be4f908…  生成时间 2026-11-16T06:20:08  会话数 2
```

文件确实被改写了（这正是 N27 描述的现象，且跨了一个月的生成时间）。而：

```
$ git status --porcelain | grep -E '^( M|M )' | grep -c collaboration/monitoring
0
$ git status --porcelain | grep -v "^D  collaboration/monitoring/"
 M .gitignore
?? collaboration/tasks/TASK-UNTRACK-MONITORING-001.md
?? openspec/changes/untrack-monitoring-snapshots/
```

排除本 change 显式移除的 13 个 `D` 之后，工作区只剩两处本 change 自己的改动。
**摘要改写没有被报告**——这就是要的效果。

### 4 · 零回归

同环境、同命令、与干净基线对照：

| 侧 | 结果 |
|---|---|
| 改动分支 | `3189 passed, 8 skipped` |
| 干净基线 `e2af634` | `3189 passed, 8 skipped` |

完全一致。相关三个测试文件单跑 `21 passed`。`ruff format --check` 331 files already formatted，
`ruff check` All checks passed。

附带的基线更正：上一轮报告沿用 `50F/3139P` 作对照基线，但同环境实测干净基线是 `3189P / 0F`
（3189 = 3139 + 50，总数吻合）。那 50 个 FAILED 是另一个解释器环境的残留，不是本仓缺陷。
本轮不再沿用该基线，也不再宣称「FAILED 集合 byte-identical」——在这个环境下没有 FAILED 可比。

## 偏离与残留

**1 · 工单 md 由手写，CLI 不生成。**
`tasks register` 只写账本（`logs/collaboration_state.json`），不产出
`collaboration/tasks/TASK-*.md`。上一轮的 `TASK-PREFLIGHT-WORKTREE-GATE-001` 同样只有账本条目、
没有 md。本 change 按 `tasks.md` 0.3 的要求手写了 md，frontmatter 作为账本镜像
（权威状态仍在账本，文件内已注明）。

**2 · 顺带发现 N26 的根因比台账写的更深，但未在本 change 处理。**
本轮实测发现 `logs/` 是**每个工作树各一份**的本机状态：

```
主工作区  34,644 B  mtime 2026-10-26  sha256 62d92b34…  tasks 18 条
wt-g11     3,301 B  mtime 2026-11-16  sha256 0472a163…  tasks  2 条
磁盘 md    26 个，与任一侧账本的交集均为 0
```

所以 N26 记录的「0 / 26 / 18 三处数字对不上账」不只是「审计口径漏了文件」，
而是**账本天生 per-worktree，磁盘 md 才是仓库共享**。任何以账本为输入的审计，
在非主工作区里只能看到该工作区自己注册过的任务。这一条已作为新证据待回填 N26，
不并入本 change（它需要先裁定任务事实源归属）。

**3 · 团队级总览的替代方案未做。**
N27 修法的第二条是「改由汇总侧生成、换跨会话聚合口径」。本 change 只止血，
仓库不再提供团队总览副本。这是有意的取舍，写进 proposal 的「不在范围」。
