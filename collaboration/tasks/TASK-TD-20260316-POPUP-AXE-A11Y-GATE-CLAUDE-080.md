# 任务: Popup axe a11y 审计门禁补齐

**任务ID**: TASK-TD-20260316-POPUP-AXE-A11Y-GATE-CLAUDE-080  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, planning-with-files, systematic-debugging]
- **scope_in**:
  - 为 Prompt Pack popup 增加基于 `axe-core` 的 Playwright a11y 审计 spec
  - 覆盖 idle / selected / empty / error 至少 4 类关键状态
  - 固化依赖、执行命令与失败排查口径，保证与现有 `popup.a11y.spec.js` 共存
  - 对必要的 popup 语义缺口做最小修复，但不扩散到无关页面
- **scope_out**:
  - 不做完整人工屏幕阅读器审计
  - 不做视觉基线
  - 不做跨浏览器矩阵

## 输入

- `products/prompt-pack-extension/chrome/src/popup/index.html`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `tests/playwright/package.json`
- `tests/playwright/README.md`
- `tests/playwright/tests/helpers/chromeHostMock.js`
- `tests/playwright/tests/popup.a11y.spec.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-POPUP-AXE-A11Y-GATE-CLAUDE-080.md`
- 必须包含:
  - 新增 axe 审计场景清单
  - 新增依赖 / scripts 说明
  - 失败 triage 口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/popup.a11y.axe.spec.js --reporter=list)
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
