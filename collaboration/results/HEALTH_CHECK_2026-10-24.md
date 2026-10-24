# 项目体检报告 - 2026-10-24T10:17:24

> 自动生成于 `2026-10-24T10:17:57.815284` by `scripts/project_healthcheck.py`


## 测试

- ✅ **测试结果**: 2654 passed, 0 failed, 1 skipped
- **覆盖率**: 88% (miss 1796 行)
```
2654 passed, 1 skipped in 30.78s
```

## Git 状态

- **最近 commit** (10):
  - `5c33107 chore(models): 探测会话用完即删，不再污染 CodeArts Doer 会话列表`
  - `17d6290 fix(dispatch): 模型池显式写 provider，钉模型不再依赖 kernel 注册表空窗`
  - `b890f89 chore(monitoring): 刷新监控摘要（投递状态/一致性审计/适配器报告）`
  - `75f7ef0 chore(memory): 同步 CodeArts 侧新增/更新的记忆条目（4 条反馈 + 2 条更新）`
  - `b8d7963 chore(config): bridgeCommand 补上 {model_fallback} 占位符（复核方在复审通过后落地）`
- **未跟踪文件**: 1 个
- **已修改未提交**: 2 个
  - `?? collaboration/results/RESULT-HEALTHCHECK-2026-10-24.md`
- ⚠️ **领先 origin/main 70 个 commit** (未推送)

## 代码规模

- **生产代码**: 100 文件 / 42333 行
- **测试代码**: 132 文件 / 51358 行
- **测试/代码比**: 1.21 (✅ 健康)

## 覆盖率分解（<80% 模块）

| 模块 | 覆盖率 |
|------|--------|
| `ai_collab/codex_integration.py` | 41% |
| `ai_collab/missing_ack_monitor.py` | 65% |
| `ai_collab/prompt_pack/sharing.py` | 65% |
| `ai_collab/integrations/dispatch_notebooklm.py` | 67% |
| `ai_collab/orchestration.py` | 68% |
| `ai_collab/activation_handler.py` | 69% |
| `ai_collab/integrations/vscode.py` | 73% |
| `ai_collab/context/graph.py` | 78% |

## 静态检查

- **ruff** (`ruff check .`): 14 个问题 (🔴)
- **mypy** (`mypy ai_collab`): 0 个错误 (✅)

## 依赖安全

- **pip-audit**: skipped

## 项目健康规则

- **CLAUDE.md 含 3 条长期经验**: ✅
- **.gitignore 存在**: ✅

## 总评

### 🏥 总分: 65/100 (C)

**健康状态**: 需关注 — 存在多个待改进项

---

*报告路径: `collaboration/results/HEALTH_CHECK_2026-10-24.md`*
*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*