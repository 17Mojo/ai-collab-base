# 任务: 跨行业 Prompt Pack 最小骨架与字段边界沉淀

**任务ID**: TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-PACK-SKELETON-CLAUDE-104  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于跨行业字段映射矩阵、Owner/Editor 标准输入契约与配对样本，沉淀一份 Prompt Pack 最小跨行业骨架
  - 明确固定字段、行业扩展字段、缺省值与缺信息回退规则
  - 给出至少一个跨行业示例链路，说明如何从 Owner 输入映射到最小 Pack 骨架
  - 在结果报告中说明该骨架如何服务后续产品化工单与示例模板
- **scope_out**:
  - 不改 Prompt Pack 运行时代码
  - 不新增 CLI 子命令
  - 不直接改 OpenSpec spec

## 输入

- `research/reverse-engineering/PACK_CROSS_INDUSTRY_FIELD_MAPPING_MATRIX_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_XIAOHONGSHU_2026-03-09.md`
- `research/reverse-engineering/PACK_OWNER_EDITOR_PAIRED_SAMPLE_EDU_FINANCE_2026-03-09.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-OWNER-EDITOR-CONTRACT-CLAUDE-102.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md`
- `research/INDEX.md`
- `tests/unit/test_pack_requirement_conversion.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-PACK-SKELETON-CLAUDE-104.md`
- 必须包含:
  - 固定字段 / 行业扩展字段边界
  - 最小骨架定义
  - 至少一个跨行业示例映射
  - 缺信息回退规则
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "字段|industry|行业|skeleton|matrix|样本" \
  research/reverse-engineering \
  collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-OWNER-EDITOR-CONTRACT-CLAUDE-102.md \
  collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md
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
