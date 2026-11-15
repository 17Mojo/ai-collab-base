# RESULT — TASK-PREFLIGHT-WORKTREE-GATE-001 · G11 接入开工检查

- **状态**: completed
- 日期：2026-11-16 · change_id：`wire-g11-into-preflight`
- 执行者：`claude_code`（AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/tmp/wt-g11`（分支 `feat/preflight-worktree-gate-2026-11-16`，基线 `origin/main @ 28e6362`）
- 范围：把上一轮明确划出范围的「G11 接进 `governance preflight`」做完，并关掉 N28

> **口径声明**：这次改动**只追加，不改既有判定**。preflight 从五项变六项，
> 前五项的通过与否只由各自原本的依据决定——这一点由逐项对比用例守住，不靠承诺。
> 残留限制照实写：`-B` 一旦执行，状态失真就已经发生；守卫是**事后检出**，不是事前阻止。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate wire-g11-into-preflight --strict
python3 -m pytest tests/unit/test_preflight_worktree_gate.py -q
python3 -m ai_collab.cli governance preflight
python3 -m pytest tests/unit/test_governance_ledger.py tests/unit/test_governance_gaps.py -q
ruff format --check .
ruff check .
```

同一工作区内的附加命令：

```
PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider          # 当前侧全量
cd /tmp/realclone && git checkout 28e6362 && PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider
diff /tmp/fail-base3.txt /tmp/fail-cur3.txt && cmp /tmp/fail-base3.txt /tmp/fail-cur3.txt
```

## 验证结果

### 1 · 为什么必须接 preflight

上一轮 G11 只挂在 `concurrent guard` 上，留了一个明摆的口子：**从不跑那条命令的人，
守卫对他完全无效。** 而 `governance preflight` 是协议规定的开工检查，每个会话开始就该跑一次。
挂到这里才真正做到「开工即拦」——它和其他项在同一条命令里，无法被单独跳过。

### 2 · 三个设计决定

**① 新项追加在末位，不插队。**
既有五项的名称与顺序是输出契约的组成部分（`[PASS] 必读清单声明` 这类文案散见于多处用例与文档）。
追加而非插入，让「顺序会不会被挤歪」变成可断言的事实：

```
$ python3 -m pytest tests/unit/test_preflight_worktree_gate.py -q
9 passed, 2 warnings in 1.49s
```

其中 `test_collision_does_not_disturb_other_checks` 在同一工作区先后以「无冲突」与
「有冲突」两种状态跑 preflight，断言除第六项外**每一项的结论完全相同**。
这是本次最要紧的一条用例：它证明新门禁只影响自己。

**② 「查不到」判 PASS，但 detail 必须披露。**
`git worktree list` 失败有两类场景：非 git 目录、`git` 不在 PATH。
两者都不能判违规（查不到 ≠ 有冲突），但也不能静默给绿：

```
[PASS] 工作树分支冲突: 无法判定（fatal: not a git repository ...），未据此判违规
```

`test_non_git_workspace_is_unavailable_not_violation` 守这两句必须在。

**③ preflight 侧不读 `worktreeCollisionSeverity`。**
`concurrent guard` 那边有分级（可降为 warning），preflight 没有。开工检查只回答
「有没有冲突」这个事实问题；分级是并发门禁的语义。让一个接入点的旋钮悄悄改变另一个的判定，
会让「preflight 过了」这句话的含义变得不可预期。

### 3 · 检测函数加固：不能让「开工检查」自己先崩

接进 preflight 后，`detect_worktree_branch_collisions()` 会在远多于以前的环境里被调用。
原来 `_run_git` 在 `git` 不在 PATH 时会抛 `FileNotFoundError`，一路逃到调用方——
那意味着开工检查自己崩掉，比检出失败更糟。已捕获 `OSError` 并返回 `error`：

```python
try:
    result = _run_git(workspace, ["worktree", "list", "--porcelain"])
except OSError as exc:
    return {"collisions": [], "worktree_count": 0, "severity": "none",
            "error": f"git 不可用: {exc}"}
```

`test_git_missing_is_unavailable_and_does_not_raise` 用 monkeypatch 让 `_run_git` 抛
`FileNotFoundError`，断言不抛异常且 `error` 含「git 不可用」。

### 4 · 六项实测

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

这是在一个「还没装备会话状态」的 worktree 里跑的，所以 4 红 1 绿是预期的。
关键是第六项按事实给出了 8 个工作树、无重复分支。

### 5 · 既有用例无需改动即通过

```
$ python3 -m pytest tests/unit/test_governance_ledger.py tests/unit/test_governance_gaps.py \
                     tests/unit/test_preflight_worktree_gate.py \
                     tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py \
                     tests/unit/test_worktree_collision_guard.py -q
116 passed, 2 warnings in 18.25s
```

既有 preflight 用例都按**名称查字典**（`checks["门禁输入完整性"]`）而不是按下标或项数，
所以追加一项不破坏它们。CLI 打印也是通用循环，无需改动——这是「追加在末位」的直接收益，
也说明当初把这次改动作成独立变更是对的：真正要动的只有 `preflight()` 尾部 20 行与文档。

