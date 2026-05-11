# 任务: results / research 归档执行器（dry-run / apply / rollback manifest）

**任务ID**: TASK-TD-20260313-ARCHIVE-EXECUTION-CLI-CODEARTS-070  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files]
- **scope_in**: 基于现有归档盘点思路，落地一个可执行的 archive executor，支持 dry-run、apply、rollback manifest 生成。
- **scope_out**: 不做真实云端归档；不做 Git LFS 或对象存储集成；不直接批量改写历史研究内容。

## 输入

- 文件:
  - `ai_collab/archive_inventory.py`
  - `collaboration/scripts/generate_archive_inventory.py`
  - `collaboration/results/OPS_RESULTS_RESEARCH_ARCHIVE_PLAN_2026-03-13.md`
  - `research/`
  - `collaboration/results/`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260313-ARCHIVE-EXECUTION-CLI-CODEARTS-070.md`
- 必须包含:
  - dry-run / apply 模式说明
  - rollback manifest 结构
  - 实际归档候选样例
  - 风险与回滚策略

## acceptance_commands

```bash
python3 -m pytest -q tests/unit/test_archive_inventory.py
python3 collaboration/scripts/generate_archive_inventory.py --workspace . --output logs/archive_inventory_test.json
python3 collaboration/scripts/apply_archive_inventory.py --workspace . --plan logs/archive_inventory_test.json --dry-run --report logs/archive_apply_dryrun_test.json
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
