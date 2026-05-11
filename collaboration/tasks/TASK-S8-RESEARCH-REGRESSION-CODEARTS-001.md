# 任务: M2 产出回归测试与边界案例报告

**任务ID**: TASK-S8-RESEARCH-REGRESSION-CODEARTS-001  
**change_id**: add-prompt-pack-lifecycle-baseline  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 对研究链路做回归验证并输出边界/失败案例
- **scope_out**: 不扩展生命周期规范范围

## 输入

- 文件: collaboration/results/RESULT_TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md, collaboration/monitoring/S8_DELIVERY_DEADLINE_PLAN_2026-03-03.md
- 截止时间: 2026-03-05 12:00（北京时间）

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S8-RESEARCH-REGRESSION-CODEARTS-001.md`
- 必须包含: 回归结果、边界案例、修正建议、风险说明

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
