# RESULT-P1-CONCURRENT-GUARD-2026-10-24：并发工作区守护 —— CLI 门禁接入（OpenSpec Phase 2.2）

- **状态**: completed
- **任务 ID**: TASK-P1-CONCURRENT-GUARD-001
- **change_id**: add-concurrent-workspace-guard
- **角色**: AGENT_EXEC（claude_code）
- **复核方**: AGENT_TEST（codearts_agent，待复核）
- **完成时间**: 2026-10-24T13:40+08:00
- **基线 commit**: `577c90a`（分支 `feat/codearts-collab-wiring`）

## 执行命令

```bash
# 1. 守护用例（含既有 23 条 + 新增 13 条）
python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py -q

# 2. 全量回归
python3 -m pytest tests/ -q

# 3. lint
python3 -m ruff check .

# 4. CLI 验收（放行 / 阻断两种形态）
python3 -m ai_collab.cli concurrent guard --workspace .
python3 -m ai_collab.cli concurrent guard --workspace . --expected-branch main
```

## 验证结果

### 1. 新增 CLI 的实际调用样例与退出码

| 命令 | 关键输出 | 退出码 |
|---|---|---|
| `concurrent guard --workspace .` | `allowed: True` / `risk_level: low` / `branch: feat/codearts-collab-wiring (expected: none)` | **0** |
| `concurrent guard --workspace . --expected-branch main` | `allowed: False` / `risk_level: high` / `violation: branch drift: expected=main actual=feat/codearts-collab-wiring` | **2** |
| `concurrent guard --workspace . --expected-branch main --force-workspace` | `allowed: True`（`risk_level` 仍为 `high`，反映评估结论本身） | **0** |
| `concurrent guard`（不带动作） | 打印提示「请指定并发门禁动作」 | 0 |

完整输出样例（阻断形态）：

```text
============================================================
AI 协作系统 - 并发工作区门禁
============================================================

工作区: /Users/raymondna/Documents/AI-collab/ai-collab-base

[并发门禁]
  allowed: False
  risk_level: high
  branch: feat/codearts-collab-wiring (expected: main)  <- drift
  baseline: none (skipped)
  foreign: 0 files (severity: none)
  report: .../logs/workspace_forensics/concurrent_guard_latest.json
  history: .../logs/workspace_forensics/concurrent_guard_history.jsonl
  violation: branch drift: expected=main actual=feat/codearts-collab-wiring

门禁阻断：请先消除分支漂移或基线过期，或在确认风险后使用 --force-workspace 显式覆盖。
```

### 2. 契约逐条核对（R1–R9）

| 契约 | 要求 | 实测 | 结论 |
|---|---|---|---|
| R1 | `_run_concurrent_guard_gate`（keyword-only、返回 bool） | 落在 `_run_spawn_agent_guard_gate` 之后，输出 `[并发门禁]` 段 | ✅ |
| R2 | 子命令 `concurrent guard` + 5 个参数 + 退出码 0/2 | 二级子命令已注册；`--watch-path` 为 `action="append"`；退出码实测 0 / 2 | ✅（见 §3 的 `--workspace` 位置偏离说明） |
| R3 | 软警告不得升级为阻断 | `foreign` 只进 `warnings`；阻断只来自 `violations`；新增用例 `test_foreign_changes_are_warning_not_blocking` 钉住 | ✅ |
| R4 | 报告落盘沿用 `guard_config` 的 report/history | 未另建落盘路径，直接打印 `report_file` / `history_file` | ✅ |
| R5 | 配置落 `.vscode/ai-collab.json`，`expectedBranch` 默认 `null`，不改 `agent-orchestration.json` | 已加 `concurrentGuard` 顶层段；`config/agent-orchestration.json` 与其 schema/template **零改动** | ✅ |
| R6 | 新建 `tests/unit/test_concurrent_guard_cli.py` | 新建，13 条用例 | ✅ |
| R7 | openspec 勾选与实际对齐 + 2.2.3 注记 | 2.1.x / 2.2.x / 3.x 共 16 条已勾；2.2.3 附偏离注记；Phase 4 三条**保持未勾** | ✅ |
| R8 | 范围限制 | 改动文件仅 4 个 + 本结果文件，见 §5 | ✅ |
| R9 | 偏离必须写进风险段 | 见「风险」段第 1、2 条 | ✅ |

