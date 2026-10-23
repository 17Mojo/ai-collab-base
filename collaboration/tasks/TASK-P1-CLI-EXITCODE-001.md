---
task_id: TASK-P1-CLI-EXITCODE-001
change_id: bugfix/no-spec
status: planning
priority: P1
assignee: codearts_agent
assignee_role: AGENT_EXEC
reviewer: claude_code
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-23T13:05:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_cli_entrypoint_exit_code.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/"
result_file: collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md
---

# TASK-P1-CLI-EXITCODE-001：让模块入口的进程退出码如实反映命令结果

> **本工单由 Claude Code（AGENT_ARCH）定义契约，CodeArts（AGENT_EXEC）实现。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
> 复核方：Claude Code（AGENT_TEST）。
>
> **本轮放开 `ai_collab/cli/__main__.py` 与 `ai_collab/__main__.py` 给 CodeArts 独占修改。**
> 这两个文件**上一轮是禁改清单里的**（`ai_collab/cli/` 下「其他文件」），因为上一轮
> 的实现范围只涉及 `_cli_main.py` 的 trending 分支。本轮工单范围**只含这两个入口
> 文件**，不含 `_cli_main.py`。

## 一、背景与真证

上一轮工单 `TASK-P1-TRENDING-CLI-001` 交付的 `--days` 校验，实现在**函数级**是
对的（`_handle_store_command` 返回 1，不抛栈）。但复核时做**真机**验证，发现
**进程级退出码丢了**：

```console
$ python3 -m ai_collab.cli pack trending --days 0
============================================================
Prompt Pack 管理系统
============================================================
错误: --days 必须为正整数（收到 0）
$ echo $?
0            ← 契约 R2 要求「非零退出码」
```

### 根因：两个模块入口都没有把 `main()` 的返回值交给进程

| 入口 | 文件 | 现状 | 退出码 |
|---|---|---|---|
| `python3 -m ai_collab.cli` | `ai_collab/cli/__main__.py` | `main()` —— **无 `sys.exit`** | 恒为 **0** |
| `python3 -m ai_collab` | `ai_collab/__main__.py` | `main()` —— **无 `sys.exit`** | 恒为 **0** |
| `ai-collab`（console script） | `pyproject.toml` → `ai_collab.cli:main` | setuptools 生成 `sys.exit(main())` | **正确** |
| 直接跑 `_cli_main.py` | `ai_collab/cli/_cli_main.py:5609` | `sys.exit(main())` | **正确** |

**同一个 CLI 有两个入口行为不一致**：装出来的 `ai-collab` 命令退出码正确，
文档里到处写的 `python3 -m ai_collab.cli ...` 退出码恒为 0。

### 影响面（复核方已逐条核实）

1. **ACK 协议命令的失败无法判定**：`cmd_ack` 的错误路径返回 1（缺 `--task-id`、
   任务不存在且无法推断 assignee），但走 `python3 -m ai_collab.cli ack ...` 时
   进程仍退出 0 —— ACK 生成失败在 shell / 看门狗 / CI 眼里是**成功**。
2. **`ack-remediation` 的健康判定失效**：该命令按 `error_count` 返回 0/1，
   现在无法用退出码判断健康与否。
3. **`--days 0` 这类友好报错无法用退出码拦截**：脚本里 `cmd && next_step`
   会在校验失败后继续往下走。

### 已核实的边界（不需要你再查）

- **CI 不依赖该 CLI 的退出码**：`.github/workflows/` 里没有任何 workflow 调用它
  （只有 ruff / mypy / pytest / bandit）。
- **仓库内 `python3 -m ai_collab.cli` 的用法都是提示文案里的命令串**
  （`ai_collab/dispatch_trigger.py`、`ai_collab/session_health.py`、
  `ai_collab/ack_watchdog.py` 等），不依赖退出码。
- 因此本改动的**风险面很小**，但语义价值高：让 CLI 第一次真正「shell 化」。

## 二、目标

1. 两个模块入口的**进程退出码 == `main()` 的返回值**；
2. **不改变任何命令的返回值语义**（只传播，不改判）；
3. 由**进程级**测试锁住（测函数返回值不算数 —— 上一轮的漏网之处正在于此）。

## 三、详细契约（逐条实现，不要自行发挥）

### R1 `ai_collab/cli/__main__.py`

把末尾改成：

```python
if __name__ == "__main__":
    sys.exit(main())
```

需要补 `import sys`（该文件目前没有 `import sys`）。

### R2 `ai_collab/__main__.py`

同样改成：

```python
if __name__ == "__main__":
    sys.exit(main())
```

该文件目前有 `from ai_collab.cli import main`，需补 `import sys`。

### R3 测试（新建 `tests/unit/test_cli_entrypoint_exit_code.py`）

**必须用 `subprocess` 跑真实进程**。直接 `main()` 调用**测不到**本工单的缺陷，
那样的测试等于没写。

建议的 helper（可调整，但必须是子进程）：

```python
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, module: str = "ai_collab.cli", workspace: str | None = None):
    cmd = [sys.executable, "-m", module]
    if workspace:
        cmd += ["-w", workspace]
    cmd += list(args)
    return subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )
```

**必测用例（至少 7 条）**：

