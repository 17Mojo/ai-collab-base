# 任务: AI Integration 模式治理 - Phase2 异常驱动回退硬化

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE2-FALLBACK-HARDEN-CLAUDE-016  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, api-test-pro]
- **scope_in**: 在 notebooklm/consensus/soul_injection 增加统一的 try-real-then-fallback 逻辑，显式记录 fallback 触发原因。
- **scope_out**: 不接入真实 MCP，不改现有外部 API 契约。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/engines/consensus_engine.py, src/ai_collab/engines/soul_injection_engine.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE2-FALLBACK-HARDEN-CLAUDE-016.md`
- 必须包含: 变更点、异常分支说明、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_codex_integration.py
python3 -m ruff check src/ai_collab/integrations src/ai_collab/engines
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

