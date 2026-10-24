# RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24：并发工作区守护 —— Phase 4 项目边界（收集边界守护 + consensus 并发契约 + 跨工作区复用验证）

- **状态**: completed
- **任务 ID**: TASK-P2-CONCURRENT-GUARD-PHASE4-001
- **change_id**: add-concurrent-workspace-guard
- **角色**: AGENT_EXEC（claude_code）
- **复核方**: AGENT_TEST（codearts_agent，待复核）
- **完成时间**: 2026-10-24T14:20+08:00
- **基线 commit**: `4684652`（分支 `feat/codearts-collab-wiring`）

## 执行命令

```bash
# 1. Phase 4 三个新文件 + 既有守护用例
python3 -m pytest tests/unit/test_project_boundary_guard.py \
                    tests/unit/test_consensus_engine_concurrency.py \
                    tests/unit/test_concurrent_guard_reuse.py \
                    tests/unit/test_concurrent_guard.py \
                    tests/unit/test_concurrent_guard_cli.py -q

# 2. 全量回归
python3 -m pytest tests/ -q

# 3. lint
python3 -m ruff check .

# 4. 验收命令（原样执行，工单 acceptance_commands 逐条）
python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_project_boundary_guard.py -q
python3 -m pytest tests/ -q
python3 -m ruff check .
python3 -m pytest tests/unit --collect-only -q

# 5. 边界自查（本仓当前状态）
find . -path ./.git -prune -o -type f \( -name 'test_*.py' -o -name '*_test.py' \) -print | grep -v '^\./tests/' || echo "（tests/ 之外无测试文件）"
```

## 验证结果

### 1. R1 收集边界守护（`tests/unit/test_project_boundary_guard.py`，5 条）

| 用例 | 断言 | 实测 |
|---|---|---|
| `test_testpaths_limited_to_tests` | `pytestconfig.getini("testpaths")` 含 `"tests"` | ✅ `["tests"]` |
| `test_no_collectable_test_files_outside_tests` | `tests/` 之外无 `test_*.py` / `*_test.py` | ✅ 命中集合为空 |
| `test_no_stray_conftest_outside_tests` | `tests/` 之外（仓库根除外）无 `conftest.py` | ✅ 命中集合为空 |
| `test_unit_collection_has_no_error` | `pytest tests/unit --collect-only -q` 退出码 0 且收尾行无 error | ✅ rc=0，`2692 tests collected in 0.54s` |
| `test_this_guard_lives_under_tests` | 守护用例自身位于 `tests/` 之下 | ✅ |

> 收集面用 **pytest 自身解析出的生效值**（`getini`），不是对 `pyproject.toml`
> 做文本匹配——理由见「风险」第 1 条。

### 2. R2 consensus 并发契约（`tests/unit/test_consensus_engine_concurrency.py`，5 条）

| 用例 | 断言 | 实测 |
|---|---|---|
| `test_same_topic_concurrent_requests_share_one_cache_entry` | N=5 并发同 topic → 全部 `mode=="mock"`、`consensus` 一致、`cache` 只有 1 条 | ✅ |
| `test_same_topic_concurrency_may_recompute` | 屏障复现「同 topic 并发会重复计算」→ provider 被调 5 次，`cache` 仍只有 1 条 | ✅ |
| `test_distinct_topics_do_not_cross_contaminate` | 3 个 topic 并发 → 各占 1 条、互不串味 | ✅ |
| `test_repeated_request_hits_cache_without_recomputing` | 二次调用走 cache，provider 只被调 1 次 | ✅ |
| `test_exception_in_one_coroutine_does_not_break_others` | 一路抛 `RuntimeError` 被 `gather(return_exceptions=True)` 收集，其余协程正常完成，引擎后续可继续用 | ✅ |

**并发契约的实测结论**（钉住的当前行为，不是理想行为）：

- 同 topic 并发**会重复计算**——`cache` 是无锁 dict，多个协程可同时 miss；
  幂等性只由 dict 单键赋值保证（**不会写坏字典**），**不保证只算一次**，
  各协程拿到的 `timestamp` 也不保证一致。
