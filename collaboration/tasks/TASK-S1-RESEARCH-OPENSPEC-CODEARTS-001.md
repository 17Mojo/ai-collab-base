# 任务: Prompt Pack 生命周期 OpenSpec 基线落地

**任务ID**: TASK-S1-RESEARCH-OPENSPEC-CODEARTS-001  
**change_id**: add-prompt-pack-lifecycle-baseline  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, compliance-checker]
- **scope_in**: 补齐 Prompt Pack 生命周期（Generation/Review/Iteration/Archive）规范细节、示例与校验证据
- **scope_out**: 不改运行时代码路径，不承担全局路由决策

## Lean Six Sigma 控制项（CTQ）

- **CTQ-1 准时性**: 当日提交结果文件（Y/N）
- **CTQ-2 质量门禁**: acceptance_commands 全部通过（Y/N）
- **CTQ-3 漂移控制**: 无越界改动（Y/N）
- **DPMO 记录**: 0/5（目标）

## 输入

- 文件: `openspec/changes/add-prompt-pack-lifecycle-baseline/*`, `openspec/project.md`, `collaboration/PROTOCOL.md`
- 上下文: 研究线需形成能力级 SSOT，支撑后续 Prompt Pack 工单派发
- 依赖: 无

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-S1-RESEARCH-OPENSPEC-CODEARTS-001.md`
- 必须包含: 变更摘要、执行命令、测试结论、风险与回滚点

## acceptance_commands（必填）

```bash
openspec validate add-prompt-pack-lifecycle-baseline --strict
python3 -m ai_collab.cli status -v
python3 -m pytest -q tests/unit/test_session_inject.py tests/unit/test_cli.py
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
