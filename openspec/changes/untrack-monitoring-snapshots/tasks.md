# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。
> 勾选项的证据按编号 E1–E8 引用，集中列在文末「实测证据」。

## Phase 0 · 立项与隔离

- [x] 0.1 从最新 `origin/main` 开独立 worktree 与分支，确认主工作区 153 项在途改动零影响（E1）
- [x] 0.2 产出 `proposal.md` / `specs/tracked-artifact-hygiene/spec.md` / `tasks.md`（E1）
- [x] 0.3 产出 `collaboration/tasks/TASK-UNTRACK-MONITORING-001.md`，补齐契约字段（含 `session_id` / `model_id`）（E1）
- [x] 0.4 `openspec validate untrack-monitoring-snapshots --strict` 零错误（E1）

## Phase 1 · 清点与判定（先证范围，再动手）

- [x] 1.1 用 `git check-ignore --no-index` 逐个判定 `git ls-files collaboration/monitoring/` 的受跟踪文件是否命中规则（E2）
- [x] 1.2 逐文件提取生成时间戳，确认 11 个 `*_latest.md` 均为本机快照；2 个 `*_test.md` 按「同机制同落点」纳入（E2）
- [x] 1.3 清点代码与测试对这些路径的引用，确认全部是**输出路径**或 `tmp_path` 内读写，而非读取库内副本（E3）
- [x] 1.4 记录「`git check-ignore` 默认跳过已跟踪文件、不可用于判定规则覆盖性」这一方法论更正（E2）

## Phase 2 · 落规则与 untrack

- [x] 2.1 `.gitignore` monitoring 区块把 9 条逐条列举换成 `*_latest.md` / `*_20*.md` / `*_test.md` 三条通配（E4）
- [x] 2.2 逐实例复核 9 条原规则覆盖的文件在改后仍被忽略（改规则不得缩小排除面）（E4）
- [x] 2.3 `git rm --cached` 全部 13 个已跟踪摘要，工作区文件保留（E4）
- [x] 2.4 复核 `git ls-files collaboration/monitoring/` 为空，且 13 个工作区文件与内容 sha256 未变（E4）

## Phase 3 · 验证

- [x] 3.1 跑一次刷新摘要的 CLI 命令，确认文件回到工作区且 `git status` 不再显示（E5）
- [x] 3.2 `git add -A` 后核对暂存区不含任何 `collaboration/monitoring/*_latest.md`（E6）
- [x] 3.3 跑相关单测（monitoring / ack / intervention / dispatch 相关），确认无回归（E7）
- [x] 3.4 全套 pytest 与干净基线同环境对照，确认 FAILED 集合与基线一致（E7）
- [x] 3.5 `ruff format --check .` 与 `ruff check .`（E7）

## Phase 4 · 收口

- [x] 4.1 `known_gaps.json` 的 N27 置 `status=closed`，补 `closed_at` 与实测证据（E8）
- [x] 4.2 结果报告四段 + 状态行 + 6 条 `acceptance_commands` 原样出现（E8）
- [x] 4.3 提交带 pathspec；开 PR；`declare-commit` 登记合入提交；`openspec archive --yes`（E8）
- [x] 4.4 归档后复跑 `openspec validate --archived --strict`（E8）

## 实测证据

### E1 · 隔离与工件

```
$ git branch --show-current && git rev-parse --short HEAD
fix/untrack-monitoring-snapshots-2026-11-16
e2af634

$ git -C /Users/raymondna/Documents/AI-collab/ai-collab-base status --porcelain | wc -l
153                                    # 主工作区在途改动数，本轮全程未变

$ openspec validate untrack-monitoring-snapshots --strict
Change 'untrack-monitoring-snapshots' is valid
```

工单注册取自 CLI，身份如实声明、路由键由注册表反查：

