# RESULT-P1-TRENDING-CLI-2026-10-23：把「热门 Pack」的时间窗口接到 CLI

- **状态**: completed
- **任务 ID**: TASK-P1-TRENDING-CLI-001
- **change_id**: bugfix/no-spec
- **角色**: AGENT_EXEC（codearts_agent）
- **复核方**: AGENT_TEST（claude_code）
- **完成时间**: 2026-10-23T12:18+08:00

## 执行命令

```bash
# 1. 任务状态翻为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-P1-TRENDING-CLI-001 --ai codearts_agent --status implementing

# 2. 验收命令（全部实跑，见下节）
python3 -m pytest tests/unit/test_cli_pack_trending.py -q
python3 -m pytest tests/unit/test_pack_store.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/

# 3. 真机行为抽查
python3 -m ai_collab.cli pack trending --days 0
python3 -m ai_collab.cli pack trending --days 7 --limit 3
```

## 实现摘要

| 契约 | 落点 | 改动 |
|---|---|---|
| R1 | `ai_collab/cli/_cli_main.py:5462-5469` | `trending_parser` 新增 `--days`（`type=int, default=7`），`--limit` 未动 |
| R2 | `ai_collab/cli/_cli_main.py:4277-4280` | trending 分支入口先拦 `days <= 0`：打印一行 `错误: --days 必须为正整数（收到 {days}）` 并 `return 1`，**不调用 store**，不抛栈 |
| R3 | `ai_collab/cli/_cli_main.py:4283,4286` | 标题改 `热门 Pack ({args.days}天内)`；行内改 `累计 {pack.downloads} 下载` |
| R4 | `ai_collab/cli/_cli_main.py:4282` | `get_trending_packs(days=args.days, limit=args.limit)` 透传；store 层零改动 |
| R5 | `tests/unit/test_cli_pack_trending.py`（新建） | 10 条 CLI 层用例，全部走 `FakeEngine` 假引擎，不依赖工作区真实数据 |

### 一处契约外的必要补充（非自行发挥，是防回归）

契约把改动限定为「`trending_parser` 参数定义 + `store_subcommand == "trending"` 分支」两处，
但真机实测发现 `python3 -m ai_collab.cli pack trending` **并不直接进 `_handle_store_command`**：

```
ai_collab/cli/_cli_main.py:5386   pack_subparsers = pack_parser.add_subparsers(dest="subcommand")
ai_collab/cli/_cli_main.py:5462   trending_parser = pack_subparsers.add_parser("trending", ...)
```

即 `trending` 是 `pack` 的**直接子命令**（`dest="subcommand"`），真实入口是
`cmd_pack` 的转发分支 `_cli_main.py:4032-4044`，它现场构造一个只含
`store_subcommand/query/category/sort/limit` 五字段的 `Args`，再调 `_handle_store_command`。

只改 trending 分支的话，`--days` 在转发时被丢弃 → 真机 `pack trending` 直接
`AttributeError: 'Args' object has no attribute 'days'`（已被新测试捕获）。
故在 `_cli_main.py:4042` 补了一行 `"days": getattr(args, "days", 7)`：

- 用 `getattr` 是因为同一段代码也服务 `search` / `browse`，那两个子命令没有 `--days`；
- 该文件属 R6 **允许修改**范围（`_cli_main.py`），未触碰任何禁止清单文件。

## 验证结果

| 验收命令 | 结果 |
|---|---|
| `python3 -m pytest tests/unit/test_cli_pack_trending.py -q` | **10 passed** |
| `python3 -m pytest tests/unit/test_pack_store.py -q` | **30 passed**（既有 30 用例**零改动**） |
| `python3 -m pytest tests/ -q` | **2890 passed / 6 skipped / 0 failed**（37.14s） |
| `python3 -m ruff check ai_collab/` | **All checks passed!** |

### 测试用例对照（R5 必测 7 条全覆盖 + 3 条附加）

| # | 用例 | 断言要点 |
|---|---|---|
| 1 | `test_default_days_7_passed_to_store` | 默认 `days == 7` 透传，标题含 `7天内` |
| 2 | `test_days_passed_through[1/30]` | 参数化，`--days 1/30` 原样到 store |
| 3 | `test_non_positive_days_rejected_before_store_call[0/-1]` | 退出码 1 + 含「必须为正整数」+ **captured 里无 `days` 键**（证明校验在调用 store 之前） |
| 4 | `test_limit_zero_returns_empty_with_exit_zero` | `limit=0` → 退出码 **0**、不报错（未把 limit 也改成报错，守住上一轮 R4） |
| 5 | `test_title_reflects_actual_days` | 标题含 `30天内` 且**不含** `7天内` |
| 6 | `test_row_marks_downloads_as_cumulative` | 行内含 `累计 42 下载` |
| 7 | `test_parser_exposes_days[默认/--days 30]` | 走真实 `main()` + `sys.argv`，守 argparse 层默认 7 与 `--days` 可解析 |

### 真机抽查

