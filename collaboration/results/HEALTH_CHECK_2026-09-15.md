# 项目体检报告 - 2026-09-15T19:25:45

> 自动生成于 `2026-09-15T19:26:10.338779` by `scripts/project_healthcheck.py`


## 测试

- ✅ **测试结果**: 2027 passed, 0 failed, 1 skipped
- **覆盖率**: 81% (miss 3366 行)
```
2027 passed, 1 skipped in 22.27s
```

## Git 状态

- **最近 commit** (10):
  - `0f83744 ci: add weekly project healthcheck workflow`
  - `ea98f36 fix(search): resolve 3 attr-defined warnings flagged by mypy strict mode`
  - `7dc574e ci: add mypy to CI informational + fix search.py union-attr`
  - `6317e43 feat(scripts): add project healthcheck script and first report`
  - `5b602ff fix(test): repair backup_dir fallback test using HOME env var`
- **未跟踪文件**: 5 个
- **已修改未提交**: 1 个
  - `?? claude_code_notification.json`
  - `?? codex_notification.json`
  - `?? copilot_notification.json`
  - `?? test_tracking_history.json`
  - `?? user_notification.json`
- ✅ 与 origin/main 同步

## 代码规模

- **生产代码**: 97 文件 / 39647 行
- **测试代码**: 115 文件 / 40136 行
- **测试/代码比**: 1.01 (✅ 健康)

## 覆盖率分解（<80% 模块）

✅ 所有模块覆盖率 ≥ 80%

## 静态检查

- **ruff**: 1169 个问题 (⚠️)
- **mypy**: 111 个错误 (⚠️)

## 依赖安全

- **pip-audit**: skipped

## 项目健康规则

- **CLAUDE.md 含 3 条长期经验**: ✅
- **.gitignore 存在**: ✅

## 总评

### 🏥 总分: 80/100 (A)

**健康状态**: 良好 — 关键指标达标，可持续维护

---

*报告路径: `collaboration/results/HEALTH_CHECK_2026-09-15.md`*
*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*