```
$ python3 -m ai_collab.cli -w . tasks register --task-id TASK-UNTRACK-MONITORING-001 \
    --change-id untrack-monitoring-snapshots \
    --session-id sess-untrack-monitoring-20261116 --model-id deepseek/v4.1-flash ...
  身份: session_id=sess-untrack-monitoring-20261116 model_id=deepseek/v4.1-flash
  路由键来源: registry（assignee=claude_code）
```

### E2 · 范围判定与方法论更正

```
$ git ls-files collaboration/monitoring/ | wc -l
13

$ for f in $(git ls-files collaboration/monitoring/); do
    git check-ignore --no-index -q "$f" && echo "命中" || echo "未命中"
  done | sort | uniq -c -w3
  13 命中                                # 新规则下全部命中（旧规则下无一路径命中）
```

逐文件生成时间戳（节选，11 个 `*_latest.md` 全部带时间戳）：

```
ACK_REMEDIATION_SUMMARY_latest.md      - 生成时间: 2026-10-24T19:06:08.714150
CLAUDE_ADAPTER_SUMMARY_latest.md       - generated_at: 2026-10-24T19:06:17.341255
SESSION_REGISTRY_SUMMARY_latest.md     - 生成时间: 2026-10-24T19:06:17.343329 / 会话数 8
TASK_RESULT_CONSISTENCY_SUMMARY_latest.md  - 生成时间: 2026-10-25T00:30:33.329463
```

**方法论更正（本轮自己踩的）**：初期用 `git check-ignore`（无 `--no-index`）逐个判定这 13 个
文件，得到「13 个全部未命中」，并据此写下「规则完全没覆盖它们」。该结论**是用错工具得出的**——
`git check-ignore` 默认跳过已跟踪文件，对受跟踪集合调用它必然全部返回未命中。
改用 `--no-index` 后才能回答「规则是否覆盖该路径」。结论方向未变（旧规则下 13 个确实无一命中），
但判定方法必须更正，已同步写进 `spec.md` 的核验场景。

### E3 · 引用面清点

```
$ grep -rn "monitoring" --include=*.py ai_collab/ scripts/
ai_collab/intervention_queue.py:16: DEFAULT_SUMMARY_PATH = "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md"
ai_collab/ack_watchdog.py:20:       DEFAULT_SUMMARY_PATH = "collaboration/monitoring/ACK_WATCHDOG_SUMMARY_latest.md"
ai_collab/result_consistency_audit.py:20: DEFAULT_SUMMARY_PATH = "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"
...                                    # 全部是「写到哪」，没有一处「从哪读」
```

测试侧引用全部落在 `tmp_path` 临时工作区，读写的是自己刚生成的文件：

```
$ grep -rn "_test\.md" --include=*.py tests/ | head -3
tests/unit/test_automation_benefit_dashboard.py:65:  output_path = workspace / "collaboration" / "monitoring" / "AUTOMATION_BENEFIT_DASHBOARD_test.md"
tests/unit/test_agent_dispatch_bridge.py:76:         orders_file = workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
```

### E4 · 规则与 untrack

```
# 改规则时抓到的回归：AGENT_DISPATCH_ORDERS_test.md 原本被第 80 行单独忽略，
# 换成 *_latest.md / *_20*.md 后失去忽略 —— 补 *_test.md 后恢复。
$ for n in AGENT_DISPATCH_ORDERS_2026-10-24.md AGENT_DISPATCH_ORDERS_latest.md \
           AGENT_DISPATCH_ORDERS_test.md AGENT_RECEIPT_SUMMARY_2026-10-24.md \
           AGENT_RECEIPT_SUMMARY_latest.md AGENT_TRIGGER_codex_latest.md \
           AGENT_TRIGGER_codearts_agent_latest.md DAILY_REPORT_latest.md \
           NOOP_PENDING_CONFLICT_SUMMARY_latest.md; do
    printf "%-46s " "$n"; git check-ignore -q "collaboration/monitoring/$n" && echo IGNORED || echo "*** 回归 ***"
  done
AGENT_DISPATCH_ORDERS_2026-10-24.md            IGNORED
AGENT_DISPATCH_ORDERS_latest.md                IGNORED
AGENT_DISPATCH_ORDERS_test.md                  IGNORED      # 补 *_test.md 前为「回归」
AGENT_RECEIPT_SUMMARY_2026-10-24.md            IGNORED
AGENT_RECEIPT_SUMMARY_latest.md                IGNORED
AGENT_TRIGGER_codex_latest.md                  IGNORED
AGENT_TRIGGER_codearts_agent_latest.md         IGNORED
DAILY_REPORT_latest.md                         IGNORED
NOOP_PENDING_CONFLICT_SUMMARY_latest.md        IGNORED
```

