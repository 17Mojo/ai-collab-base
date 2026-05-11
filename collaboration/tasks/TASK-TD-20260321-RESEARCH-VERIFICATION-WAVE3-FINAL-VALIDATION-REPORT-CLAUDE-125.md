# 任务: Research verification wave3 final validation report

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-FINAL-VALIDATION-REPORT-CLAUDE-125  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 在 `TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-SYNTHESIS-REMEDIATION-CODEARTS-124` 完成后，汇总 `121-124` 资产形成 Wave 3 最终验证报告
  - 归档最终验证结论、证据链、收口状态、残余风险、是否可关闭 Wave 3
  - 将最终验证报告接入 `research/INDEX.md`
- **scope_out**:
  - 不重做 `121-124` 的研究资产
  - 不修改主工作区产品代码
  - 不提前开启下一波研究任务

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_OVERLAP_ANALYSIS_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_SYNTHESIS_REMEDIATION_2026-03-21.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-FINAL-VALIDATION-REPORT-CLAUDE-125.md`
- 必须包含:
  - Wave 3 验证结论
  - 证据链摘要
  - 收口检查清单
  - 残余风险与回滚
  - 是否建议关闭 Wave 3

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md
rg -n "Wave 3|验证结论|证据链|收口|风险|回滚" research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md" research/INDEX.md
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
