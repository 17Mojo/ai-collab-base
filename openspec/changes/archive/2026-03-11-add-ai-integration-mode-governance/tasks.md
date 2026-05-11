# Tasks

## 1. Configuration Foundation
- [x] 1.1 创建 `src/ai_collab/config/__init__.py` 目录结构
- [x] 1.2 创建 `src/ai_collab/config/integration_flags.py`，定义 `IntegrationMode` 枚类（MOCK/FALLBACK/REAL）
- [x] 1.3 实现 `DEFAULT_INTEGRATION_MODES` 字典，配置各模块默认模式
- [x] 1.4 实现工具函数：`get_mode()`, `is_mock_mode()`, `should_use_fallback()`

## 2. Mock Response Standardization
- [x] 2.1 修改 `src/ai_collab/integrations/notebooklm.py`：
  - 在所有模拟响应中添加 `_mock=True` 和 `_mock_reason`
  - 添加模块级警告日志，标注 MVP 模式
- [x] 2.2 修改 `src/ai_collab/engines/consensus_engine.py`：
  - 在 `_query_multiple_ais()` 的模拟响应中添加标记
  - 添加模块级警告日志
- [x] 2.3 修改 `src/ai_collab/engines/soul_injection_engine.py`：
  - 在 `_apply_style()` 的模拟响应中添加标记
  - 添加模块级警告日志

## 3. Testing & Validation
- [x] 3.1 创建 `tests/unit/test_integration_flags.py`：
  - 测试模式查询函数
  - 测试环境变量覆盖逻辑
  - 测试标记验证工具
- [x] 3.2 验证所有模拟响应可通过 `_mock` 字段识别
- [x] 3.3 验证警告日志在模拟模式下正常输出

## 4. Documentation
- [x] 4.1 更新 `COLLABORATION_GUIDELINES.md`，说明 AI 集成模式治理规则
- [x] 4.2 添加配置说明到 `ARCHITECTURE.md`，说明三种模式的使用场景
- [x] 4.3 创建 `docs/ai-integration-mode-guide.md`，提供配置示例与最佳实践

## 5. Quality Gates
- [x] 5.1 `pytest -q tests/unit/test_integration_flags.py tests/unit/test_codex_integration.py`
- [x] 5.2 `python3 -c "from src.ai_collab.config.integration_flags import get_mode; print(get_mode('notebooklm'))"`
- [x] 5.3 `python3 -m ai_collab.cli tasks validate-contract --scope active --strict`

## 6. OpenSpec Validation
- [x] 6.1 创建 `ai-integration-mode` spec（spec delta 文档）
- [x] 6.2 `openspec validate add-ai-integration-mode-governance --strict`
- [x] 6.3 `openspec show add-ai-integration-mode-governance --json --deltas-only`

## 7. Migration Planning (Future Phases)
- [x] 7.1 创建 Phase 2 实施工单（异常驱动回退）
- [x] 7.2 创建 Phase 3 实施工单（真实 MCP 集成）
- [x] 7.3 创建 Phase 4 实施工单（Mock 层分离）

## Dependencies & Blocking
- ✅ **Available Now**: 基于 `RESULT_TASK-TD-20260305-AI-INTEGRATION-CLAUDE-003` 的分析结果
- ⏳ **Blocked Until**: Codex 审核并批准本提案
- ⏳ **Parallel Work Items**: 可并行执行 1.x 和 2.x 任务
