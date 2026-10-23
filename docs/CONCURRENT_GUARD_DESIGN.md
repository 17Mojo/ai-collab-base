# 并发工作区治理设计（Concurrent Workspace Guard）

**状态**: 设计待评审  
**创建日期**: 2026-09-26  
**样本来源**: 2026-09-26 并行冲突事件  
**关联变更**: `openspec/changes/add-concurrent-workspace-guard`（本仓）  
**适用项目**: 基础项目 `ai-collab-base`（本仓）  

> **2026-10-23 去外部化说明**：本设计初版把「基础项目 + 一个外部研究项目」
> 作为共同适用对象，那个外部项目副本已于同日清理（见
> `collaboration/results/RESULT-P0-CONSENSUS-ENGINE-001.md` 的归档说明）。
> 本设计的治理层与服务层**本就与被治理对象无关** —— 它管的是
> 「多 Agent 共享同一 git working tree」这件事，与仓库里放什么代码无关。
> 下文所有 `hermes_target` 字样均已改写为本仓语境；冲突样本的历史事实保留不变。

---

## 一、背景与动机

### 1.1 触发事件

2026-09-26 一次常规提交任务中，核实仓库状态时发现**并行冲突**：

- 本会话产出的 3 个 commit 已在 `main` 上，但**当前 HEAD 已漂移到 `refactor/slimming-2026-09-20`**
- 本会话基于 `main@81a02c5`（`schema_v2.py` 1022 行）准备改动，而 `main` 实际已推进到 962 行（`ReviewWorkflow` 被删除）
- 工作区混入 **486+ 行非本会话的未提交改动**（4 个文件），无法区分归属
- 一个**外部项目副本目录**被 pytest 收集，导致全量测试 `collection error`
  （历史事实：该目录当时名为 `hermes_target/`，2026-10-23 已随噪声清理删除）

### 1.2 问题定性（用户）

> 以本次并行冲突为**样本**，进行基础项目与研究项目的**功能自验证迭代**。这类问题在**框架平台多 Agent 协作**场景和**浏览器多智能体平台组织协作**中都会发生，需要**治理层**和**服务层**增强。

### 1.3 与现有变更的关系

运行时状态文件的并发（`state_manager` / `notification` 的状态写入）由文件锁机制覆盖。

**本设计补齐的是另一个维度**：文件锁解决的是**运行时状态文件**的并发，而本次冲突发生在 **git 工作区级**（分支 / 基线 / 归属 / 测试隔离），是**开发时协作**的并发。

| 维度 | 现有机制覆盖 | 本设计覆盖 |
|------|-------------|-----------|
| 运行时状态文件并发 | ✅ 文件锁 | — |
| git 工作区并发 | ❌ 未覆盖 | ✅ 本设计 |
| 测试套件隔离 | ❌ 未覆盖 | ✅ 本设计 |

---

## 二、冲突样本分析

### 2.1 事件时间线（重构）

```text
T0  本会话在 main@81a02c5 完成第 4 步 3 个 commit（001c7b4/3b19bd0/caeb8af）
T1  并行协作者在 main 继续提交 17 个 commit（含删除 ReviewWorkflow，1022→962 行）
T2  从 main@f76d25c 分出 refactor/slimming-2026-09-20 分支
T3  HEAD 被切换到 refactor/slimming-2026-09-20（本会话无感知）
T4  本会话基于旧版本（T0 时的 1022 行）准备第 5 步改动
T5  提交前核实发现：分支漂移 + 基线过期 + 归属不清 + 测试污染
```

### 2.2 四类缺口

| # | 缺口 | 本次表现 | 检测信号 |
|---|------|---------|---------|
| G1 | **分支漂移** | HEAD 从 `main` 漂到 `refactor/slimming-2026-09-20` | `git rev-parse --abbrev-ref HEAD` ≠ 预期分支 |
| G2 | **基线过期** | 基于 1022 行版本，实际 962 行 | 工作基线 commit 不是目标分支的祖先 / 目标文件已变更 |
| G3 | **归属不清** | 工作区混入 486+ 行他人未提交改动 | 未提交改动的 mtime / 内容与会话标记不匹配 |
| G4 | **测试污染** | 外部项目副本目录被收集 → `ModuleNotFoundError` | pytest 收集到非目标项目目录 |

