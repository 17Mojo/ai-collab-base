# 任务: 技术债工单 - AI Integration 模拟逻辑收敛

**任务ID**: TASK-TD-20260305-AI-INTEGRATION-CLAUDE-003  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: ai-integration-engineer
- **support_skills**: [backend-architect, systematic-debugging]
- **scope_in**: 收敛 `integrations/engines` 中模拟响应路径，改为真实适配或显式 feature flag 回退策略。
- **scope_out**: 不引入新的外部平台依赖，不变更现有 CLI 对外参数。

## 输入

- 文件: src/ai_collab/integrations/notebooklm.py, src/ai_collab/engines/consensus_engine.py, src/ai_collab/engines/soul_injection_engine.py, ai_collab/codex_integration.py, tests/unit/test_codex_integration.py, tests/unit/test_dispatch_trigger.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-INTEGRATION-CLAUDE-003.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_codex_integration.py tests/unit/test_dispatch_trigger.py
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
