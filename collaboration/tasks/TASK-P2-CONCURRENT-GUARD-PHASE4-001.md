---
task_id: TASK-P2-CONCURRENT-GUARD-PHASE4-001
change_id: add-concurrent-workspace-guard
status: planning
priority: P2
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: testing
support_skills:
  - documentation
created_at: 2026-10-24T11:08:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_project_boundary_guard.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 -m pytest tests/unit --collect-only -q"
result_file: collaboration/results/RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24.md
---

# TASK-P2-CONCURRENT-GUARD-PHASE4-001：并发工作区守护 —— Phase 4 项目边界（测试隔离守护 + consensus 并发用例 + 跨工作区复用验证）

> **本工单由 Claude Code（AGENT_ARCH）定义契约，Claude Code（AGENT_EXEC）实现，
> CodeArts（AGENT_TEST）复核。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
>
> **前置依赖**：`TASK-P1-CONCURRENT-GUARD-001`（Phase 2.2 CLI 门禁接入）。
> 本工单只依赖 Phase 2.1 的核心模块（已实现）与 Phase 3 的守护用例（已实现），
> **不依赖** CLI 入口是否完成——R4 的复用性验证直接调
> `ai_collab.concurrent_guard.run_concurrent_guard()`。

## 一、背景与真证

OpenSpec 变更 `add-concurrent-workspace-guard` 的 Phase 4「项目边界（暂缓）」共 3 条，
实测状态：

| 条目 | 内容 | 实测状态 | 证据 |
|---|---|---|---|
| 4.1 | pytest 收集边界：`testpaths` 限定 `tests/`，仓库内不存放外部项目副本 | 🟡 **一半完成** | `pyproject.toml:48` 已是 `testpaths = ["tests"]`（且带 2026-09-26 陷阱注释）；但**缺防回归断言**（设计文档 §6.3 要求「新增测试断言外部副本目录不被主套件收集」） |
| 4.2 | 修 `test_consensus_engine.py` 导入 + 补并发用例 | 🟡 **一半完成** | 导入已正常：`tests/unit/test_consensus_engine.py` 的 `from ai_collab.engines.consensus_engine import ConsensusEngine` 解析成功，该文件 + `test_consensus_engine_extra.py` **20 passed**；但**并发用例完全不存在**：`grep -rn "gather\|ThreadPool\|threading" tests/unit/test_consensus*.py` → 零命中 |
| 4.3 | 验证 concurrent guard 在任意共享工作区的复用 | ❌ **未开工** | 无任何跨工作区复用测试；设计文档 §6.3/§6.4 要求「治理层与被治理仓库解耦，可复用于任何共享工作区」「同一套守卫跨仓库通用」 |

### 1.1 为什么要补 consensus 并发用例

`ai_collab/engines/consensus_engine.py:54` 有一个**实例级可变字典**：

```python
self.cache: dict[str, dict[str, Any]] = {}
```

`generate_consensus()`（`:88`）先读 `self.cache[topic]`、算完再写回（`:121`），
**全程无锁**。并发场景（多个 Agent 同时对同一 topic 请求共识）下：

- 两个协程可能同时 cache miss → 重复调用 provider（浪费，非致命）
- `dict` 单键赋值在 CPython 下是原子的，所以**不会**写坏字典，但**行为不确定**
  （同一 topic 返回两份不同的 `generated_at`）

这正是 2026-09-26 那次并发冲突在共识引擎侧的对应面：**共享可变状态 + 无并发契约
+ 无守护用例**。本工单要做的不是修这个竞态（那超出「项目边界」范围），而是
**把当前行为用用例钉住**，让后续任何人改共识引擎时能看到并发契约。

### 1.2 复用性为什么必须验证

`run_concurrent_guard(workspace=...)` 接收的是**任意** workspace 路径。若实现里
不小心写死了本仓路径、或读了本仓特有的配置，跨仓库就会失效——而本仓自己是唯一
测试对象，**永远测不出来**。必须在 `tmp_path` 构造的**另一个** git repo 上跑一次，
证明它真的与被治理仓库解耦。

## 二、目标

1. `testpaths` 收集边界有**防回归用例**守护（外部项目副本不会被主套件收集）。
2. consensus 引擎的并发行为有**用例钉住**（当前语义被固定下来）。
3. concurrent guard 的**跨工作区复用性**有实测证据。
4. `openspec/changes/add-concurrent-workspace-guard/tasks.md` 的 Phase 4 勾选与实际对齐。

## 三、详细契约

### R1 新建 `tests/unit/test_project_boundary_guard.py`：pytest 收集边界守护

设计文档 §6.3「项目边界守护」要求的防回归断言。至少覆盖：

1. **`testpaths` 限定 `tests/`**：读 `pyproject.toml`，断言
   `[tool.pytest.ini_options].testpaths` 包含 `"tests"`。
