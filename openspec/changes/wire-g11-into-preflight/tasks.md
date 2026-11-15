# Implementation Tasks

> 勾选必须附实测证据（命令 + 关键输出），集中列在文末 E1–E6。

## Phase 0 · 立项

- [x] 0.1 从 `origin/main @ 28e6362` 开独立 worktree 与分支（小写 `-b`，不用 `-B`）
- [x] 0.2 产出 `proposal.md` / `specs/governance-coverage/spec.md` / `tasks.md`
- [x] 0.3 `openspec validate wire-g11-into-preflight --strict` 零错误

## Phase 1 · 检测函数加固

- [x] 1.1 `detect_worktree_branch_collisions()` 捕获 `OSError`（git 不在 PATH 时不逃逸）
- [x] 1.2 失败返回空冲突 + `error`，由调用方决定口径（查不到 ≠ 有冲突）
- [x] 1.3 正常路径行为不变（既有 12 条 G11 用例全过）

## Phase 2 · 接入 preflight

- [x] 2.1 `preflight()` 追加第六项「工作树分支冲突」，**追加在末位**不插队
- [x] 2.2 冲突 → 该项 FAIL、总结论 FAIL、退出码 1；detail 点名分支与工作树数量
- [x] 2.3 无冲突 → PASS，detail 给出工作树数量
- [x] 2.4 无法判定 → PASS 但 detail 明写「无法判定…未据此判违规」，绿色不静默
- [x] 2.5 preflight 侧不读 `worktreeCollisionSeverity`（开工检查只回答事实，不做分级）
- [x] 2.6 docstring「五项」→「六项」

## Phase 3 · 规则文本

- [x] 3.1 `PROTOCOL §14.6` 新增「两个接入点」表（concurrent guard / preflight）与分工说明
- [x] 3.2 `PROTOCOL §14.6` 写明「查不到」的口径（PASS + 披露，不判违规）
- [x] 3.3 修正编号乱序：14.5 门禁分层 → **14.6 G11** → **14.7 综合风险评级**
- [x] 3.4 代码注释与用例里的章节引用同步为 §14.6

## Phase 4 · 缺口台账

- [x] 4.1 N28 待做 ⑤（接 preflight）标记完成
- [x] 4.2 N28 `status: closed`，写明残留限制是「事后检出而非事前阻止」而非待修项
- [x] 4.3 N28 的 `where` 补入 `governance.py:preflight` 与新用例文件

## Phase 5 · 测试与门禁

- [x] 5.1 9 条 preflight 用例：接线 / 顺序 / 阻断 / 不挤歪既有项 / 无误报 / 不可判定 / git 缺失
- [x] 5.2 全套 pytest 与干净基线两侧同环境对照，FAILED 集合一致
- [x] 5.3 `ruff format --check .` / `ruff check .`
- [x] 5.4 `openspec validate wire-g11-into-preflight --strict`

## Phase 6 · 收口

- [x] 6.1 结果报告四段 + 状态行 + `acceptance_commands` 原样出现
- [x] 6.2 ACK 由 CLI 生成、任务状态经 CLI 变更
- [x] 6.3 提交带 pathspec；开 PR；登记合入提交；归档

## 明确不在本 change 范围

- **不改既有五项的判定逻辑**：只追加，不动前五项任何一行。
- **不给 preflight 加分级/降级开关**：开工检查只有 PASS/FAIL。
- **不阻止 `-B` 执行本身**：git 没有能拦住工作树操作的前置钩子，仍是事后检出。
- **不改 `concurrent guard` 的行为**：对它的唯一改动是检测函数的异常加固。

## 偏离与理由

**1. 顺带修了上一轮留下的编号乱序**

上一轮把 G11 小节插在「综合风险评级」之前，结果文件里出现 `§14.7` 在 `§14.6` 之前。
这次按语义重排为 14.5 门禁分层 → **14.6 G11** → **14.7 综合风险评级**（先分层、再逐项细节、
最后聚合评级，读起来才顺）。代价是要同步改三处引用：`governance.py` 的 detail 文案、
用例里的断言、N28 的 `where`。改了并复跑验证。这属于修自己上一轮的手误，不是扩大范围。

