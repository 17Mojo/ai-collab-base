# 任务: Research verification wave3 evidence matrix

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-EVIDENCE-MATRIX-CODEARTS-122  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 在 Wave 2 完整收口后，归一化各门禁结果中的证据与命令输出，形成 Wave 3 可复用证据矩阵
  - 汇总 bootstrap / review / test / E2E 四类资产的输入、命令、结果、风险、回滚与下一步含义
  - 将“允许进入下一阶段”的判定整理成一张矩阵，供 W3-002 直接引用
  - 将该矩阵接入 `research/INDEX.md`
- **scope_out**:
  - 不直接做重叠问题分析
  - 不修改主工作区产品代码
  - 不提前执行 Wave 3 综合修复

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-EVIDENCE-MATRIX-CODEARTS-122.md`
- 必须包含:
  - 证据来源矩阵
  - 命令 / 结论 / 风险三元组
  - 对 W3-002 的输入说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md
rg -n "证据|来源|命令|结论|风险|回滚|Wave 3" \
  research/MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE3_EVIDENCE_MATRIX_2026-03-21.md" research/INDEX.md
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
