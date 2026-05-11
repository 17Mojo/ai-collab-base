# 任务: Day2 真实任务 - TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006

**任务ID**: TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 修正 CLI 帮助文案中的旧协作模式描述（Copilot -> CodeArts），保持治理口径一致
- **scope_out**: 不做未授权架构重写，不跳过契约与结果门禁

## 输入

- 文件: ai_collab/cli.py, src/cli.py, tests/unit/test_cli.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006.md`
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
