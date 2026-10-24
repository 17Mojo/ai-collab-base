---
task_id: TASK-P1-CONCURRENT-GUARD-001
change_id: add-concurrent-workspace-guard
status: planning
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-24T11:05:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 -m ai_collab.cli concurrent guard --workspace ."
result_file: collaboration/results/RESULT-P1-CONCURRENT-GUARD-2026-10-24.md
---

# TASK-P1-CONCURRENT-GUARD-001：并发工作区守护 —— CLI 门禁接入（OpenSpec Phase 2.2）

> **本工单由 Claude Code（AGENT_ARCH）定义契约，Claude Code（AGENT_EXEC）实现，
> CodeArts（AGENT_TEST）复核。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。

## 一、背景：openspec 任务清单已过期，实际进度与清单不一致

OpenSpec 变更 `add-concurrent-workspace-guard` 的 `tasks.md` 里 Phase 2.1 与 Phase 3
全部是未勾选状态，**但这些工作实际上已经完成**。实测结论：

| Phase 2.1 / Phase 3 条目 | 清单状态 | 实测状态 | 证据 |
|---|---|---|---|
| 2.1.1 `inspect_git_context` | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:54` |
| 2.1.2 `detect_branch_drift` | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:105` |
| 2.1.3 `detect_baseline_staleness` | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:122` |
| 2.1.4 `detect_foreign_changes` | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:158` |
| 2.1.5 `assess_concurrent_risk` | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:213` |
| 2.1.6 报告持久化 | 未勾选 | ✅ 已实现 | `ai_collab/concurrent_guard.py:299`（`run_concurrent_guard`） |
| 3.1–3.6 共 23 条守护用例 | 未勾选 | ✅ 全绿 | `python3 -m pytest tests/unit/test_concurrent_guard.py -q` → **23 passed** |
| 3.7 ruff + 全量回归 | 未勾选 | ✅ ruff 全绿 | `ruff check ai_collab/concurrent_guard.py tests/unit/test_concurrent_guard.py` → All checks passed |
| **2.2.1 `_run_concurrent_guard_gate`** | 未勾选 | ❌ **缺失** | `grep -n "concurrent" ai_collab/cli/_cli_main.py` → 无任何命中 |
| **2.2.2 CLI 子命令 `concurrent guard`** | 未勾选 | ❌ **缺失** | 同上 |
| **2.2.3 配置项接入** | 未勾选 | ❌ **缺失** | `.vscode/ai-collab.json` 无 `concurrentGuard` 段 |

`ai_collab/concurrent_guard.py` 已可直接调用，实测：

```bash
$ python3 -c "from ai_collab.concurrent_guard import run_concurrent_guard; ..."
risk_level= high allowed= False
violations= ['branch drift: expected=main actual=feat/codearts-collab-wiring']
```

**结论：核心检测能力与守护测试已就绪，唯一缺口是「怎么被调用」——没有 CLI 入口，
这块能力目前无法在派单/门禁流程里生效。** 本工单只补这一层，不重做核心模块。

### 1.1 附带修正：2.2.3 的配置落点写错了

`tasks.md` 2.2.3 写的是「配置项接入 `agent-orchestration.json` 的 `concurrentGuard` 段」。
实测**运行时配置源不是这个文件**：

```python
# ai_collab/cli/_cli_main.py:3440（cmd_workspace_guard）
config = VSCodeIntegration.get_project_config()
```

`VSCodeIntegration.get_project_config()` 读的是 **`.vscode/ai-collab.json`**（见
`ai_collab/integrations/vscode.py`）。佐证：`workspaceGuard`、`spawnAgentGuard` 两段
在 `config/agent-orchestration.json` 与 `.vscode/ai-collab.json` 里**都不存在**，
实际生效的是各 guard 模块内部的内置默认值——`.vscode/ai-collab.json` 里也没有这两段。

因此本工单把 `concurrentGuard` 落在 **`.vscode/ai-collab.json`**（运行时配置源），
**不要**加进 `config/agent-orchestration.json`（那是角色编排配置，语义不同）。
R5 对此有明确要求。

## 二、目标

1. `python3 -m ai_collab.cli concurrent guard` 可用，输出与设计文档 4.2 节一致。
2. 门禁分级严格遵守设计文档 4.5：drift(G1)/stale(G2) 硬门禁，foreign(G3) 软警告。
3. 配置项可通过 `.vscode/ai-collab.json` 的 `concurrentGuard` 段覆盖。
4. 有单测守护 CLI 层（解析、退出码、分级、报告落盘）。
5. `openspec/changes/add-concurrent-workspace-guard/tasks.md` 的勾选状态与**实际**对齐。

## 三、详细契约

### R1 `ai_collab/cli/_cli_main.py`：新增 `_run_concurrent_guard_gate`

放在 `_run_spawn_agent_guard_gate`（`:304`）之后，风格与之对齐（keyword-only 参数、
统一 `print` 段、返回 bool 表示是否放行）：

```python
def _run_concurrent_guard_gate(
    *,
    workspace: str,
    config: dict,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
    watch_paths: list[str] | None = None,
    session_started_at: str | None = None,
    force_workspace: bool = False,
) -> bool:
    """执行并发工作区守护门禁，并输出结论。"""
