# RESULT — TASK-WORKTREE-COLLISION-GUARD-001 · 工作树分支冲突守卫 + 两处口径更正

- **状态**: completed
- 日期：2026-11-16 · change_id：`add-worktree-collision-guard`
- 执行者：`claude_code`（AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/tmp/wt-wtguard`（分支 `feat/worktree-collision-guard-2026-11-16`，基线 `origin/main @ 2a968a2`）
- 范围：把「`-B` / `-C` 抢夺已被签出分支」这条只写在报告里的话，落成 `concurrent_guard` 的检测项；
  并回填上一轮结果报告的两处数字口径

> **口径声明**：本次两件事性质不同，分开记。
> **守卫**是真行为变更（新信号、新配置键、新 CLI 行、12 条用例）；
> **口径更正**是记录纠正（不覆盖首版正文，追加「记录更正」章节保留痕迹）。
> 守卫只落 `concurrent guard`，**没有**接进 `governance preflight`——preflight 项数是既有契约，
> 加第六项属独立变更，代价写进 N28 待做项，不假装已全覆盖。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate add-worktree-collision-guard --strict
python3 -m pytest tests/unit/test_worktree_collision_guard.py -q
python3 -m pytest tests/unit/test_concurrent_guard_cli.py -q
python3 -m ai_collab.cli concurrent guard
ruff format --check .
ruff check .
```

同一工作区内的附加命令：

```
python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_reuse.py -q   # 既有回归
PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider                   # 当前侧全量
cd /tmp/realclone && PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider
diff /tmp/fail-base2.txt /tmp/fail-cur2.txt && cmp /tmp/fail-base2.txt /tmp/fail-cur2.txt
```

## 验证结果

### 1 · 守卫：为什么这个状态必须由代码拦

`HEAD` 文件内容是 `ref: refs/heads/<branch>`，而 `refs/` 由所有 worktree 共享。
移动引用 = **同时移动所有指向它的 HEAD**，但各工作树的索引不跟着走。`git status` 的两项比较里，
「索引 vs HEAD」这一项因此全部失真。

而正常 git 造不出这个状态——占用检查是有的：

```
$ git checkout main          → fatal: 'main' is already checked out at '.../main-repo'
$ git switch   main          → fatal: 'main' is already checked out at '.../main-repo'
$ git checkout -B main feat  → Switched to and reset branch 'main'      ← 放行
$ git switch   -C main       → Switched to and reset branch 'main'      ← 放行
```

**只有大写 `-B` / `-C`（语义为「强制重置该分支」）能绕过。** 因此「同一分支被两个 worktree
签出」一旦出现，就是事故痕迹，不是配置问题——这正是可以做成硬门禁的原因：它没有合法用途。

### 2 · 检测实现（只读）

`detect_worktree_branch_collisions()` 解析 `git worktree list --porcelain`，按 `branch` 行分组，
多于一处即判冲突。三个细节是刻意的：

| 细节 | 处理 | 理由 |
|---|---|---|
| detached HEAD | 无 `branch` 行，不计入 | 它没有分支归属，计进去会造成假冲突 |
| detached 存在时 | 仍统计其他工作树 | 不能因为有个 detached 就漏掉真冲突 |
| git 命令失败 | 返回空冲突 + `error` | 查不到 ≠ 无冲突，但也不能据此判违规 |

### 3 · 定级：默认硬门禁，可降级但不静默

```
$ python3 -m pytest tests/unit/test_worktree_collision_guard.py -q
9 passed, 2 warnings in 1.86s
```

| 用例 | 断言 |
|---|---|
| `test_single_worktree_no_collision` | 单工作树 → 空冲突、severity=none |
| `test_distinct_branches_no_collision` | 两工作树不同分支 → 空冲突、count=2 |
| `test_detached_worktree_not_counted_as_collision` | detached → 空冲突、count=2 |
| `test_detects_collision_made_by_force_reset` | `-B` 抢占后 → 1 条冲突、branch=feat1、两条路径都在 |
| `test_collision_blocks_by_default` | `allowed=False`、`risk_level=high`、violations 含该信号 |
| `test_collision_can_be_downgraded_to_warning` | 降级后 `allowed=True`，但**仍在 warnings 里** |
| `test_clean_repo_stays_low_risk` | 干净仓库 → low、无冲突 |
| `test_run_persists_collision_signal_and_threshold` | 报告落盘含信号与阈值 |
| `test_severity_config_comes_from_guard_config` | 配置驱动降级，thresholds 如实记录 |

降级那条是本组最要紧的：**静默放行等于没装**。所以降级的语义是「不阻断」，不是「不存在」。

### 4 · 可观测性：落盘不显示等于半个守卫

`concurrent` CLI 增加一行，放行时也显示：

```
$ python3 -m ai_collab.cli concurrent guard
[并发门禁]
  allowed: True
  risk_level: low
  branch: feat/worktree-collision-guard-2026-11-16 (expected: none)
  baseline: none (skipped)
  foreign: 0 files (severity: none)
  worktrees: 7 (collisions: none)
```

阻断时额外给出**正确修法**，而不是只说「用 --force 覆盖」：

```
  violation: worktree collision: 同一分支被多个工作树签出（feat1 @ 2 处）
  worktree 冲突不能靠覆盖解决：先让多余的工作树脱离该分支（git worktree remove 或
  git checkout --detach），否则它的 git status 会把基线漂移报成大量假改动。
```

