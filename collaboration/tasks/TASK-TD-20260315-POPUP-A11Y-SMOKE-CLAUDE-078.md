# 任务: Popup a11y 回归基线补齐

**任务ID**: TASK-TD-20260315-POPUP-A11Y-SMOKE-CLAUDE-078  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, systematic-debugging, planning-with-files]
- **scope_in**:
  - 为 Prompt Pack popup 补齐 Playwright a11y smoke suite
  - 覆盖 keyboard navigation / focus visible / aria-label / role=status / error-state 可达性
  - 验证空态、错误态、执行态的关键可访问性信号
  - 更新测试说明，明确本地与 CI 执行方式
- **scope_out**:
  - 不做视觉快照基线
  - 不改 Pack 存储协议
  - 不引入新的产品页面

## 输入

- `products/prompt-pack-extension/chrome/src/popup/index.html`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `tests/playwright/README.md`
- `tests/playwright/TEST_IMPROVEMENT_PLAN.md`
- `tests/playwright/TEST_IMPROVEMENT_SUMMARY.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260315-POPUP-A11Y-SMOKE-CLAUDE-078.md`
- 必须包含:
  - 新增 a11y 场景列表
  - 覆盖到的键盘/语义信号
  - 与现有 popup runtime suite 的兼容性说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/popup.a11y.spec.js --reporter=list)
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
