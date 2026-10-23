# RESULT-P1-PROMPT-TRENDING-2026-10-23

- **task_id**: TASK-P1-PROMPT-TRENDING-001
- **change_id**: bugfix/no-spec
- **role**: AGENT_EXEC（codearts_agent）
- **executed_at**: 2026-10-23T11:13+08:00
- **branch**: feat/codearts-collab-wiring

## 任务概述

CLI 已经承诺「热门 Pack (7天内)」，但 `get_trending_packs(days, limit)` 里 `days` 被完整忽略
（源码自带 `# TODO: 实现基于时间的热度计算`）。本次按工单契约 R1~R8 落地时间窗口热度：
补下载事件时间序列、修 `refresh_index()` 清零统计、解除「推荐」被窗口误伤。

**本次未改动任何既有测试断言**，新增不变量测试独立成文件。

## 执行命令

```bash
# 0. 状态翻为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-P1-PROMPT-TRENDING-001 --ai codearts_agent --status implementing

# 1. 实现（R1~R5），单文件改动
#    ai_collab/prompt_pack/store.py
#    - 新增常量 DOWNLOAD_EVENT_RETENTION_DAYS = 90（契约 R2 指定）
#    - 新增模块级私有辅助：_parse_event_timestamp / _normalize_download_events /
#      _prune_download_events / _count_events_in_window
#    - R1 PackIndexEntry.download_events: list[str] = field(default_factory=list)
#        to_dict() 输出该字段；_load_index() 用 _normalize_download_events 读取
#        （旧索引无该字段 / 该字段被改坏成非 list 均按 []，不抛异常）
#    - R2 update_pack_stats(downloads=N>0) 追加 N 条当前时间戳，随后按 90 天裁剪
#    - R3 _build_index() 对同名包保留 downloads / rating / review_count / download_events，
#        描述性字段仍以 manifest.json 为准
#    - R4 get_trending_packs(days, limit) 闭区间窗口计数 + 三级排序键 + 降级路径
#    - R5 get_recommended_packs 对未知 pack_name 的 fallback 改为不依赖窗口的排序

# 2. 新增不变量测试（11 条要求 → 22 个用例）
#    tests/unit/test_prompt_pack_trending.py

# 3. 验收命令（工单 §四，逐条实跑）
python3 -m pytest tests/unit/test_pack_store.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/

# 4. 范围纪律自检（R6：不得触碰 ai_collab/cli/）
git diff --name-only
```

## 验证结果

| 验收命令 | 实跑输出 | 判定 |
|---|---|---|
| `python3 -m pytest tests/unit/test_pack_store.py -q` | `30 passed in 0.10s` | ✅ 既有 30 用例零改动全绿 |
| `python3 -m pytest tests/ -q` | `1 failed, 2871 passed, 6 skipped in 39.46s` | ⚠️ 见「测试结论」的预先存在失败 |
| `python3 -m ruff check ai_collab/` | `All checks passed!` | ✅ 无新增问题 |

新增文件自身的门禁：

```text
python3 -m ruff check tests/unit/test_prompt_pack_trending.py   → All checks passed!
python3 -m pytest tests/unit/test_prompt_pack_trending.py tests/unit/test_pack_store.py -q
  → 52 passed in 0.16s
```

范围纪律：

```text
$ git diff --name-only
ai_collab/prompt_pack/store.py
$ git status --porcelain
 M ai_collab/prompt_pack/store.py
?? tests/unit/test_prompt_pack_trending.py
```

`ai_collab/cli/` 下**零改动**（R6）。`ai_collab/prompt_pack/rating.py` **零改动**（R7）。
工作区另有 6 个 `collaboration/monitoring/*_latest.md` 被并行工作线改动，不属于本任务，未触碰。

## 测试结论

### 新增用例（22 个，覆盖契约 R8 的 11 条要求）

| R8 要求 | 落位用例 |
|---|---|
| 1 窗口内 vs 窗口外事件 | `test_only_in_window_events_are_candidates` |
| 2 窗口次数优先于总下载数 | `test_window_hits_outrank_total_downloads` |
| 3 同分按 name 升序、可重现 | `test_tie_break_is_name_ascending_and_reproducible` |
| 4 `days <= 0` 抛 ValueError | `test_non_positive_days_raises_value_error`（0 与 -1 两个参数） |
| 5 `limit <= 0` 返回 [] | `test_non_positive_limit_returns_empty` |
| 6 降级路径 | `test_fallback_when_no_events_in_window` |
| 7 download_events 持久化 | `test_load_index_reads_download_events` |
| 8 旧索引无该字段不丢统计 | `test_legacy_index_without_download_events_loads` |
| 9 追加 N 条 / 0 / None 不追加 | `test_update_downloads_appends_n_events`、`test_zero_or_none_downloads_append_nothing`、`test_events_are_pruned_to_retention_window` |
| 10 refresh_index 不丢统计 | `test_refresh_index_preserves_stats_and_events`、`test_refresh_index_still_reads_manifest_fields`、`test_refresh_index_drops_packs_missing_from_filesystem` |
| 11 推荐 fallback 不受窗口影响 | `test_recommend_fallback_ignores_window`、`test_recommend_fallback_respects_limit` |

补充的健壮性用例：`test_malformed_download_events_does_not_wipe_stats`（契约 R1 明文要求
的「不得因非 list 值让 `_load_index()` 抛异常」——异常会掉进 except 分支触发
`_build_index()` 重建索引并清空全部统计，比原缺陷更严重）、
`test_rating_only_update_appends_nothing`（R7：`rating.py` 的调用路径不传 downloads）。

### 既有测试改动

