# 项目体检报告 - 2026-10-24T15:26:28

> 自动生成于 `2026-10-24T15:27:07.598571` by `scripts/project_healthcheck.py`


## 测试

- ✅ **测试结果**: 2692 passed, 0 failed, 1 skipped
- **覆盖率**: 88% (miss 1796 行)
```
2692 passed, 1 skipped in 36.83s
```

## Git 状态

- **最近 commit** (10):
  - `414f091 feat(openspec): 落地 OpenSpec 规范驱动工作流并补齐变更工件`
  - `04bca05 fix(memory): 修订已被证伪的 CLI 退出码条目（缺陷已于 a938cd8 修复）`
  - `5b35d59 docs(result): 补齐 Phase 4 结果文件的验收命令（任务收口门禁要求原样出现）`
  - `79c5c37 chore(monitoring): 刷新结果一致性摘要（Phase 4 收口）`
  - `e6fb352 test(guard): 并发工作区守护 Phase 4 项目边界（OpenSpec Phase 4）`
- **未跟踪文件**: 0 个
- **已修改未提交**: 0 个
- ⚠️ **领先 origin/main 90 个 commit** (未推送)

## 代码规模

- **生产代码**: 100 文件 / 42515 行
- **测试代码**: 137 文件 / 52315 行
- **测试/代码比**: 1.23 (✅ 健康)

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

- **ruff** (`ruff check .`): 0 个问题 (✅)
- **mypy** (`mypy ai_collab`): 0 个错误 (✅)

## 依赖安全

- **pip-audit**: skipped

## 项目健康规则

- **CLAUDE.md 含 3 条长期经验**: ✅
- **.gitignore 存在**: ✅

## 总评

### 🏥 总分: 85/100 (A)

**健康状态**: 良好 — 关键指标达标，可持续维护

---

*报告路径: `collaboration/results/HEALTH_CHECK_2026-10-24.md`*
*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*