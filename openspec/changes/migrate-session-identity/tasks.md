# Implementation Tasks

> 勾选必须附实测证据（命令 + 关键输出），集中列在文末 E1–E7。

## Phase 0 · 立项

- [x] 0.1 从最新 `origin/main` 开独立 worktree 与分支，主工作区在途改动零影响
- [x] 0.2 产出 `proposal.md` / `specs/task-contract/spec.md` / `tasks.md`
- [x] 0.3 `openspec validate migrate-session-identity --strict` 零错误

## Phase 1 · 身份模块

- [x] 1.1 `ai_collab/identity.py`：`session_id` / `model_id` 规范化与格式校验
- [x] 1.2 `resolve_identity(task)`：三态判定 declared / legacy / missing + 原因
- [x] 1.3 `derive_assignee_from_session()`：按会话注册表反查路由键（反查不到返回空）

## Phase 2 · 契约层

- [x] 2.1 契约加入 `session_id` / `model_id`，时间切点 `IDENTITY_REQUIRED_SINCE`
- [x] 2.2 切点后缺失判不合法；切点前判定 legacy 并计数，不判错、不编造
- [x] 2.3 格式非法与缺失分别报错
- [x] 2.4 `validate-contract` 输出新增 `legacy_identity` 计数

## Phase 3 · CLI

- [x] 3.1 `tasks register/update` 支持 `--session-id` / `--model-id`
- [x] 3.2 只给身份时按注册表反查路由键；反查不到拒绝创建
- [x] 3.3 `tasks migrate-identity`：默认只读审计，三类计数；`--apply` 只写注册表事实

## Phase 4 · 规则文本（须与代码同 commit）

- [x] 4.1 `PROTOCOL §7.3` 改为 session_id + model_id，assignee_provider 降级为过渡路由键
- [x] 4.2 `PROTOCOL` 新增 §7.5「身份与路由分离」
- [x] 4.3 `PROTOCOL §12` 把 `SUPPORTED_ASSIGNEES` 明确为过渡兼容白名单并写出淘汰条件
- [x] 4.4 `AI-COLLABORATION-STANDARDS §2.1` 加入身份字段检查项

## Phase 5 · 测试与门禁

- [x] 5.1 新增用例：新工单缺失身份 → 不合法；历史缺失 → legacy 计数；格式非法 → 区分原因；
      反查成功 / 反查失败；审计只读不写；`--apply` 不编造
- [x] 5.2 全套 pytest 与干净基线两侧同环境对照，FAILED 集合一致
- [x] 5.3 `ruff format --check .` / `ruff check .`
- [x] 5.4 `openspec validate migrate-session-identity --strict`

## Phase 6 · 收口

- [x] 6.1 结果报告四段 + 状态行 + 6 条 `acceptance_commands` 原样出现
- [x] 6.2 ACK 由 CLI 生成、任务状态经 CLI 变更
- [x] 6.3 提交带 pathspec；开 PR；登记合入提交；归档

## 明确不在本 change 范围

- **运行时路由迁移**：ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康仍按 `assignee` 过滤。
  淘汰条件写进 `PROTOCOL §12`，作为后续 change 的入口判据。
- 给历史工单编造 `session_id`（26 个工单文件中多数会话已消失，无事实可依）
- `provider_registry` 配置结构改造
- `2X` 激活词体系与 `quickfix/no-ticket` 轻量通道

## 偏离与理由

**1. `migrate_task_contracts` 保持不填身份（未按"顺手补齐"实现）**

实施到 Phase 5 时 `migrate_task_contracts` 一度被改成顺带补 `session_id` / `model_id`，
导致 6 条既有用例变红。复核后判定这是**设计错误而非测试过时**：

- `migrate_task_contracts` 的职责是「补齐缺失的**契约字段**」（`change_id` / `reviewer` 等），
  这些字段的值可以从工单自身已有信息推导；
- 身份字段**不可推导**——历史会话已经结束，注册表里没有记录，任何填充都是编造；
- 两者正交。让迁移函数顺手造身份，正是 `proposal.md` 里点名拒绝的「把没做的补齐」。

因此回退迁移逻辑，改为给 **5 处测试夹具** 补 `session_id` / `model_id`。理由：这些用例测的是
「完整契约能通过校验」与性能基线，不是「缺身份时如何报错」——后者由
`tests/unit/test_session_identity.py` 专门覆盖。修夹具不降低任何被测行为的标准。

**2. `total=18` 与磁盘 26 个任务文件不一致（审计覆盖面已披露，未在本 change 修）**

`audit_task_identity` 读的是状态账本 `logs/collaboration_state.json` 的 `tasks` 字典（18 条），
而 `collaboration/tasks/TASK-*.md` 有 26 个文件。差 8 条，意味着**身份审计看不见那 8 个文件**。
这不是本 change 引入的缺陷（账本即事实源是既有设计），但它会让「`legacy=18`」被误读成
「全部任务都已计数」。已登记为 `known_gaps.json` N26，本 change 不扩大范围去修数据同步。

