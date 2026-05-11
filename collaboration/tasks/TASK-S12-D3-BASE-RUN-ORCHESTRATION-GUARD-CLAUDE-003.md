# 任务: S12 Day3 基座任务 - RUN 编排守卫

**任务ID**: TASK-S12-D3-BASE-RUN-ORCHESTRATION-GUARD-CLAUDE-003  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 加固 RUN 流程中的“派发/收口/no-op”分支提示与保护，降低误触发与重复触发。
- **scope_out**: 不改 AI 类型枚举，不新增外部依赖。

## 输入

- 文件: ai_collab/cli.py, tests/unit/test_cli.py, collaboration/PROTOCOL.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S12-D3-BASE-RUN-ORCHESTRATION-GUARD-CLAUDE-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_cli.py
python3 -m ai_collab.cli 2x all --dry-run
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
