# 任务: Day3 加速任务 - TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009

**任务ID**: TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: Day3: 对齐 CLI 帮助信息与当前协作角色口径，消除误导说明。
- **scope_out**: 不绕过门禁，不进行未授权架构变更

## 输入

- 文件: ai_collab/cli.py, src/cli.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py
python3 -m ai_collab.cli --help
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
