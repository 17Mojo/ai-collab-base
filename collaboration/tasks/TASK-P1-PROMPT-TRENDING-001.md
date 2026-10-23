---
task_id: TASK-P1-PROMPT-TRENDING-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: codearts_agent
assignee_role: AGENT_EXEC
reviewer: claude_code
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-23T12:40:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_pack_store.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/"
result_file: collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md
---

# TASK-P1-PROMPT-TRENDING-001：让「热门 Pack (7天内)」名副其实

> **本工单由 Claude Code（AGENT_ARCH）定义契约，CodeArts（AGENT_EXEC）实现。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
> 复核方：Claude Code（AGENT_TEST）。

## 一、背景与真证

CLI 已经在**承诺**一个时间窗口：

```python
# ai_collab/cli/_cli_main.py:4058-4063
elif args.store_subcommand == "trending":
    packs = search_engine.get_trending_packs(days=7, limit=args.limit)
    print("\n热门 Pack (7天内):")
```

但实现里 `days` 参数**被完整地忽略**：

```python
# ai_collab/prompt_pack/store.py:299-313
def get_trending_packs(self, days: int = 7, limit: int = 10) -> list[PackIndexEntry]:
    # TODO: 实现基于时间的热度计算
    # 当前简单按下载次数排序
    all_packs = self.registry.get_all_packs()
    return sorted(all_packs, key=lambda x: x.downloads, reverse=True)[:limit]
```

**这是用户可见的口不符**：界面写「7天内」，实际给的是「历史累计下载排行」。
`days` 形同虚设，且源码里留着 `# TODO: 实现基于时间的热度计算` —— 本仓自己标注的未完成项。

**根因链（三层，缺一不可）**：

| 层 | 位置 | 现状 |
|---|---|---|
| L1 数据 | `PackIndexEntry` | 只有累计计数 `downloads: int`，**没有任何时间戳** ⇒ 窗口无从计算 |
| L2 写入 | `PackRegistry.update_pack_stats(downloads=N)` | 只累加计数，**不记录时间** ⇒ 就算算窗口也没有数据 |
| L3 统计 | `refresh_index()` → `_build_index()` | 重建索引时用**全新条目**覆盖旧条目 ⇒ `downloads`/`rating`/`review_count` **全部归零** |

L3 尤其关键：即使 L1/L2 实现了下载事件，**一次 `refresh_index()` 就会把事件历史清空**，
热度功能活不过一次刷新。所以 L3 必须一起修。

## 二、目标

1. `get_trending_packs(days, limit)` 真正按**时间窗口**计算热度；
2. 索引里有**下载事件时间序列**，可持久化、可回溯；
3. `refresh_index()` 不再清空已积累的统计与下载事件；
4. 「推荐 Pack」不被新窗口语义误伤；
5. 全部行为由不变量测试锁住。

## 三、详细契约（逐条实现，不要自行发挥）

### R1 数据模型：下载事件时间序列

**文件**：`ai_collab/prompt_pack/store.py`

`PackIndexEntry` 新增字段：

```python
download_events: list[str] = field(default_factory=list)   # ISO-8601 下载时间戳
```

- `field` 若尚未 import，需补 `from dataclasses import field`（当前文件用的是 `@dataclass`）。
- `to_dict()` **必须**输出 `"download_events": [...]`。
- `PackRegistry._load_index()` 读取时用 `entry_data.get("download_events", [])`。
  **向后兼容**：旧索引文件没有该字段时按 `[]` 处理。
- **健壮性要求**：`download_events` 存在但不是 `list`（例如被手工改坏成字符串）时，
  按 `[]` 处理，**不得**让 `_load_index()` 抛异常 —— 现有 except 分支会
  `_build_index()` 重建索引并**清空全部统计**，那会丢掉下载历史，属于比原缺陷更严重的回归。
- `_build_index()` 新建的条目 `download_events=[]`。

### R2 事件写入：记下「什么时候下载的」

**函数**：`PackRegistry.update_pack_stats(downloads=N)`

- `N > 0` 时：向 `entry.download_events` 追加 **N 条**当前时间戳（`datetime.now().isoformat()`）。
- `N <= 0` 或 `N is None` 时：**不追加**。
- 追加后**裁剪**：只保留**最近 90 天**的事件（按事件时间戳与当前时间之差判断），
  防止索引文件无限膨胀。90 天是本契约指定的常量，请在代码里写成具名常量并注释来源。
- 现有函数末尾已有 `self._save_index()`，保持不变（落盘自动包含新字段）。

### R3 统计存活：refresh_index 不得清零

**函数**：`PackRegistry._build_index()`（`refresh_index()` 走这条路）

- 重建索引时，对**同名**的包**保留**旧条目的 `downloads` / `rating` / `review_count` / `download_events`。
- 其余字段（`version` / `description` / `author` / `category` / `created_at` / `updated_at` / `tags`）
  以文件系统的 `manifest.json` 为准（现有行为不变）。
- 旧索引里有、但文件系统里已不存在的包：**维持现有行为**（从索引中移除）。本工单不改这一点。

