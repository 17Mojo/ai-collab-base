# 任务: AI Integration 模式治理 - 配置基座落地

**任务ID**: TASK-TD-20260305-AI-MODE-CONFIG-CLAUDE-010  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [ai-integration-engineer, api-test-pro]
- **scope_in**: 创建 `src/ai_collab/config/integration_flags.py` 与模式查询工具函数，支持环境变量覆盖并提供最小单测覆盖。
- **scope_out**: 不修改现有集成模块业务逻辑，不引入真实 MCP 调用。

## 输入

- 文件: openspec/changes/add-ai-integration-mode-governance/, src/ai_collab/, tests/unit/

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-CONFIG-CLAUDE-010.md`
- 必须包含: 执行命令、实现摘要、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_integration_flags.py
python3 -m ruff check src/ai_collab/config tests/unit/test_integration_flags.py
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
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
