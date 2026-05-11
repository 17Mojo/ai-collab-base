# 任务: 研究索引状态回写与同步规则自动化

**任务ID**: TASK-TD-20260319-RESEARCH-STATE-SYNC-AUTOMATION-CODEARTS-099  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 为 `research/INDEX.md` 建立稳定的状态回写规则与同步 checklist
  - 明确研究文档从 `规划中 / 待同步 / 已完成` 到结果文档、任务文档的回写触发时机
  - 盘点当前 `research/` 主线中最容易漂移的状态字段与引用路径
  - 在结果报告中给出后续研究任务的最小同步操作口径
- **scope_out**:
  - 不新增新的研究主题
  - 不改 Prompt Pack 产品代码
  - 不修改 OpenSpec 规范正文

## 输入

- `research/INDEX.md`
- `research/IMPLEMENTATION_SUMMARY.md`
- `research/PROMPT_PACK_V2_RESEARCH_PROGRESS.md`
- `research/reverse-engineering/`
- `collaboration/results/BASE_RESEARCH_7DAY_EXECUTION_PLAN_2026-03-19.md`
- `collaboration/results/PROJECT_PROGRESS_SYNC_2026-03-01.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-STATE-SYNC-AUTOMATION-CODEARTS-099.md`
- 必须包含:
  - 建议的研究状态集合与判定口径
  - 回写触发时机与责任人说明
  - `research/INDEX.md` 最小维护 checklist
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "最后更新|状态|规划中|已完成|待同步" research/INDEX.md research
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
