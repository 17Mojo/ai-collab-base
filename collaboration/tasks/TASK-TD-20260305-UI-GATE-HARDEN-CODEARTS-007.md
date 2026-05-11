# 任务: 技术债工单 - UI 门禁硬化（CodeArts）

**任务ID**: TASK-TD-20260305-UI-GATE-HARDEN-CODEARTS-007  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [ui-designer, api-test-pro, devops-architect]
- **scope_in**: 把 UI 可访问性基线从“告警型脚本”升级为“可失败的质量门禁”，并接入快速门禁流程。
- **scope_out**: 不做大规模 UI 重设计，不引入重型视觉回归平台。

## 输入

- 文件: tests/e2e/test_ui_accessibility.py, docs/UI_ACCESSIBILITY_BASELINE.md, scripts/pre_release_check.sh, .github/workflows/ci.yml

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-UI-GATE-HARDEN-CODEARTS-007.md`
- 必须包含: 门禁策略、失败判定规则、执行命令、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/e2e/test_ui_accessibility.py tests/e2e/test_integration.py
bash scripts/pre_release_check.sh --workspace . --quick
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