### 3. 新增 13 条守护用例覆盖

| 组 | 用例 | 钉住的行为 |
|---|---|---|
| 参数解析 | `test_watch_path_repeatable_and_branch_parsed` | `concurrent guard` 二级子命令可达；`--watch-path` 收成列表 |
| 参数解析 | `test_missing_action_prints_hint_without_crashing` | 缺动作不崩，给提示 |
| 退出码 | `test_branch_drift_blocks_with_exit_code_2` | drift → 2 |
| 退出码 | `test_clean_repo_exits_zero` | 干净 → 0 |
| 退出码 | `test_force_workspace_overrides_drift` | `--force-workspace` → 0 |
| 分级 | `test_foreign_changes_are_warning_not_blocking` | G3 只进 `warnings`，`violations` 为空，`allowed=True`，退出码 0 |
| 分级 | `test_drift_is_blocking_violation` | G1 进 `violations`，`risk_level=high`，退出码 2 |
| 分级 | `test_require_baseline_without_baseline_is_warning_only` | `requireBaselineCommit` 缺基线时只软警告，不阻断 |
| 配置接线 | `test_config_supplies_expected_branch_when_cli_absent` | 无 CLI 参数时取配置 `expectedBranch` |
| 配置接线 | `test_cli_argument_overrides_config` | CLI 覆盖配置 |
| 配置接线 | `test_config_can_disable_guard` | `enabled=false` 放行 |
| 落盘 | `test_report_and_history_written_into_workspace` | latest.json 可解析、history.jsonl 追加 1 行 |
| 落盘 | `test_report_path_from_config_is_honoured` | 落盘路径可由配置覆盖 |

### 4. 验收命令实测输出

| 命令 | 结果 |
|---|---|
| `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py -q` | `36 passed in 9.33s`（既有 23 + 新增 13） |
| `python3 -m pytest tests/ -q` | `2995 passed, 6 skipped in 44.69s`（0 failed；基线 2982 → +13） |
| `python3 -m ruff check .` | `All checks passed!` |
| `python3 -m ai_collab.cli concurrent guard --workspace .` | 输出 `[并发门禁]` 段，退出码 0 |

### 5. 改动文件（对照 R8 禁止清单）

| 文件 | 性质 |
|---|---|
| `ai_collab/cli/_cli_main.py` | 新增 import、`_run_concurrent_guard_gate`、`cmd_concurrent_guard`、子命令注册、分发分支 |
| `.vscode/ai-collab.json` | **仅**新增顶层 `concurrentGuard` 段，既有键零改动 |
| `tests/unit/test_concurrent_guard_cli.py` | 新建（13 条） |
| `openspec/changes/add-concurrent-workspace-guard/tasks.md` | 仅改勾选状态 + 2.2.3 注记 |
| `collaboration/results/RESULT-P1-CONCURRENT-GUARD-2026-10-24.md` | 本文件 |

**零改动**：`ai_collab/concurrent_guard.py`、`config/agent-orchestration.json` 及其
schema/template、`ai_collab/` 下其他文件、`collaboration/tasks/` 下任何已有工单、
`memory/`、`docs/CONCURRENT_GUARD_DESIGN.md`、`openspec/.../proposal.md`。

## 测试结论

- **新增用例**：13 条，全绿。
- **既有守护用例**：23 条，**零回归**（合并运行 36 passed）。
- **全仓回归**：`2995 passed, 6 skipped`，**0 failed**；6 条 skip 全部是
  `test_studio_integration.py` 的「本地 8000 端口后端未启动」，与本次改动无关
  （改动前基线同为 6 skipped）。
- **lint**：`ruff check .` → `All checks passed!`，零新增。
- **CLI 行为**：退出码契约（0/2）、门禁分层（drift 阻断 / foreign 不阻断）、
  报告落盘三项均有守护用例，非人工断言。

**结论**：Phase 2.2 全部验收标准通过。

## 风险

