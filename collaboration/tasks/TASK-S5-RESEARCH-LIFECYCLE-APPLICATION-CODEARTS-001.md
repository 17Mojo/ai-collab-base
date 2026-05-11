# 任务: 生命周期规范在真实研究链路中的应用验证

**任务ID**: TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001  
**change_id**: add-prompt-pack-lifecycle-baseline  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 将生命周期手册应用到一条真实 Prompt Pack 变更样例，产出阶段证据清单与偏差项
- **scope_out**: 不扩展新生命周期阶段，不引入额外技术栈

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 在 S5 时间窗内提交结果
- **CTQ-2 质量门禁**: acceptance_commands 全部通过
- **CTQ-3 漂移控制**: 无越界改动
- **DPMO 记录**: 0/6

## 输入

- 文件: openspec/changes/add-prompt-pack-lifecycle-baseline/specs/prompt-pack-lifecycle/spec.md, collaboration/guides/PROMPT_PACK_LIFECYCLE_OPS_PLAYBOOK.md
- 上下文: 生命周期基线已建立，需验证“可执行性 + 可证据化”
- 依赖: TASK-S2-RESEARCH-LIFECYCLE-OPS-CODEARTS-001

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md`
- 必须包含: 阶段执行证据、偏差项、修正建议、回滚点

## acceptance_commands（必填）

```bash
openspec validate add-prompt-pack-lifecycle-baseline --strict
python3 -m ai_collab.cli status -v
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