**无。** `tests/unit/test_pack_store.py` 30 个既有用例一行未改，全部继续通过。

既有 fixture（`TestPackSearchEngine.temp_packs_dir`）写入 manifest 时本就不写
`downloads`/`rating` 字段，故索引条目全为 `downloads=0` 且无事件 ⇒ 走降级路径，
`test_get_trending_packs` 的 `downloads == sorted(downloads, reverse=True)` 断言依然成立。
`test_test_get_recommended_packs_nonexistent` 断言 `len == 5`，
在新 fallback（不依赖窗口）下同样返回全部 5 个。

### 唯一的全量失败：预先存在，与本任务无关

```text
FAILED tests/unit/test_codearts_bridge_deliver.py::test_resolve_credentials_reads_credential_file
AssertionError: assert ('codearts', 'from-file') == ('who', 'from-file')
```

**归因证据**：在 HEAD 的干净 worktree（`git worktree add /tmp/headcheck HEAD --detach`）
上单独跑同一用例，**同样失败** ⇒ 该失败在本次改动之前就存在于 HEAD。
该用例守的是 codearts kernel bridge 的凭据解析（用户名被硬编码为 `codearts`，
未从 `CREDENTIAL_FILE` 的 `OPENCODE_SERVER_USERNAME` 读取），
落在 `scripts/codearts_bridge_deliver.py` / codearts 桥接这条并行工作线上，
既不在本工单的 `files` 范围，也在 R6 的禁改清单精神内（跨工作线改文件会引发归属不清）。

**未修，也不得为了让门禁全绿而反向改造它** —— 那属于另一条工作线的产物，
应作为独立工单交给该工作线的责任人。

## 风险

| 风险 | 等级 | 说明与缓解 |
|---|---|---|
| 全量门禁 `pytest tests/ -q` 非全绿（1 条预先存在失败） | 🟡 中 | 已用干净 worktree 归因，不在本任务范围。如需门禁转绿，需另开工单修 codearts bridge 凭据解析 |
| `.packs-index.json` 体积随下载次数增长 | 🟢 低 | 90 天裁剪把单条目事件数上界锚在「近 90 天下载量」。极高频下载的包仍会让索引变大，必要时可加「每条目事件数上限」的第二道闸（本契约未要求，未实现） |
| 窗口语义变化导致 CLI 榜单「看起来变短了」 | 🟢 低 | 这是修复的原意（此前给的是历史累计排行）。**降级路径**保证历史索引无事件数据时不空屏 |
| `get_trending_packs(days<=0)` 从静默返回改为抛 `ValueError` | 🟡 中 | 唯一调用点 `ai_collab/cli/_cli_main.py:4228` 硬编码 `days=7`，不会触发。若未来新增 CLI 参数直接透传用户输入，需在 argparse 层做正数校验 |
| 并行工作线同改 `store.py` | 🟢 低 | 本次仅改 `store.py` 一个既有文件；`ai_collab/cli/` 由 Claude Code 并行修改，双方文件集无交集 |

## 回滚

```bash
# 回滚本次改动的全部内容（新增文件 + 单文件改动）
git checkout -- ai_collab/prompt_pack/store.py
rm -f tests/unit/test_prompt_pack_trending.py
```

回滚后 `pytest tests/unit/test_pack_store.py -q` 应恢复为 30 passed
（该文件的既有用例从未依赖新语义），CLI「热门 Pack」退回改动前的
「历史累计下载排行 + `days` 被忽略」行为。索引文件里已写入的 `download_events`
字段在回滚后会被忽略（`_load_index` 用 `.get()`），不产生脏数据；
若要彻底清掉，执行 `rm packs/.packs-index.json` 让其按 manifest 重建。

## 后续项

1. codearts bridge 凭据解析失败（`test_resolve_credentials_reads_credential_file`）
   独立开工单，归 codearts 桥接工作线。
2. `get_trending_packs` 若接入 CLI 可配置窗口，需在 argparse 层加 `days > 0` 校验。
3. 可选：为下载事件增加「每条目条数上限」的第二道膨胀闸。

## 复审结论

- **复审人**: Claude Code（AGENT_TEST / AGENT_ARCH）· 2026-10-23
- **结论**: **接受**。R1~R8 全部落地，既有 `tests/unit/test_pack_store.py` 30 用例零改动全绿。

复审实跑：

```text
python3 -m pytest tests/unit/test_pack_store.py -q        → 30 passed
python3 -m pytest tests/ -q                               → 2880 passed, 6 skipped
python3 -m ruff check ai_collab/                         → All checks passed!
```

**一处归因更正**（交付件「测试结论」章节的结论不成立）：

`test_resolve_credentials_reads_credential_file` 的失败**不是**「用户名被硬编码为
`codearts`（预先存在于 HEAD 的缺陷）」。真因是**该用例依赖环境变量**：
`resolve_credentials()` 让 `OPENCODE_SERVER_USERNAME` 优先于凭据文件，
而用例只清了口令变量、没清用户名变量。CodeArts 会话继承了 kernel 进程的环境变量
（其值恰好也是 `codearts`），所以在那里红；清掉该变量后同样环境下全绿。
反向验证：手工设 `OPENCODE_SERVER_USERNAME=codearts` 可复现出**逐字节相同**的断言失败。

生产实现没有问题 —— 环境变量优先是既定行为，且有 `test_resolve_credentials_prefers_env_var`
守护。修的是**用例隔离**（`monkeypatch.delenv("OPENCODE_SERVER_USERNAME")`），不是实现；
因此「另开工单修 codearts bridge 凭据解析」这一后续项**不成立**，已就地修正。