1. **偏离 1（已按契约 R9 披露）**：`--workspace` 的位置。
   契约 R2 与设计文档 4.2 写的调用形态是 `concurrent guard --workspace .`（子命令**之后**），
   但仓库里 `--workspace` 是**全局**选项（`parser.add_argument("-w", "--workspace")`，
   `_cli_main.py:4848`），子命令之后传会报 `unrecognized arguments`。
   **处置**：给 `concurrent guard` 子命令单独注册一个 `--workspace`，用
   `default=argparse.SUPPRESS`——显式传入时覆盖全局值，不传时**不写回**、
   全局值不丢。实测三种形态都通：`cli concurrent guard --workspace .`、
   `cli --workspace . concurrent guard`、`cli concurrent guard`（默认当前目录）。
   > 副作用记录：这是本仓第一个支持「子命令之后传 `--workspace`」的子命令。
   > 其它子命令（如 `workspace-guard`）仍是全局位-only，本工单**未**改动它们
   > （R8 范围限制），属相邻问题，见「后续」。

2. **偏离 2（已按契约 R9 披露）**：`requireBaselineCommit` 的语义。
   契约 R2 只写「未传基线时跳过基线判定」，没给 `requireBaselineCommit` 独立语义。
   本实现的处置：配置要求基线但未提供时，CLI **打印一条软警告**
   （`config requires a baseline commit but none was provided (check skipped)`），
   **不阻断**（退出码仍 0）。理由：设计文档 4.5 明确「硬门禁只放 git 真证」，
   「配置缺项」不是 git 真证；把它做成硬门禁会造成假阳性阻断。
   有守护用例 `test_require_baseline_without_baseline_is_warning_only` 钉住。

3. **配置落点与 openspec 原任务描述不一致**：`tasks.md` 2.2.3 原写
   `agent-orchestration.json`，实测运行时配置源是 `.vscode/ai-collab.json`
   （`VSCodeIntegration.get_project_config()` → `ai_collab/integrations/vscode.py:77`）。
   已按运行时事实落地，并在 `tasks.md` 2.2.3 附注记说明理由。
   `config/agent-orchestration.json` 及其 schema/template 零改动。

4. **本工单只提供 CLI 入口**：`allowed` 由 CLI 返回，但**「派单前自动调用」
   尚未接入**——`cmd_run` / `cmd_dispatch` 链路里没有调用 `concurrent guard`。
   按 R9 不扩大范围，此项属未开工能力，**不得**宣称「并发守护已接入派单主流程」。

5. **配置默认 `expectedBranch: null`**：本仓工作分支是 `feat/codearts-collab-wiring`，
   若默认写 `main` 会让每次门禁调用都报 drift 变成噪声。按设计文档
   「`expectedBranch` 默认 None（跳过）」，默认 `null` 时**跳过漂移判定**——
   也就是说默认配置下本门禁**不会**因为分支名不同而阻断。

6. **新增的 `logs/workspace_forensics/concurrent_guard_*.json*` 落盘文件**：
   `logs/` 整体在 `.gitignore:39` 内，不进版本库，也不污染 `git status`。
   但门禁每次运行都会**追加**一行历史，长跑会累积；未做轮转（不在本工单范围）。

## 回滚

```bash
# 1. 代码回滚（本工单 4 个改动文件）
git checkout -- ai_collab/cli/_cli_main.py .vscode/ai-collab.json \
                openspec/changes/add-concurrent-workspace-guard/tasks.md
rm -f tests/unit/test_concurrent_guard_cli.py

# 2. 或按 commit 精确回滚
git revert <TASK-P1-CONCURRENT-GUARD-001 的实现 commit>

# 3. 清理落盘产物（可选，不在版本库内）
rm -f logs/workspace_forensics/concurrent_guard_latest.json \
      logs/workspace_forensics/concurrent_guard_history.jsonl
```

**回滚后状态**：`_cli_main.py` 恢复原状，`concurrent guard` 子命令消失，
openspec 勾选回到本次改动前的状态；`ai_collab/concurrent_guard.py` 核心模块
（本次未动）仍可被直接调用，23 条守护用例不受影响。

## 后续（不在本工单范围）

- `workspace-guard` / `spawn-agent-guard` 等子命令的 `--workspace` 位置不一致
  （只能用全局位），可考虑统一为本文档的 SUPPRESS 写法。
- 「派单前自动调用并发门禁」尚未接入（见风险 4）。
- Phase 4 三条（项目边界）由 `TASK-P2-CONCURRENT-GUARD-PHASE4-001` 承接，
  `tasks.md` 中 Phase 4 保持未勾选。
