# 任务: Research verification wave3 synthesis remediation

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-SYNTHESIS-REMEDIATION-CODEARTS-124  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-DIFF-INVENTORY-CLAUDE-121`、`TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-EVIDENCE-MATRIX-CODEARTS-122`、`TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-OVERLAP-ANALYSIS-CLAUDE-123` 已完成资产，整理 Wave 3 综合修复方案
  - 将 Keep / Skip / Adapt 判定转成可执行的综合修复清单、最小写集边界、执行顺序与 reviewer 检查点
  - 为 `W3-004` 最终验证报告提供稳定输入边界与收口口径
  - 将综合修复资产接入 `research/INDEX.md`
- **scope_out**:
  - 不重跑 Wave 2 历史验证来替代综合修复
  - 不修改主工作区产品代码
  - 不提前生成最终验证报告

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE3_SYNTHESIS_REMEDIATION_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-SYNTHESIS-REMEDIATION-CODEARTS-124.md`
- 必须包含:
  - 综合修复清单
  - keep / skip / adapt 执行边界
  - 对 `W3-004` 的输入说明
  - 最小写集与执行顺序
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE3_SYNTHESIS_REMEDIATION_2026-03-21.md
rg -n "综合修复|keep|skip|adapt|W3-004|风险|回滚" research/MULTI_AGENT_VERIFICATION_WAVE3_SYNTHESIS_REMEDIATION_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE3_SYNTHESIS_REMEDIATION_2026-03-21.md" research/INDEX.md
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