### 2.3 根因分析

**根因：多 Agent 共享同一 git working tree，缺少「工作区独占 + 身份标记」机制。**

现有机制假设：

| 假设 | 现实 |
|------|------|
| 一个工作区同一时刻只有一个 Agent | 多 Agent 并行操作同一工作区 |
| Agent 知道自己应该在哪个分支 | Agent 不感知分支切换 |
| 改动归属可通过任务登记推断 | 未登记的改动无法归属 |
| 测试套件只收集本项目 | 研究项目目录混入收集范围 |

### 2.4 影响面

| 影响 | 严重度 | 说明 |
|------|-------|------|
| 改动不可移植 | 🔴 高 | 基于过期基线，rebase 冲突或语义错误 |
| 污染他人工作 | 🔴 高 | 贸然提交会把他人的未提交改动一起提交 |
| 丢失他人工作 | 🔴 高 | 贸然 `checkout`/`reset --hard` 会清除他人改动 |
| 测试套件失效 | 🟡 中 | collection error 阻塞全量回归 |
| 决策依据失真 | 🟡 中 | 基于错误版本做设计判断 |

---

## 三、能力矩阵

### 3.1 现有资产盘点

| 层 | 资产 | 能力 | 覆盖缺口 |
|----|------|------|---------|
| 治理层 | `collaboration/PROTOCOL.md` v3.0 | 角色编排 / 命令 / 心跳 / 交接 | 无并发工作区条款 |
| 治理层 | `collaboration/COLLABORATION_GUIDELINES.md` | 协作流程 | 无并发约束 |
| 服务层 | `ai_collab/workspace_guard.py` (385 行) | dirty 数量阈值 / domain 分类 | G1-G4 均不覆盖 |
| 服务层 | `ai_collab/spawn_agent_guard.py` (304 行) | write-set 重叠（已登记任务） | 仅覆盖已登记任务，G3 不覆盖 |
| 服务层 | `ai_collab/session_registry.py` (520 行) | 会话注册 | 无分支/基线感知 |
| 服务层 | `ai_collab/handoff_notification.py` (382 行) | 交接通知 | 无并发告警 |
| CLI | `_run_workspace_guard_gate` / `_run_spawn_agent_guard_gate` | 两类门禁 | 无 concurrent 门禁 |
| 测试 | `test_workspace_guard*.py` / `test_spawn_agent_guard*.py` | 守护现有能力 | 无并发冲突场景 |

### 3.2 缺口 → 能力映射

| 缺口 | 新增能力 | 分层 |
|------|---------|------|
| G1 分支漂移 | `detect_branch_drift()` | 服务层 |
| G2 基线过期 | `detect_baseline_staleness()` | 服务层 |
| G3 归属不清 | `detect_foreign_changes()` | 服务层 |
| G4 测试污染 | pytest `norecursedirs` + 项目边界守护 | 测试层 |
| G1-G3 综合 | `assess_concurrent_risk()` | 服务层 |
| 治理约束 | 「并发工作区安全」协议章节 | 治理层 |
| 门禁接入 | `_run_concurrent_guard_gate` | CLI |
| 回归守护 | `test_concurrent_guard.py`（样本 fixture） | 测试层 |

### 3.3 分层设计

```text
┌─────────────────────────────────────────────────────────┐
│ 治理层（规则）                                            │
│  PROTOCOL.md「并发工作区安全」                            │
│  · 工作区独占原则  · 分支约定  · 基线声明  · 归属标记     │
└─────────────────────────────────────────────────────────┘
                          ↓ 约束
┌─────────────────────────────────────────────────────────┐
│ 服务层（自动化检测）                                       │
│  ai_collab/concurrent_guard.py                           │
│  · inspect_git_context      · detect_branch_drift        │
│  · detect_baseline_staleness · detect_foreign_changes    │
│  · assess_concurrent_risk                                │
│  CLI gate: _run_concurrent_guard_gate                    │
└─────────────────────────────────────────────────────────┘
                          ↓ 守护
┌─────────────────────────────────────────────────────────┐
│ 测试层（回归）                                            │
│  tests/unit/test_concurrent_guard.py（含冲突样本 fixture）│
│  pytest 项目边界隔离（仓库内不放外部项目副本）             │
└─────────────────────────────────────────────────────────┘
```

