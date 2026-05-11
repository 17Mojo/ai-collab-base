# 任务: Popup 执行状态同步一致性加固

**任务ID**: TASK-TD-20260311-POPUP-STATUS-SYNC-CLAUDE-055  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 加固 popup 执行态与 content 真实状态的一致性（避免 transient 文案与内部状态脱节）
  - 为执行、暂停、恢复、停止补状态同步策略（必要时主动刷新 `getStatus`）
  - 补 1~2 条 e2e 断言覆盖“最终状态一致”
- **scope_out**:
  - 不改 Pack schema
  - 不引入外部依赖

## 输入

- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `products/prompt-pack-extension/chrome/src/content/message-handler.js`
- `tests/e2e/test_prompt_pack_runtime_overrides.py`
- `tests/playwright/tests/popup.runtime.spec.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260311-POPUP-STATUS-SYNC-CLAUDE-055.md`
- 必须包含:
  - 状态同步策略说明（执行/暂停/恢复/停止）
  - 至少 1 条新增测试的通过证据
  - 风险与回滚

## acceptance_commands（必填）

```bash
cd tests/playwright && npm run test -- --reporter=list tests/popup.runtime.spec.js
python3 -m pytest -q tests/e2e/test_prompt_pack_runtime_overrides.py tests/e2e/test_integration.py
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
