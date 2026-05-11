# 任务: Playwright 扩展宿主 Mock 失败模式补齐

**任务ID**: TASK-TD-20260314-PLAYWRIGHT-HOST-MOCK-CODEARTS-075  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [frontend-architect, planning-with-files]
- **scope_in**:
  - 扩展 `chromeHostMock`，补齐 Playwright 错误处理场景所需的失败/超时模式
  - 支持 `storageGetFails`
  - 支持 `tabsSendMessageFails`
  - 支持 `tabsSendMessageTimeout`
  - 保证现有 popup runtime 用例不被破坏
- **scope_out**:
  - 不修改 popup 视觉结构
  - 不修改 CI workflow
  - 不做跨浏览器扩展

## 输入

- `tests/playwright/tests/helpers/chromeHostMock.js`
- `tests/playwright/tests/error_handling.spec.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/TEST_IMPROVEMENT_SUMMARY.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260314-PLAYWRIGHT-HOST-MOCK-CODEARTS-075.md`
- 必须包含:
  - 新增 mock failure modes 清单
  - mock 行为与真实扩展宿主差异说明
  - 覆盖到的错误处理用例
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright install chromium && npx playwright test tests/error_handling.spec.js --grep "Chrome API 失败|执行失败|网络超时")
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
