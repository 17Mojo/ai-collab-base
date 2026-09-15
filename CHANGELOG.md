# Changelog

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Added (新增)
- **CI/CD 增强**
  - 新增 .github/workflows/security.yml: Bandit 静态代码扫描 + pip-audit 依赖漏洞扫描
  - 新增 .github/workflows/nightly.yml: 每日 UTC 02:00 跑全量测试 + HTML coverage 报告
  - README 补全 CI 状态徽章 (Build / Test / Security Scan)

### Changed (变更)
- .github/workflows/test.yml: 移除 pytest tests/integration/ 的 || true 静默容错, 改为 continue-on-error: true (渐进式收紧)
- ai_collab/orchestration.py: subprocess.run(check_command, shell=True) 重构为 shlex.split + shell=False, 消除 B602 注入告警 (命令来源是硬编码常量, 实际无注入风险)

### Fixed (修复)
- 6 个 Bandit High 风险清零
  - ai_collab/context/aggregator.py (239, 248): MD5 加 usedforsecurity=False (cache key 用途)
  - ai_collab/context/graph.py (252): 同上
  - ai_collab/engines/soul_injection_engine.py (149): 同上 (幂等性缓存键)
  - ai_collab/integrations/multi_source.py (266): 同上 (内容指纹/去重键)

### Security (安全)
- 启用 safety 替代品 pip-audit 扫描依赖漏洞 (safety check 命令 2024-06 已弃用)

---

## 历史发布

详细历史见 git log。早期版本未维护 CHANGELOG。

### 引用
- 本次 PR: ci/security-and-nightly-2026-09 -> main (commit 4aec1ce)
- 推送: 2026-09-14
- 验证: GitHub Actions 4 个 workflow 全部 success
  - Code Quality: 11s
  - Test Suite: 28s
  - Build Artifacts: 32s
  - Security Scan: 35s
- 本地稳定性: pytest 1792 passed + bandit High=0 (连续 3 轮一致)


## [2026-09-15] 覆盖率提升 + 死代码清理

### Removed (清理)
- ai_collab/cli_commands/ (10 文件, 与 cli/ 重复)
- ai_collab/pack/schema_v2_cleaned.py (草稿)
- ai_collab/pack_integration.py (零引用)
- ai_collab/tools/ (含 skills_converter)
- ai_collab/skills/ (simple/editor)
- 净减 -4836 行死代码

### Fixed (修复 4 个生产 bug)
- handoff_id timestamp 冲突: 整数秒 → 毫秒+微秒双重防冲突
- context/search.py 读 item.score 字段不存在 → 改 item.confidence
- context/search.py 读 item.source 字段不存在 → 改 item.source_type (2 处)
- context/search.py _filter_by_scope 缺 query 参数 → NameError

### Added (新增 81 个测试用例)
- tests/unit/test_pack_executor_mvp.py: 36 用例 (78% 局部)
- tests/unit/test_consensus_engine_extra.py: 14 用例 (93% 局部)
- tests/unit/test_workspace_guard_extra.py: 31 用例 (94% 局部)
- test_context_search.py 修复 2 处 fixture typo (eng → engine)

### Test Coverage
- TOTAL: 80% (17338 stmts, 3394 miss)
- 关键模块: context/search.py 85%, pack_executor_mvp.py 78%,
  consensus_engine.py 93%, workspace_guard.py 94%, handoff_notification.py 90%
- 测试总数: 1928 → 2015 passed (+87 净增, 6 fail 全修)

### Changed
- .gitignore: 新增 7 行规则屏蔽沙箱/通知/本地测试记录
- CLAUDE.md: 新增「从 2026-09-15 覆盖率任务提炼的 3 条长期经验」章节