2. **仓库根无外部项目副本**：断言仓库根目录下**不存在** pytest 会收集的测试文件
   （即 `test_*.py` / `*_test.py`）。允许存在 `tests/` 之外的**非测试**目录
   （如 `scripts/`、`docs/`），但不允许出现测试文件——这是 2026-09-26 事故的直接成因
   （外部项目副本目录被 pytest 收集 → `ModuleNotFoundError`）。
   > 注意：`tests/` 之外的目录若含 `conftest.py` 也会被 pytest 收集，
   > 断言时把 `conftest.py` 一起纳入检查范围更稳妥。
3. **主套件收集无 error**：`python3 -m pytest tests/unit --collect-only -q` 退出码为 0
   （用 `subprocess` 在测试里跑，或直接断言 `pytest.ExitCode.OK`）。
4. **新增测试文件不会逃逸到 `tests/` 之外**：断言本文件自身路径在 `tests/` 下
   （自检，防后人把守护用例写到仓库根）。

> **不要**用 `norecursedirs` 解决——`pyproject.toml` 的注释已明确该问题的正解是
> `testpaths` + 不放外部副本，而不是排除目录。

### R2 补 consensus 并发用例

**在 `tests/unit/test_consensus_engine.py` 里新增**（或新建
`tests/unit/test_consensus_engine_concurrency.py`，二选一，但**不要**改动既有
20 条用例的语义）。至少覆盖：

1. **同 topic 并发请求**：`asyncio.gather` 同时发起 N 个（建议 N=5）相同 topic 的
   `generate_consensus()`，断言：
   - 全部返回 `mode == "mock"`（在 mock 模式下跑，避免真实网络调用）；
   - 返回结果的 `consensus` 字段一致；
   - `engine.cache` 里该 topic 只有 1 个条目（不会被重复写入成多份状态）。
2. **不同 topic 并发请求**：不同 topic 并发，断言 `engine.cache` 里每个 topic 各 1 条，
   且互不串味（topic A 的结果里不含 topic B 的内容）。
3. **缓存命中语义**：并发结束后再调一次同 topic，断言走的是 cache 路径
   （返回结果与并发阶段一致，且**没有**再次调用 provider——用 mock 计数断言）。
4. **并发下的异常隔离**：让其中一路抛异常（monkeypatch 某次调用抛错），断言
   `asyncio.gather(..., return_exceptions=True)` 能把异常收集起来，且**其余协程正常完成**，
   引擎实例没有进入半损坏状态（后续调用仍能正常工作）。

> 用例必须**确定性**：不要依赖 `sleep` 时序。用 `asyncio.Event` /
> `monkeypatch` 控制的同步点，或直接接受「cache 可能有 1~N 条」的宽松断言——
> **但**第 1 条里「cache 里该 topic 只有 1 个条目」是 dict 语义决定的必然结果，可以硬断言。

### R3 记录并发契约

在 `ai_collab/engines/consensus_engine.py` 的 `generate_consensus()` 的 docstring
里**补一段**并发说明（当前该方法没有 docstring），写明：

- `self.cache` 是实例级、无锁的；
- 并发同 topic 可能重复计算（幂等性由 dict 语义保证，不保证只算一次）；
- 并发不同 topic 互不影响。

**只是加说明，不改并发语义**（改语义属于另一个工单，不得顺手做）。
若确实需要加锁，另开工单。

### R4 复用性验证：跨工作区

在 `tests/unit/test_concurrent_guard.py` 里**新增**一个用例类
（如 `TestCrossWorkspaceReuse`），或新建 `tests/unit/test_concurrent_guard_reuse.py`：

1. 在 `tmp_path` 构造一个**与本仓无关**的 mini git repo（`git init` + 至少 1 次 commit），
   目录名不要含 `ai_collab` 之类字样。
2. 在该 repo 上调用
   `run_concurrent_guard(workspace=<tmp repo>, expected_branch="main")`，
   断言：
   - 返回 `risk_level` 与 `allowed` 是**布尔/字符串**且符合预期
     （因为 tmp repo 的默认分支名可能是 `master` 或 `main`，断言应写成
     「要么 drift 命中、要么未命中，但**结论必须自洽**」，不要硬编码某个分支名）；
   - 报告文件写在 **tmp repo 内**（`report_file` 路径以 tmp repo 开头），
     **不是**本仓路径——这是「与被治理仓库解耦」的核心断言；
   - 本仓工作区**没有**被本次调用写入任何文件（断言本仓
     `logs/workspace_forensics/concurrent_guard_latest.json` 的 mtime 未变，
     或更简单：断言 `report_file` 不在本仓路径下）。
3. 再在**本仓**上跑一次同样的调用，断言报告仍写在本仓的
   `logs/workspace_forensics/` 下——证明「同一套守卫跨仓库通用」。

> **注意**：`run_concurrent_guard` 会写 `latest.json` + `history.jsonl`。
> 在 tmp repo 上调用时**必须**传 `guard_config={"report": "<tmp 内路径>",
> "history": "<tmp 内路径>"}`，否则会写进**本仓**的 `logs/workspace_forensics/`
> （污染工作区）。**这是本条最容易踩的坑，务必显式传路径。**

