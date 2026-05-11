# 任务: Runtime Overrides 的 CI 可跑 E2E 与扩展宿主 Mock

**任务ID**: TASK-TD-20260309-E2E-CI-RUNTIME-OVERRIDES-CODEARTS-053  
**change_id**: add-pack-runtime-style-react-conversion-layer  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [frontend-architect, systematic-debugging]
- **scope_in**: 建立可在 CI 运行的扩展宿主 E2E，覆盖 runtime_overrides 透传与执行结果，消除 `chrome.storage` 假阳性。
- **scope_out**: 不做视觉回归系统建设；不做跨浏览器兼容矩阵。

## 输入

- 文件:
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/tasks.md`
  - `products/prompt-pack-extension/chrome/src/popup/popup.js`
  - `products/prompt-pack-extension/chrome/src/content/message-handler.js`
  - `products/prompt-pack-extension/chrome/src/content/pack-executor.js`
  - `tests/e2e/test_integration.py`
  - `tests/e2e/test_ui_accessibility.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260309-E2E-CI-RUNTIME-OVERRIDES-CODEARTS-053.md`
- 必须包含:
  - E2E 场景清单与通过率
  - 扩展宿主 mock 策略说明
  - `chrome.storage` 假阳性规避证据
  - CI 接入建议

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_prompt_pack_runtime_overrides.py
python3 -m pytest -q tests/e2e/test_integration.py tests/e2e/test_ui_accessibility.py
openspec validate add-pack-runtime-style-react-conversion-layer --strict
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