---

## 四、接口设计

### 4.1 模块：`ai_collab/concurrent_guard.py`

#### 4.1.1 `inspect_git_context(workspace: Path) -> dict`

收集 git 上下文（只读）。

```python
{
    "ok": True,
    "branch": "refactor/slimming-2026-09-20",   # 当前 HEAD 分支（detached 时为 None）
    "head_commit": "672f496...",                 # HEAD commit
    "upstream": "origin/main",                   # 追踪的 upstream（无则 None）
    "ahead": 5,                                  # 领先 upstream 的 commit 数
    "behind": 0,                                 # 落后 upstream 的 commit 数
    "dirty_total": 6,                            # 未提交改动数
    "dirty_paths": ["ai_collab/pack/schema_v2.py", ...],  # 前 N 条路径
}
```

#### 4.1.2 `detect_branch_drift(workspace, expected_branch: str | None) -> dict`

检测 HEAD 分支是否符合预期。

```python
{
    "drifted": True,
    "expected": "main",
    "actual": "refactor/slimming-2026-09-20",
    "severity": "high",   # high | none
}
```

**判定**：`expected_branch` 为 None → 跳过（`drifted=False`）；`actual != expected` → `drifted=True`。

#### 4.1.3 `detect_baseline_staleness(workspace, baseline_commit: str, watch_paths: list[str]) -> dict`

检测工作基线是否过期。

```python
{
    "stale": True,
    "baseline_commit": "81a02c5",
    "head_commit": "672f496",
    "changed_watch_paths": [
        {"path": "ai_collab/pack/schema_v2.py", "commits_since": 3},
    ],
    "severity": "high",
}
```

**判定**：`watch_paths` 中任一文件在 `baseline_commit..HEAD` 区间有变更 → `stale=True`。

#### 4.1.4 `detect_foreign_changes(workspace, session_started_at: str, tracked_paths: list[str] | None) -> dict`

检测工作区中非本会话的未提交改动。

```python
{
    "foreign_count": 4,
    "foreign_paths": [
        {"path": "tests/unit/test_enhanced.py", "mtime": "2026-09-20T16:55:00"},
    ],
    "severity": "high",   # high（有 foreign）| none
}
```

**判定**：未提交改动的文件 mtime **早于** `session_started_at` → 判定为 foreign（非本会话）。

> **局限声明**：mtime 是启发式信号，非真证。同一会话内 checkout 也可能刷新 mtime。本能力定位为**风险提示**，不作硬阻断依据（见 §4.5）。

#### 4.1.5 `assess_concurrent_risk(workspace, *, expected_branch, baseline_commit, watch_paths, session_started_at) -> dict`

综合评估并发风险。

```python
{
    "risk_level": "high",   # high | medium | low
    "git_context": {...},
    "signals": {
        "branch_drift": {...},
        "baseline_stale": {...},
        "foreign_changes": {...},
    },
    "violations": ["branch drift: expected=main actual=refactor/..."],
    "warnings": ["foreign changes detected: 4 files"],
    "allowed": False,   # 无 high 信号 → True
}
```

**风险评级规则**：

| 条件 | risk_level | allowed |
|------|-----------|---------|
| 任一 high 信号（drift / stale / foreign） | high | False |
| 仅 medium 信号（如 ahead 过多） | medium | True |
| 无信号 | low | True |

### 4.2 CLI gate：`_run_concurrent_guard_gate`

```bash
python3 -m ai_collab.cli concurrent guard \
  --workspace . \
  --expected-branch main \
  --baseline-commit 81a02c5 \
  --watch-path ai_collab/pack/schema_v2.py \
  --session-started-at 2026-09-26T05:40:00
```

输出（对齐现有 gate 风格）：

