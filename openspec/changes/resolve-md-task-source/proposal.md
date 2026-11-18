# Change Proposal: Resolve md Task Source

## Why

`known_gaps.json` **N26**（P2 / open）记录了「身份审计只读账本（18 条），磁盘另有 8 个任务文件未被计入」。
两天后复核发现这个描述**已经过时**，真实情况有三层：

**层 1 · 账本不是仓库事实，是每个工作树各一份的本机状态。**
`logs/` 被 gitignore。实测同一分支下：

```
主工作区   logs/collaboration_state.json  34,644 B  tasks 18 条  sha256 62d92b34…
wt-g11     logs/collaboration_state.json   3,301 B  tasks  2 条  sha256 0472a163…
全新 clone 账本为空                                  tasks  0 条
磁盘                        collaboration/tasks/TASK-*.md  27 个，始终不变
```

三个账本与磁盘工单的**交集都是 0**。「差 8 条」只在那台主工作区成立；换台机器差值是 27 或 2。
因此「把 8 个文件补录进账本」不是仓库层面的解——补完只对那一台机器生效。

**层 2 · 即使把 md 全登记进账本，身份字段也会在最后一米丢掉。**
`scripts/verify_task_file_contracts.py` 扫 md、解析 frontmatter、调 `register_task(...)` /
`update_task_contract(...)`，但**两处调用都没传 `session_id` / `model_id`**。
而这两个函数**都支持这两个参数，内部也真的会写进账本**（`state_manager.py:1083-1084`、
`:1427-1428`；写入在 `:1139-1140`、`:1496-1503`）。
不修这个，把 27 个 md 全补进账本，身份审计照样报 `legacy=27`——「补完还是漏」会让人
误判迁移没跑完而反复返工，正是 N26 影响面第 ② 条。

**层 3 · 双输入源不是没人知道，但身份这一维没人管。**
`verify_task_file_contracts.py` 的 docstring 第一段就写着「`tasks validate-contract` 读的是
运行时状态库，**不读** `collaboration/tasks/*.md`」。它给的解法是临时登记再校验，
且刻意不写全局状态文件；但它不检查身份。于是身份只在账本侧被查，md 侧的校验器完全没覆盖。

用户 2026-11-18 裁定选 **A：md 是事实源**。

## What Changes

- 新增 `ai_collab/task_md_sync.py`：把 `collaboration/tasks/TASK-*.md` 的 frontmatter
  **同步进当前工作树账本**。只写 md 里**已声明**的字段；md 没写身份的就留空，
  由 `resolve_identity()` 按切点判 `legacy`。**不推导、不补全、不编造**。
- `scripts/verify_task_file_contracts.py` 的两处登记调用补传 `session_id` / `model_id`；
  `parse_frontmatter` 改为复用新模块，消除重复实现。
- CLI 新增 `tasks sync-from-md`：显式同步入口，输出同步条数与跳过条数；支持 `--dry-run`。
- `audit_task_identity()` 返回结果追加 `input_source`：写明账本条数、最近一次 md 同步的
  时间与条数，让 `legacy=18` 不再读起来像全量。
- `tasks migrate-identity` 打印该来源说明；不存在的同步记录显示「未同步过 md」，不静默。
- `PROTOCOL` 写清标准流程：`tasks sync-from-md` → `tasks migrate-identity`。
- `known_gaps.json` N26 → closed，补本轮实测证据。

## 明确不在本 change 范围

- **不改 `audit_task_identity` 的只读语义**：它仍然只读账本，不自动触发同步。
  同步是独立、显式、可审计的一步。理由：让只读审计偷偷写盘，会让「审计过了」的含义
  不可预期——和 G11 不读并发门禁降级开关是同一条原则。
- **不把历史 26/27 个 md 的缺失身份补齐**：历史会话已结束，注册表无事实可依，任何填充都是编造。
  同步后它们应判 `legacy`，这是正确结果，不是待修项。
- **不改账本的存储位置或共享方式**：账本仍 per-worktree、仍 gitignored。
  A 方案的一致性来自「审计前显式同步」，不是把账本变成共享文件。
- **不回写 md**：同步方向单向（md → 账本）。账本里后来补的路由键不写回 md。
- **不接 preflight**：同步是有副作用的操作，不能塞进开工检查。是否强制由 PROTOCOL 纪律承担。
- **N25**：需用户解冻，独立处理。

## 验收标准（可机器判定）

1. 在**全新 clone**（账本为空）上：跑 `tasks sync-from-md` 后账本条数 == 磁盘 md 条数。
2. 同步后 `tasks migrate-identity` 的 `total` == 磁盘 md 条数；有身份的 md 判 `declared`，
   无身份的历史 md 判 `legacy`；`missing` / `invalid` 均为 0（不得凭空制造错误）。
3. **不编造**：对一份故意只写 `session_id` 不写 `model_id` 的 md，同步后该条判 `partial`，
   账本里 `model_id` 必须为空字符串。
4. **幂等**：连续同步两次，账本中 `tasks` 内容的 sha256 不变，条数不变；
   允许元数据 `md_sync.synced_at` 刷新——它是「最近一次同步」的审计信息，
   为追求整个文件字节不变而丢掉时间戳是错误取舍。
5. **不回写 md**：同步前后所有 md 文件 sha256 不变。
6. `audit_task_identity` 的 `input_source` 在无同步记录时明确写「未同步过 md」，不静默。
7. 全套 pytest 与干净基线同环境对照，结果一致。
