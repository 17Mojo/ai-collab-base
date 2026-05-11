# 任务: 技术债工单 - AI Integration OpenSpec 提案（Claude）

**任务ID**: TASK-TD-20260305-AI-OPENSPEC-CLAUDE-009  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [backend-architect, ai-integration-engineer, devops-architect]
- **scope_in**: 产出 AI Integration mock/fallback/real 模式治理的 OpenSpec 提案与任务清单，不实施代码改动。
- **scope_out**: 不修改生产逻辑，不提交行为级代码实现。

## 输入

- 文件: openspec/project.md, openspec/specs/, src/ai_collab/integrations/, src/ai_collab/engines/, collaboration/results/RESULT_TASK-TD-20260305-AI-INTEGRATION-CLAUDE-003.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-OPENSPEC-CLAUDE-009.md`
- 必须包含: proposal 变更动机、spec delta、tasks checklist、风险与迁移方案

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
