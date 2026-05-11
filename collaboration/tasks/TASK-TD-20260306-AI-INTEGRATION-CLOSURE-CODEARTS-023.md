# 任务: AI Integration 生产闭环 - Mock 标记与健康端点补齐

**任务ID**: TASK-TD-20260306-AI-INTEGRATION-CLOSURE-CODEARTS-023  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, api-test-pro]
- **scope_in**: 为 notebooklm/consensus/soul_injection 的模拟响应统一 `_mock/_mock_reason` 字段，补充 integration health 输出（mode/fallback/配置来源）并加测试。
- **scope_out**: 不接入真实 MCP，不修改对外 API 主路径契约。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/engines/consensus_engine.py, src/ai_collab/engines/soul_injection_engine.py, local-backend/app/api/health.py, tests/unit/test_ai_integration_mock_flags.py, tests/unit/test_integration_flags.py
- 依赖: TASK-TD-20260306-OPENSPEC-CLOSURE-CLAUDE-022

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-AI-INTEGRATION-CLOSURE-CODEARTS-023.md`
- 必须包含: mock 标记矩阵、health 字段定义、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_integration_flags.py tests/integration/test_api.py
python3 -m ruff check src/ai_collab/config src/ai_collab/integrations src/ai_collab/engines local-backend/app
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled

