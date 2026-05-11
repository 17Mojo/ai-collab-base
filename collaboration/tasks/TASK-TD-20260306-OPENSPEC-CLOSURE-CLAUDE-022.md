# 任务: OpenSpec 收口 - AI Integration Mode 治理变更闭环

**任务ID**: TASK-TD-20260306-OPENSPEC-CLOSURE-CLAUDE-022  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: compliance-checker
- **support_skills**: [ai-integration-engineer, devops-architect]
- **scope_in**: 对 `add-ai-integration-mode-governance` 执行“已实现项回填 + 未实现项拆分”收口，确保 tasks 与实现状态一致。
- **scope_out**: 不做新的功能扩展，不引入新的外部依赖。

## 输入

- 文件: openspec/changes/add-ai-integration-mode-governance/tasks.md, openspec/changes/add-ai-integration-mode-governance/proposal.md, openspec/changes/add-ai-integration-mode-governance/specs/ai-integration-mode/spec.md
- 依赖: TASK-TD-20260306-AI-INTEGRATION-CLOSURE-CODEARTS-023

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-OPENSPEC-CLOSURE-CLAUDE-022.md`
- 必须包含: 回填明细、拆分策略、验证命令、风险与回滚

## acceptance_commands（必填）

```bash
openspec validate add-ai-integration-mode-governance --strict
openspec show add-ai-integration-mode-governance --json --deltas-only
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

