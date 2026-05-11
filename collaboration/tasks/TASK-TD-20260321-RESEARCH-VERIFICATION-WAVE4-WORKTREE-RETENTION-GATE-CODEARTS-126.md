# 任务: Research verification wave4 worktree retention gate

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-WORKTREE-RETENTION-GATE-CODEARTS-126  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 Wave 3 已关闭状态，盘点当前主仓库、验证 worktree、helper repo 与历史 prunable worktree 的保留关系
  - 输出 keep / prune-candidate / defer 三段式 retention plan
  - 明确 owner lock、安全执行顺序、前置检查命令与非破坏性回滚口径
  - 不直接清空主工作区，不直接删除任何未确认的真实工作目录
- **scope_out**:
  - 不修改产品代码
  - 不直接执行高风险清理命令
  - 不替代 archive / index / backlog 同步任务

## 输入

- `collaboration/results/WAVE3_CLOSEOUT_SUMMARY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md`
- `collaboration/PROTOCOL.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE4_WORKTREE_RETENTION_PLAN_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-WORKTREE-RETENTION-GATE-CODEARTS-126.md`
- 必须包含:
  - 当前 worktree / helper repo 清单
  - retention 分类矩阵
  - 安全执行顺序
  - owner lock / 风险说明
  - 非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE4_WORKTREE_RETENTION_PLAN_2026-03-21.md
rg -n "worktree|helper repo|retention|prunable|owner lock|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE4_WORKTREE_RETENTION_PLAN_2026-03-21.md
git worktree list
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
