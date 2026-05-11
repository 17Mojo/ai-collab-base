# 任务: Follow-up governance 验证矩阵与 observability artifact 接入 CI

**任务ID**: TASK-TD-20260313-CI-GOVERNANCE-OBS-CLAUDE-071  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**: 将 follow-up governance 相关的验证矩阵和 observability 产物上传策略接入 CI / nightly，保证任务资产、receipt 自愈、daily report 三条能力在 CI 中可见。
- **scope_out**: 不重写整条 CI；不改 Playwright job；不做 release 流程重构。

## 输入

- 文件:
  - `.github/workflows/ci.yml`
  - `.github/workflows/nightly.yml`
  - `collaboration/results/CHERRY_PICK_MERGE_CHECKLIST_FOLLOWUP_2026-03-13.md`
  - `ai_collab/daily_report.py`
  - `scripts/agent_receipt_bridge.py`
  - `ai_collab/state_manager.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260313-CI-GOVERNANCE-OBS-CLAUDE-071.md`
- 必须包含:
  - 新增/修改的 workflow job 或 step
  - follow-up governance 验证命令清单
  - observability artifact 上传清单
  - 失败时如何定位

## acceptance_commands

```bash
python3 -m pytest -q tests/unit/test_state_manager.py tests/unit/test_agent_receipt_bridge.py tests/unit/test_daily_report.py
python3 -m py_compile ai_collab/state_manager.py ai_collab/daily_report.py scripts/agent_receipt_bridge.py
grep -n "upload-artifact@v4" .github/workflows/ci.yml .github/workflows/nightly.yml
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