```text
[并发门禁]
  allowed: False
  risk_level: high
  branch: refactor/slimming-2026-09-20 (expected: main)  ← drift
  baseline: 81a02c5 → 672f496 (1 watched path changed)   ← stale
  foreign: 4 files
  report: logs/workspace_forensics/concurrent_guard_latest.json
  violation: branch drift: expected=main actual=refactor/slimming-2026-09-20
```

### 4.3 报告 Schema

对齐现有 `workspace_guard` / `spawn_agent_guard` 的报告约定：

- 最新报告：`logs/workspace_forensics/concurrent_guard_latest.json`
- 历史追加：`logs/workspace_forensics/concurrent_guard_history.jsonl`

```json
{
  "generated_at": "2026-09-26T...",
  "workspace": "/path/to/workspace",
  "risk_level": "high",
  "allowed": false,
  "git_context": {...},
  "signals": {...},
  "violations": [...],
  "warnings": [...],
  "thresholds": {...},
  "report_file": "...",
  "history_file": "..."
}
```

### 4.4 配置项（`agent-orchestration.json` 新增段）

```json
{
  "concurrentGuard": {
    "enabled": true,
    "expectedBranch": "main",
    "requireBaselineCommit": false,
    "foreignChangeSeverity": "warning",
    "aheadWarnThreshold": 20,
    "report": "logs/workspace_forensics/concurrent_guard_latest.json",
    "history": "logs/workspace_forensics/concurrent_guard_history.jsonl"
  }
}
```

### 4.5 硬门禁 vs 软警告分层（遵循既有原则）

按 `feedback_test_gate_design.md`：硬门禁只放**真证**，启发式信号降级软警告。

| 信号 | 性质 | 门禁等级 |
|------|------|---------|
| 分支漂移（G1） | git 真证 | **硬门禁**（可阻断） |
| 基线过期（G2） | git 真证 | **硬门禁**（可阻断） |
| 归属不清（G3） | mtime 启发式 | **软警告**（不阻断） |
| 测试污染（G4） | pytest 配置 | 测试层修复 |

> 明确拒绝：把 mtime 启发式当硬门禁 → 会造成假阳性阻断。

---

## 五、治理层增强

### 5.1 `PROTOCOL.md` 新增章节

拟新增「**第十四章：并发工作区安全**」，包含 4 条约束：

#### 5.1.1 工作区独占原则

- 同一 git working tree 同一时刻**至多一个 Agent 处于写模式**
- 多 Agent 并行时，各自使用**独立 worktree**（`git worktree add`）或**独立 clone**
- 共享工作区仅允许**只读**操作（inspect / 分析）

#### 5.1.2 分支约定

- 每个任务在**声明的分支**上进行，写入任务文件 `branch` 字段
- 提交前必须校验 `git rev-parse --abbrev-ref HEAD` == 声明分支
- 禁止在未声明的分支上提交

#### 5.1.3 基线声明

- 任务开始时记录 `baseline_commit`（`git rev-parse HEAD`）
- 提交前校验 `watch_paths` 未被他人推进
- 基线过期时先 rebase / 重新核实，禁止直接提交

#### 5.1.4 归属标记

- 未提交改动通过**会话标记文件**（如 `.ai_collab_session.json`）关联 owner
- 提交前区分「本会话改动」vs「他人改动」
- 禁止 `git add -A` / `git checkout -- .` / `git reset --hard` 等无差别操作

### 5.2 与现有章节的关系

| 章节 | 关注 | 本设计关系 |
|------|------|-----------|
| 九、心跳与反空转 | 任务状态超时 | 互补（状态 vs 工作区） |
| 十、会话交接 | 上下文续接 | 互补（交接 vs 并发） |
| 十四、并发工作区安全（新） | 工作区并发 | 本设计 |

---

## 六、验证方案（功能自验证迭代）

### 6.1 测试层：`tests/unit/test_concurrent_guard.py`

**核心思路**：把本次冲突**固化为 fixture 样本**，守护检测能力。

| 测试组 | 用例 | 守护 |
|--------|------|------|
| TestInspectGitContext | 收集 branch/head/dirty | 基础 inspect |
| TestBranchDrift | 漂移/未漂移/expected=None | G1 |
| TestBaselineStaleness | 过期/未过期/无变更 | G2 |
| TestForeignChanges | 有/无 foreign（mtime 边界） | G3 |
| TestAssessRisk | high/medium/low 三级 | 综合评级 |
| TestRegressionSample20260926 | **本次冲突完整复现** | 端到端样本 |

