# 任务: S12 Day2 研究任务 - 派发状态漂移审计

**任务ID**: TASK-S12-D2-RESEARCH-DISPATCH-STATE-DRIFT-AUDIT-CODEARTS-002  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files]
- **scope_in**: 审计 dispatch_state、trigger_history、active tasks 三者的一致性，输出漂移分类与缓解策略。
- **scope_out**: 不修改历史日志，不手动修补状态文件。

## 输入

- 文件: logs/agent_dispatch_state.json, logs/task_dispatch_history.jsonl, logs/task_trigger_history.jsonl

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S12-D2-RESEARCH-DISPATCH-STATE-DRIFT-AUDIT-CODEARTS-002.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli dispatch --dry-run
python3 -m ai_collab.cli trigger --phrase "2X DISPATCH CodeArts" --include-pending --dry-run
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