**3. `collaboration/monitoring/*_latest.md` 未纳入本次提交**

这两个文件被跟踪，但数据源是 gitignored 的本机 `logs/session_registry_state.json`。本 worktree
跑过一次 CLI 后它们就被改写成「单会话」视图（8 → 1）。提交会把 main 上的团队会话总览覆盖掉，
且 diff 形如正常刷新。已从 pathspec 排除并 `git checkout --` 还原，登记为 `known_gaps.json` N27。

**4. 干净基线检出上 `preflight` 仍会 FAIL**——缺的是本机活动，不是代码。见结果报告 §残留边界。

## 证据

### E1 · 身份模块冒烟（四态判定）

```
$ python3 - <<'PY'（resolve_identity 直接调用）
declared -> {'state': 'declared', ...}          # session+model 齐全且合法
legacy   -> {'state': 'legacy', ...}            # created_at < 2026-11-16 且未声明
missing  -> {'state': 'missing', ...}           # created_at >= 2026-11-16 且未声明
invalid  -> {'state': 'invalid', ...}           # session_id 含空格 / model_id 超长
```

### E2 · 新增用例

```
$ python3 -m pytest tests/unit/test_session_identity.py -q
34 passed, 2 warnings in 0.42s
```

覆盖：declared 通过 / 切点后缺失不合法 / 切点前 legacy 不判错且计数 / 格式非法与缺失区分 /
注册表反查成功 / 反查失败拒绝创建 / 审计只读不改文件 / `--apply` 只写注册表事实。

### E3 · 受影响夹具回归

```
$ python3 -m pytest tests/unit/test_state_manager.py -q
40 passed

$ python3 -m pytest tests/perf/test_performance_baseline.py tests/unit/test_perf_isolation_guard.py -q
10 passed
```

### E4 · 静态门禁

```
$ ruff format --check .
329 files already formatted

$ ruff check .
All checks passed!
```

（上一轮曾在 `_cli_main.py` 留下 `IDENTITY_REQUIRED_SINCE` / `resolve_identity` 两个未使用导入，
已删除；`ruff format` 另修正 1 处长行。）

### E5 · OpenSpec 严格校验

```
$ openspec validate migrate-session-identity --strict
Change 'migrate-session-identity' is valid
```

### E6 · 全套回归对照（两侧同环境，`PYTHONPATH=/tmp/noshim:$PYTHONPATH` 遮蔽沙箱 mkdir shim）

基线 = `git archive 768b7f2` 展开后 `git init` 的干净快照；工作树 = 本分支。

```
基线:   50 failed, 3084 passed, 8 skipped, 3 warnings in 42.89s
工作树: 50 failed, 3118 passed, 8 skipped, 3 warnings in 43.42s
净增通过 = 3118 - 3084 = 34（= 新增用例数）

$ grep '^FAILED ' run-baseline.txt | sort > fail-base.txt
$ grep '^FAILED ' run-worktree.txt | sort > fail-work.txt
$ diff fail-base.txt fail-work.txt
（无输出）
$ cmp -s fail-base.txt fail-work.txt && echo "byte-identical"
byte-identical
```

50 条既有失败全部集中在 `test_consensus_engine*` / `test_soul_injection*` /
`test_ai_integration_mock_flags`，均为依赖外部 LLM 服务的环境型失败，与本 change 无关
（分布：provider_client 13、real_adapter 12、consensus_engine 10、concurrency 5、
soul_injection_engine 4、consensus_engine_extra 3、mock_flags 3）。

### E7 · 真实账本上的只读审计（含「不写入」证明）

```
$ shasum -a 256 <main>/logs/collaboration_state.json
62d92b3408f39d92b97170edf87440098086ba90925583583e8e78a009f1b5d4

$ python3 -m ai_collab.cli -w <main> tasks migrate-identity
身份迁移审计: scope=all apply=False cutoff=2026-11-16 total=18 declared=0 partial=0
              legacy=18 missing=0 invalid=0
  路由键可补全项: 0（注册表未提供可反查的会话）
  只读审计，未写入任何文件（加 --apply 才写，且只写注册表事实）
  提示: legacy 是历史欠账，本命令不为其编造身份值

$ shasum -a 256 <main>/logs/collaboration_state.json   # 复算
62d92b3408f39d92b97170edf87440098086ba90925583583e8e78a009f1b5d4
```

哈希前后一致 → 「审计默认只读」不是注释里的承诺，是实测。同时该轮结束后主工作区
`git status --porcelain | wc -l` 仍为 `153`，在途改动零触碰。
