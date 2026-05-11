# 任务: Popup 错误态与空态运行时 UX 补强

**任务ID**: TASK-TD-20260314-POPUP-ERROR-STATE-CLAUDE-076  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 为 popup 增加稳定可见的 `.error-state` 与 `.error-message`
  - 补齐空 Pack、无效 Pack、执行失败、消息超时等运行时可视反馈
  - 统一重试入口与状态栏失败文案
  - 让 Playwright 错误处理断言对应到真实 UI，而不是仅靠 console 日志
- **scope_out**:
  - 不做 Pack 编辑器
  - 不改 settings 页面
  - 不调整 Pack JSON 存储结构

## 输入

- `products/prompt-pack-extension/chrome/src/popup/index.html`
- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `tests/playwright/tests/error_handling.spec.js`
- `tests/playwright/TEST_IMPROVEMENT_SUMMARY.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260314-POPUP-ERROR-STATE-CLAUDE-076.md`
- 必须包含:
  - 新增/调整的错误态与空态 UI 清单
  - retry / timeout 行为说明
  - 与现有 execute/status 协议的兼容性说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/error_handling.spec.js --grep "空 Pack 列表|Chrome API 失败|无效 Pack 数据|执行失败")
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
