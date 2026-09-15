# 项目体检报告 - 2026-09-15T18:30:54

> 自动生成于 `2026-09-15T18:31:19.053209` by `scripts/project_healthcheck.py`


## 测试

- ✅ **测试结果**: 2027 passed, 0 failed, 1 skipped
- **覆盖率**: 81% (miss 3365 行)
```
2027 passed, 1 skipped in 22.38s
```

## Git 状态

- **最近 commit** (10):
  - `6317e43 feat(scripts): add project healthcheck script and first report`
  - `5b602ff fix(test): repair backup_dir fallback test using HOME env var`
  - `8b1dc23 test(state_manager): add VSCode path resolution and enum tests`
  - `f017629 build: strengthen mypy and ruff rules to catch field mismatches`
  - `13cef06 ci: add coverage gate to prevent regression at 80 percent floor`
- **未跟踪文件**: 5 个
- **已修改未提交**: 2 个
  - `?? claude_code_notification.json`
  - `?? codex_notification.json`
  - `?? copilot_notification.json`
  - `?? test_tracking_history.json`
  - `?? user_notification.json`
- ✅ 与 origin/main 同步

## 代码规模

- **生产代码**: 97 文件 / 39641 行
- **测试代码**: 115 文件 / 40136 行
- **测试/代码比**: 1.01 (✅ 健康)

## 覆盖率分解（<80% 模块）

✅ 所有模块覆盖率 ≥ 80%

## 静态检查

- **ruff**: 1167 个问题 (⚠️)
- **mypy**: 112 个错误 (⚠️)

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