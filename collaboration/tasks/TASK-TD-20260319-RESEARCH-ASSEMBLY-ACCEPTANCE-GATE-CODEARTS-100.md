# 任务: Prompt Pack 组装验收口径与发布前检查单沉淀

**任务ID**: TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 基于 `PACK_EDITOR_ASSEMBLY_CHECKLIST`、需求转换模板与配对样本，沉淀一份可执行的 Prompt Pack 组装验收口径
  - 明确“可发布 / 需返工 / 缺信息”的失败分类与最小判定标准
  - 给出发布前检查单、Reviewer 快速审阅清单，以及建议绑定的命令级验收入口
  - 在结果报告中说明该口径如何承接 `099` 的状态回写治理，并作为后续产品化工单输入
- **scope_out**:
  - 不改 Prompt Pack 运行时代码
  - 不新增 OpenSpec spec delta
  - 不实现 CLI 新命令，只定义口径与建议入口

## 输入

- `research/reverse-engineering/PACK_EDITOR_ASSEMBLY_CHECKLIST_2026-03-09.md`
- `research/reverse-engineering/PACK_REQUIREMENT_CONVERSION_FORM_OWNER_TEMPLATE_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_XIAOHONGSHU_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_EDU_FINANCE_2026-03-09.md`
- `research/reverse-engineering/PACK_CROSS_INDUSTRY_FIELD_MAPPING_MATRIX_2026-03-09.md`
- `research/INDEX.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-STATE-SYNC-AUTOMATION-CODEARTS-099.md`
- `collaboration/results/BASE_RESEARCH_7DAY_EXECUTION_PLAN_2026-03-19.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md`
- 必须包含:
  - 组装验收 checklist
  - 失败分类（可发布 / 需返工 / 缺信息）
  - Reviewer 快速审阅清单
  - 建议绑定的命令级验收入口
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "assembly|checklist|Owner|Editor|样本|字段" \
  research/reverse-engineering \
  research/INDEX.md
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
