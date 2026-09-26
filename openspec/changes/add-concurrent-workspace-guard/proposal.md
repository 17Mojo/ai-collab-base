# Change Proposal: Add Concurrent Workspace Guard

## Why

2026-09-26 一次常规提交任务中暴露**并行冲突**：本会话基于过期基线（`main@81a02c5`）准备改动，而 `main` 已被并行协作者推进（删除 `ReviewWorkflow`）；HEAD 漂移到 `refactor/slimming-2026-09-20`；工作区混入 486+ 行他人未提交改动。

现有治理层（`PROTOCOL.md` v3.0）和服务层（`workspace_guard.py` / `spawn_agent_guard.py`）**未覆盖 git 工作区级并发**：分支漂移、基线过期、归属不清、测试污染。

与 `migrate-parallel-architecture-to-hermes` 互补：该变更覆盖**运行时状态文件并发**（文件锁），本变更覆盖**开发时 git 工作区并发**。

## What Changes

### 新增

| 文件 | 内容 | 层 |
|------|------|---|
| `ai_collab/concurrent_guard.py` | 5 个检测函数 + 综合风险评级 | 服务层 |
| `tests/unit/test_concurrent_guard.py` | 守护测试 + 2026-09-26 冲突样本 fixture | 测试层 |
| `docs/CONCURRENT_GUARD_DESIGN.md` | 技术设计文档（已产出） | 文档 |

### 修改

| 文件 | 内容 | 层 |
|------|------|---|
| `collaboration/PROTOCOL.md` | 新增第十四章「并发工作区安全」 | 治理层 |
| `ai_collab/cli/_cli_main.py` | 接入 `_run_concurrent_guard_gate` | CLI |
| `config/agent-orchestration.json` | 新增 `concurrentGuard` 配置段 | 配置 |

### 接口设计

```python
inspect_git_context(workspace) -> dict
detect_branch_drift(workspace, expected_branch) -> dict
detect_baseline_staleness(workspace, baseline_commit, watch_paths) -> dict
detect_foreign_changes(workspace, session_started_at) -> dict
assess_concurrent_risk(workspace, *, expected_branch, baseline_commit, watch_paths, session_started_at) -> dict
```

详细设计见 `docs/CONCURRENT_GUARD_DESIGN.md`。

### 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| mtime 启发式误报（G3） | 中 | 降级软警告，不阻断 |
| 分支约定过严影响现有流程 | 中 | `expectedBranch` 默认 None（跳过） |
| 与并行协作者工作区冲突 | 高 | 本变更不修改他人未提交改动；实施前先核实归属 |

## Impact

- **Affected specs**: `concurrent-workspace-safety`（新增，对应 PROTOCOL.md 第十四章）
- **Affected code**:
  - `ai_collab/concurrent_guard.py`（新增）
  - `ai_collab/cli/_cli_main.py`（接入 gate）
  - `collaboration/PROTOCOL.md`（新增章节）
- **Non-goals**: 不自动解决 git 冲突、不强制 worktree 隔离、不替代现有 guard、不覆盖运行时状态文件并发
- **ROI**: 把本次冲突固化为可复用检测能力，避免未来同类事件
