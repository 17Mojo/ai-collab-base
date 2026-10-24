# Implementation Tasks

## Phase 1: 治理层（协议 + OpenSpec）

- [x] 1.1 产出技术设计文档 `docs/CONCURRENT_GUARD_DESIGN.md`
- [x] 1.2 `collaboration/PROTOCOL.md` 新增第十四章「并发工作区安全」
- [x] 1.3 创建 OpenSpec change `add-concurrent-workspace-guard/`

## Phase 2: 服务层（concurrent_guard + CLI gate）

### 2.1 核心模块

- [x] 2.1.1 实现 `inspect_git_context(workspace)` — 收集 branch/head/upstream/dirty
- [x] 2.1.2 实现 `detect_branch_drift(workspace, expected_branch)` — 分支漂移检测
- [x] 2.1.3 实现 `detect_baseline_staleness(workspace, baseline_commit, watch_paths)` — 基线过期检测
- [x] 2.1.4 实现 `detect_foreign_changes(workspace, session_started_at)` — 归属检测（mtime 启发式）
- [x] 2.1.5 实现 `assess_concurrent_risk(...)` — 综合风险评级
- [x] 2.1.6 报告持久化（latest.json + history.jsonl，对齐现有 guard 约定）

### 2.2 CLI 接入

- [x] 2.2.1 在 `_cli_main.py` 加 `_run_concurrent_guard_gate`
- [x] 2.2.2 加 CLI 子命令 `concurrent guard`
- [x] 2.2.3 配置项接入 `.vscode/ai-collab.json` 的 `concurrentGuard` 段
      > **注记（与原任务描述的偏离，已按运行时事实修正）**：原任务写的是
      > `agent-orchestration.json`，但实测**运行时配置源不是该文件**——
      > `VSCodeIntegration.get_project_config()` 读的是 `.vscode/ai-collab.json`
      > （`ai_collab/integrations/vscode.py:77`）；`config/agent-orchestration.json`
      > 是角色编排配置，语义不同。本次只动 `.vscode/ai-collab.json`（新增顶层
      > `concurrentGuard` 段），**未改** `config/agent-orchestration.json` 及其
      > schema/template。

## Phase 3: 测试层（守护 + 冲突样本）

- [x] 3.1 `tests/unit/test_concurrent_guard.py` — TestInspectGitContext
- [x] 3.2 TestBranchDrift（漂移/未漂移/expected=None）
- [x] 3.3 TestBaselineStaleness（过期/未过期/无变更）
- [x] 3.4 TestForeignChanges（有/无 foreign + mtime 边界）
- [x] 3.5 TestAssessRisk（high/medium/low 三级）
- [x] 3.6 TestRegressionSample20260926 — 本次冲突完整复现（mini git repo fixture）
- [x] 3.7 ruff lint 全绿 + 全量回归无新增失败

## Phase 4: 项目边界（暂缓）

- [x] 4.1 pytest 收集边界：仓库内不存放外部项目副本，`testpaths` 限定 `tests/`
      > 由 `tests/unit/test_project_boundary_guard.py` 守护（5 条）：`testpaths`
      > 取 pytest 自身解析出的生效值；`tests/` 之外无 pytest 会收集的测试文件、
      > 无越界 conftest.py；主套件 `--collect-only` 无收集错误；守护用例自身位于
      > `tests/` 之下。
- [x] 4.2 修 `test_consensus_engine.py` 导入 + 并发守护
      > 导入本就正常（`from ai_collab.engines.consensus_engine import ConsensusEngine`
      > 解析成功，既有 20 条用例全绿）；并发守护由
      > `tests/unit/test_consensus_engine_concurrency.py` 补齐（5 条），
      > 把 `ConsensusEngine.cache` 的**当前**无锁语义钉成契约，并在
      > `generate_consensus` 的 docstring 里写明。
- [x] 4.3 验证 concurrent guard 在任意共享工作区的复用
      > 由 `tests/unit/test_concurrent_guard_reuse.py` 守护（3 条）：在与本仓无关的
      > mini git repo 上实跑，报告落在该 repo 内、本仓 `logs/` 未被写入；
      > 同一套守卫在本仓上报告仍落在本仓 `logs/workspace_forensics/`。