### 6 · 测试结论（全套回归，两侧同环境）

基线 = 真实 clone 对齐到 `28e6362`（`git status` 0 条）；当前 = 本分支工作树。

| 侧 | 结果 |
| --- | --- |
| 基线 | `50 failed, 3130 passed, 8 skipped, 3 warnings in 45.35s` |
| 当前 | `50 failed, 3139 passed, 8 skipped, 3 warnings in 48.75s` |
| 净增通过 | `9`（= 新增用例数） |
| `diff` / `cmp` FAILED 集合 | **无输出 / byte-identical** |

### 7 · 顺带修正：上一轮留下的编号乱序

上一轮把 G11 小节插在「综合风险评级」之前，文件里出现 `§14.7` 在 `§14.6` 之前。
本次按语义重排为 14.5 门禁分层 → **14.6 G11** → **14.7 综合风险评级**
（先分层、再逐项细节、最后聚合评级）。同步改了三处引用：`governance.py` 的 detail 文案、
用例断言、N28 的 `where`。

### 8 · 缺口台账

```
总数 28 {'closed': 24, 'wontfix': 1, 'open': 3}
open 的: ['N25', 'N26', 'N27']
```

**N28 已关闭**（`closed_at = 2026-11-16`）。它的待做 ⑤（接 preflight）已完成，
`where` 补入了 `governance.py:preflight` 与新用例文件。

关掉它的依据：N28 登记的缺陷是「没有检测、operator 一个 `-B` 就中」。
现在两个接入点都生效，且 `preflight` 是每次开工必经。残留的「事后检出而非事前阻止」
是 git 的能力边界（没有能拦住工作树操作的前置钩子），不构成待修项——写进 `fix` 末尾，
留给下一个读这条的人。

## 风险

1. **preflight 的输出从五项变六项，是可见的行为变更。**
   CLI 打印与按名称查字典的用例不受影响，但**人读的文档与会话习惯**会受影响：
   如果有笔记或流程写着「五项全绿」，需要更新口径。已核对现役文档：
   仅 `TASK-CLOSE-GOV-GAPS-001.md` 与 `RESULT-CLOSE-GOV-GAPS-001.md` 提到「五项」，
   二者都是历史交付记录，不改写；PROTOCOL 不按项数描述 preflight。

2. **「无法判定」判 PASS 是个可争论的取舍。**
   fail-closed 的做法是拿不到结论就不放行。选 PASS 的理由：这类失败只发生在
   「非 git 目录」或「git 不在 PATH」，前者本来就没有工作树、后者的风险面在别的项上
   （`HEAD 治理登记` 同样依赖 git，会一起红）。但 PASS 有代价——detail 必须写清
   「未据此判违规」才不算静默，这句话现在由用例守着，改动它会红。

3. **检测仍是事后的。**
   `-B` 一旦执行，主工作区的 HEAD 就已经被动前移、`status` 已经失真。守卫的价值在于
   该状态**不会自愈**，下一次 preflight 必然抓到。要真正做到事前阻止，需要 git 层面的
   钩子（不存在）或把切分支的入口收进脚本，属另一个方向。

4. **preflight 侧不读降级开关，是有意的不对称。**
   `concurrent guard` 可以降到 warning，preflight 不行。若有人期望「降级后 preflight 也放行」，
   会得到相反结果。这个不对称写在 PROTOCOL §14.6 的接入点表里，并有用例
   （`test_collision_blocks` / 规格 Scenario「并发门禁被降级时开工检查仍拦」）固定下来。

5. **本 change 的合入同样会被覆盖率门禁拦下。**
   生效边界 `4d04acd` 之后每个 merge commit 都要先 `declare-commit`。顺序：
   `merge → declare-commit → 提交登记表 → 复跑 → archive`。

## 回滚

- **preflight**：删除 `checks.append({"name": "工作树分支冲突", ...})` 那一段与延迟导入，
  回到五项。回退后 `concurrent guard` 侧的 G11 不受影响（它是独立检测项）。
- **检测加固**：`detect_worktree_branch_collisions` 的 `try/except OSError` 去掉即可，
  行为回到「git 缺失时抛异常」——但那会让 preflight 在 git 缺失时崩，不建议单独回退这一段。
- **规则文本**：`PROTOCOL §14.6` 的「两个接入点」表与「查不到」的口径可独立删除；
  编号重排（14.6/14.7 互换）也可以单独回退，但那会恢复上一轮的乱序。
- **N28**：按约定只改 `status` 不删；回退时置回 `open` 并说明原因，保留已完成的结论。
- **整体**：`git revert <本 change 的提交>`。新增用例与 change 工件随之删除。
- **上一轮结果报告**：本 change **没有**改动
  `RESULT-WORKTREE-COLLISION-GUARD-001.md`。它的风险 1 写着「已写进 N28 待做 ⑤」，
  在它交付时是准确的；闭环说明由本报告与 N28 的 `closed` 状态承担。
