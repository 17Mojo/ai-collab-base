# 任务: Research verification wave3 diff inventory

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-DIFF-INVENTORY-CLAUDE-121  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 Wave 2 四个门禁任务全部完成后，收集可用于 Wave 3 综合修复的差异与证据输入
  - 复用 `/private/tmp/cc-claude-codex`、`/private/tmp/ai-collab-system-verify-wave2-claude` 与 Wave 2 结果文件
  - 盘点 worktree / helper repo / 研究资产 / 结果文件 / 可疑改动来源，形成 diff inventory
  - 明确哪些差异属于高置信输入，哪些只是辅助证据，供 W3-002 重叠分析使用
- **scope_out**:
  - 不直接执行重叠问题分析
  - 不直接修改主工作区产品代码
  - 不提前关闭 W3-002/W3-003/W3-004

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE3-DIFF-INVENTORY-CLAUDE-121.md`
- 必须包含:
  - 差异来源清单
  - worktree / helper repo / 结果文件证据位置
  - commit / branch / path 级别的输入索引
  - 高置信 / 辅助证据分层
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md
rg -n "diff|commit|worktree|helper repo|证据|风险|回滚" \
  research/MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE3_DIFF_INVENTORY_2026-03-21.md" research/INDEX.md
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
