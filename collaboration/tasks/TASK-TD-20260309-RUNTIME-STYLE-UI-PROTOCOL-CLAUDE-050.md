# 任务: Runtime 风格微调 UI 与消息协议接入

**任务ID**: TASK-TD-20260309-RUNTIME-STYLE-UI-PROTOCOL-CLAUDE-050  
**change_id**: add-pack-runtime-style-react-conversion-layer  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [backend-architect, systematic-debugging]
- **scope_in**: 在 Popup 增加运行时风格微调字段，并将 `runtime_overrides` 接入 `executePack` 协议透传链路。
- **scope_out**: 不实现 GUI JSON 编辑器；不改动 Pack 存储结构。

## 输入

- 文件:
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/proposal.md`
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/design.md`
  - `openspec/changes/add-pack-runtime-style-react-conversion-layer/specs/prompt-pack-runtime-style/spec.md`
  - `products/prompt-pack-extension/chrome/src/popup/index.html`
  - `products/prompt-pack-extension/chrome/src/popup/popup.js`
  - `products/prompt-pack-extension/chrome/src/content/message-handler.js`
  - `products/prompt-pack-extension/chrome/src/content/pack-executor.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260309-RUNTIME-STYLE-UI-PROTOCOL-CLAUDE-050.md`
- 必须包含:
  - 新增 UI 字段清单
  - 新旧 `executePack` payload 对比
  - 兼容性说明（无 overrides 请求）
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_integration.py
python3 -m pytest -q tests/e2e/test_ui_accessibility.py
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
