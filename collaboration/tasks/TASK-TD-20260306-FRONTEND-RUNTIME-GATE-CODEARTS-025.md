# 任务: 前端运行时门禁 - UI 可访问性与视觉回归落地

**任务ID**: TASK-TD-20260306-FRONTEND-RUNTIME-GATE-CODEARTS-025  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [ui-designer, api-test-pro]
- **scope_in**: 将 UI 基线从静态检查升级为可执行的运行时门禁（至少补充一条自动化运行链：a11y 或视觉快照）。
- **scope_out**: 不做大规模 UI 重设计，不改核心业务流程。

## 输入

- 文件: tests/e2e/test_ui_accessibility.py, docs/UI_ACCESSIBILITY_BASELINE.md, .github/workflows/nightly.yml, products/prompt-pack-extension/chrome/src/popup/*
- 上下文: 当前文档定义了视觉/a11y 命令，但仓库内缺少完整可执行链路。

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-FRONTEND-RUNTIME-GATE-CODEARTS-025.md`
- 必须包含: 新增门禁链路、基线更新策略、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_ui_accessibility.py tests/e2e/test_integration.py
python3 -m ruff check tests/e2e/test_ui_accessibility.py
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

