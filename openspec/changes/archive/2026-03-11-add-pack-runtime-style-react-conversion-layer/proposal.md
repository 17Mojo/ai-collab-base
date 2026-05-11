# 增加 Prompt Pack 运行时风格微调与 ReAct 需求转换层

## Why

当前 Prompt Pack 链路存在两个关键缺口：

- **执行侧缺口**：Operator 无法在执行时安全微调风格（如 style_profile/tone/length），只能依赖固定 JSON，导致“个体执行风格”与“标准模板”难兼容。
- **编辑侧缺口**：Owner 的自然语言诉求缺乏标准化转换层，需求无法稳定映射到可审计的 Pack 元素组合与校验流程。

需要在不破坏现有导入/执行主链路的前提下，补齐“运行时风格覆盖 + ReAct 转换闭环”能力。

## What Changes

### 新增能力

1. **Prompt Pack 运行时风格微调能力（Runtime Overrides）**
   - 在扩展 Popup 增加运行时参数字段（如 `style_profile`、`tone`、`length`、`compliance_level`）。
   - 扩展 `executePack` 消息协议，支持透传 `runtime_overrides`。
   - 执行引擎在运行时合并覆盖参数，不回写基线 Pack JSON。

2. **ReAct 需求转换层（Owner NL -> Pack Draft）**
   - 建立固定 6 步转换流程：需求拆解、元素检索、冲突观察、组合推理、草案生成、校验观察。
   - 输出标准产物：候选 Pack 草案、继承/变更清单、校验报告、测试建议。
   - 要求转换结果通过 schema 与业务合规双闸。

3. **门禁与测试闭环**
   - 对 `runtime_overrides` 增加白名单与边界校验。
   - 对转换草案增加 `PromptPackV2.from_dict + validate()` 校验。
   - 补充单测、集成测与扩展宿主 E2E，确保 CI 可跑。

### Scope Out

- 不在本次变更中实现可视化 JSON 编辑器。
- 不在本次变更中实现自动发布到线上平台。
- 不在本次变更中引入新的外部模型供应商。

## Impact

- Affected specs:
  - `prompt-pack-runtime-style`（新增）
  - `pack-requirement-conversion`（新增）
- Affected code（预期）:
  - `products/prompt-pack-extension/chrome/src/popup/index.html`
  - `products/prompt-pack-extension/chrome/src/popup/popup.js`
  - `products/prompt-pack-extension/chrome/src/content/message-handler.js`
  - `products/prompt-pack-extension/chrome/src/content/pack-executor.js`
  - `src/ai_collab/pack/*`（转换层/校验适配）
  - `tests/unit/*`, `tests/e2e/*`
- 风险控制:
  - 保持默认无覆盖参数时的旧行为兼容。
  - 使用白名单避免运行时参数污染核心结构。
  - 使用 feature flag/渐进启用降低回归风险。
