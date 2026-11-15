# Change Proposal: Wire G11 Into Preflight

## Why

G11（工作树分支冲突）上一轮已落成 `concurrent guard` 的检测项，但**只在显式跑那条命令时生效**。
这留了一个明摆着的口子：**从不跑 `concurrent guard` 的人，守卫对他完全无效。**

而 `governance preflight` 是协议里规定的**开工检查**——每个会话开始就该跑一次。把 G11 挂到这里，
才真正做到「开工即拦」：它和其他检查项在同一条命令里，无法被单独跳过。

上一轮把这件事明确划出范围（`add-worktree-collision-guard` 的 Non-goals 写了「preflight 固定五项，
加第六项会改变输出契约并牵动既有断言，属独立变更」）。这次就是那次独立变更。

## What Changes

| 位置 | 改动 |
|------|------|
| `ai_collab/governance.py:preflight` | 追加第六项「工作树分支冲突」；docstring 五项 → 六项 |
| `ai_collab/concurrent_guard.py:detect_worktree_branch_collisions` | 加固：`git` 不可用时 `OSError` 不再逃逸，返回 `error` 交由调用方定口径 |
| `PROTOCOL §14.6` | 新增「两个接入点」表（`concurrent guard` 显式跑 / `preflight` 开工即拦）与「查不到」的口径 |
| `PROTOCOL` 编号 | 修正上一轮把 G11 插在「综合风险评级」之前的乱序：14.5 门禁分层 → **14.6 G11** → **14.7 综合风险评级** |
| `known_gaps.json` N28 | 待做 ⑤（接 preflight）已完成 → `status: closed` |

### 三个必须交代的设计决定

**1. 新项追加在末位，不插队。**
既有五项的顺序与名称是报告文案的既有契约（`[PASS] 必读清单声明` 等见于多处用例与文档）。
新项放末尾，把「顺序会不会被挤歪」变成可断言的事实——`test_collision_does_not_disturb_other_checks`
逐项比对无冲突 / 有冲突两次的结论，除第六项外必须完全相同。

**2. 「查不到」判 PASS，但 detail 必须披露。**
`git worktree list` 失败的场景有两类：非 git 目录、`git` 不在 PATH。
两者都**不能判违规**（查不到 ≠ 有冲突），但也不能静默给绿。所以：

```
[PASS] 工作树分支冲突: 无法判定（fatal: not a git repository ...），未据此判违规
```

detail 里明写「无法判定」与「未据此判违规」，让这个 PASS 是可解释的而不是沉默的。
另外 `detect_worktree_branch_collisions()` 现在捕获 `OSError`——接进 preflight 后它会在更多
环境里跑，若 `git` 不在 PATH 时抛 `FileNotFoundError`，「开工检查」自己就先崩了。

**3. preflight 侧不读 `worktreeCollisionSeverity`。**
`concurrent guard` 那边有分级（可降为 warning），preflight 没有。理由：开工检查只回答
「有没有冲突」这个事实问题，不做分级判断——分级是并发门禁的语义，不是开工检查的。
两个接入点分工不同，不要让一个的旋钮悄悄影响另一个。

## Non-goals（明确划界）

- **不改既有五项的判定逻辑。** 只追加，不动前五项任何一行判定。
- **不给 preflight 加分级/降级开关。** 开工检查只有 PASS/FAIL。
- **不阻止 `-B` 执行本身。** git 没有能拦住工作树操作的前置钩子，这仍是事后检出。
  守卫的价值在于该状态不会自愈，下一次 preflight 必然抓到。
- **不改 `concurrent guard` 的任一行为。** 本 change 对它的唯一改动是检测函数的异常加固，
  正常路径行为不变。

## Impact

- `governance preflight` 的输出从五项变六项。CLI 打印是通用循环，无需改动；
  按名称查字典的既有用例（`test_governance_ledger.py`、`test_governance_gaps.py`）不受影响。
- 有冲突时 preflight 直接 FAIL（退出码 `1`），不再需要额外跑 `concurrent guard` 才发现。
- 本仓当前 8 个工作树各在不同分支或 detached，该项实测 `8 个工作树，无重复分支`。
