# Implementation Tasks

> 勾选必须附实测证据（命令 + 关键输出），集中列在文末 E1–E6。

## Phase 0 · 立项

- [x] 0.1 从 `origin/main @ 2a968a2` 开独立 worktree 与分支（小写 `-b`，不用 `-B`）
- [x] 0.2 产出 `proposal.md` / `specs/concurrent-workspace-safety/spec.md` / `tasks.md`
- [x] 0.3 `openspec validate add-worktree-collision-guard --strict` 零错误

## Phase 1 · 检测层

- [x] 1.1 `detect_worktree_branch_collisions()`：只读解析 `git worktree list --porcelain`
- [x] 1.2 重复分支聚合成 `collisions[]`（branch + 各路径），`worktree_count` 如实计数
- [x] 1.3 detached HEAD 无 `branch` 行 → 不参与计数，也不掩盖真冲突
- [x] 1.4 git 命令失败 → 空冲突 + `error`，不据此判违规

## Phase 2 · 门禁定级

- [x] 2.1 `assess_concurrent_risk()` 新增 `worktree_collision_severity`（默认 `high`）
- [x] 2.2 信号进 `signals["worktree_collisions"]`；默认进 `violations` 并阻断
- [x] 2.3 `warning` 降级后仍进 `warnings`，不静默丢弃
- [x] 2.4 `run_concurrent_guard()` 从 `concurrentGuard.worktreeCollisionSeverity` 读配置并写入 `thresholds`

## Phase 3 · 可观测性

- [x] 3.1 `concurrent` CLI 新增 `worktrees: N (collisions: ...)` 行，放行时也显示
- [x] 3.2 阻断时给出正确修法（`checkout --detach` / `update-ref`）并说明覆盖不是解
- [x] 3.3 `.vscode/ai-collab.json` 增加 `worktreeCollisionSeverity: "high"` 让旋钮可发现

## Phase 4 · 规则文本（与代码同 commit）

- [x] 4.1 `PROTOCOL §14.5` 门禁分层表新增 G11 行（git 真证 / 硬门禁 / 可阻断）
- [x] 4.2 `PROTOCOL §14.7` 新增小节：现象 / 为何是硬门禁 / 危害 / 检出手法 / 修法
- [x] 4.3 `PROTOCOL §14.6` 措辞由「三信号」改为「四信号」

## Phase 5 · 测试与门禁

- [x] 5.1 检测层 9 条用例（4 检测 + 5 分级/落盘），含正反两侧
- [x] 5.2 CLI 层 3 条用例（退出码 2 / 修法提示 / 放行时显示 none）
- [x] 5.3 全套 pytest 与干净基线两侧同环境对照，FAILED 集合一致
- [x] 5.4 `ruff format --check .` / `ruff check .`
- [x] 5.5 `openspec validate add-worktree-collision-guard --strict`

## Phase 6 · 收口

- [x] 6.1 结果报告四段 + 状态行 + `acceptance_commands` 原样出现
- [x] 6.2 ACK 由 CLI 生成、任务状态经 CLI 变更
- [x] 6.3 提交带 pathspec；开 PR；登记合入提交；归档

## 明确不在本 change 范围

- **不接进 `governance preflight`**：preflight 固定五项，加第六项会改变输出契约并牵动既有断言。
  接 preflight 留作后续（已登记 N28 待做 ⑤）。
- **不重排既有分级**：G1/G2 仍硬门禁、G3 仍软警告，新信号独立成第四类。
- **不拦截未来的 `git -B` 操作**：git 无前置钩子能拦住工作树操作；守卫检测的是结果状态。
  状态一旦出现就会被拦，这已足够。
- **不自动修复**：不替用户执行 `checkout --detach` / `update-ref`——那会改写别人的工作树。

## 偏离与理由

**1. 守卫只在 `concurrent guard` 生效，未接 `governance preflight`**

用户的要求是「补一条 known_gaps，或直接落成 concurrent_guard 里的一个检查项」。选了后者。
但**没有**顺手接进 preflight：preflight 目前固定五项，多处断言与报告文案依赖这个项数，
加第六项属独立的行为变更，不塞进本次。代价是「开工即拦」还没做到，只在显式跑
`concurrent guard` 时生效——这一点写进 N28 的待做项，而不是假装已经全覆盖。

**2. 保留了 `worktreeCollisionSeverity` 降级开关**

严格说 G11 没有任何合法用途（git 自己就不让造这个状态），不给开关更省事。仍给了，理由是
既有 `foreignChangeSeverity` 已确立「同一信号可分级」的先例，保持一致性；且降级后**仍进
warnings**，不存在静默放行的路径。如果后续认为不应给出口，删掉这个键即可，默认值就是 high。

**3. 顺带修正了上一轮结果报告的两处口径（不在本 change 的 change_id 范围内）**

`RESULT-MIGRATE-SESSION-IDENTITY-001.md` 是已归档 change 的交付物，本次改动它属于
**记录更正**而非功能变更。理由：两处都是数字写错（preflight 三项实为四项；`18` 不可从仓库复现），
留着会传下去。更正是追加章节 + 显式标注，不覆盖首版正文，保留痕迹。

## 证据

### E1 · 检测层用例

```
$ python3 -m pytest tests/unit/test_worktree_collision_guard.py -q
9 passed, 2 warnings in 1.86s
```

覆盖正反两侧：单工作树不误报 / 不同分支不误报 / detached 不误报 /
`-B` 抢占后必报（branch + 2 条路径）/ 默认阻断 / 降级仍进 warnings /
干净仓库保持 low / 落盘含信号与阈值 / 配置驱动降级。

### E2 · CLI 层用例

```
$ python3 -m pytest tests/unit/test_concurrent_guard_cli.py tests/unit/test_worktree_collision_guard.py -q
25 passed, 2 warnings in 5.84s
```

含 `collisions: feat1 x2` 输出断言与「worktree 冲突不能靠覆盖解决」提示断言。

### E3 · 既有并发守护回归

```
$ python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py \
                     tests/unit/test_concurrent_guard_reuse.py -q
42 passed, 2 warnings in 9.80s
```

新信号未改变 G1/G2/G3 的既有判定与退出码。

### E4 · 对本仓实跑（无误报）

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

7 个 worktree 各在不同分支或 detached，守卫判 `none`。

### E5 · 静态门禁与 OpenSpec

```
$ ruff format --check .
330 files already formatted

$ ruff check .
All checks passed!

$ openspec validate add-worktree-collision-guard --strict
Change 'add-worktree-collision-guard' is valid
```

### E6 · 全套回归（两侧同环境，`PYTHONPATH=/tmp/noshim:$PYTHONPATH`）

基线 = 真实 clone `git clone git@github.com:17Mojo/ai-collab-base.git @ 2a968a2`（工作区干净，0 改动）；
当前 = 本分支工作树。

```
基线:   50 failed, 3118 passed, 8 skipped, 3 warnings in 41.78s
当前:   50 failed, 3130 passed, 8 skipped, 3 warnings in 46.48s
净增 = 3130 - 3118 = 12（= 9 检测 + 3 CLI 用例）

$ diff fail-base2.txt fail-cur2.txt   → 无输出
$ cmp  fail-base2.txt fail-cur2.txt   → byte-identical
```