这与既有 `--force-workspace` 的语义有张力，是刻意的：覆盖只让门禁闭嘴，失真仍在。

### 5 · 既有分级未被重排

```
$ python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py \
                     tests/unit/test_concurrent_guard_reuse.py -q
42 passed, 2 warnings in 9.80s
```

G1/G2 仍硬门禁、G3 仍软警告，新信号独立成第四类，不改变任何既有退出码。

### 6 · 测试结论（全套回归，两侧同环境）

基线用**真实 clone**（`git clone git@github.com:17Mojo/ai-collab-base.git @ 2a968a2`，
`git status` 为 0 条），不是 `git archive` 快照——上一轮用快照时因 `4d04acd` 不存在
导致 preflight 出现假 FAIL，这次避开。

| 侧 | 结果 |
| --- | --- |
| 基线 | `50 failed, 3118 passed, 8 skipped, 3 warnings in 41.78s` |
| 当前 | `50 failed, 3130 passed, 8 skipped, 3 warnings in 46.48s` |
| 净增通过 | `12`（= 9 检测 + 3 CLI 用例） |
| `diff` / `cmp` FAILED 集合 | **无输出 / byte-identical** |

### 7 · 静态门禁与 OpenSpec

```
$ ruff format --check .   → 330 files already formatted
$ ruff check .            → All checks passed!
$ openspec validate add-worktree-collision-guard --strict
Change 'add-worktree-collision-guard' is valid
```

### 8 · 记录更正（上一轮结果报告）

`RESULT-MIGRATE-SESSION-IDENTITY-001.md` 首版有两处口径不准，已追加「记录更正」章节
（保留首版正文，不覆盖）：

| 项 | 首版 | 实测 |
|---|---|---|
| 干净检出 `preflight` | 「三项 FAIL」 | **四项 FAIL**——漏了门禁输入完整性。当时是我在 worktree 里建了 `.vscode/ai-collab.local.json` 才 PASS |
| `legacy_identity=18` | 读起来像仓库事实 | **不可从仓库复现**：真实 clone 上 `checked=0` / `total=0`，磁盘 26 个任务文件。三处数字为 0 / 26 / 18 |

第二条影响更大：任何以账本为输入的身份审计，在新鲜检出上都是空跑，**看不出**历史工单缺身份。
已追加进 `known_gaps.json` N26 的证据链与影响面。

## 风险

1. **守卫只在 `concurrent guard` 被调用时生效，开工时不会自动拦。**
   `governance preflight` 目前固定五项，加第六项会改变输出契约并牵动既有断言，属独立变更。
   所以本次只落 `concurrent guard`。这意味着：**一个人如果从不跑 concurrent guard，
   守卫对他无效**。已写进 N28 待做 ⑤（接 preflight）。这是当前最实的缺口。

2. **检测的是结果状态，不是操作本身。**
   git 没有能拦住工作树操作的前置钩子，所以守卫只能在事故发生后报出来，
   无法阻止 `-B` 执行。缓解点在于：状态会**持续存在**（两个 worktree 同分支不会自愈），
   因而必然被下一次 check 抓到。人工前置检查（`git worktree list`）仍是第一道。

3. **降级开关给了绕过路径。**
   `worktreeCollisionSeverity: "warning"` 会让冲突不阻断。保留了它（对齐既有
   `foreignChangeSeverity` 先例），但降级后仍进 warnings。若认为不该给出口，删掉该键即可，
   默认就是 high。

4. **不自动修复是刻意的保守选择。**
   守卫不替用户执行 `checkout --detach` / `update-ref`——那会改写**别人的**工作树，
   比误操作本身风险更大。只报错并给出正确命令。

5. **本 change 的合入同样会被覆盖率门禁拦下。**
   生效边界 `4d04acd` 之后每个 merge commit 都要先 `declare-commit` 才能过 `--strict`。
   顺序沿用已验证的：`merge → declare-commit → 提交登记表 → 复跑 → archive`。

6. **顺带修改了已归档 change 的结果报告。**
   `RESULT-MIGRATE-SESSION-IDENTITY-001.md` 属上一轮交付物，本次改它不在
   `add-worktree-collision-guard` 的 change_id 范围内。判断依据：两处都是数字写错，
   留着会传下去；处理方式是**追加更正章节**而非改写正文，首版结论仍可查。

## 回滚

- **守卫**：删除 `detect_worktree_branch_collisions()` 与 `assess_concurrent_risk` 里的
  接入块，`signals["worktree_collisions"]` 与 `thresholds["worktreeCollisionSeverity"]` 随之消失；
  CLI 的 `worktrees:` 行一并删除。回退后门禁行为与 2a968a2 完全一致。
- **配置**：删掉 `.vscode/ai-collab.json` 的 `worktreeCollisionSeverity` 键即可，
  代码里缺省即 `high`，旧配置无需改动也能工作。
- **规则文本**：`PROTOCOL §14.5` 的 G11 行与 §14.7 整节可独立删除；
  **必须与代码同时回退**，否则出现「规则说要拦、代码不拦」。
- **记录更正**：不建议回退。两处数字有实测支撑（真实 clone 的输出），
  回退等于把已知错误的数字放回去。若要撤销，需同时撤掉 `known_gaps.json` N26 的新增证据。
- **N28**：按约定只改 `status` 不删，回退时置 `wontfix` 并保留结论。
- **整体**：`git revert <本 change 的提交>`。
