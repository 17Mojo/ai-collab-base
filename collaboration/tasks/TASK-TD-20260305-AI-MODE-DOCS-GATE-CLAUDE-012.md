# 任务: AI Integration 模式治理 - 文档与门禁收口

**任务ID**: TASK-TD-20260305-AI-MODE-DOCS-GATE-CLAUDE-012  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [devops-architect, compliance-checker, api-test-pro]
- **scope_in**: 补齐 AI 模式治理文档（协作规范/架构说明/使用指南），并执行 OpenSpec + 测试门禁收口。
- **scope_out**: 不新增业务功能，不更改现有部署拓扑。

## 输入

- 文件: COLLABORATION_GUIDELINES.md, ARCHITECTURE.md, docs/, openspec/changes/add-ai-integration-mode-governance/, tests/unit/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-DOCS-GATE-CLAUDE-012.md`
- 必须包含: 文档变更摘要、门禁命令结果、风险与回滚

## acceptance_commands（必填）

```bash
openspec validate add-ai-integration-mode-governance --strict
python3 -m pytest -q tests/unit/test_integration_flags.py tests/unit/test_ai_integration_mock_flags.py
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
