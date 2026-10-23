---
task_id: TASK-P1-TRENDING-CLI-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: codearts_agent
assignee_role: AGENT_EXEC
reviewer: claude_code
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-23T12:50:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_cli_pack_trending.py -q"
  - "python3 -m pytest tests/unit/test_pack_store.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/"
result_file: collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md
---

# TASK-P1-TRENDING-CLI-001：把「热门 Pack」的时间窗口接到 CLI

> **本工单由 Claude Code（AGENT_ARCH）定义契约，CodeArts（AGENT_EXEC）实现。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
> 复核方：Claude Code（AGENT_TEST）。
>
> **本轮与上一轮的归属变化（重要）**：上一轮禁改 `ai_collab/cli/`，是因为
> Claude Code 当时正在同一工作区并行改 `ai_collab/cli/_cli_main.py`。
> **本轮 Claude Code 不再改该文件**（已于 2026-10-23 12:20 提交并停手），
> 所以 `ai_collab/cli/_cli_main.py` 的 pack trending 段**由 CodeArts 独占修改**。
> 详见 R6。

## 一、背景与真证

上一轮工单 `TASK-P1-PROMPT-TRENDING-001` 已让 `get_trending_packs(days, limit)`
**真正按时间窗口**算热度（已复审通过，提交 `a80e183`）。但 **CLI 这一层还没跟上**：

```python
# ai_collab/cli/_cli_main.py:4277-4282
elif args.store_subcommand == "trending":
    packs = search_engine.get_trending_packs(days=7, limit=args.limit)
    print("\n热门 Pack (7天内):")
    for idx, pack in enumerate(packs, 1):
        print(f"  {idx}. {pack.name} (v{pack.version})")
        print(f"     {pack.rating:.1f}★ | {pack.downloads} 下载")
```

三处还停留在旧世界：

| # | 现状 | 为什么是问题 |
|---|---|---|
| B1 | `days=7` **硬编码** | 窗口能力做出来了，用户却改不了 —— 能力等于没交付 |
| B2 | 标题硬编码 `热门 Pack (7天内)` | 一旦窗口可配，标题还写「7天内」= **又一次口不符**（上一轮刚修掉的那类缺陷） |
| B3 | 每行打印 `{pack.downloads} 下载` | `downloads` 是**历史累计**下载数，不是窗口内下载次数。榜单按窗口排序、数字却是累计，读者会误读成「这 7 天下载了 N 次」 |

另外 store 层已经规定 `days <= 0` 抛 `ValueError`（`TASK-P1-PROMPT-TRENDING-001` 的 R4），
**CLI 层必须先拦一道**：不能把一个 `ValueError` 栈直接甩给用户。

## 二、目标

1. `pack trending` 支持 `--days`（默认 7），窗口真正可配；
2. `--days <= 0` 在 CLI 层被**友好拦下**（非零退出码 + 一行中文错误），不抛栈；
3. 标题与输出**如实反映**实际窗口与数字口径；
4. 全部行为由 CLI 层测试锁住。

## 三、详细契约（逐条实现，不要自行发挥）

### R1 新增 `--days` 参数

**文件**：`ai_collab/cli/_cli_main.py`（`trending_parser` 定义处，约 5458 行）

```python
trending_parser = pack_subparsers.add_parser("trending", help="热门 Pack")
trending_parser.add_argument("--limit", type=int, default=10, help="数量限制")
trending_parser.add_argument(
    "--days",
    type=int,
    default=7,
    help="统计窗口天数：按最近 N 天内的下载次数排序",
)
```

- `--days` 默认 **7**（保持既有行为不变）。
- `--limit` 保持 `type=int, default=10` **不变**。

### R2 CLI 层正数校验（不得抛栈）

**位置**：`ai_collab/cli/_cli_main.py` 的 `store_subcommand == "trending"` 分支，
**调用 `get_trending_packs` 之前**。

- `args.days <= 0` 时：
  - 打印**一行**错误，形如 `错误: --days 必须为正整数（收到 0）`；
  - `return 1`（**非零退出码**）；
  - **不得**让 `ValueError` 冒到用户面前（不得出现 traceback）。
- `args.limit <= 0`：**保持既有语义** —— store 层返回 `[]`，CLI 打印空榜单、
  退出码 **0**。**不要**把 limit 也改成报错（上一轮 R4 已锁定 `limit<=0 → []`）。

### R3 标题与口径必须如实

- 标题改为 `print(f"\n热门 Pack ({args.days}天内):")` —— 数字取实际 `--days`，
  **不得**再写死 7。
- 每行的下载数改为**累计口径**的标注：`{pack.rating:.1f}★ | 累计 {pack.downloads} 下载`。
  - 「累计」二字是**必须**的：窗口化之后这个数字是历史累计下载数，
    不标注就会让读者误读成窗口内下载次数。
- **不要**在 CLI 里自己算窗口内下载次数：窗口边界逻辑在 store 层（R4 已实现闭区间
  `[now - days, now]`），在 CLI 里复制一份必然随时间漂移。

### R4 days 必须透传给 store

```python
packs = search_engine.get_trending_packs(days=args.days, limit=args.limit)
```

- **不得**改 store 层语义（`ai_collab/prompt_pack/store.py` 已被复审锁定，见 R6）。

