# 任务: Owner / Editor / Reviewer 标准输入契约与字段映射沉淀

**任务ID**: TASK-TD-20260319-RESEARCH-OWNER-EDITOR-CONTRACT-CLAUDE-102  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 Owner 转换单、Editor 组装检查单与 `100` 的验收口径，沉淀一份 Owner / Editor / Reviewer 的标准输入契约
  - 明确各角色的字段职责、必填项、可选项、缺信息回退口径
  - 给出该契约与当前 Prompt Pack schema / requirement conversion 的映射说明
  - 在结果报告中说明如何把该契约用作后续正式工单、模板和示例输入
- **scope_out**:
  - 不改 Prompt Pack 运行时代码
  - 不新增 CLI 子命令
  - 不做跨行业字段骨架扩展

## 输入

- `research/reverse-engineering/PACK_REQUIREMENT_CONVERSION_FORM_OWNER_TEMPLATE_2026-03-09.md`
- `research/reverse-engineering/PACK_EDITOR_ASSEMBLY_CHECKLIST_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_XIAOHONGSHU_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_EDU_FINANCE_2026-03-09.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md`
- `research/INDEX.md`
- `tests/unit/test_pack_requirement_conversion.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-OWNER-EDITOR-CONTRACT-CLAUDE-102.md`
- 必须包含:
  - 三角色标准输入契约
  - 字段职责表
  - 与 Prompt Pack schema / conversion 的映射说明
  - 缺信息回退口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "Owner|Editor|Reviewer|schema|字段|转换单|检查单" \
  research/reverse-engineering \
  research/INDEX.md \
  tests/unit/test_pack_requirement_conversion.py
python3 -m pytest -q tests/unit/test_pack_requirement_conversion.py
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
