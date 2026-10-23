# RESULT-P1-CLI-EXITCODE-2026-10-23：让模块入口的进程退出码如实反映 main() 返回值

- **状态**: completed
- **任务 ID**: TASK-P1-CLI-EXITCODE-001
- **change_id**: bugfix/no-spec
- **角色**: AGENT_EXEC（codearts_agent）
- **复核方**: AGENT_TEST（claude_code）
- **完成时间**: 2026-10-23T15:20+08:00

## 执行命令

```bash
# 1. 任务状态翻为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-P1-CLI-EXITCODE-001 --ai codearts_agent --status implementing

# 2. 契约验收命令（全部实跑，输出见下节）
python3 -m pytest tests/unit/test_cli_entrypoint_exit_code.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/

# 3. 手工真机验收（两个入口各跑一次）
python3 -m ai_collab.cli pack trending --days 0; echo "退出码=$?"
python3 -m ai_collab pack trending --days 0; echo "退出码=$?"

# 4. 返回值语义不变性机检（改动前后须完全一致）
grep -c 'return 0$' ai_collab/cli/_cli_main.py   # 78
grep -c 'return 1$' ai_collab/cli/_cli_main.py   # 97
grep -c 'return 2$' ai_collab/cli/_cli_main.py   # 8
```

### 实现摘要

本次改动**只做入口传播**（把 `main()` 的返回值交给进程），**不改任何命令的返回值语义**。

| 契约 | 落点 | 改动 |
|---|---|---|
| R1 | `ai_collab/cli/__main__.py:20-21` | 末尾 `main()` → `sys.exit(main())`。该文件**原本已有 `import sys`**（第 8 行），无需补 import |
| R2 | `ai_collab/__main__.py:8,13-14` | 末尾 `main()` → `sys.exit(main())`；新增 `import sys` |
| R3 | `tests/unit/test_cli_entrypoint_exit_code.py`（新建，77 行 / 7 条用例） | 全部走 `subprocess` 真实子进程，**没有一条直接调用 `main()`** |
| R4 | `ai_collab/cli/_cli_main.py` | **零改动**（见验证结果的三项计数） |
| R5 | — | 只动了允许清单内的 2 个入口 + 1 个新建测试 + 本结果文件 |

最终 diff（`git diff ai_collab/cli/__main__.py ai_collab/__main__.py`）：

```diff
--- a/ai_collab/__main__.py
+++ b/ai_collab/__main__.py
@@ -5,7 +5,9 @@ AI Collab CLI 入口脚本
 用法: python3 -m ai_collab.cli [命令] [选项]
 """
 
+import sys
+
 from ai_collab.cli import main
 
 if __name__ == "__main__":
-    main()
+    sys.exit(main())
--- a/ai_collab/cli/__main__.py
+++ b/ai_collab/cli/__main__.py
@@ -17,4 +17,4 @@ if project_root not in sys.path:
 from ai_collab.cli._cli_main import main
 
 if __name__ == "__main__":
-    main()
+    sys.exit(main())
```

## 验证结果

### 1. 验收命令全绿

| 命令 | 结果 |
|---|---|
| `python3 -m pytest tests/unit/test_cli_entrypoint_exit_code.py -q` | `7 passed in 0.81s` |
| `python3 -m pytest tests/ -q` | `2897 passed, 6 skipped in 39.24s`（0 failed；6 skipped 全部是环境依赖型：`test_database_indexes.py` 缺 backend db、`test_studio_integration.py` 5 条需 127.0.0.1:8000 在线） |
| `python3 -m ruff check ai_collab/` | `All checks passed!`（**无新增问题**） |
| `python3 -m ruff check tests/unit/test_cli_entrypoint_exit_code.py` | `All checks passed!` |

### 2. 手工真机验收（真实输出，未剪辑）

```console
$ python3 -m ai_collab.cli pack trending --days 0; echo "退出码=$?"
============================================================
Prompt Pack 管理系统
============================================================
错误: --days 必须为正整数（收到 0）
退出码=1

$ python3 -m ai_collab pack trending --days 0; echo "退出码=$?"
============================================================
Prompt Pack 管理系统
============================================================
错误: --days 必须为正整数（收到 0）
退出码=1
```

两个入口退出码均为 **1**（契约只要求非 0，实测值满足）。

### 3. 7 条进程级用例的实测退出码

| # | 命令 | 契约期望 | 实测 | 断言 |
|---|---|---|---|---|
| 1 | `pack trending --days 0` | 非 0；stdout 含「必须为正整数」；stderr 无 Traceback | `rc=1`，stdout 含该文案，stderr 空 | ✅ |
| 2 | `pack trending --days -1` | 非 0 | `rc=1`，stderr 空 | ✅ |
| 3 | `pack trending --days 7 --limit 0` | 0 | `rc=0` | ✅ |
| 4 | `pack trending --limit 0` | 0 | `rc=0` | ✅ |
| 5 | `pack trending --days 0`（`module="ai_collab"`） | 非 0 | `rc=1`，stdout 含该文案，stderr 空 | ✅ |
| 6 | `ack --task-id none --status ok`（`-w <tmp_path>`） | 0 且 stdout 含 ACK 行 | `rc=0`，stdout `O.ACK|task=none\|status=ok\|result=none` | ✅ |
| 7 | `ack`（缺 `--task-id`） | 非 0 | `rc=2`（argparse `the following arguments are required: --task-id`） | ✅ |

### 4. 返回值语义未变（R4 机检）

`_cli_main.py` 三类 return 的行数**改动前后完全一致**：

```console
$ grep -c 'return 0$' ai_collab/cli/_cli_main.py   # 78  （基线 78）
$ grep -c 'return 1$' ai_collab/cli/_cli_main.py   # 97  （基线 97）
$ grep -c 'return 2$' ai_collab/cli/_cli_main.py   # 8   （基线 8）
```

