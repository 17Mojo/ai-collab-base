# 任务: 跨行业 Pack 骨架模板化与索引接入

**任务ID**: TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-TEMPLATE-KIT-CLAUDE-106  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `104` 的跨行业骨架结论，沉淀一份可直接复用的 Prompt Pack 模板资产
  - 在模板中明确固定字段、行业扩展字段、缺省值策略与缺信息回退规则
  - 给出至少两个行业示例映射，说明如何从 Owner 输入落到最小 Pack 骨架
  - 更新 `research/reverse-engineering/README.md` 与 `research/INDEX.md`，让该模板资产可发现、可复用
  - 在结果报告中说明该模板如何服务后续产品化派单与示例模板扩展
- **scope_out**:
  - 不改 Prompt Pack 运行时代码
  - 不新增 CLI 子命令
  - 不修改 OpenSpec spec

## 输入

- `research/reverse-engineering/PACK_CROSS_INDUSTRY_FIELD_MAPPING_MATRIX_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_XIAOHONGSHU_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_EDU_FINANCE_2026-03-09.md`
- `research/reverse-engineering/PACK_REQUIREMENT_CONVERSION_FORM_OWNER_TEMPLATE_2026-03-09.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-PACK-SKELETON-CLAUDE-104.md`
- `research/reverse-engineering/README.md`
- `research/INDEX.md`
- `tests/unit/test_pack_requirement_conversion.py`

## 输出要求

- 资产文件: `research/reverse-engineering/PACK_CROSS_INDUSTRY_TEMPLATE_KIT_2026-03-19.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-TEMPLATE-KIT-CLAUDE-106.md`
- 必须包含:
  - 固定字段 / 行业扩展字段边界
  - 最小骨架定义
  - 至少两个行业示例映射
  - 缺省值与缺信息回退规则
  - 索引接入说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/reverse-engineering/PACK_CROSS_INDUSTRY_TEMPLATE_KIT_2026-03-19.md
rg -n "固定字段|行业扩展字段|缺省值|缺信息回退|示例映射|最小骨架" \
  research/reverse-engineering/PACK_CROSS_INDUSTRY_TEMPLATE_KIT_2026-03-19.md
rg -n "PACK_CROSS_INDUSTRY_TEMPLATE_KIT_2026-03-19.md" \
  research/reverse-engineering/README.md \
  research/INDEX.md
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
