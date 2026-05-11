# 任务: 复核 CodeArts 生命周期应用结果并给出通过/退回结论

**任务ID**: TASK-S5-RESEARCH-LIFECYCLE-VERIFY-CLAUDE-002  
**change_id**: add-prompt-pack-lifecycle-baseline  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 对 CodeArts 的生命周期应用结果做复核，给出通过/退回结论与修正项
- **scope_out**: 不替代 CodeArts 重写研究内容

## 输入

- 文件: collaboration/results/RESULT_TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md, collaboration/tasks/TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md
- 上下文: CodeArts 结果文件已交付，需完成通过/退回复核并形成收口结论

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S5-RESEARCH-LIFECYCLE-VERIFY-CLAUDE-002.md`
- 必须包含: 复核结论（通过/退回）、证据核验结果、修正建议、风险说明

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESULT_TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md
openspec validate add-prompt-pack-lifecycle-baseline --strict
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