**没有为了让任何用例通过而改动过任何 `return 0/1/2`。**

### 5. 改动范围核对（R5）

`git status --short` 中属于本工单的改动：

```
 M ai_collab/__main__.py                  ← 允许
 M ai_collab/cli/__main__.py              ← 允许
?? tests/unit/test_cli_entrypoint_exit_code.py  ← 允许（新建）
?? collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md ← 本结果文件
```

禁止清单中的文件（`_cli_main.py`、`ai_collab/cli/__init__.py`、`pyproject.toml`、
`ai_collab/intervention_queue.py`、`ai_collab/ack_protocol.py`、
`scripts/agent_dispatch_bridge.py`）**全部零改动**。
工作区另有 6 个 `collaboration/monitoring/*_latest.md` 的修改，是**并行协作进程**
产生的报告刷新，不属于本工单，未被本工单触碰。

**既有测试零改动**：`tests/` 下除新建文件外，无任何既有测试文件被修改
（`git status` 未列出任何既有测试文件）。

### 6. 影响面（语义价值）

改动前 `python3 -m ai_collab.cli ...` 的退出码恒为 0，导致：

1. **ACK 协议命令失败无法判定** —— `cmd_ack` 的错误路径（缺 `--task-id`、
   任务不存在且无法推断 assignee）返回 1，但进程仍退出 0，ACK 生成失败在
   shell / 看门狗 / CI 眼里是**成功**。现在这类失败退出码为 1（缺参数时 argparse 为 2）。
2. **`ack-remediation` 的健康判定失效** —— 该命令按 `error_count` 返回 0/1，
   现在可以用退出码判断健康与否。
3. **`--days 0` 这类友好报错无法用退出码拦截** —— 脚本里的 `cmd && next_step`
   现在会在校验失败后正确短路。

### 测试结论

| 契约条款 | 结论 | 证据 |
|---|---|---|
| R1 `ai_collab/cli/__main__.py` | ✅ 通过 | 末尾 `sys.exit(main())`；`import sys` 原本已存在（第 8 行），未新增 import |
| R2 `ai_collab/__main__.py` | ✅ 通过 | 末尾 `sys.exit(main())` + 新增 `import sys` |
| R3 进程级测试 | ✅ 通过 | `tests/unit/test_cli_entrypoint_exit_code.py` 7 条用例，**全部走 `subprocess` 真实子进程**，无一条直接调用 `main()` |
| R4 返回值语义不变 | ✅ 通过 | `_cli_main.py` 的 `return 0/1/2` 计数 = **78 / 97 / 8**，与改动前**完全一致** |
| R5 范围限制 | ✅ 通过 | 只改 `ai_collab/cli/__main__.py`、`ai_collab/__main__.py` + 新建测试 + 本结果文件；禁止清单文件零改动；既有测试零改动 |
| R6 文档与口径 | ✅ 通过 | 头部状态行 `- **状态**: completed` 在第 3 行（40 行内）；四段齐备；计数对比与回滚方式已写明 |

**整体结论：契约 R1–R6 全部满足，验收命令全绿，无回归。**

## 风险

1. **退出码从「恒 0」变为「有语义」，可能影响依赖旧行为的老脚本**：
   仓库内已核实 **CI 不依赖该 CLI 的退出码**（`.github/workflows/` 里没有任何
   workflow 调用它，只有 ruff / mypy / pytest / bandit）；仓库内
   `python3 -m ai_collab.cli` 的用法都是**提示文案里的命令串**
   （`ai_collab/dispatch_trigger.py`、`ai_collab/session_health.py`、
   `ai_collab/ack_watchdog.py` 等），不依赖退出码。但**外部**若有
   `python3 -m ai_collab.cli ... || true` 之外的静默假设（如 `if cmd; then`）
   会开始看到新的分支走向 —— 这正是本工单的目标，但属于行为变更，需知会。
2. **`ai_collab/hooks/` 下 4 个 hook 入口未改（也不需要改）**：
   `stop_check.py`、`session_inject.py`、`spawn_agent_preflight.py`、`pre_compact.py`
   的 `main()` 签名都是 `-> None`（**无返回值语义**），其中 `stop_check.py` 用
   `sys.exit(0)` / `sys.exit(2)` 直接控制退出码。对 `-> None` 的函数写
   `sys.exit(main())` 反而会把 `None` 传给 `sys.exit`（打印 `None` 并以 1 退出），
   **属于有害改动**。它们不在本工单允许清单内，故**未改**，此处仅作知会。
3. **未发现其它「丢掉退出码」的模块入口**：`ai_collab/cli/_cli_main.py:5609`
   （直接跑 `_cli_main.py`）与 `pyproject.toml` 的 console script
   `ai_collab.cli:main`（setuptools 生成 `sys.exit(main())`）**原本就正确**，
   本次无需改动，也未改动。
4. **`ack --task-id none` 是否写工作区** —— 实测 `cmd_ack` 的 `task_id == "none"`
   分支在 `print` 后**直接 `return 0`**，**不写任何状态文件**。测试仍按契约用
   `-w <tmp_path>` 隔离（`-w` 需置于子命令之前，实测生效），属双保险。

## 回滚

两个文件各改一行，`git checkout --` 即可整体回滚：

```bash
git checkout -- ai_collab/cli/__main__.py ai_collab/__main__.py
rm -f tests/unit/test_cli_entrypoint_exit_code.py   # 新建文件，非跟踪文件
```

回滚后退出码将恢复为「恒 0」的旧行为（即本工单修复前的缺陷状态）。
回滚**不需要**触碰 `_cli_main.py`（本工单未改动它），也不影响任何既有测试。
