# Change Proposal: Add Worktree Collision Guard

## Why

`worktree` 共享同一份 `.git`（对象库 + `refs/`），各自独立的只有 `HEAD` / 索引 / 工作树。
而 `HEAD` 文件里写的是 `ref: refs/heads/<branch>` —— 移动 ref 等于**同时移动所有指向它的
HEAD**，但索引不跟着走。后果不是理论问题，2026-11-16 实测过一次：

本仓主工作区长期停在 `main` 且带 150+ 条未提交改动。在一处 worktree 里执行
`git checkout -q main 2>/dev/null || git checkout -q -B main origin/main` 后：

| 项 | 操作前 | 操作后 |
|---|---|---|
| 主工作区 HEAD | `36d9ec2` | `2cc2790`（被动前移） |
| 主工作区索引 | `36d9ec2` 基线 | 未变 |
| `git status` 条目 | 153 | **424** |

多出来的不全是真实改动，而是「索引 vs 新 HEAD」的基线漂移，其中包含 `D` 型
**「删除」假象**——文件根本没被删，只是索引里没有而新 HEAD 有。

### 为什么正常 git 拦不住

`worktree` 有占用检查：`git worktree add` 拒绝重复分支，`git checkout <branch>` /
`git switch <branch>` 都会以 `fatal: '<branch>' is already checked out at '<path>'` 拦住。

**但大写 `-B` / `-C` 会绕过它。** 这两个 flag 的语义是「强制重置该分支」，git 认为
你明确要重写引用，因而只保证当前 worktree 内部一致，不管别处。实测：

```
$ git checkout main          → fatal: 'main' is already checked out at '.../main-repo'
$ git switch   main          → fatal: 'main' is already checked out at '.../main-repo'
$ git checkout -B main feat  → Switched to and reset branch 'main'      ← 放行
$ git switch   -C main       → Switched to and reset branch 'main'      ← 放行
```

于是「同一分支被两个 worktree 签出」这个状态**只能由 `-B` / `-C` 或手工 `update-ref` 造成**。
换句话说：一旦出现，它不是配置问题，是**事故痕迹**。

### 为什么要在代码里拦，不只在文档里记

上一轮同类问题的处理方式是「在报告里写一句话」，结果 `platform-freeze` 那次证明了
那种记法不管用：环境变量给冻结站仍会照跑，直到落成代码级闸门才真拦住。
本次同理——`-B` 是手滑一次就中的操作，靠「记住了别用」不是守卫。

## What Changes

| 位置 | 改动 |
|------|------|
| `ai_collab/concurrent_guard.py` | 新增 `detect_worktree_branch_collisions()`：只读解析 `git worktree list --porcelain`，重复分支即判违规。detached HEAD 无 `branch` 行，不参与计数 |
| `assess_concurrent_risk()` | 新增 `worktree_collision_severity` 参数（默认 `high`），信号进 `signals["worktree_collisions"]`，默认进 `violations` 阻断 |
| `run_concurrent_guard()` | 从 `concurrentGuard.worktreeCollisionSeverity` 读配置，写入 `thresholds` 留痕 |
| `concurrent` CLI | 新增 `worktrees: N (collisions: ...)` 行；阻断时给出**正确修法**而非只说「用 --force 覆盖」 |
| `.vscode/ai-collab.json` | `concurrentGuard` 增加 `worktreeCollisionSeverity: "high"`，让旋钮可发现 |
| `PROTOCOL §14.5` | 门禁分层表新增 G11 行（git 真证 / 硬门禁 / 可阻断） |
| `PROTOCOL §14.7` | 新增小节：现象 / 为何是硬门禁 / 危害 / 检出手法 / 修法 |

### 定级理由：硬门禁，不是软警告

对齐既有分层原则「硬门禁对齐真证，软警告承载启发式」。G11 的检测输入是
`git worktree list --porcelain` 的直接输出，不依赖 mtime、不依赖启发式，属 git 真证。
且该状态**没有任何合法用途**——git 自己就不让造。因此默认硬门禁。

保留降级开关（`worktreeCollisionSeverity: "warning"`）是为了给「已知在迁移中的临时布局」
一条出路，但**降级后仍进 `warnings`，不静默**——静默放行等于没装。

## Non-goals（明确划界）

- **不接进 `governance preflight`。** preflight 目前固定五项，加第六项会改变其输出契约
  并牵动既有断言。本次只落 `concurrent guard`，接 preflight 留作后续（已登记 N28 待做 ⑤）。
- **不改 `concurrent guard` 的既有分级。** G1/G2 仍硬门禁、G3 仍软警告，新信号独立成第四类，
  不重排既有语义。
- **不试图拦截未来的 `git -B` 操作。** 守卫检测的是**结果状态**（两个 worktree 同分支），
  不是命令本身——git 没有前置钩子能拦住工作树操作。这已足够：状态一旦出现就会被拦。
- **不自动修复。** 不替用户执行 `checkout --detach` 或 `update-ref`——那会改写别人的工作树，
  是比误操作更大的风险。只报错 + 给人正确的命令。

## Impact

- 本仓现有 7 个 worktree 各在不同分支或 detached，实跑 `concurrent guard` 为
  `collisions: none`，**无误报**。
- 若有人再次触发 `-B` 抢占，`concurrent guard` 会以退出码 `2` 阻断，并在输出里说明
  「覆盖不是解，先让多余工作树脱离该分支」。
- `concurrentGuard` 配置新增一个键；缺省即 `high`，旧配置无需改动也能生效。