**2. 「无法判定」判 PASS 而不是 FAIL**

可以争论该 fail-closed（拿不到结论就不放行）。选 PASS 的理由：这类失败只发生在
「非 git 目录」或「git 不在 PATH」，而前者本来就没有工作树、后者的风险面在别的项上
（`HEAD 治理登记` 同样依赖 git，会一起红）。判 FAIL 会让「在一个纯壳目录里跑 preflight」
永远红，而那种场景下该项根本没意义。

但 PASS 不等于静默——detail 强制写「无法判定（原因），未据此判违规」，
`test_non_git_workspace_is_unavailable_not_violation` 守这句话必须在。

**3. 上一轮的结果报告不改**

`RESULT-WORKTREE-COLLISION-GUARD-001.md` 的风险 1 写着「已写进 N28 待做 ⑤（接 preflight）」。
那句话在它交付时是准确的，本 change 完成后才过期。不改写历史交付物，
由本 change 的结果报告 + N28 的 `closed` 状态承担闭环说明。

## 证据

### E1 · preflight 六项实测（本仓）

```
$ python3 -m ai_collab.cli governance preflight
[FAIL] 必读清单声明: .ai_collab_session.json 缺失或为空，无法核验必读清单
[FAIL] 状态机时效: 状态文件缺失或无 last_updated
[FAIL] 门禁输入完整性: 未装备，缺: ['expectedBranch', 'baselineCommit', 'watchPaths']
[PASS] HEAD 治理登记: 边界后合并提交 4 个，未登记 0 个
[FAIL] 显式 ACK 证据: 无显式 ACK
[PASS] 工作树分支冲突: 8 个工作树，无重复分支
preflight: FAIL
```

前五项口径未变（这次是在未装备的 worktree 里跑的，故 4 红 1 绿），第六项是新增的。

### E2 · 新增用例

```
$ python3 -m pytest tests/unit/test_preflight_worktree_gate.py -q
9 passed, 2 warnings in 1.49s
```

覆盖：六项且末位是新项 / 既有五项顺序不变 / 冲突使该项与总结论同 FAIL /
detail 点名分支与工作树数 / **冲突只让第六项变红（其余逐项结论相同）** /
干净仓库给工作树数 / detached 不算冲突 / 非 git 目录判无法判定不判违规 /
git 缺失时抛 `OSError` 也不崩。

### E3 · 相关模块回归

```
$ python3 -m pytest tests/unit/test_governance_ledger.py tests/unit/test_governance_gaps.py \
                     tests/unit/test_preflight_worktree_gate.py \
                     tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py \
                     tests/unit/test_worktree_collision_guard.py -q
116 passed, 2 warnings in 18.25s
```

既有按名称查字典的断言（`test_preflight_fails_when_guard_not_equipped` 等）无需改动即通过——
这是「追加在末位」的直接收益。

### E4 · 静态门禁与 OpenSpec

```
$ ruff format --check .   → 331 files already formatted
$ ruff check .            → All checks passed!
$ openspec validate wire-g11-into-preflight --strict
Change 'wire-g11-into-preflight' is valid
```

### E5 · 全套回归（两侧同环境，`PYTHONPATH=/tmp/noshim:$PYTHONPATH`）

基线 = 真实 clone 对齐到 `28e6362`（`git status` 0 条）；当前 = 本分支工作树。

```
基线:   50 failed, 3130 passed, 8 skipped, 3 warnings in 45.35s
当前:   50 failed, 3139 passed, 8 skipped, 3 warnings in 48.75s
净增 = 3139 - 3130 = 9（= 新增用例数）

$ diff fail-base3.txt fail-cur3.txt   → 无输出
$ cmp  fail-base3.txt fail-cur3.txt   → byte-identical
```

### E6 · 缺口台账

```
$ python3 -c "...Counter(g['status'] ...)"
总数 28 {'closed': 24, 'wontfix': 1, 'open': 3}
open 的: ['N25', 'N26', 'N27']
```

N28 已从 open 转入 closed（`closed_at = 2026-11-16`），残留限制写进 `fix` 末尾：
「事后检出而非事前阻止」是 git 的能力边界，不构成待修项。
