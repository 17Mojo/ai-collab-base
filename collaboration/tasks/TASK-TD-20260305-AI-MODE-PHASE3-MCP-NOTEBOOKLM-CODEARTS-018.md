# 任务: AI Integration 模式治理 - Phase3 NotebookLM 真实 MCP 接入

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE3-MCP-NOTEBOOKLM-CODEARTS-018  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, devops-architect]
- **scope_in**: 为 NotebookLM 集成实现真实 MCP 调用路径，并与 `IntegrationMode` 开关联动。
- **scope_out**: 不扩展到其他引擎，不变更任务状态机。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/config/integration_flags.py, tests/unit/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE3-MCP-NOTEBOOKLM-CODEARTS-018.md`
- 必须包含: MCP 接入点、开关联动说明、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_integration_flags.py
python3 -m ruff check src/ai_collab/integrations/notebooklm.py src/ai_collab/config/integration_flags.py
openspec validate add-ai-integration-mode-governance --strict
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