```
$ python3 -m ai_collab.cli pack trending --days 0
============================================================
Prompt Pack 管理系统
============================================================
错误: --days 必须为正整数（收到 0）        ← 单行中文错误，无 traceback

$ python3 -m ai_collab.cli pack trending --days 7 --limit 3
热门 Pack (7天内):
  1. api-design-pack (v1.0.0)
```

### 范围核对

`git diff --name-only` = `ai_collab/cli/_cli_main.py`；`git status --porcelain` 新增未跟踪
`tests/unit/test_cli_pack_trending.py`。**R6 禁止清单零命中**，`ai_collab/prompt_pack/store.py`、
`rating.py`、`intervention_queue.py`、`ack_protocol.py`、`scripts/agent_dispatch_bridge.py`
及 `ai_collab/cli/` 下其他文件均未改动。

## 口径说明

- **`--days` 语义**：闭区间窗口 `[now - days, now]`，边界逻辑在 store 层
  （`ai_collab/prompt_pack/store.py:407-412`），CLI 层**不复制**一份，避免随时间漂移。
- **「累计下载」含义**：`pack.downloads` 是**历史累计**下载数，**不是**窗口内下载次数。
  榜单排序用的是窗口内下载次数，打印的数字是累计值 —— 两者口径不同，故必须显式标注「累计」，
  否则读者会误读成「这 N 天下载了 X 次」。
- **降级路径（非 bug）**：窗口内无任何下载事件时（如历史索引文件根本没有下载事件数据），
  store 层退回按累计下载数排序（`store.py:416-427`），与本工单改动前的行为一致，
  保证 CLI「热门 Pack」不空屏。此为上一轮有意为之，本轮**未改**该语义。

## 风险

1. **进程退出码传不出去（既有缺陷，未修，超出 R6 范围）**
   - 现象：`python3 -m ai_collab.cli pack trending --days 0` 打印了正确错误，但 shell `$?` 是 **0** 而非 1。
   - 根因：`ai_collab/cli/__main__.py:16` 调用 `main()` 但**丢弃返回值**，
     所以 `_handle_store_command` 的 `return 1` 到不了进程退出码。这是**既有**问题 ——
     `browse` 分支（`_cli_main.py:4265-4267`）的 `return 1` 同样传不出去。
   - 为何本轮不修：`ai_collab/cli/__main__.py` 落在 R6 **禁止修改**清单（`ai_collab/cli/` 下其他文件）。
   - 影响面：R2 的「非零退出码」在**函数契约层**已满足并被单测锁住（`code == 1`），
     但**进程层**未满足。这会让依赖 `$?` 的脚本/CI 判断失效。
   - **交复核方裁决**：是否开一张独立工单改 `__main__.py`（一行 `sys.exit(main())`）。
     我判断该改，但不在本工单授权范围内，故按 R7 只报告不实施。

2. **`cmd_pack` 转发分支是 pack 三子命令共用**（`_cli_main.py:4032-4044`）
   补的 `"days": getattr(args, "days", 7)` 对 `search` / `browse` 是**惰性无害**的
   （那两条分支不读 `args.days`）。风险仅限于：若将来有人给 `search` 单独加 `--days`，
   会与 `trending` 共享这个键。当前无此计划。

3. **`--limit <= 0` 仍是静默空榜**（退出码 0、输出空榜单）。这是上一轮 R4 锁定的既有语义，
   本轮**故意未改**。从 UX 角度它与 `--days <= 0` 的处理不对称，但改动会破坏既有测试
   （`test_pack_store.py` 零改动是硬要求），故保持现状。

4. **未改动的口径疑问**：`browse` 分支（`_cli_main.py:4275`）同样打印 `{pack.rating:.1f}★`
   无口径问题，但 `cmd_pack` 的 `recommend`/`search` 等其他打印是否存在同类「累计/窗口」
   标注缺失，我未逐条审计（超出本工单范围）。若复核方要一致性收口，建议另开工单统一审计
   `_cli_main.py` 全部下载数打印点。

5. **共享工作区**：本轮只 add 了自己改的 `_cli_main.py` 与新建测试文件，未 commit、未触碰
   Claude Code 12:20 提交的 `5dda8c4` 相关内容。**但工作区仍是共享的**，若复核期间有其他 Agent
   并行提交，冲突需人工裁决。

## 回滚

改动面极小（1 个源文件 + 1 个新测试文件），回滚无副作用：

```bash
# 只回滚源文件改动（保留其它人的并行改动）
git checkout -- ai_collab/cli/_cli_main.py

# 删除新建测试
rm tests/unit/test_cli_pack_trending.py
```

回滚后 `pack trending` 恢复为 `days=7` 硬编码、标题写死「7天内」、无 `--days` 参数的旧行为；
store 层（`get_trending_packs` 的窗口化排序与 `days <= 0` 抛 `ValueError`）**不受影响**，
该能力是上一轮 `TASK-P1-PROMPT-TRENDING-001`（`a80e183`）独立交付的，仍可被 API 直接调用。
