# 设计：并发工作区守护（Concurrent Workspace Guard）

> 完整技术设计见 [`docs/CONCURRENT_GUARD_DESIGN.md`](../../../docs/CONCURRENT_GUARD_DESIGN.md)（454 行，含事件样本分析、能力矩阵、接口逐项说明、验证矩阵与实施计划）。本文件只记录**设计层面的取舍与决策**，不重复该文档的内容。

## Context

2026-09-26 一次常规提交任务中暴露并行冲突：会话基于过期基线 `main@81a02c5` 准备改动，而 `main` 已被并行协作者推进，HEAD 漂移到 `refactor/slimming-2026-09-20`，工作区混入 486+ 行他人未提交改动。

既有治理层与服务层覆盖的是**运行时状态文件并发**（`workspace_guard.py` / `spawn_agent_guard.py`），不覆盖**开发时 git 工作区并发**。本变更补的是后者：分支漂移、基线过期、归属不清、测试污染四类缺口。

约束：本地优先、零云依赖、不引入新依赖、不改变既有 guard 的行为。

## Goals / Non-Goals

**Goals**

- 在提交/派单前给出**可判定**的并发风险结论（放行 / 阻断），而不是给人看的提醒。
- 结论必须**落盘留痕**，事后能复盘「当时看到了什么」。
- 治理层与被治理仓库**解耦**：同一套守卫能用在任何共享工作区上。
- 分层：只有 **git 硬证据**可以阻断，启发式判断只能软警告。

**Non-Goals**（与 proposal 一致）

- 不自动解决 git 冲突。
- 不强制 worktree 隔离。
- 不替代既有 guard（`workspace_guard` / `spawn_agent_guard`）。
- 不覆盖运行时状态文件并发。
- 不新增第三方依赖。

## Decisions

### D1：按证据强度分层，而不是按「检测项重要性」分层

| 层 | 检测项 | 证据 | 处置 |
|---|---|---|---|
| G1 | 分支漂移 | git 硬证据 | **阻断**（违规） |
| G2 | 基线过期 | git 硬证据 | **阻断**（违规） |
| G3 | 归属不明改动 | mtime 启发式 | **软警告**（默认） |

**理由**：mtime 启发式会误报（文件被 checkout、恢复、rsync 都会改 mtime），把启发式当阻断依据会让门禁变成「随机拒绝」，最终会被绕过或整体关闭。git 硬证据不会误报。

**备选方案**：全部阻断。否决——G3 误报率不可控。
**备选方案**：全部只警告。否决——分支漂移是 2026-09-26 事故的直接成因，放成警告等于没门禁。

### D2：G3 的严重级别可配置，默认 `warning`

`foreignChangeSeverity` 可设为 `high` 让 G3 也阻断，但**默认不阻断**。

**理由**：默认值应取「不会误伤正常协作」的那一端；需要强约束的团队显式打开。

### D3：运行时配置源是 `.vscode/ai-collab.json`，不是 `config/agent-orchestration.json`

原任务描述写的是 `config/agent-orchestration.json`，实测**运行时配置源不是它**：`VSCodeIntegration.get_project_config()` 读的是 `.vscode/ai-collab.json`（`ai_collab/integrations/vscode.py:77`）。`config/agent-orchestration.json` 是**角色编排**配置，语义不同。

**决策**：配置接入 `.vscode/ai-collab.json` 的 `concurrentGuard` 段，`config/agent-orchestration.json` 及其 schema/template **不动**。

**理由**：配置项必须落在**真正会被读到**的地方；写到不生效的配置文件里，等于没配还多一份误导性文档。

### D4：未声明期望分支时跳过分支检测

`expectedBranch` 为 `null` 时不产生分支漂移违规。

**理由**：分支约定是**团队/会话级**的，硬编码一个默认分支会误伤所有不在该分支上的会话。宁可不检测，也不给假阻断。

### D5：报告落点相对「被治理工作区」解析，默认 `logs/workspace_forensics/`

`run_concurrent_guard(workspace=...)` 的报告与历史路径都是相对 `workspace` 解析的，可通过 `guard_config` 覆盖。

**理由**：守护器是治理层，被治理对象是工作区。报告若落在固定仓库里，就绑死了「只能治理本仓」——跨工作区复用无从谈起。

**推论（已由测试钉住）**：在外部工作区上调用时**必须**显式传 `guard_config` 指向该工作区内部的路径，否则会污染本仓的 `logs/`。

### D6：CLI 参数优先于项目配置

取值顺序：命令行参数 > `.vscode/ai-collab.json` 的 `concurrentGuard` 段 > 内置默认值。

**理由**：CLI 是一次性覆盖的常规手段，优先级最高；配置文件是持久化默认值。

**附带坑**：argparse 的嵌套子解析器会把子命令参数拷进父命名空间，子级 `--workspace` 若用普通默认值会**用 `None` 覆盖全局值**。因此子级 `--workspace` 用 `default=argparse.SUPPRESS`。

### D7：`enabled=false` 或 `force=True` 时放行，但仍记录结论

放行不等于不记录：报告里保留 `enabled` / `forced` 标记与全部信号。

**理由**：需要「强制通过」的场景（紧急提交、门禁自身故障排查）必须留痕，否则事后无法区分「真的没问题」和「被强制放行」。

### D8：复用既有 guard 的报告落点约定

`latest.json`（最新结论）+ `history.jsonl`（逐次追加）沿用 `workspace_guard` 的既有约定。

**理由**：一致性——运维/复盘时不需要为每种 guard 学一套落盘格式。

## Risks / Trade-offs

- **[mtime 启发式误报]** → 默认降级为软警告；`foreignChangeSeverity` 可升级；严重级别由调用方按场景选择。
- **[期望分支约定过严影响现有流程]** → `expectedBranch` 默认 `null`（跳过），由会话显式声明。
- **[与并行协作者工作区冲突]** → 本变更不修改他人未提交改动；实施前先核实归属。
- **[门禁被当成万能钥匙]** → `force` 在报告中留痕（`forced: true`），强制放行可被审计。
- **[结论自洽性被破坏]** → `allowed` ⇔ 无违规、`risk_level` 与违规/警告数量一致，由测试断言。
- **[新增守护模块与既有 guard 职责重叠]** → 二者覆盖不同并发面（运行时状态文件 vs 开发时 git 工作区），本变更不修改既有 guard。

## Migration Plan

无破坏性迁移：

1. 新增 `ai_collab/concurrent_guard.py`（新模块，不改动既有模块行为）。
2. `.vscode/ai-collab.json` 新增 `concurrentGuard` 顶层段（新增键，不改既有键）。
3. `collaboration/PROTOCOL.md` 新增第十四章（新增章节）。
4. CLI 新增 `concurrent guard` 子命令（新增子命令，不改既有子命令）。

**回滚**：删除 `concurrent_guard.py` 与 `concurrent guard` 子命令、移除 `.vscode/ai-collab.json` 的 `concurrentGuard` 段、删除新增测试文件即可；既有 guard 与 CLI 子命令不受影响。运行时产物 `logs/workspace_forensics/concurrent_guard_*.json*` 可直接删除（`logs/` 不进版本库）。

**启用顺序建议**：先以 `expectedBranch: null` 跑一段时间观察误报，再按会话显式声明期望分支。

## Open Questions

无。以下问题**不影响**本变更的 spec、取舍与任务拆分，留待后续工单处理：

- 共识引擎（`ConsensusEngine.cache`）的无锁并发语义是否需要加锁/去重——属独立工单，本变更不涉及。
- 门禁是否应在派单链路中**自动调用**（当前需显式运行 `concurrent guard`）。
