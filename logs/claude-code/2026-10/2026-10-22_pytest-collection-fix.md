# 开发记录：pytest collection error 修复（hermes_target 隔离）

## 记录信息

- **任务ID**: quickfix/no-spec（用户直接指令）
- **AI类型**: Claude Code
- **时间**: 2026-10-22
- **分支**: `refactor/slimming-2026-09-20`
- **任务描述**: 现场核验 2026-09-20 审计报告的 P0 清单后，修复 `hermes_target/` 导致的 pytest collection error，恢复全量测试可跑。

---

## 背景（现场核验结论）

对基于 2026-09-20 审计的深度分析报告执行「洞察 vs 真证」核验，关键差异：

| 洞察（2026-09-20 审计） | 真证（2026-10-22 核验） |
|---|---|
| mypy 109 错误 | 0 错误（99 源文件，9590f0b 清零） |
| 冷启动绑定 uninitialized | binding_status=active / multi_agent |
| CONSENSUS-ENGINE 任务 pending | ready_to_implement，实为向外部 Hermes 移植 |
| 测试 2062 passed | collect 2665 + 1 collection error（hermes_target） |
| CI 无覆盖率阈值 | test.yml 已有 fail-under=85 硬门禁 |

四元组：mypy=0 错误/99 文件/`mypy ai_collab`/mypy 2.3.1；测试=2665 collected/1 error/`pytest --collect-only -q`/Python 3.14.6。

## 根因

`hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` 是外部 Hermes 移植目标的本地副本（TASK-P0-CONSENSUS-ENGINE-001 工作产物），其 `hermes_agent` 模块不在本仓库依赖内，pytest 默认从根目录收集时触发 `ModuleNotFoundError`（2026-09-26 已知陷阱）。

## 修复

`pyproject.toml` 新增 `[tool.pytest.ini_options]`：

```toml
testpaths = ["tests"]
```

方案选择依据：
- **白名单优于黑名单**：`find` 真证确认 tests/ 之外零测试文件，testpaths 不会漏收集
- **对齐 CI 口径**：CI 跑 `tests/unit/`（test.yml），本地 testpaths 覆盖面 >= CI
- hermes_target/ 是活跃工作线（3ae6cca），保留目录仅排除收集

## 验证

- `pytest --collect-only -q`: 2665 collected / **0 errors**（修复前 2665 + 1 error，数量不变，无测试误排除）
- 冒烟：`pytest tests/unit/test_pack_schema_validator.py` → 64 passed / 0.07s
- ruff：不适用（toml 不在 ruff 检查范围）

## 变更文件

- `pyproject.toml`（+9 行，新增 pytest 配置段）

## 风险与回滚

- 风险：未来若有测试置于 tests/ 之外（如 local-backend 独立测试），不会被根目录收集——当前真证为无此情况
- 回滚点：删除 `[tool.pytest.ini_options]` 段即可恢复原行为

## 后续建议

1. 全量跑 `pytest`（现在已可跑）拿通过率 + 覆盖率真证，验证 CI 85% 阈值本地达成
2. slimming 分支领先 main 20 提交未合并，评估合并收尾
3. 治理报告已 stale 33 天（result-consistency 2026-09-19 生成），可刷新

---

# 续：无争议收尾三项（2026-10-22 同日）

用户确认「零外部用户」后选择「暂不拍板路线，先收尾」，执行三项无争议工作。

## 任务 1：推送 ahead 2

- `git fetch` 后确认 ahead 2，推送 `157cb2c..3ae6cca` → 远端。三条底线（测试全绿/代码在远端/无未 ACK 完成项）全绿。

## 任务 2：gen_facts 收尾

发现并修正脚本两处真 bug：

| 问题 | 真证 | 修正 |
|---|---|---|
| 输出时间戳文件名 | 会积累快照堆积（已有 `FACTS_2026-10-21_193044.md` 无人认领权威） | 固定 `docs/FACTS.generated.md` |
| 第 3 节远端同步语义写反 | `HEAD..origin/main` 实为 behind 且硬编码 main；在 slimming 分支上会把 ahead 20 误报成 unpushed | 改用 `@{u}` 的 unpushed/behind |

接入：`nightly.yml` 新增生成 + artifact 上传（不自动提交回仓库，避免 CI 写入引入归属不清——PROTOCOL.md 14.4）。

## 任务 3：清理与归档

- **CONFLICT-1772060801 残留**（实际 2026-02-27 已结案）：`ACTION_ITEMS.md` P0-1 标记完成、`OWNERSHIP.md` 状态改已解决、`logs/monitoring_backup` 仪表盘（gitignore 本地文件）加过期警告。
- **历史规则文件归档**：6 个文件 `rules/` → `rules/archive/`（claude_code_memory / codex_agent_rules / codearts_agent_rules / copilot_rules / trae_rules / agent_governance_quickstart），加统一归档警告头。
- **同步引用 13 处**（消除半死文件误导）：`CLAUDE.md` P0 清单移除已归档项（此前与 P2 定位自相矛盾）、`AI_BEHAVIOR_CONSTRAINT_FILES.md` P2 表、`OWNERSHIP.md` 文件清单、CODEX_SPAWN 指南、归档文件内自引用。
- 修正批量替换引入的 `.md.md` 双后缀（7 文件 13 处）。

## 验证与提交

- 全量真证：**2686 passed / 6 skipped / 0 failed**（47.74s；比核验时 2660 多 26 个，来自并行协作者新增测试）
- 2 个提交（conventional commits + scope）：`e9d1bb2`（chore(scripts)）、`1c4bf4b`（docs(rules)），已推送
- 提交时精确 add 本会话文件，避开并行协作者（TASK-P1-GOV-CONVERGE-001）在途改动

## 未完成 / 遗留

1. **`pyproject.toml` testpaths 修复未入库**：该文件混入并行协作者的 asyncio/markers/coverage omit 配置（同一配置段），无法拆分为独立提交，需其任务收口时一并提交。修复已在本地生效。
2. 治理报告 stale（result-consistency 生成于 2026-09-19）
3. `_cli_main.py` 5,027 行未拆（并行任务在途）
4. 产品验证缺口：真机跨平台回归 + 第一个外部用户（路线拍板的前置实验）