```

内部调用：

```python
from ..concurrent_guard import run_concurrent_guard
```

`guard_config` 取自 `config.get("concurrentGuard", {})`（当 `config` 是 dict 且该值是
dict 时），并允许 CLI 参数覆盖配置里的同名值。

输出格式对齐设计文档 4.2 节（`[并发门禁]` 段）：

```text
[并发门禁]
  allowed: False
  risk_level: high
  branch: refactor/slimming-2026-09-20 (expected: main)  ← drift
  baseline: 81a02c5 → 672f496 (1 watched path changed)   ← stale
  foreign: 4 files
  report: logs/workspace_forensics/concurrent_guard_latest.json
  history: logs/workspace_forensics/concurrent_guard_history.jsonl
  violation: branch drift: expected=main actual=refactor/slimming-2026-09-20
```

> 具体字段名以 `run_concurrent_guard` 返回的 report 结构为准（`git_context` /
> `signals` / `violations` / `warnings` / `risk_level` / `allowed` /
> `report_file` / `history_file`），不要自造字段。

### R2 CLI 子命令 `concurrent guard`

按设计文档 4.2 节的命令行形态注册（`subparsers.add_parser("concurrent", ...)` +
二级 `add_parser("guard", ...)`，或等价实现）：

```bash
python3 -m ai_collab.cli concurrent guard \
  --workspace . \
  --expected-branch main \
  --baseline-commit 81a02c5 \
  --watch-path ai_collab/pack/schema_v2.py \
  --session-started-at 2026-09-26T05:40:00
```

参数要求：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--workspace` | 否 | 默认当前目录 |
| `--expected-branch` | 否 | 未传时取配置 `expectedBranch`；两者都没有则**不判定漂移**（跳过） |
| `--baseline-commit` | 否 | 未传时取配置 `requireBaselineCommit`/`baselineCommit`；都没有则跳过基线判定 |
| `--watch-path` | 否 | **可重复**（`action="append"`），未传时取配置 `watchPaths` |
| `--session-started-at` | 否 | ISO 时间串，未传时取配置 `sessionStartedAt`；都没有则跳过归属判定 |
| `--force-workspace` | 否 | 强制放行（等价 `run_concurrent_guard(force=True)`） |

**退出码**：`allowed=True` → `0`；`allowed=False` → `2`（与 `cmd_workspace_guard`
的 `return 0 if allowed else 2` 保持一致）。

### R3 门禁分级：不得把软警告升级为阻断

设计文档 4.5 明确：drift(G1) / stale(G2) 是 **git 真证** → 硬门禁；foreign(G3) 是
**mtime 启发式** → 软警告，**不阻断**。

`run_concurrent_guard` 已实现该分层（`foreign_change_severity` 默认 `"warning"`）。
CLI 层**不得**把 `warnings` 里的内容算作阻断理由；阻断只能来自 `violations`。

> `run_concurrent_guard` 里 `enabled=False` 或 `force=True` 时 `allowed` 恒为 True，
> CLI 需保证 `enabled` 从配置读取、`force` 只由 `--force-workspace` 触发。

### R4 报告落盘

`run_concurrent_guard` 已按 `guard_config` 的 `report` / `history` 写
`logs/workspace_forensics/concurrent_guard_latest.json` 与
`concurrent_guard_history.jsonl`。CLI 只需把返回的 `report_file` / `history_file`
打印出来，**不要**另建落盘路径。

### R5 配置项落点

在 `.vscode/ai-collab.json` 顶层新增 `concurrentGuard` 段，键名与设计文档 4.4 节
一致：

```json
"concurrentGuard": {
  "enabled": true,
  "expectedBranch": null,
  "requireBaselineCommit": false,
  "baselineCommit": null,
  "watchPaths": [],
  "sessionStartedAt": null,
  "foreignChangeSeverity": "warning",
  "aheadWarnThreshold": 20,
  "report": "logs/workspace_forensics/concurrent_guard_latest.json",
  "history": "logs/workspace_forensics/concurrent_guard_history.jsonl"
}
```

- `expectedBranch` **默认 `null`**：本仓当前工作分支是
  `feat/codearts-collab-wiring`，若默认写 `"main"` 会让每次门禁调用都报 drift，
  变成噪声。默认 `null` 时跳过漂移判定，与设计文档「`expectedBranch` 默认 None（跳过）」一致。
