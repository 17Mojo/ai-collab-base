# 任务: 技术债工单 - Backend Ruff 清零与门禁恢复

**任务ID**: TASK-TD-20260305-BACKEND-RUFF-CLAUDE-001  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [systematic-debugging]
- **scope_in**: 修复 `local-backend/app` 当前 ruff 报错，恢复 Backend 最小门禁可执行通过。
- **scope_out**: 不新增业务 API，不做破坏性 Schema 调整。

## 输入

- 文件: local-backend/app/main.py, local-backend/app/api/__init__.py, local-backend/app/api/packs.py, local-backend/app/api/schemas.py, local-backend/app/core/*.py, local-backend/app/models/__init__.py

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-BACKEND-RUFF-CLAUDE-001.md`
- 必须包含: 执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ruff check ai_collab src/ai_collab local-backend/app
python3 -m pytest -q tests/integration/test_api.py tests/unit/test_state_manager.py
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
