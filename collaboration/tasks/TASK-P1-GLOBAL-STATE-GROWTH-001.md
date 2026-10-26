---
task_id: TASK-P1-GLOBAL-STATE-GROWTH-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: performance-expert
support_skills:
  - devops-architect
created_at: 2026-10-24T20:40:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_state_manager_global_sync.py -q"
  - "python3 -m pytest tests/perf/ -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
result_file: collaboration/results/RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md
---

# TASK-P1-GLOBAL-STATE-GROWTH-001：全局状态文件无上限增长 + 死条目从不回收

> **本工单是 PR #2 复核过程中挖出的独立产品缺陷**，不属于 PR #2 的交付范围。
> PR #2 只做了「让性能基线不再依赖运行者的机器历史」；**缺陷本身没有被修**。
> 这里登记成独立工单，避免它随 PR #2 的合并一起「消失」。

## 一、问题

`StateManager._sync_to_global()`（`ai_collab/state_manager.py:838`）把**每个**
`workspace_path` 的完整状态写进全局文件：

- 全局文件路径：`VSCodeStateManager.get_global_state_file()`
  （`ai_collab/state_manager.py:145-149`）→ `os.path.expanduser("~/.vscode/ai-collab")`
  + `collaboration_state.json`。`expanduser` 在 POSIX 上跟随 `HOME`、在 Windows 上跟随
  `USERPROFILE`。
- 写入方式：**读整份 → 改一条 → 写回整份**（`global_state[workspace_key] = {...}`，
  `ai_collab/state_manager.py:853`）。
- **从不回收**已经不存在的 workspace 条目——没有 LRU、没有 mtime 淘汰、没有体积上限。

## 二、实测证据（2026-10-24，作者侧独立实测）

开发机 `~/.vscode/ai-collab/collaboration_state.json`：

| 指标 | 实测值 |
|---|---|
| 体积 | 5,424,838 字节（5.4 MB） |
| 条目数 | 1581 |
| 其中**测试自身泄漏**的临时目录条目 | **1578**（pytest 临时目录 + macOS `tempfile.mkdtemp()` 路径） |
| 真实工作区条目 | **3** |
| 泄漏条目占总字符数 | 3,707,336 / 3,895,775 = **95.2%** |

3 条真实工作区条目及其体量：

- `/Users/raymondna/Documents/ai-collab-system` —— 100 个任务 / 164,160 字符
- `.` —— 4 个任务 / 5,811 字符
- `/Users/raymondna/Documents/AI-collab/ai-collab-base` —— 13 个任务 / 18,468 字符

**后果 1（无上限增长）**：每跑一次测试套件就往全局文件里塞一条临时目录条目，
永远不删。文件只增不减。

**后果 2（写放大）**：每次 `update_task_status` 都要把整份全局文件重新序列化一遍。
拿真实文件的**逐字节副本**做隔离复现，单次 update 稳定落在 0.098~0.103 秒
（`state_update_single` 阈值 0.1s 的**上下横跳**）；把 HOME 隔离到空目录后，
同一用例只要 0.0011 秒——**约 90 倍差距**。

这正是 PR #2 复核发现 #2「性能基线偶发失败」的**真实根因**。

## 三、PR #2 已经做了什么（边界说明）

**已做**（PR #2 范围内，属「让测量可信」）：

- `tests/perf/conftest.py` —— 把 `HOME` / `USERPROFILE` 指向临时目录，
  性能基线不再依赖运行者的机器历史；
- `tests/unit/test_perf_isolation_guard.py` —— 把这个前提钉成机器可检的守护
  （含「污染态 vs 隔离态」约 90 倍的对照断言）；
- `.github/workflows/test.yml` —— 把 `tests/perf/` 纳入 PR 门禁。

**未做**（本工单范围）：全局文件本身的无上限增长与死条目回收。
**没有**改 `ai_collab/state_manager.py` 的写入逻辑——那是**产品行为变更**，
需要单独选型（见第四节），不能在复核 PR 的顺手修改里夹带。

## 四、待定设计问题（动手前先答）

1. **回收策略**：按 LRU？按 mtime？按「路径已不存在则删」？还是显式 TTL？
2. **回收时机**：写入时顺手回收？后台定期？读取时惰性回收？
3. **上限兜底**：条目数上限 / 文件体积上限，超限后怎么办（拒绝写 / 淘汰最旧）？
4. **兼容性**：全局文件还有别的读取方吗？删条目会不会丢掉用户可见的状态？
   （`.` 与 `ai-collab-system` 这类真实工作区**绝不能被误删**。）
5. **并发**：`_file_lock` 已存在，但「读—改—写」跨进程并发是否安全？
   回收逻辑引入后会不会放大竞态？
6. **与 VSCode 扩展侧的共享语义**是否冲突——全局文件是否承担跨窗口/跨项目共享职责？

## 五、验收标准

- [x] 给出回收策略的**选型理由**（为什么选 A 不选 B、备选方案是什么），不只给实现
- [x] 补守护用例：连续写入 N 个**已消失**的临时 workspace 后，全局文件的条目数 /
      体积**不随之无上限增长**
- [x] 守护用例必须**反向可验证**（把回收逻辑改坏 → 用例变红）
- [x] 真实工作区条目**不被误删**（有专门用例钉住）
- [x] `tests/unit/test_state_manager.py`、`tests/unit/test_state_manager_extra.py`、
      `tests/unit/test_state_manager_v2_coverage.py`、`tests/perf/` 全部保持绿
- [x] 结果报告按 PROTOCOL §7.4 四段（执行命令 / 验证结果 / 测试结论 / 风险 / 回滚）
- [x] 收口时 `tasks update --status completed` 能通过门禁

> 交付结果见
> [`RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md`](../results/RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md)
> （第四节 6 个设计问题的逐条回答在「验证结果」小节里）。

## 六、验收命令

- `python3 -m pytest tests/unit/test_state_manager_global_sync.py -q`
- `python3 -m pytest tests/perf/ -q`
- `python3 -m pytest tests/ -q`
- `python3 -m ruff check .`
- `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 七、参考

- `ai_collab/state_manager.py:145-149` —— 全局文件路径（`expanduser` 跟随 `HOME`）
- `ai_collab/state_manager.py:838-855` —— `_sync_to_global()`（读整份 / 改一条 / 写回整份）
- `tests/perf/conftest.py` —— PR #2 加的隔离装置
- `tests/unit/test_perf_isolation_guard.py` —— PR #2 加的隔离守护 + 90 倍对照
- `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md` —— 复核发现 #2
  （复核方把根因归为「阈值抖动」，实测证伪：真实根因是全局状态文件的无上限增长）
