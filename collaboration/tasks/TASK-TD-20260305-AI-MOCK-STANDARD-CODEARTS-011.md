# 任务: AI Integration 模式治理 - 模拟响应标准化

**任务ID**: TASK-TD-20260305-AI-MOCK-STANDARD-CODEARTS-011  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, api-test-pro]
- **scope_in**: 在 NotebookLM/Consensus/Soul Injection 三个模块中统一添加 `_mock` 与 `_mock_reason` 标记和警告日志，并补充对应单测。
- **scope_out**: 不实现真实 MCP 集成，不调整外部 API 契约。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/engines/consensus_engine.py, src/ai_collab/engines/soul_injection_engine.py, tests/unit/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MOCK-STANDARD-CODEARTS-011.md`
- 必须包含: 执行命令、变更点、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py
python3 -m ruff check src/ai_collab/integrations src/ai_collab/engines tests/unit/test_ai_integration_mock_flags.py
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