- 不同 topic 并发**互不影响**（按键隔离）。
- 命中缓存的重复调用**不再触发 provider**。
- 单个协程异常**不影响其余协程**，引擎不进入半损坏状态。

### 3. R3 并发契约写进 docstring

`ai_collab/engines/consensus_engine.py` 的 `generate_consensus()` 原本只有一行
`"""生成通识内容"""`。现补为写明上述四条契约的 docstring，并显式声明
「本方法**没有**加锁，改并发语义属于另一个工单」。

**只加说明，未改任何并发语义**（`self.cache` 的读写位置、mock/real 分支、
fallback 分支全部逐字未动）。

### 4. R4 跨工作区复用验证（`tests/unit/test_concurrent_guard_reuse.py`，3 条）

**实际 tmp repo 的路径形态**（契约要求写清）：

```text
tmp_path/
└── shared-workspace-sample/          ← 目录名刻意不含 ai_collab 之类字样
    ├── .git/
    ├── README.md
    └── logs/
        └── forensics/
            ├── latest.json            ← 报告落点（tmp repo 内部）
            └── history.jsonl
```

`tmp_path` 形如
`/private/var/folders/8z/t_zl45pj5kx6qjl4z2bdp7km0000gn/T/pytest-of-raymondna/pytest-<N>/test_<name>0/shared-workspace-sample`。

| 用例 | 断言 | 实测 |
|---|---|---|
| `test_guard_runs_on_foreign_workspace` | 报告落在 tmp repo 内（`report_file` 以 tmp 路径开头、`PROJECT_ROOT not in report_file.parents`）；报告内容 `workspace` 指向 tmp repo；**本仓** `logs/workspace_forensics/concurrent_guard_latest.json` 的 mtime **未变** | ✅ |
| `test_guard_detects_drift_on_foreign_workspace` | 在 tmp repo 上切到 `other-branch` → 同样能识别 drift（`allowed=False`、`risk_level=high`） | ✅ |
| `test_same_guard_also_works_on_this_repository` | 同一套守卫在本仓跑 → 报告仍落在本仓 `logs/workspace_forensics/` 下 | ✅ |

**结论自洽性**：三条用例都额外断言「`allowed` ⇔ 无 `violations`」且
`risk_level` 与违规/警告数量一致（high / medium / low）——结论必须自洽，
不硬编码某个分支名。

> **最容易踩的坑已避开**：在 tmp repo 上调用时**显式**传了
> `guard_config={"report": "<tmp 内路径>", "history": "<tmp 内路径>"}`。
> 不传的话 `run_concurrent_guard` 会按 `<workspace>/logs/workspace_forensics/`
> 落盘——在 tmp repo 上是 tmp 内部路径，但一旦误传本仓路径就会**污染被治理方
> 的工作区**。本工单的 `test_guard_runs_on_foreign_workspace` 用 mtime 比对把这条钉住。

### 5. 契约逐条核对（R1–R7）

| 契约 | 要求 | 实测 | 结论 |
|---|---|---|---|
| R1 | 新建 `tests/unit/test_project_boundary_guard.py`，4 项断言 | 5 条用例齐备 | ✅（见「风险」1、2） |
| R2 | consensus 并发用例 4 类 | 5 条用例齐备，未改动既有 20 条用例的语义 | ✅（见「风险」3） |
| R3 | `generate_consensus` docstring 写明并发契约 | 已补，**仅 docstring** | ✅ |
| R4 | 跨工作区复用验证 | 3 条用例齐备 | ✅ |
| R5 | openspec Phase 4 三行勾选 | 已勾，各行附实测证据注记 | ✅ |
| R6 | 范围限制 | 改动文件见 §6，零越界 | ✅ |
| R7 | 文档与口径 | 本文件 §4 写清 tmp repo 路径形态与报告落点；未宣称根治 | ✅ |

### 6. 改动文件（对照 R6 禁止清单）

