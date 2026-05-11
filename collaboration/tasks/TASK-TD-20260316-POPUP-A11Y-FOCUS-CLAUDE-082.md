# 任务: Popup 键盘导航与焦点回归补齐

**任务ID**: TASK-TD-20260316-POPUP-A11Y-FOCUS-CLAUDE-082  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, planning-with-files, systematic-debugging]
- **scope_in**:
  - 强化 Prompt Pack popup 的键盘导航、焦点可见性与 retry/empty state a11y smoke
  - 扩展 `popup.a11y.spec.js`，覆盖 loaded / empty / error 至少 3 类状态的 tab/focus 断言
  - 如发现必要缺口，可对 popup 语义或 focus 样式做最小修复
  - 更新 README 中的 a11y smoke 口径，说明该 suite 与 axe suite 的分工
- **scope_out**:
  - 不做视觉快照基线
  - 不做性能阈值
  - 不引入新的外部依赖

## 输入

- `products/prompt-pack-extension/chrome/src/popup/index.html`
- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `tests/playwright/README.md`
- `tests/playwright/tests/popup.a11y.spec.js`
- `tests/playwright/tests/helpers/chromeHostMock.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-POPUP-A11Y-FOCUS-CLAUDE-082.md`
- 必须包含:
  - 新增 keyboard/focus 场景清单
  - 如果修改 popup 语义/样式，说明原因
  - 失败 triage 口径
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