| # | 命令 | 断言 |
|---|---|---|
| 1 | `pack trending --days 0` | `returncode != 0`；stdout 含「必须为正整数」；**stderr 不含 `Traceback`** |
| 2 | `pack trending --days -1` | `returncode != 0` |
| 3 | `pack trending --days 7 --limit 0` | `returncode == 0`（成功路径不受影响） |
| 4 | `pack trending --limit 0` | `returncode == 0` |
| 5 | `pack trending --days 0`（**走 `ai_collab` 入口**，`module="ai_collab"`） | `returncode != 0`（两个入口都要覆盖） |
| 6 | `ack --task-id none --status ok` | `returncode == 0` 且 stdout 含 ACK 行（确认 ACK 协议命令的成功路径没被改坏） |
| 7 | `ack`（缺 `--task-id`） | `returncode != 0`（argparse 自身报 2，命令行确实有 `--task-id` 必填） |

**用例 6 的隔离要求**：`ack` 会读写 ACK 桥接状态，测试**必须**用
`tmp_path` 作为工作区传入（`-w <tmp_path>`），不得污染真实工作区。
若实测发现 `ack --task-id none` 仍会写工作区文件，改用 `tmp_path` 兜底，
并在结果文件里说明。

### R4 不得改任何命令的返回值语义

**只允许把 `main()` 的返回值传给 `sys.exit`，禁止改动返回值本身。**

可机检的不变量 —— `ai_collab/cli/_cli_main.py` 里这三类 return 的**行数**必须
与改动前**完全一致**：

```console
$ grep -c 'return 0$' ai_collab/cli/_cli_main.py   # 改动前后都是 78
$ grep -c 'return 1$' ai_collab/cli/_cli_main.py   # 改动前后都是 97
$ grep -c 'return 2$' ai_collab/cli/_cli_main.py   # 改动前后都是 8
```

**禁止**为了让某个用例通过而把 `return 1` 改成 `return 0`（或反之）。
若你判断某个命令的返回值本身就不对：**不要改** —— 在结果文件「风险」段写明
你的判断与理由，由复核方决定。

### R5 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---|---|
| `ai_collab/cli/__main__.py` | `ai_collab/cli/_cli_main.py`（**任何一行**都不许改） |
| `ai_collab/__main__.py` | `ai_collab/cli/__init__.py` |
| `tests/unit/test_cli_entrypoint_exit_code.py`（**新建**） | `pyproject.toml`（console script 入口已正确，不许动） |
| `collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md` | `ai_collab/intervention_queue.py`、`ai_collab/ack_protocol.py`、`scripts/agent_dispatch_bridge.py`（Claude Code 2026-10-23 刚修的派单链路） |

**既有测试零改动**：既有测试文件**一行都不许改**。若某条既有用例因新语义必须
修改：**逐条在结果文件里说明改了什么、为什么**，**不得**静默删改断言。

### R6 文档与口径

- 结果文件**头部**必须有一行可机读的状态（**前 40 行内**）：

  ```markdown
  - **状态**: completed
  ```

  **为什么**：终态一致性审计（`ai_collab/result_consistency_audit.py`）靠头部的
  状态行核对「任务状态」与「结果文件声明的状态」是否一致，解析不到就报
  `unparseable_result_header`。上一轮交付漏了这一行被审计判为不可解析
  （当时由复核方补上），本轮**必须自己写**。

- 结果文件必须写清：
  - 本次改的是**入口传播**，不是命令语义；
  - 改动前后 `_cli_main.py` 的 return 计数对比（78 / 97 / 8）；
  - 影响面：ACK 失败此前无法用退出码判定、现在可以；
  - **回滚**方式（两个文件各改一行，`git checkout --` 即可）；
  - 若你发现还有别的入口也丢退出码（如某个 `scripts/*.py` 里的 `main()` 调用），
    **不要改** —— 写进结果文件「风险」段，由复核方决定。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_cli_entrypoint_exit_code.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check ai_collab/` 无**新增**问题
- [ ] **手工**（必须实跑并把真实输出贴进结果文件）：

  ```console
  $ python3 -m ai_collab.cli pack trending --days 0; echo "退出码=$?"
  错误: --days 必须为正整数（收到 0）
  退出码=1
  ```

  > 注意：退出码**具体是多少**由 `main()` 的返回值决定，契约只要求**非 0**。
  > 实测值可能是 1；只要非 0 即通过。

- [ ] `grep -c 'return [012]$' ai_collab/cli/_cli_main.py` 的三个计数与 78 / 97 / 8 一致
- [ ] `git diff --name-only` **不含** R5 禁止清单里的任何文件
- [ ] 结果文件含「执行命令 / 验证结果 / 风险 / 回滚」四段
      （缺任一段，`tasks validate-contract` 会判失败）

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**（手写 ACK 会被回执桥接判为「非显式 ACK」而拒绝收口）：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-CLI-EXITCODE-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md
```

把该命令**原样输出**的一行回复回来（形如
`A.ACK|task=TASK-P1-CLI-EXITCODE-001|status=ok|result=collaboration/results/RESULT-P1-CLI-EXITCODE-2026-10-23.md`）。

## 六、参考

- 待修文件：`ai_collab/cli/__main__.py`、`ai_collab/__main__.py`
- 只读参照：`ai_collab/cli/_cli_main.py:5609`（`_cli_main.py` 里已有的正确写法）
- 上一轮交付与复审：`collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