#### ⚠️ 契约勘误（2026-10-24 复核阶段实测，本工单已关闭）

上面 R4 注意事项里的「否则会写进**本仓**」**与实现不符**，已作废。实测结论：

- 落点规则是 `workspace / report_rel`（`ai_collab/concurrent_guard.py`）——
  **相对路径**落在**被治理工作区**自己的目录下，**绝对路径**按调用方给的位置落
  （pathlib 的 `Path / 绝对路径` 语义：右操作数绝对 → 左操作数被丢弃）。
- 因此**不传** `guard_config` 时，默认落在**被治理工作区**自己的
  `logs/workspace_forensics/` 下，**不会**写进本仓。
- 真正会污染本仓的写法是**显式**传入本仓的绝对路径。

显式传 tmp 内部路径**仍是推荐写法**（落点不依赖默认值），但理由是
「显式胜于隐式」，**不是**「否则会污染本仓」。

复核证据：把实现改成 `Path(__file__).parents[1] / report_rel`（落点写死本仓）后，
本工单原有 3 条复用用例**全部仍绿**（覆盖缺口）；补了
`tests/unit/test_concurrent_guard_reuse.py::test_default_report_path_stays_inside_guarded_workspace`
之后，该 mutation 才被**唯一地**捕获（`1 failed, 3 passed`）。
详见 `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md`。

### R5 更新 openspec 任务清单

`openspec/changes/add-concurrent-workspace-guard/tasks.md`：

- 4.1 → 勾选（`testpaths` 已有限制 + 本工单补上防回归断言）
- 4.2 → 勾选（导入已修 + 本工单补并发用例）
- 4.3 → 勾选（本工单的跨工作区复用验证）
- **不得**改动 Phase 2 / Phase 3 的勾选状态（那些归 `TASK-P1-CONCURRENT-GUARD-001`
  与既成事实）。

### R6 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---------|---------|
| `tests/unit/test_project_boundary_guard.py`（新建） | `ai_collab/concurrent_guard.py`（除非发现跨工作区复用的真实 bug，须在「风险」段写明并单独裁决） |
| `tests/unit/test_consensus_engine.py` 或新建 `tests/unit/test_consensus_engine_concurrency.py` | `ai_collab/engines/consensus_engine.py` 的**并发语义**（只允许按 R3 加 docstring 说明） |
| `tests/unit/test_concurrent_guard.py`（新增用例类）或新建 `tests/unit/test_concurrent_guard_reuse.py` | `pyproject.toml` 的 `testpaths` 及其他既有配置 |
| `ai_collab/engines/consensus_engine.py`（**仅** `generate_consensus` 的 docstring） | `config/agent-orchestration.json` 及其 schema/template |
| `openspec/changes/add-concurrent-workspace-guard/tasks.md`（仅 Phase 4 三行勾选） | `docs/CONCURRENT_GUARD_DESIGN.md` |
| `collaboration/results/RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24.md`（新建） | `collaboration/tasks/` 下任何已有工单 |
| | `memory/` 下任何文件（只读镜像） |
| | `logs/` 下任何文件（**尤其不得**把 tmp repo 的报告写进本仓 `logs/`） |

### R7 文档与口径

- 结果文件必须写清「跨工作区复用验证的实际 tmp repo 路径形态与报告落点」。
- 若偏离契约任一条，**必须在结果文件「风险」段写明偏离点与理由**。
- **不要**宣称「并发冲突已被根治」——本工单固化的是**当前行为契约**，
  共识引擎的无锁缓存仍是已知的技术债。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_project_boundary_guard.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check .` → `All checks passed!`（**零新增**）
- [ ] `python3 -m pytest tests/unit --collect-only -q` 退出码 0，无 collection error
- [ ] `git status --short` 中**不出现** `logs/` 下的新增/修改（tmp repo 报告未污染本仓）
- [ ] `git diff --name-only` **不含** R6 禁止清单里的任何文件
- [ ] 结果文件含「执行命令 / 验证结果 / 测试结论 / 风险 / 回滚」各段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] 结果文件头部的 `- **状态**: completed` 在**前 40 行内**

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P2-CONCURRENT-GUARD-PHASE4-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24.md
```

把该命令**原样输出**的一行回复回来。

## 六、参考

- OpenSpec 变更：`openspec/changes/add-concurrent-workspace-guard/`（proposal.md / tasks.md）
- 技术设计：`docs/CONCURRENT_GUARD_DESIGN.md`（§6.3 项目边界验证、§6.4 端到端验证矩阵）
- 核心模块：`ai_collab/concurrent_guard.py`
- 既有守护用例：`tests/unit/test_concurrent_guard.py`（23 条，含
  `TestRegressionSample20260926` 的 mini git repo fixture 可参考）
- 共识引擎：`ai_collab/engines/consensus_engine.py`
- `pyproject.toml:43-48`（`testpaths` 现状与 2026-09-26 陷阱注释）
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
