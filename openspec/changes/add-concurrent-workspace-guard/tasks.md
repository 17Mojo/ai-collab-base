# Implementation Tasks

## Phase 1: 治理层（协议 + OpenSpec）

- [x] 1.1 产出技术设计文档 `docs/CONCURRENT_GUARD_DESIGN.md`
- [x] 1.2 `collaboration/PROTOCOL.md` 新增第十四章「并发工作区安全」
- [x] 1.3 创建 OpenSpec change `add-concurrent-workspace-guard/`

## Phase 2: 服务层（concurrent_guard + CLI gate）

### 2.1 核心模块

- [ ] 2.1.1 实现 `inspect_git_context(workspace)` — 收集 branch/head/upstream/dirty
- [ ] 2.1.2 实现 `detect_branch_drift(workspace, expected_branch)` — 分支漂移检测
- [ ] 2.1.3 实现 `detect_baseline_staleness(workspace, baseline_commit, watch_paths)` — 基线过期检测
- [ ] 2.1.4 实现 `detect_foreign_changes(workspace, session_started_at)` — 归属检测（mtime 启发式）
- [ ] 2.1.5 实现 `assess_concurrent_risk(...)` — 综合风险评级
- [ ] 2.1.6 报告持久化（latest.json + history.jsonl，对齐现有 guard 约定）

### 2.2 CLI 接入

- [ ] 2.2.1 在 `_cli_main.py` 加 `_run_concurrent_guard_gate`
- [ ] 2.2.2 加 CLI 子命令 `concurrent guard`
- [ ] 2.2.3 配置项接入 `agent-orchestration.json` 的 `concurrentGuard` 段

## Phase 3: 测试层（守护 + 冲突样本）

- [ ] 3.1 `tests/unit/test_concurrent_guard.py` — TestInspectGitContext
- [ ] 3.2 TestBranchDrift（漂移/未漂移/expected=None）
- [ ] 3.3 TestBaselineStaleness（过期/未过期/无变更）
- [ ] 3.4 TestForeignChanges（有/无 foreign + mtime 边界）
- [ ] 3.5 TestAssessRisk（high/medium/low 三级）
- [ ] 3.6 TestRegressionSample20260926 — 本次冲突完整复现（mini git repo fixture）
- [ ] 3.7 ruff lint 全绿 + 全量回归无新增失败

## Phase 4: 研究项目（暂缓）

- [ ] 4.1 pytest `norecursedirs` 隔离 `hermes_target`
- [ ] 4.2 修 `test_consensus_engine.py` 导入 + 并发守护
- [ ] 4.3 在 hermes_target 上验证 concurrent guard 复用
