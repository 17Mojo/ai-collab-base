# 任务: Research verification wave5 backlog historical freeze

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-BACKLOG-HISTORICAL-FREEZE-CLAUDE-130  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 将 `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md` 从“入口已冻结”补齐为“正文也冻结”的 archive-grade 版本
  - 收正旧的 Wave 3 / Wave 4 状态表述与旧回滚片段
  - 新增一份 historical freeze 资产文档，说明哪些内容保留为历史、哪些内容已被 Wave 3/4 正式结果取代
  - 保持 `research/INDEX.md` 与新资产同步
- **scope_out**:
  - 不新开历史波次任务
  - 不重跑 Wave 1~4 历史验证
  - 不修改产品代码

## 输入

- `collaboration/results/WAVE4_CLOSEOUT_SUMMARY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE5_HISTORICAL_FREEZE_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-BACKLOG-HISTORICAL-FREEZE-CLAUDE-130.md`
- 必须包含:
  - backlog freeze 规则
  - 被替代内容与正式来源映射
  - INDEX 同步结果
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE5_HISTORICAL_FREEZE_2026-03-21.md
rg -n "historical freeze|Wave 3|Wave 4|替代|风险|回滚" research/MULTI_AGENT_VERIFICATION_WAVE5_HISTORICAL_FREEZE_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE5_HISTORICAL_FREEZE_2026-03-21.md" research/INDEX.md
rg -n "历史快照|Wave 3|Wave 4|已收口" research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md
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
