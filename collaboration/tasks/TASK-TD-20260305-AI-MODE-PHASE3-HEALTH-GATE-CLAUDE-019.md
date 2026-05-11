# 任务: AI Integration 模式治理 - Phase3 健康检查与门禁收口

**任务ID**: TASK-TD-20260305-AI-MODE-PHASE3-HEALTH-GATE-CLAUDE-019  
**change_id**: add-ai-integration-mode-governance  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P2

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [ai-integration-engineer, compliance-checker]
- **scope_in**: 增加 AI integration 健康检查输出（模式、回退计数、最近错误）并纳入门禁命令。
- **scope_out**: 不新增部署拓扑，不变更生产路由。

## 输入

- 文件: ai_collab/cli.py, scripts/pre_release_check.sh, docs/ai-integration-mode-guide.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-AI-MODE-PHASE3-HEALTH-GATE-CLAUDE-019.md`
- 必须包含: 新增门禁命令、健康字段定义、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m ai_collab.cli status -v
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

