# 任务: 发布冲刺 - 客户交付包与验收清单固化

**任务ID**: TASK-TD-20260306-CUSTOMER-DELIVERY-PACK-CODEARTS-027  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [backend-architect, ui-designer]
- **scope_in**: 固化客户交付包清单（安装、启动、验收、回滚）并完成一次交付前演练记录。
- **scope_out**: 不新增业务功能，不做结构性重构。

## 输入

- 文件: docs/RELEASE_CHECKLIST.md, docs/API_DOCUMENTATION.md, docs/CHROME_EXTENSION_GUIDE.md, prompt-pack-backend-v2.0.0.zip, prompt-pack-extension-v2.0.0.zip

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-CUSTOMER-DELIVERY-PACK-CODEARTS-027.md`
- 必须包含: 交付清单、演练命令与结果、已知限制、风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/integration/test_api.py tests/e2e/test_integration.py
ls -la prompt-pack-backend-v2.0.0.zip prompt-pack-extension-v2.0.0.zip
python3 -m ai_collab.cli status
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

