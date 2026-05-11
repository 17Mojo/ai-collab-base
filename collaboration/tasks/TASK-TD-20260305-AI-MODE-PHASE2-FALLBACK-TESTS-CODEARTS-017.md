# 任务: AI Integration 模式治理 - Phase2 回退链路测试加固

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE2-FALLBACK-TESTS-CODEARTS-017  
**change_id**: add-ai-integration-mode-governance  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [ai-integration-engineer]
- **scope_in**: 增加 fallback 触发、异常注入、mock 标记一致性测试，并固化到单测门禁。
- **scope_out**: 不改业务逻辑，不新增线上部署依赖。

## 输入

- 文件: tests/unit/test_ai_integration_mock_flags.py, tests/unit/test_codex_integration.py, src/ai_collab/integrations/*

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE2-FALLBACK-TESTS-CODEARTS-017.md`
- 必须包含: 新增用例清单、失败注入样本、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_ai_integration_mock_flags.py tests/unit/test_codex_integration.py
python3 -m ruff check tests/unit/test_ai_integration_mock_flags.py tests/unit/test_codex_integration.py
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

