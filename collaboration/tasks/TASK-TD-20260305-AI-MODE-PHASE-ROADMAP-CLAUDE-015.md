# 任务: AI Integration 模式治理 - Phase2/3/4 路线工单化

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE-ROADMAP-CLAUDE-015  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [backend-architect, devops-architect]
- **scope_in**: 完成 openspec 7.x：将 Phase 2（异常驱动回退）/Phase 3（真实 MCP 集成）/Phase 4（Mock 层分离）拆解为可执行任务卡，明确依赖、验收命令与回滚策略。
- **scope_out**: 不实施功能代码，不修改现有任务状态机逻辑。

## 输入

- 文件: openspec/changes/add-ai-integration-mode-governance/tasks.md, openspec/changes/add-ai-integration-mode-governance/proposal.md, src/ai_collab/integrations/, src/ai_collab/engines/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE-ROADMAP-CLAUDE-015.md`
- 必须包含: 新增任务清单、依赖图、优先级建议、风险与回滚

## acceptance_commands（必填）

```bash
ls collaboration/tasks/TASK-TD-20260305-AI-MODE-PHASE2-*.md collaboration/tasks/TASK-TD-20260305-AI-MODE-PHASE3-*.md collaboration/tasks/TASK-TD-20260305-AI-MODE-PHASE4-*.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
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
