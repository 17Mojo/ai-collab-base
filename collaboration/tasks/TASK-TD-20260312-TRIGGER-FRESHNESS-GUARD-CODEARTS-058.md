# 任务: Trigger 新鲜度守卫与可观测性

**任务ID**: TASK-TD-20260312-TRIGGER-FRESHNESS-GUARD-CODEARTS-058  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, frontend-architect]
- **scope_in**:
  - 增加 trigger payload 新鲜度检查（generated_at/sourceOrders 与 dispatch 报告对齐）
  - 若 stale 则输出明确告警并给出一键修复命令
  - 更新运维文档中“派发后必做校验”段落
- **scope_out**:
  - 不改变 ACK 协议格式
  - 不引入新外部服务

## 输入

- `ai_collab/cli.py`
- `collaboration/monitoring/AGENT_TRIGGER_*_latest.md`
- `collaboration/PROTOCOL.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260312-TRIGGER-FRESHNESS-GUARD-CODEARTS-058.md`
- 必须包含:
  - stale 判定规则
  - 告警输出示例
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py -k "trigger or dispatch"
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli status -v
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
