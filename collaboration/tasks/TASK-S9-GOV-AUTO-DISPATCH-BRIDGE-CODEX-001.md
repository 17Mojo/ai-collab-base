# 任务: S9 自动派单桥接（V1）

**任务ID**: TASK-S9-GOV-AUTO-DISPATCH-BRIDGE-CODEX-001  
**change_id**: add-agent-dispatch-bridge  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 落地自动派单桥接能力（候选识别、指令包生成、派发审计）
- **scope_out**: 不接入外部会话自动发送，仅完成桥接层与CLI入口

## 输入

- 文件: ai_collab/cli.py, scripts/task_controller_daemon.py, collaboration/PROTOCOL.md
- OpenSpec: openspec/changes/add-agent-dispatch-bridge

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-GOV-AUTO-DISPATCH-BRIDGE-CODEX-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_cli.py
python3 -m ai_collab.cli dispatch --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
openspec validate add-agent-dispatch-bridge --strict
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