- **不要**改 `config/agent-orchestration.json` 与 `config/agent-orchestration.schema.json`。
- **不要**改 `.vscode/ai-collab.json` 里已有的任何键。

### R6 新建 `tests/unit/test_concurrent_guard_cli.py`

至少覆盖：

1. **参数解析**：`concurrent guard --expected-branch main --watch-path a --watch-path b`
   能被 argparse 正确解析，`watch-path` 收成列表。
2. **退出码**：构造 drift 场景 → 退出码 `2`；无风险场景 → `0`。
3. **分级**：只有 foreign 变化（G3）时 → **不阻断**（退出码 `0`，但报告里
   `warnings` 非空）；drift（G1）时 → 阻断（退出码 `2`）。
4. **报告落盘**：`logs/workspace_forensics/concurrent_guard_latest.json` 被写出来且
   能解析为 JSON。
5. **既有 23 条用例必须继续通过**：`tests/unit/test_concurrent_guard.py` 不得回归。

> 构造 git 场景建议用 `tmp_path` + `subprocess` 建 mini git repo（既有
> `tests/unit/test_concurrent_guard.py` 的 `TestRegressionSample20260926` 已有现成
> fixture 可参考复用）。

### R7 更新 openspec 任务清单

`openspec/changes/add-concurrent-workspace-guard/tasks.md` 的勾选状态必须与**实际**
对齐：

- 2.1.1–2.1.6、3.1–3.6、3.7 → 勾选（已完成）
- 2.2.1–2.2.3 → 勾选（本工单完成后）
- Phase 4 全部 → **保持未勾选**（属于另一个工单 `TASK-P2-CONCURRENT-GUARD-PHASE4-001`）

同时在 2.2.3 那一行加一句注记，说明配置落点是 `.vscode/ai-collab.json` 而非
`agent-orchestration.json`，并写明理由（运行时配置源是
`VSCodeIntegration.get_project_config()` 读的 `.vscode/ai-collab.json`）。

### R8 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---------|---------|
| `ai_collab/cli/_cli_main.py`（仅新增 gate 函数 + 子命令注册 + 分发） | `ai_collab/concurrent_guard.py`（核心模块已实现且有 23 条用例守护；确需改动须在结果文件「风险」段说明） |
| `.vscode/ai-collab.json`（仅新增 `concurrentGuard` 段） | `config/agent-orchestration.json` 及其 schema/template |
| `tests/unit/test_concurrent_guard_cli.py`（新建） | `ai_collab/` 下其他任何文件 |
| `openspec/changes/add-concurrent-workspace-guard/tasks.md`（仅改勾选状态与 2.2.3 注记） | `openspec/changes/add-concurrent-workspace-guard/proposal.md` |
| `collaboration/results/RESULT-P1-CONCURRENT-GUARD-2026-10-24.md`（新建） | `collaboration/tasks/` 下任何已有工单 |
| | `memory/` 下任何文件（只读镜像） |
| | `logs/` 下任何文件 |
| | `docs/CONCURRENT_GUARD_DESIGN.md`（设计已定稿，除非发现与实现冲突且须在风险段写明） |

### R9 文档与口径

- 结果文件必须写清「新增 CLI 的实际调用样例 + 退出码」。
- 若偏离契约任一条，**必须在结果文件「风险」段写明偏离点与理由**，不要静默改语义。
- **不要**宣称并发守护已接入派单主流程——本工单只提供 CLI 入口，
  「派单前自动调用」是另一个未开工的能力，不得顺手扩大范围。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check .` → `All checks passed!`（**零新增**）
- [ ] `python3 -m ai_collab.cli concurrent guard --workspace .` 能正常输出 `[并发门禁]` 段
- [ ] `git diff --name-only` **不含** R8 禁止清单里的任何文件
- [ ] 结果文件含「执行命令 / 验证结果 / 测试结论 / 风险 / 回滚」各段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] 结果文件头部的 `- **状态**: completed` 在**前 40 行内**

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-CONCURRENT-GUARD-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-CONCURRENT-GUARD-2026-10-24.md
```

把该命令**原样输出**的一行回复回来。

## 六、参考

- OpenSpec 变更：`openspec/changes/add-concurrent-workspace-guard/`（proposal.md / tasks.md）
- 技术设计：`docs/CONCURRENT_GUARD_DESIGN.md`（§4.2 CLI gate、§4.4 配置项、§4.5 门禁分层）
- 核心模块：`ai_collab/concurrent_guard.py`
- 既有守护用例：`tests/unit/test_concurrent_guard.py`（23 条）
- CLI 参考实现：`ai_collab/cli/_cli_main.py` 的 `_run_workspace_guard_gate`（`:242`）、
  `_run_spawn_agent_guard_gate`（`:304`）、`cmd_workspace_guard`（`:3436`）
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
