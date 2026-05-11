# 任务: 技术债工单 - Frontend 质量门禁固化

**任务ID**: TASK-TD-20260305-FRONTEND-GATE-CLAUDE-002  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, devops-architect]
- **scope_in**: 固化 Chrome/VSCode 扩展相关回归门禁入口并接入 CI。
- **scope_out**: 不做 UI 重构，不新增产品功能。

## 输入

- 文件: .github/workflows/ci.yml, scripts/pre_release_check.sh, tests/e2e/test_integration.py, tests/unit/test_vscode_integration.py, products/prompt-pack-extension/chrome/, products/vscode-extension/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-FRONTEND-GATE-CLAUDE-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_integration.py tests/unit/test_vscode_integration.py
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
