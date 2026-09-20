# 项目体检报告 - 2026-09-20T10:36:14

> 自动生成于 `2026-09-20T10:36:40.651604` by `scripts/project_healthcheck.py`


**完成时间**: 2026-09-20T10:36:14+08:00  
**报告版本**: 1.0.0

## 测试

- ✅ **测试结果**: 2062 passed, 0 failed, 1 skipped
- **覆盖率**: 81% (miss 3339 行)
```
2062 passed, 1 skipped in 22.43s
```

## Git 状态

- **最近 commit** (10):
  - `caeb8af test(api): 补 5 个测试守护 schema_validator 非阻断式接入`
  - `3b19bd0 feat(api): 接入 schema_validator 到 pack CRUD 端点（非阻断式）`
  - `001c7b4 fix(schema_validator): validate_data 防御 None 值避免 TypeError`
  - `81a02c5 test(schema_v2): 补 9 个测试守护 validate() 新增 4 项检查`
  - `58070cf feat(schema_v2): 补 PromptPackV2.validate() 4 项结构完整性检查`
- **未跟踪文件**: 1 个
- **已修改未提交**: 1 个
  - `?? test_tracking_history.json`
- ⚠️ **领先 origin/main 23 个 commit** (未推送)

## 代码规模

- **生产代码**: 97 文件 / 39725 行
- **测试代码**: 116 文件 / 40572 行
- **测试/代码比**: 1.02 (✅ 健康)

## 覆盖率分解（<80% 模块）

✅ 所有模块覆盖率 ≥ 80%

## 静态检查

- **ruff**: 0 个问题 (✅)
- **mypy**: 109 个错误 (⚠️)

## 依赖安全

- **pip-audit**: skipped

## 项目健康规则

- **CLAUDE.md 含 3 条长期经验**: ✅
- **.gitignore 存在**: ✅

## 总评

### 🏥 总分: 65/100 (C)

**健康状态**: 需关注 — 存在多个待改进项

---

*报告路径: `collaboration/results/HEALTH_CHECK_2026-09-20.md`*
*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*