# 任务: Popup 响应式视觉基线扩面

**任务ID**: TASK-TD-20260316-POPUP-VISUAL-RESPONSIVE-CODEARTS-083  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging, frontend-architect]
- **scope_in**:
  - 扩展 `popup_visual_regression.spec.js`，覆盖 compact/mobile 视口与 empty/error 等关键视觉状态
  - 补齐对应 screenshot snapshots，保证 suite 可直接回归执行
  - 更新 README 中视觉回归维护口径，说明何时更新 snapshots、何时视为真实回归
  - 尽量限定在 Playwright 测试与基线资产，不主动改 popup 产品代码
- **scope_out**:
  - 不改 popup 信息架构
  - 不做 axe/a11y 语义修复
  - 不引入新的 CI workflow

## 输入

- `tests/playwright/README.md`
- `tests/playwright/tests/popup_visual_regression.spec.js`
- `tests/playwright/tests/popup_visual_regression.spec.js-snapshots/`
- `tests/playwright/tests/helpers/chromeHostMock.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-POPUP-VISUAL-RESPONSIVE-CODEARTS-083.md`
- 必须包含:
  - 新增视觉场景清单
  - snapshot 维护说明
  - 失败 triage 口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/popup_visual_regression.spec.js --reporter=list)
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