### R4 窗口计算：热度排序语义

**函数**：`PackSearchEngine.get_trending_packs(days=7, limit=10)`

| 情形 | 行为 |
|---|---|
| `days <= 0` | 抛 `ValueError`，消息里须包含 `days` 字样 |
| `limit <= 0` | 返回 `[]`（**不抛**） |
| 正常 | 见下 |

正常路径：

1. 窗口 = `[now - timedelta(days=days), now]`（**闭区间**）。
2. **候选** = 窗口内**至少有一次**下载事件的 Pack。
3. 排序键（依次比较）：
   1. 窗口内下载次数 **desc**；
   2. 总下载数 `downloads` **desc**；
   3. `name` **asc** —— 稳定 tie-break，保证结果**可重现**（同分时按名称字典序）。
4. 取前 `limit` 个返回。

**降级路径（必须实现）**：若候选为空（例如历史索引根本没有事件数据），
**退回**按 `downloads` desc 排序的前 `limit` 个 —— 与本工单改动前的行为一致，
保证 CLI「热门 Pack」不会因为历史数据缺失而空屏。
降级语义必须写进**代码注释**与**结果文件**（读者要能看出这是有意为之，不是 bug）。

### R5 解除「推荐」被窗口误伤

**函数**：`PackSearchEngine.get_recommended_packs(pack_name, limit=5)`

- 当 `pack_name` 不在索引里时，当前 fallback 调 `self.get_trending_packs(limit=limit)`。
  R4 落地后，这条路径会被 7 天窗口裁掉 —— 但「推荐」的语义不该被 7 天窗口绑架。
- **修复**：fallback 改为**不依赖窗口**的排序（`downloads` desc，再 `name` asc），
  语义 = 「全部 Pack 里最热门的」。
- 同类别推荐分支（`rating * 10 + downloads * 0.1`）**行为不变**。

### R6 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---|---|
| `ai_collab/prompt_pack/store.py` | **`ai_collab/cli/_cli_main.py`** |
| `tests/unit/test_pack_store.py`（或新建 `tests/unit/test_prompt_pack_trending.py`） | `ai_collab/cli/` 下**任何**其他文件 |
| `collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md` | `ai_collab/prompt_pack/rating.py`（除非确有无法绕开的依赖，且需在结果文件说明） |

**为什么禁 `ai_collab/cli/`**：Claude Code 正在**同一工作区**并行修改
`ai_collab/cli/_cli_main.py`（另一条工作线：派单即入队接线）。
两个 Agent 同时改一个文件 = 合并冲突 + 归属不清。
**共享工作区纪律：只 add 自己改的文件。**

### R7 既有行为不得回归

- `ai_collab/prompt_pack/rating.py` 调用 `update_pack_stats(rating=..., review_count=...)`，
  **不传 downloads** ⇒ 不得因此产生任何下载事件。
- `tests/unit/test_pack_store.py` 的**既有用例必须全部继续通过**。
  若某条既有用例因新语义必须修改：**逐条在结果文件里说明改了什么、为什么**，
  **不得**静默删改断言。

### R8 测试要求（新增用例至少覆盖以下 11 条）

1. 窗口内事件 vs 只有窗口外事件 → 前者入选、后者不入选；
2. 窗口内下载次数**优先于**总下载数参与排序；
3. 完全同分时按 `name` 升序，**结果可重现**；
4. `days <= 0` 抛 `ValueError`；
5. `limit <= 0` 返回 `[]`；
6. 降级路径：窗口内无任何事件 → 返回按总下载数排序的结果；
7. `download_events` **持久化**：写盘后重新 `PackRegistry` 加载仍在；
8. **旧索引文件**（无 `download_events` 字段）能正常加载，不报错、统计不丢；
9. `update_pack_stats(downloads=N)` 追加 **N** 条事件；`downloads=0` / `None` 不追加；
10. `refresh_index()` 后 `downloads` / `download_events` **不丢**；
11. `get_recommended_packs` 对**不存在的** `pack_name`，fallback **不受窗口影响**。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_pack_store.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check ai_collab/` 无**新增**问题
- [ ] 结果文件 `collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md` 存在，
      且含「执行命令 / 测试结论 / 风险 / 回滚」四段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] `git diff --name-only` **不含** `ai_collab/cli/` 下任何文件
- [ ] 既有测试若被改动，改动理由**逐条**写进结果文件

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**（手写 ACK 会被回执桥接判为「非显式 ACK」而拒绝收口）：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-PROMPT-TRENDING-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md
```

把该命令**原样输出**的一行回复回来（形如
`A.ACK|task=TASK-P1-PROMPT-TRENDING-001|status=ok|result=collaboration/results/RESULT-P1-PROMPT-TRENDING-2026-10-23.md`）。

## 六、参考

- 实现文件：`ai_collab/prompt_pack/store.py`（`PackIndexEntry` / `PackRegistry` / `PackSearchEngine`）
- 既有测试：`tests/unit/test_pack_store.py`
- CLI 消费点（**只读参考，不要改**）：`ai_collab/cli/_cli_main.py:4058`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
