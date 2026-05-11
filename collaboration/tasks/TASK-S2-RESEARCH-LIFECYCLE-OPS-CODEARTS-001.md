# 任务: Prompt Pack 生命周期执行手册（Ops）

**任务ID**: TASK-S2-RESEARCH-LIFECYCLE-OPS-CODEARTS-001  
**change_id**: add-prompt-pack-lifecycle-baseline  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, compliance-checker]
- **scope_in**: 形成生命周期工单执行手册（阶段入口/出口/证据模板）
- **scope_out**: 不改运行时代码

## 输入

- `openspec/changes/add-prompt-pack-lifecycle-baseline/specs/prompt-pack-lifecycle/spec.md`
- `collaboration/PROTOCOL.md`

## 输出要求

- `collaboration/guides/PROMPT_PACK_LIFECYCLE_OPS_PLAYBOOK.md`
- `collaboration/results/RESULT_TASK-S2-RESEARCH-LIFECYCLE-OPS-CODEARTS-001.md`

## acceptance_commands

```bash
openspec validate add-prompt-pack-lifecycle-baseline --strict
python3 -m ai_collab.cli status -v
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
