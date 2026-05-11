## Context

目标是在不引入高风险自动提交的前提下，把“工作区与暂存区治理”自动化，减少人工胶水操作与堆积风险。

现状：
- 已有分域安全暂存命令：`stage-source/stage-ops/stage-docs/stage-other/stage-safe`
- 已有工作区门禁：`workspace-guard`
- 缺失：定时巡检与收口后自动治理触发

## Goals / Non-Goals

- Goals:
  - 自动巡检并按域治理，降低堆积
  - 工单收口后自动触发一次治理，缩短暴露窗口
  - 全流程可追踪、可回滚、默认非破坏
- Non-Goals:
  - 自动 commit / push
  - 自动删除文件或强制 reset
  - 替代现有人工审核点

## Decisions

- Decision 1: 引入统一命令 `hygiene`
  - 行为：`workspace-guard` → `stage-safe --dry-run` → 按策略执行 `stage-safe`
  - 理由：复用现有能力，最小增量

- Decision 2: 收口后触发采用“同步轻触发”
  - 在 `receipt` 成功后根据 `workspaceHygiene.onReceiptClose` 执行一次 `hygiene`
  - 理由：确保每次收口后立即降堆积

- Decision 3: 定时轮询采用“可选启用”
  - `workspaceHygiene.enabled=true` 时由 controller/daemon 周期触发
  - 理由：兼容不同运行环境与资源预算

- Decision 4: 回滚保障采用“快照日志”而非自动提交
  - 写入 `logs/workspace_forensics/hygiene_latest.json` + history JSONL
  - 记录候选计数、域分布、样例路径、执行结果
  - 理由：审计充分且风险低

## Risks / Trade-offs

- 风险：轮询频率过高导致噪声日志过多
  - 缓解：最小轮询间隔 + 仅变更时落详细记录
- 风险：自动暂存覆盖开发者临时状态预期
  - 缓解：默认仅 ops/docs/other；source 需显式开启
- 风险：收口后附加动作增加命令耗时
  - 缓解：超时保护 + 失败降级为告警

## Migration Plan

1. 增加 `workspaceHygiene` 配置默认值（关闭定时轮询，开启收口后触发）
2. 实现 `hygiene --dry-run` 与 `hygiene` 命令
3. 接入 `receipt` 后触发
4. 加入 controller 周期调用入口
5. 测试通过后启用到默认流程

## Open Questions

- 是否默认将 `source` 纳入自动治理域？（建议默认否）
- 定时轮询默认周期设为 10 分钟还是 15 分钟？（建议 15）
