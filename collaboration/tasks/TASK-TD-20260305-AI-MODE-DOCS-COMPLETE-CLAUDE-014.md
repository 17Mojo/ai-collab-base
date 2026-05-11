# 任务: AI Integration 模式治理 - 文档缺口补齐

**任务ID**: TASK-TD-20260305-AI-MODE-DOCS-COMPLETE-CLAUDE-014  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [devops-architect, compliance-checker]
- **scope_in**: 完成 openspec 4.x：更新 `collaboration/COLLABORATION_GUIDELINES.md` 与 `ARCHITECTURE.md` 的 AI 模式治理章节，并创建 `docs/ai-integration-mode-guide.md`（含配置优先级、环境变量、示例、故障排查）。
- **scope_out**: 不修改运行时代码，不更改 CI 流程与部署拓扑。

## 输入

- 文件: openspec/changes/add-ai-integration-mode-governance/, collaboration/COLLABORATION_GUIDELINES.md, ARCHITECTURE.md, src/ai_collab/config/integration_flags.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-DOCS-COMPLETE-CLAUDE-014.md`
- 必须包含: 文档变更摘要、门禁结果、风险与回滚

## acceptance_commands（必填）

```bash
test -f docs/ai-integration-mode-guide.md
grep -n "AI_INTEGRATION_MODE\\|IntegrationMode\\|mock\\|fallback\\|real" ARCHITECTURE.md collaboration/COLLABORATION_GUIDELINES.md docs/ai-integration-mode-guide.md
openspec validate add-ai-integration-mode-governance --strict
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
