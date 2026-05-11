# 任务: Research assembly runbook asset

**任务ID**: TASK-TD-20260320-RESEARCH-ASSEMBLY-RUNBOOK-ASSET-CODEARTS-111  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 基于 `100` 的研究结论，把 Prompt Pack 组装验收口径沉淀成一份可直接复用的执行资产
  - 新建一份 runbook，明确 Owner / Editor / Reviewer 的输入、输出、命令级检查项、失败分类与回滚口径
  - 将该 runbook 接入 `research/reverse-engineering/README.md` 与 `research/INDEX.md`，让后续派单可直接引用
  - 在结果报告中说明该资产如何服务后续 Pack 产品化与派单验收
- **scope_out**:
  - 不改 Prompt Pack 运行时代码
  - 不新增 CLI 子命令
  - 不修改 OpenSpec spec

## 输入

- `research/reverse-engineering/PACK_EDITOR_ASSEMBLY_CHECKLIST_2026-03-09.md`
- `research/reverse-engineering/PACK_REQUIREMENT_CONVERSION_FORM_OWNER_TEMPLATE_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_XIAOHONGSHU_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_EDU_FINANCE_2026-03-09.md`
- `research/reverse-engineering/PACK_CROSS_INDUSTRY_TEMPLATE_KIT_2026-03-19.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md`
- `research/reverse-engineering/README.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/reverse-engineering/PACK_ASSEMBLY_ACCEPTANCE_RUNBOOK_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-ASSEMBLY-RUNBOOK-ASSET-CODEARTS-111.md`
- 必须包含:
  - Owner / Editor / Reviewer 责任边界
  - 输入物 / 输出物清单
  - 命令级验收 checklist
  - 失败分类与回滚
  - 索引接入说明

## acceptance_commands（必填）

```bash
test -f research/reverse-engineering/PACK_ASSEMBLY_ACCEPTANCE_RUNBOOK_2026-03-20.md
rg -n "Owner|Editor|Reviewer|输入物|输出物|验收命令|失败分类|回滚" \
  research/reverse-engineering/PACK_ASSEMBLY_ACCEPTANCE_RUNBOOK_2026-03-20.md
rg -n "PACK_ASSEMBLY_ACCEPTANCE_RUNBOOK_2026-03-20.md" \
  research/reverse-engineering/README.md \
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
