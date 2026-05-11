# AI Integration Mode Governance

## Why

当前项目中多个 AI 集成模块（NotebookLM、Consensus Engine、Soul Injection Engine）存在 MVP 模拟逻辑，导致：

- **模拔回退不透明**：无法区分真实响应与模拟响应，影响调试与质量评估
- **生产环境风险**：模拟逻辑可能意外流入生产，降低交付质量
- **迁移路径缺失**：从模拟到真实适配的演进路径不明确，缺乏治理框架
- **测试/生产混淆**：同一代码同时服务于测试和生产，增加维护复杂度

需要一个统一的 AI 集成模式治理框架，明确 Mock/Fallback/Real 三种模式，并提供清晰的迁移路径。

## What Changes

### 新增能力
1. **集成模式定义与配置**
   - 定义三种集成模式：`mock`（仅测试）、`fallback`（优先真实，失败回退）、`real`（仅生产）
   - 创建统一配置文件 `src/ai_collab/config/integration_flags.py`
   - 支持环境变量覆盖：`AI_INTEGRATION_MODE`

2. **模拟响应规范化**
   - 所有模拟响应添加 `_mock=True` 和 `_mock_reason` 标记
   - 添加警告日志，明确标注 MVP 模式
   - 文档化每个集成模块的回退策略

3. **健康检查与监控**
   - 添加集成健康检查端点
   - 支持按模块查询当前模式
   - 记录模拟响应频次与触发原因

### 不包含（Scope Out）
- 实现 Real 模式的真实 MCP 集成（需要独立工单）
- 大规模重构 Mock 层分离（长期目标，不在本提案范围）
- 修改现有 CLI 参数或用户接口

## Impact

- **Affected specs**: `ai-integration-mode` (新增 spec)
- **Affected code**:
  - `src/ai_collab/config/integration_flags.py` (新增)
  - `src/ai_collab/integrations/notebooklm.py` (修改：添加标记与警告)
  - `src/ai_collab/engines/consensus_engine.py` (修改：添加标记与警告)
  - `src/ai_collab/engines/soul_injection_engine.py` (修改：添加标记与警告)
  - `tests/unit/test_integration_flags.py` (新增测试)

- **Risk Assessment**:
  - **低风险**：仅添加配置和标记，不修改核心逻辑
  - **向后兼容**：默认行为保持不变（FALLBACK 模式）
  - **可回滚**：所有变更可通过 git checkout 快速回退

- **Migration Path**:
  1. **Phase 1**（本次提案）：添加配置文件与模拟响应标记
  2. **Phase 2**（独立工单）：实现 Fallback 模式的异常驱动回退
  3. **Phase 3**（独立工单）：实现 Real 模式的真实 MCP 集成
  4. **Phase 4**（长期）：分离 Mock 层，生产代码纯净化

## Success Criteria

1. 新增 `src/ai_collab/config/integration_flags.py`，定义 `IntegrationMode` 枚举与默认模式
2. 所有模拟响应添加 `_mock` 标记，可通过日志识别
3. 测试覆盖模式查询、环境变量覆盖、标记验证
4. 文档说明三种模式的使用场景与配置方法
5. OpenSpec 验证通过：`openspec validate add-ai-integration-mode-governance --strict`

## Alternatives Considered

### Alternative 1: 直接分离 Mock 层
- **优点**：生产代码纯净，符合最佳实践
- **缺点**：重构工作量大，可能引入回归风险
- **结论**：作为长期目标（Phase 4），不在本次提案范围

### Alternative 2: 异常驱动的自动回退
- **优点**：自动回退，无需手动配置
- **缺点**：需要实现真实版本方法，增加复杂度
- **结论**：作为 Phase 2 的实施方案

### Alternative 3: 无需治理，保持现状
- **优点**：无需改动
- **缺点**：模拔回退不透明，生产风险高
- **结论**：无法满足生产质量要求，不可接受
