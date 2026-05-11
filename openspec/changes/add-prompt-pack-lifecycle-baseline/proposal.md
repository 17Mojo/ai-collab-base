# 建立 Prompt Pack 生命周期 OpenSpec 基线

## Why

当前项目已进入“OpenSpec 管能力、工单管执行”的治理模式，但 `openspec/specs/` 为空，导致 Prompt Pack 生成/审核/迭代/归档缺乏可验证的能力基线，后续变更难以审计。

## What Changes

- 新增 Prompt Pack 生命周期能力规范基线（Generation/Review/Iteration/Archive）。
- 定义 OpenSpec 变更与工单派发的映射约束（`change_id` 绑定、结果文件要求、验收命令）。
- 增加执行示例，明确“何时必须走 OpenSpec，何时可直接走 bugfix/no-spec”。

## Impact

- Affected specs: `prompt-pack-lifecycle`
- Affected docs: `openspec/project.md`, `collaboration/PROTOCOL.md`, `collaboration/templates/*`
- 风险: 基线过宽会抬高小变更成本，需要明确边界与例外策略。
