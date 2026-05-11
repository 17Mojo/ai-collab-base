# 任务: S11 Day1 研究任务 - Chatbox 协议失败样例归档

**任务ID**: TASK-S11-D1-RESEARCH-CHATBOX-PROTOCOL-FAILURE-LOG-CODEARTS-001  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files]
- **scope_in**: 归档并分类聊天框执行中的失败样例（漏贴、错位、超长回报截断）并给出可执行缓解矩阵。
- **scope_out**: 不改控制器阈值，不修改历史归档文件。

## 输入

- 文件: collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md, collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md, logs/task_dispatch_history.jsonl

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S11-D1-RESEARCH-CHATBOX-PROTOCOL-FAILURE-LOG-CODEARTS-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli dispatch --dry-run
python3 -m ai_collab.cli receipt --dry-run
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
