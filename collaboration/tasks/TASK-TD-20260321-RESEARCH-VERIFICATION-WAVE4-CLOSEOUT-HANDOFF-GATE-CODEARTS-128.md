# 任务: Research verification wave4 closeout handoff gate

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-CLOSEOUT-HANDOFF-GATE-CODEARTS-128  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 `126/127` 完成后，汇总 Wave 4 的 retention 与 archive sync 结果
  - 形成可直接用于下一轮执行或收口的 handoff gate
  - 输出依赖确认、执行顺序、门禁命令与剩余风险
- **scope_out**:
  - 在 `126/127` 未完成前不提前执行
  - 不直接修改产品代码
  - 不代替 `126/127` 各自的资产产出

## 输入

- `collaboration/results/RESEARCH_VERIFICATION_WAVE4_WORKTREE_RETENTION_PLAN_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md`
- `collaboration/results/WAVE3_CLOSEOUT_SUMMARY_2026-03-21.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE4_HANDOFF_GATE_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-CLOSEOUT-HANDOFF-GATE-CODEARTS-128.md`
- 必须包含:
  - `126/127` 收口摘要
  - 下一步执行顺序
  - 门禁命令
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE4_HANDOFF_GATE_2026-03-21.md
rg -n "126|127|handoff|门禁|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE4_HANDOFF_GATE_2026-03-21.md
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
