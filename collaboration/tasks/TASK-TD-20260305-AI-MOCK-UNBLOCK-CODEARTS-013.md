# 任务: AI Integration 模式治理 - Mock 标准化解阻与收口

**任务ID**: TASK-TD-20260305-AI-MOCK-UNBLOCK-CODEARTS-013  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, api-test-pro]
- **scope_in**: 完成 openspec 2.x + 3.2/3.3：为 NotebookLM/Consensus/Soul Injection 模块补齐 `_mock` 与 `_mock_reason` 标记、警告日志，并创建缺失测试 `tests/unit/test_ai_integration_mock_flags.py`，解决 `011` 阻塞。
- **scope_out**: 不接入真实 MCP，不变更外部 API 契约，不重构业务流程。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/engines/consensus_engine.py, src/ai_collab/engines/soul_injection_engine.py, src/ai_collab/config/integration_flags.py, collaboration/results/RESULT_TASK-TD-20260305-AI-MOCK-STANDARD-CODEARTS-011.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MOCK-UNBLOCK-CODEARTS-013.md`
- 必须包含: 阻塞根因修复说明、执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_codex_integration.py
python3 -m ruff check src/ai_collab/integrations/notebooklm.py src/ai_collab/engines/consensus_engine.py src/ai_collab/engines/soul_injection_engine.py tests/unit/test_ai_integration_mock_flags.py
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
