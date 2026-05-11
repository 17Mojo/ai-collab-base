# 任务: Research verification wave7 final archive summary

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-FINAL-ARCHIVE-SUMMARY-CODEARTS-135  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 Wave 1-6 现有结果，沉淀一份 archive-grade 最终摘要
  - 汇总验证链路的主资产地图、保留运行资产与复用入口
  - 明确项目当前已完成范围、非目标与后续复用方式
  - 只写研究/结果资产，不触碰产品代码
- **scope_out**:
  - 不执行新的 worktree 删除
  - 不执行 branch cleanup
  - 不修改产品代码

## 输入

- `collaboration/results/WAVE6_CLOSEOUT_SUMMARY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLOSEOUT_GATE_2026-03-22.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_FINAL_ARCHIVE_SUMMARY_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-FINAL-ARCHIVE-SUMMARY-CODEARTS-135.md`
- 必须包含:
  - Wave 1-6 完整摘要
  - primary asset map
  - 保留 worktree / helper repo 说明
  - 复用入口与非目标边界

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_FINAL_ARCHIVE_SUMMARY_2026-03-22.md
rg -n "Wave 1-6|asset map|helper repo|worktree|steady state|复用|非目标" research/MULTI_AGENT_VERIFICATION_FINAL_ARCHIVE_SUMMARY_2026-03-22.md
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