`TestRegressionSample20260926` 用 `tmp_path` 构造迷你 git 仓库，复现「分支漂移 + 基线过期 + foreign 改动」三信号，断言 `risk_level == "high"` 且 `allowed is False`。

### 6.2 基础项目验证

- `pytest tests/unit/test_concurrent_guard.py -v` 全绿
- `ruff check ai_collab/concurrent_guard.py tests/unit/test_concurrent_guard.py` 全绿
- 全量回归无新增失败

### 6.3 项目边界验证

| 项 | 动作 | 验收 |
|----|------|------|
| G4 测试隔离 | pyproject.toml `testpaths` 限定 `tests/`（仓库内不存放外部项目副本） | 全量 collection 无 error |
| 项目边界守护 | 新增测试断言外部副本目录不被主套件收集 | 防回归 |
| consensus 并发守护 | 修 `test_consensus_engine.py` 导入 + 补并发用例 | 本仓 consensus 测试可跑 |
| 并发治理复用 | 治理层与被治理仓库解耦，可复用于任何共享工作区 | 同一套守卫跨仓库通用 |

### 6.4 端到端验证矩阵

| 场景 | 基础项目 | 复用性（任意共享工作区） |
|------|---------|---------|
| 分支漂移检测 | ✅ fixture | ✅ fixture |
| 基线过期检测 | ✅ fixture | ✅ fixture |
| 归属检测 | ✅ fixture | ✅ fixture |
| 测试隔离 | ✅ 断言 | ✅ 断言 |
| CLI gate | ✅ 命令验证 | ✅ 命令验证 |

---

## 七、实施计划

| Phase | 内容 | 交付物 | 依赖 |
|-------|------|--------|------|
| **P1 治理层** | PROTOCOL.md 新增第十四章 | 协议文档更新 | 本设计评审通过 |
| **P2 服务层** | `concurrent_guard.py` + CLI gate | 模块 + CLI | P1 |
| **P3 测试层** | `test_concurrent_guard.py`（含样本 fixture） | 测试套件 | P2 |
| **P4 项目边界** | 测试隔离 + consensus 并发守护 | 隔离修复 + 测试 | P2 |

**提交拆分**（遵循用户偏好）：

1. `docs(protocol): 新增并发工作区安全章节`（P1）
2. `feat(guard): 新增 concurrent_guard 并发工作区检测`（P2）
3. `feat(cli): 接入 concurrent guard 门禁`（P2）
4. `test(guard): 补 concurrent_guard 守护 + 2026-09-26 冲突样本`（P3）
5. `fix(pytest): 隔离外部项目副本目录的测试收集`（P4）

---

## 八、风险与回滚

| 风险 | 等级 | 缓解 |
|------|------|------|
| mtime 启发式误报（G3） | 中 | 降级软警告，不阻断 |
| 分支约定过严影响现有流程 | 中 | `expectedBranch` 默认 None（跳过） |
| 与并行协作者的工作区冲突 | 🔴 高 | **本设计不修改他人未提交改动**；实施前先核实工作区归属 |
| `git worktree` 迁移成本 | 低 | 渐进推行，先服务层后治理层 |

**回滚**：新增模块与协议章节均为**增量**，回滚只需 revert 对应 commit，不影响现有 `workspace_guard` / `spawn_agent_guard`。

**实施前置约束（重要）**：

> 实施本设计前，必须先确认工作区状态（`git status` + `git log`），
> 区分「本会话改动」与「他人未提交改动」。
> **禁止**在未确认归属的情况下提交或清理工作区（本次冲突的直接教训）。

---

## 九、非目标（Non-Goals）

- ❌ 自动解决 git 冲突（仅检测与告警）
- ❌ 强制 worktree 隔离（先约定，后工具化）
- ❌ 替代 `workspace_guard` / `spawn_agent_guard`（互补，不替代）
- ❌ 运行时状态文件并发（由状态文件锁机制覆盖）