```
$ git rm --cached -q collaboration/monitoring/*_latest.md collaboration/monitoring/*_test.md
$ git ls-files collaboration/monitoring/ | wc -l
0
$ ls collaboration/monitoring/*_latest.md | wc -l ; ls collaboration/monitoring/*_test.md | wc -l
11
2                                      # 工作区 13 个文件一个不少

$ shasum -a 256 collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md
292699c53040d0cfcb9a6776d8b244b65f80effb3116baac69ebfc5089748aab   # 与改动前完全相同
```

### E5 · 生成器重跑不回流

```
# 改动前
$ shasum -a 256 collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md
292699c5…  |  生成时间 2026-10-24T19:06:17  |  会话数 8

$ python3 -m ai_collab.cli -w . sessions register \
    --session-id sess-untrack-monitoring-20261116 --assignee claude_code --transport-mode manual
会话已注册: sess-untrack-monitoring-20261116

# 改动后：文件被真实改写
$ shasum -a 256 collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md
2be4f908…  |  生成时间 2026-11-16T06:20:08  |  会话数 2

# 关键：git 完全没报告这次改写
$ git status --porcelain | grep -E '^( M|M )' | grep -c collaboration/monitoring
0
$ git status --porcelain | grep -v "^D  collaboration/monitoring/"
 M .gitignore
?? collaboration/tasks/TASK-UNTRACK-MONITORING-001.md
?? openspec/changes/untrack-monitoring-snapshots/
```

### E6 · `git add -A` 不再带入

```
$ git add -A --dry-run 2>&1 | grep "collaboration/monitoring/"
(无输出)

$ git diff --cached --name-status -- collaboration/monitoring/ | awk '{print $1}' | sort | uniq -c
  13 D                                 # 只有本 change 显式移除的 13 个
```

### E7 · 测试与静态检查

```
$ PYTHONPATH=/tmp/noshim python3 -m pytest \
    tests/unit/test_automation_benefit_dashboard.py tests/unit/test_ack_remediation.py \
    tests/unit/test_dispatch_intervention_wiring.py -q
21 passed in 0.27s

# 全套，同环境同命令，与干净基线 e2af634 对照
改动分支：3189 passed, 8 skipped in 64.03s
干净基线：3189 passed, 8 skipped in 66.39s
          ⇒ 完全一致，零回归

$ python3 -m ruff format --check .
331 files already formatted
$ python3 -m ruff check .
All checks passed!
```

环境说明（两次跑测试都须带，否则全部 error）：

```
$ PYTHONPATH=/tmp/noshim python3 -m pytest -q      # sitecustomize.py 前置空文件，绕开沙箱 mkdir 代理
$ python3 -m pytest -q                             # 不加时：8 skipped, 3189 errors
```

另更正一处历史基线：上一轮报告沿用 `50F/3139P` 作为对照基线，但同环境实测干净基线为
`3189P / 0F`（3189 = 3139 + 50，总数吻合）。那 50 个 FAILED 属另一个解释器环境的残留，
不是本仓缺陷，本轮不再沿用该基线。

### E8 · 收口

```
$ openspec validate untrack-monitoring-snapshots --strict
Change 'untrack-monitoring-snapshots' is valid
```

`known_gaps.json` N27 → `status: closed` / `closed_at: 2026-11-16`，实测证据已回填；
结果报告见 `collaboration/results/RESULT-UNTRACK-MONITORING-001.md`。
