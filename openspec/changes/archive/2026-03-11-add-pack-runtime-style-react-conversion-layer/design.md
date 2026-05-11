## Context

目标是在不破坏既有 Prompt Pack 执行路径的前提下，补齐两条链路：
1. 执行链路：Operator 运行时风格微调。
2. 编辑链路：Owner 自然语言需求到 Pack 草案的标准转换。

现状：
- Popup 支持导入与执行，但执行请求 `input` 默认空对象，未携带风格参数。
- 后端/引擎已有 soul/profile 能力，但未形成统一执行协议。
- 需求到 JSON 的转换主要依赖人工经验，缺少标准产物与审计轨迹。

## Goals / Non-Goals

- Goals:
  - 建立运行时风格覆盖协议，且不回写基线 JSON。
  - 建立 ReAct 转换层标准流程与交付物。
  - 建立 schema + 合规双闸的最小门禁。
  - 交付可派发任务与可执行验收命令。
- Non-Goals:
  - 不实现 GUI 内完整 JSON 编辑。
  - 不实现自动化发布编排。
  - 不重构全部 Pack 架构。

## Decisions

- Decision 1: 运行时覆盖参数走消息协议 `runtime_overrides`
  - 执行请求新增 `data.runtime_overrides` 字段。
  - 白名单字段：`style_profile`, `tone`, `length`, `compliance_level`, `temperature_bias`。
  - 理由：最小增量接入，不改动已有 `input` 语义。

- Decision 2: 覆盖参数仅作用于执行上下文
  - 执行时合并为 `effective_config`，禁止写回 Pack 文件与存储主副本。
  - 理由：保证模板稳定与审计一致性。

- Decision 3: ReAct 转换层采用固定产物协议
  - 输入：Owner 转换单（自然语言诉求 + 约束）。
  - 输出：`draft_pack.json` + `change_manifest.md` + `validation_report.md`。
  - 理由：便于跨角色协作与回溯。

- Decision 4: 双闸校验
  - 结构闸：`PromptPackV2.from_dict` 与 `validate()`。
  - 业务闸：合规规则覆盖、禁用词策略、行业指标完整性。
  - 理由：避免“结构合法但业务违规”。

## Risks / Trade-offs

- 风险：运行时覆盖字段过多引入行为分歧
  - 缓解：白名单 + 默认值 + 非法值回退。
- 风险：ReAct 转换输出不稳定
  - 缓解：固定模板 + 必填项校验 + 审核清单。
- 风险：测试成本上升
  - 缓解：优先覆盖协议和门禁路径，逐步扩展场景测试。

## Migration Plan

1. 定义协议与字段白名单。
2. 实现 Popup -> Content -> Executor 透传链路。
3. 实现转换层草案输出与校验报告。
4. 增加单测/集成/E2E，先在 CI dry-run。
5. 渐进启用并观察回归指标。

## Open Questions

- `runtime_overrides` 是否需要按平台进一步分组（如 xiaohongshu_only）？
- ReAct 转换层首版放 CLI 还是服务端 API（当前建议 CLI 优先）？
