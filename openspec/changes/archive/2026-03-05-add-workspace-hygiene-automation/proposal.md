# 增加工作区/暂存区链路自动治理（Workspace Hygiene Automation）

## Why

当前系统虽然具备 `stage-source/stage-ops/stage-docs/stage-other` 与 `stage-safe`，但仍依赖人工触发，存在两个持续风险：
- 工作区与暂存区堆积，导致误操作窗口扩大（尤其跨 Sprint 连续执行后）
- 工单收口后未及时治理，后续回滚与审计成本上升

需要把“工作区治理”从人工步骤升级为自动流程，使其成为控制面的默认保障能力。

## What Changes

- 新增工作区治理自动流程（Workspace Hygiene Loop）：
  - **定时轮询**：按配置周期自动执行巡检与分域治理
  - **收口后即时触发**：在 `receipt` 成功收口后自动触发一次治理流程
- 新增治理命令入口（例如 `hygiene`）：
  - 统一执行：门禁评估 → `stage-safe` 预览 → 条件满足后执行分域暂存
  - 支持 `--dry-run`、域顺序配置、阈值策略
- 新增“可回滚安全点”机制（非破坏性）：
  - 每次自动治理写入带时间戳的清单/快照引用（不自动提交、不自动推送）
  - 记录治理前后文件计数与域分布，便于误操作后追溯
- 新增配置段（`workspaceHygiene`）：
  - `enabled`, `pollIntervalMinutes`, `onReceiptClose`, `domainOrder`, `maxCandidatesPerRun`, `autoStage`, `createCheckpoint`
- 新增测试覆盖：
  - CLI 路由、轮询判定、收口触发、门禁阻断与快照记录

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/cli.py`
  - `ai_collab/workspace_guard.py`
  - `scripts/agent_receipt_bridge.py`（或 receipt 调用链）
  - `tests/unit/test_cli.py`
  - `tests/unit/test_safe_stage.py`
- 风险控制:
  - 默认只做安全暂存，不做自动 commit/push
  - 门禁不通过时只记录告警，不强制破坏性动作
