# 任务: 技术债工单 - P0 封板与发布阻塞修复（Codex）

**任务ID**: TASK-TD-20260305-P0-CLOSEOUT-CODEX-006  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: user  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [compliance-checker, api-test-pro]
- **scope_in**: 将当日技术债交付封板入库并修复 pre-release 唯一阻塞（安全扫描误报）。
- **scope_out**: 不新增业务功能，不改动产品行为设计。

## 输入

- 文件: tests/unit/test_scan_secrets_pii.py, scripts/pre_release_check.sh, collaboration/tasks/, collaboration/results/, .github/workflows/nightly.yml

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260305-P0-CLOSEOUT-CODEX-006.md`
- 必须包含: 执行命令、测试结论、提交哈希、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q tests/unit/test_scan_secrets_pii.py
RUN_PERF_SMOKE=1 bash scripts/pre_release_check.sh --workspace . --quick
git log --oneline -2
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
