# 项目体检报告 - 2026-10-22T17:16:32

> 自动生成于 `2026-10-22T17:17:04.952027` by `scripts/project_healthcheck.py`


## 测试

- ✅ **测试结果**: 2370 passed, 0 failed, 1 skipped
- **覆盖率**: 88% (miss 1720 行)
```
2370 passed, 1 skipped in 29.17s
```

## Git 状态

- **最近 commit** (10):
  - `118acc8 docs(collab): TASK-P1-GOV-CONVERGE-001 工单、结果报告与 P0 契约校正`
  - `fd49835 fix(state): 修复 workspace merge 优先级 bug，state 不再保留陈旧路径`
  - `689b613 feat(cli): react_convert 接入主 CLI pack convert 子命令并补测试`
  - `120d00f fix(pack): 修复 market_store 的 sqlite3 连接泄漏（15 处）`
  - `bbfb426 fix(ci): 还原被误删的 pytest/coverage 配置，覆盖率门禁收敛到唯一事实源`
- **未跟踪文件**: 0 个
- **已修改未提交**: 0 个
- ⚠️ **领先 origin/main 7 个 commit** (未推送)

## 代码规模

- **生产代码**: 99 文件 / 40438 行
- **测试代码**: 121 文件 / 44271 行
- **测试/代码比**: 1.09 (✅ 健康)

## 覆盖率分解（<80% 模块）

✅ 所有模块覆盖率 ≥ 80%

## 静态检查

- **ruff**: 0 个问题 (✅)
- **mypy**: 0 个错误 (✅)

## 依赖安全

- **pip-audit**: skipped

## 项目健康规则

- **CLAUDE.md 含 3 条长期经验**: ✅
- **.gitignore 存在**: ✅

## 总评

### 🏥 总分: 85/100 (A)

**健康状态**: 良好 — 关键指标达标，可持续维护

---

*报告路径: `collaboration/results/HEALTH_CHECK_2026-10-22.md`*
*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*