### R5 CLI 层测试（新建 `tests/unit/test_cli_pack_trending.py`）

**测试调用约定**（`_handle_store_command` 自己 `create_pack_store`，所以要替换工厂）：

```python
import sys
from types import SimpleNamespace

import ai_collab.cli as cli


def _run_trending(monkeypatch, capsys, *, days, limit=10, packs=None):
    """调用 CLI 的 pack trending 分支，返回 (退出码, stdout)。"""
    import ai_collab.prompt_pack.store as store_mod

    captured = {}

    class FakeEngine:
        def get_trending_packs(self, days=7, limit=10):
            captured["days"] = days
            captured["limit"] = limit
            return list(packs or [])

    monkeypatch.setattr(store_mod, "create_pack_store", lambda *a, **k: FakeEngine())

    args = SimpleNamespace(store_subcommand="trending", days=days, limit=limit)
    code = cli._handle_store_command(args, "packs")
    return code, capsys.readouterr().out, captured
```

> `create_pack_store` 是在 `_handle_store_command` **函数体内** import 的，
> 所以 `monkeypatch.setattr(store_mod, "create_pack_store", ...)` 生效。

**必测用例（至少 6 条）**：

1. 默认 `days=7` 透传给 store（断言 `captured["days"] == 7`）；
2. `--days 1` / `--days 30` 透传正确（参数化）；
3. `--days 0` → 退出码 **1** + stdout 含「必须为正整数」；**且** `captured` 里
   **没有** `days` 键（证明校验发生在调用 store **之前**，没白跑一次查询）；
4. `--days -1` → 同上；
5. `--limit 0` → 退出码 **0**，输出为空榜单（不报错）；
6. 标题里的天数与实际 `--days` 一致（stdout 含 `30天内` 之类）；
7. 每行含「累计」标注。

**附加要求**：测试**不得**依赖工作区真实数据 —— 一律用 `FakeEngine` 假引擎。

### R6 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---|---|
| `ai_collab/cli/_cli_main.py` —— **仅** pack trending 相关的两处：`trending_parser` 参数定义 + `store_subcommand == "trending"` 分支 | `ai_collab/prompt_pack/store.py`（上一轮已复审锁定） |
| `tests/unit/test_cli_pack_trending.py`（**新建**） | `ai_collab/prompt_pack/rating.py` |
| `collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md` | `ai_collab/intervention_queue.py`、`ai_collab/ack_protocol.py`、`scripts/agent_dispatch_bridge.py`（Claude Code 2026-10-23 刚修的派单链路） |
| | `ai_collab/cli/` 下**其他**文件、`ai_collab/cli/__init__.py` |

**为什么这轮放开 `ai_collab/cli/`**：上一轮禁它是**临时**的（防两个 Agent 同改一个文件）。
本轮 Claude Code 在 `_cli_main.py` 上的改动已提交（`5dda8c4`）并停手，
不存在并行编辑。**共享工作区纪律仍适用**：只 add 自己改的文件。

**既有测试零改动**：`tests/unit/test_pack_store.py` 与
`tests/unit/test_dispatch_intervention_wiring.py` 等既有文件**一行都不许改**。
若某条既有用例因新语义必须修改：**逐条在结果文件里说明改了什么、为什么**，
**不得**静默删改断言。

### R7 文档与口径

- 结果文件**头部**必须有一行可机读的状态（**前 40 行内**）：

  ```markdown
  - **状态**: completed
  ```

  **为什么**：终态一致性审计（`ai_collab/result_consistency_audit.py`）靠头部
  的状态行核对「任务状态」与「结果文件声明的状态」是否一致，解析不到就报
  `unparseable_result_header`。上一轮交付就漏了这一行，被审计判为不可解析
  （已由复核方补上）。本轮**必须自己写**，不要等人来补。

- 结果文件必须写清：`--days` 的语义（闭区间窗口 `[now - days, now]`）、
  「累计下载」的含义、以及**降级路径**（窗口内无任何下载事件时退回按累计下载排序，
  这是上一轮有意为之，不是 bug）。
- 若你认为 CLI 还需要别的口径调整，**先不要做** —— 在结果文件的「风险」段写明
  你的判断与理由，由复核方决定。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_cli_pack_trending.py -q` 全绿
- [ ] `python3 -m pytest tests/unit/test_pack_store.py -q` 全绿（既有 30 用例零改动）
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check ai_collab/` 无**新增**问题
- [ ] 结果文件 `collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md` 存在，
      且含「执行命令 / 验证结果 / 风险 / 回滚」四段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] `git diff --name-only` **不含** R6 禁止清单里的任何文件
- [ ] 既有测试若被改动，改动理由**逐条**写进结果文件

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**（手写 ACK 会被回执桥接判为「非显式 ACK」而拒绝收口）：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-TRENDING-CLI-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md
```

把该命令**原样输出**的一行回复回来（形如
`A.ACK|task=TASK-P1-TRENDING-CLI-001|status=ok|result=collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md`）。

## 六、参考

- 实现文件：`ai_collab/cli/_cli_main.py`（`_handle_store_command` 的 trending 分支 + `trending_parser`）
- 上一轮已锁定的 store 层语义：`ai_collab/prompt_pack/store.py`（**只读**）
- 上一轮交付与复审结论：`collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