| 文件 | 性质 |
|---|---|
| `tests/unit/test_project_boundary_guard.py` | 新建（5 条） |
| `tests/unit/test_consensus_engine_concurrency.py` | 新建（5 条） |
| `tests/unit/test_concurrent_guard_reuse.py` | 新建（3 条） |
| `ai_collab/engines/consensus_engine.py` | **仅** `generate_consensus` 的 docstring |
| `openspec/changes/add-concurrent-workspace-guard/tasks.md` | 仅 Phase 4 三行勾选 + 注记 |
| `collaboration/results/RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24.md` | 本文件 |

**零改动**：`ai_collab/concurrent_guard.py`、`ai_collab/cli/_cli_main.py`、
`pyproject.toml`、`config/agent-orchestration.json` 及其 schema/template、
`docs/CONCURRENT_GUARD_DESIGN.md`、`openspec/.../proposal.md`、
`collaboration/tasks/` 下任何已有工单、`memory/`、`logs/`。

### 7. 验收命令实测输出

| 命令 | 结果 |
|---|---|
| 五个相关测试文件 | `49 passed in 10.56s`（13 本工单新增 + 36 既有守护） |
| `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_project_boundary_guard.py -q` | `28 passed in 7.32s` |
| `python3 -m pytest tests/ -q` | `3008 passed, 6 skipped in 44.47s`（0 failed；基线 2995 → +13） |
| `python3 -m ruff check .` | `All checks passed!` |
| `python3 -m pytest tests/unit --collect-only -q` | `2692 tests collected in 0.57s`，rc=0，无收集错误 |
| `git status --short` | **不含** `logs/` 下的任何新增/修改（tmp repo 报告未污染本仓） |

## 测试结论

- **本工单新增用例**：13 条，全绿。
- **既有守护用例**：36 条（23 条核心 + 13 条 Phase 2.2 CLI），**零回归**。
- **全仓回归**：`3008 passed, 6 skipped`，**0 failed**；6 条 skip 全部是
  `test_studio_integration.py` 的「本地 8000 端口后端未启动」，与本次改动无关
  （改动前基线同为 6 skipped）。
- **lint**：`ruff check .` → `All checks passed!`，零新增。
- **既有 20 条 consensus 用例**：语义未改动，全部仍绿。

**结论**：Phase 4 全部验收标准通过。

## 风险

1. **偏离 1（已按契约 R9 披露）**：`testpaths` 的取法。
   契约 R1.1 写的是「读 `pyproject.toml`，断言 `[tool.pytest.ini_options].testpaths`
   包含 `"tests"`」。本实现改用 **`pytestconfig.getini("testpaths")`**——
   pytest 自己解析出的生效值。理由：`pyproject.toml` 声明
   `requires-python = ">=3.8"`，而标准库 `tomllib` 是 3.11+，
   CI 矩阵含 **3.10**；若测试里直接 `import tomllib`，在 3.10 上会 ImportError，
   得额外引入 `tomli` 依赖。用 pytest 自身的解析结果既**更权威**
   （测的是「pytest 实际怎么收集」，不是「文件里怎么写的」），
   又**不引入版本约束与新依赖**。若坚持文本解析，`pyproject.toml` 改个格式就可能假绿。

2. **偏离 2（已按契约 R9 披露）**：边界扫描范围与 conftest 的例外。
   契约 R1.2 写的是「断言**仓库根目录下**不存在 pytest 会收集的测试文件」。
   本实现扫的是**整个工作树**（跳过 `.git`/`.venv`/`node_modules`/各类缓存/
   `dist`/`build`/`logs` 等与源码无关的目录），比「根目录」更严——
   因为 2026-09-26 那次事故的外项目副本是**以目录形式**落在根下的，
   只看根目录本层会漏掉目录内部更深层的测试文件。
   唯一放宽处：**仓库根的 `conftest.py` 允许存在**（顶层 conftest 是 pytest
   的合法常规用法），但 `tests/` 之外的**任何其它目录**里有 `conftest.py` 即判失败
   （外部项目副本的典型特征）。本仓当前根目录无 `conftest.py`，断言成立。

