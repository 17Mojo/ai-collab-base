# 任务: 技术债工单 - UI 可访问性与视觉基线补齐

**任务ID**: TASK-TD-20260305-UI-BASELINE-CODEARTS-002  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: ui-designer
- **support_skills**: [frontend-architect, api-test-pro]
- **scope_in**: 建立扩展端 UI 可访问性与视觉回归最小基线（文档 + 可执行取证流程）。
- **scope_out**: 不进行大规模视觉重设计，不替换现有交互框架。

## 输入

- 文件: docs/CHROME_EXTENSION_GUIDE.md, docs/PROJECT_INTRODUCTION.md, products/prompt-pack-extension/chrome/src/, products/vscode-extension/, tests/e2e/test_integration.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-UI-BASELINE-CODEARTS-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_integration.py
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [x] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
