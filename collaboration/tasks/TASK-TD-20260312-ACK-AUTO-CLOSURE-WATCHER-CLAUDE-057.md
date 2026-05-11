# 任务: ACK 自动收口 Watcher（testing -> completed）

**任务ID**: TASK-TD-20260312-ACK-AUTO-CLOSURE-WATCHER-CLAUDE-057  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 为 ACK 协议行新增自动解析入口（A.ACK/C.ACK）
  - 命中 `status=ok/completed` 时自动执行结果文件校验与 `testing -> completed`
  - 输出结构化审计日志（成功/失败原因）
- **scope_out**:
  - 不改现有任务 schema
  - 不改 dispatch/trigger 业务规则

## 输入

- `ai_collab/cli.py`
- `ai_collab/state_manager.py`
- `collaboration/PROTOCOL.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260312-ACK-AUTO-CLOSURE-WATCHER-CLAUDE-057.md`
- 必须包含:
  - ACK 解析规则
  - 自动收口判定条件
  - 失败场景与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py -k "ack or receipt or tasks"
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