3. **偏离 3（已按契约 R9 披露）**：R2/R4 的落点选择。
   契约 R2/R4 都给了二选一（「在既有文件里新增」**或**「新建独立文件」）。
   本实现选了**新建独立文件**（`test_consensus_engine_concurrency.py` /
   `test_concurrent_guard_reuse.py`）：既有 20 条 consensus 用例**一字未改**，
   并发契约与复用验证各自成文件、职责清晰，且便于日后单独引用。
   契约明确允许此选项，故不构成语义偏离，仅记录选择。

4. **本工单固化的是「当前行为契约」，不是修掉竞态**。
   `ConsensusEngine.cache` 仍是**实例级、无锁**的普通 dict。同 topic 并发
   **仍会重复计算**（`test_same_topic_concurrency_may_recompute` 就是它的
   防回归钉子）。共识引擎的无锁缓存**仍是已知技术债**——
   **不得宣称「并发冲突已被根治」**。要加锁/去重/保证只算一次，
   需另开工单（并同步更新本文件的并发契约）。

5. **新增的 `tests/unit/test_project_boundary_guard.py::test_unit_collection_has_no_error`
   会起一个子进程跑 `pytest --collect-only`**（实测 ~1.2s）。在 CI 上会多一次
   pytest 启动开销，可接受；若将来套件变大需要优化，可改为只收集
   `tests/unit` 的子集或加 `--co -q --no-header` 精简输出。

6. **`test_same_guard_also_works_on_this_repository` 会写本仓的
   `logs/workspace_forensics/concurrent_guard_latest.json` 与 `history.jsonl`**。
   `logs/` 在 `.gitignore:39` 内，不进版本库、不污染 `git status`（已实测），
   但**本仓工作树里确实多了这两个文件**（运行时产物，非代码变更）。

7. **`test_no_collectable_test_files_outside_tests` 跳过了 `logs/` 目录**。
   `logs/` 是 gitignored 的运行时产物目录（门禁报告、开发日志、openspec 备份
   都落在这里），不属于版本库内容。若有人把外部项目副本放进 `logs/`，
   本用例不会报——但那种副本 pytest 也不会收集（`testpaths` 限定 `tests/`），
   不会造成 2026-09-26 那类事故。

## 回滚

```bash
# 1. 测试与文档回滚（本工单 5 个改动文件）
git checkout -- ai_collab/engines/consensus_engine.py \
                openspec/changes/add-concurrent-workspace-guard/tasks.md
rm -f tests/unit/test_project_boundary_guard.py \
      tests/unit/test_consensus_engine_concurrency.py \
      tests/unit/test_concurrent_guard_reuse.py

# 2. 或按 commit 精确回滚
git revert <TASK-P2-CONCURRENT-GUARD-PHASE4-001 的实现 commit>

# 3. 清理运行时产物（可选，不在版本库内）
rm -f logs/workspace_forensics/concurrent_guard_latest.json \
      logs/workspace_forensics/concurrent_guard_history.jsonl
```

**回滚后状态**：三个新测试文件消失，`generate_consensus` 的 docstring 还原，
openspec Phase 4 回到未勾选；`ai_collab/concurrent_guard.py` 核心模块与
Phase 2.2 的 CLI 门禁**均不受影响**（本工单未触碰它们）。

## 后续（不在本工单范围）

- 共识引擎的无锁缓存（加锁 / 去重 / 只算一次）需另开工单，并同步更新本文件
  §2 的并发契约。
- `workspace-guard` / `spawn-agent-guard` 的 `--workspace` 位置与 `concurrent guard`
  不一致（见 `RESULT-P1-CONCURRENT-GUARD-2026-10-24.md` 的「后续」）。
- 「派单前自动调用并发门禁」尚未接入（见 `RESULT-P1-CONCURRENT-GUARD-2026-10-24.md`
  风险 4）。
