# 任务: Research verification wave3 overlap analysis

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-OVERLAP-ANALYSIS-CLAUDE-123  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 在 `TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-DIFF-INVENTORY-CLAUDE-121` 与 `TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-EVIDENCE-MATRIX-CODEARTS-122` 完成后，执行 Wave 3 重叠问题分析
  - 基于差异清单与证据矩阵，识别高置信重叠问题、独特发现、可保留 / 跳过 / 适配项
  - 为 W3-003 综合修复提供清晰输入边界与优先级建议
  - 将分析资产接入 `research/INDEX.md`
- **scope_out**:
  - 不直接应用综合修复
  - 不提前生成最终 Wave 3 synthesis report
  - 不修改主工作区产品代码

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-OVERLAP-ANALYSIS-CLAUDE-123.md`
- 必须包含:
  - 重叠问题列表
  - 独特发现列表
  - keep / skip / adapt 判定
  - 对 W3-003 的输入说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md
rg -n "重叠|独特|keep|skip|adapt|风险|回滚" \
  research/MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md" research/INDEX.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [x] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
