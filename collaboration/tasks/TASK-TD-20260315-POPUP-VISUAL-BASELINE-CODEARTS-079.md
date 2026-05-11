# 任务: Popup 视觉回归基线补齐

**任务ID**: TASK-TD-20260315-POPUP-VISUAL-BASELINE-CODEARTS-079  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [frontend-architect, planning-with-files]
- **scope_in**:
  - 为 Prompt Pack popup 建立 Playwright 视觉快照基线
  - 覆盖 idle / empty / selected / completed / error / timeout 等关键状态
  - 固化快照更新、失败排查、截图产物口径
  - 保证与现有 GUI demo / runtime suite 不冲突
- **scope_out**:
  - 不做跨浏览器视觉矩阵
  - 不改 CI workflow 之外的发布流程
  - 不调整 popup 产品文案策略

## 输入

- `products/prompt-pack-extension/chrome/src/popup/index.html`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `tests/playwright/README.md`
- `tests/playwright/tests/helpers/chromeHostMock.js`
- `tests/playwright/TEST_IMPROVEMENT_SUMMARY.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260315-POPUP-VISUAL-BASELINE-CODEARTS-079.md`
- 必须包含:
  - 新增视觉快照场景清单
  - baseline 文件位置与更新命令
  - trace / screenshot 失败排查口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/popup.visual.spec.js --reporter=list)
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
