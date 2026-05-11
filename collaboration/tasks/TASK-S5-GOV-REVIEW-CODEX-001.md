# 任务: S5 闭环审查、修正与沉淀

**任务ID**: TASK-S5-GOV-REVIEW-CODEX-001  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 对 S5 基座/研究工单执行审查、修正回灌、文档沉淀并发布迭代结论
- **scope_out**: 不替代 Claude/CodeArts 的具体实现工作

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 在 S5 时间窗内收口
- **CTQ-2 质量门禁**: 核心命令全绿
- **CTQ-3 漂移控制**: 无冲突/无违规派单
- **DPMO 记录**: 0/6

## 输入

- 文件: collaboration/monitoring/BASE_RESEARCH_ITERATION_LOOP_2026-03-03.md, collaboration/tasks/TASK-S5-BASE-RUNTIME-PROBE-CLAUDE-001.md, collaboration/tasks/TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001.md
- 上下文: 需要形成“实施-审查-修正-沉淀-应用-测试实践”闭环证据
- 依赖: TASK-S5-BASE-RUNTIME-PROBE-CLAUDE-001, TASK-S5-RESEARCH-LIFECYCLE-APPLICATION-CODEARTS-001

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S5-GOV-REVIEW-CODEX-001.md`
- 必须包含: 审查结论、修正项清单、沉淀文件、下一轮建议

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli status -v
python3 -m ai_collab.cli controller --once --dry-run
python3 scripts/sync_mcp_unified.py --workspace . --check
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
