# 任务: AI Integration 模式治理 - Phase4 Mock 层分离

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE4-MOCK-LAYER-SPLIT-CODEARTS-020  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [ai-integration-engineer, api-test-pro]
- **scope_in**: 将模拟响应逻辑从业务引擎中拆分到独立 mock provider 层，降低生产路径耦合。
- **scope_out**: 不新增业务能力，不修改外部接口字段。

## 输入

- 文件: src/ai_collab/integrations/, src/ai_collab/engines/, tests/unit/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE4-MOCK-LAYER-SPLIT-CODEARTS-020.md`
- 必须包含: 分层设计、迁移步骤、兼容性结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_integration_flags.py
python3 -m ruff check src/ai_collab/integrations src/ai_collab/engines
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

