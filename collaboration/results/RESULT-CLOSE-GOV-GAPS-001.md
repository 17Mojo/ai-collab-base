# RESULT — TASK-CLOSE-GOV-GAPS-001 · 收口治理门禁剩余三处缺口

- **状态**: completed
- 日期：2026-11-16 · change_id：`close-governance-gaps`
- 执行者：`claude_code`（AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/tmp/wt-gov-gaps`（分支 `feat/close-governance-gaps-2026-11-16`，基线 `origin/main @ 64b56ac`）
- 范围：上一轮 `restore-governance-enforcement` 结果报告诚实登记的三处缺口

> **口径声明**：三条缺口都按「正反两侧都要有机器用例」验收——不只证明装上能动，
> 还要证明**改了就该红**（必读文档变更 → stale；旧格式声明 → 不合法；覆盖层 → 不改受跟踪文件）。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate close-governance-gaps --strict
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli governance preflight
python3 -m pytest tests/unit/test_governance_gaps.py -q
python3 -m ruff format --check .
python3 -m ruff check .
```

同一工作区内的附加命令：

```
python3 -m ai_collab.cli sessions ack-reads --session-id sess-close-gov-gaps-20261116 --assignee claude_code
git check-ignore -q <path>                       # 逐条验证忽略规则正反两侧
PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider   # 当前侧
cd /tmp/gov-gaps-baseline && PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider
comm -13 base_failed cur_failed && comm -23 base_failed cur_failed && cmp base_failed cur_failed
python3 -m ai_collab.cli tasks register|update ... ; python3 -m ai_collab.cli ack ...
```

## 验证结果

### 1. 缺口 A · 必读清单从裸自证改为可核验声明

声明写入（唯一入口）：

```
$ python3 -m ai_collab.cli sessions ack-reads --session-id sess-close-gov-gaps-20261116
必读清单声明已写入:
  file: .ai_collab_session.json
  session_id: sess-close-gov-gaps-20261116
  acknowledged_at: 2026-11-16T04:53:41.660337
  declared: 4  verified: 4
  verify: PASS  已声明 4 条，核验通过 4/4
```

反向证明「改了就该红」（同一条用例族，15 条新用例全过）：

| 用例 | 断言 |
| --- | --- |
| `test_modified_required_read_becomes_stale` | 声明后改 `PROTOCOL.md` → `ok=False`、`stale=[PROTOCOL.md]`、detail 点名该文件 |
| `test_legacy_session_format_is_rejected` | 只有路径名的旧格式 → `legacy=True`、`ok=False`、提示经 `sessions ack-reads` 重新生成 |
| `test_missing_required_read_fails` | 声明后删文件 → `ok=False`、进入 `missing` |
| `test_ack_refuses_when_required_read_absent` | 必读文件缺失时**拒绝**生成声明（`GovernanceError`），不写半份声明 |
| `test_cli_ack_reads_requires_session_id` | 缺 `--session-id` → `exit=1`，不允许无主体声明 |

### 2. 缺口 B · 会话级配置覆盖层

```
$ python3 -m ai_collab.cli governance preflight
[PASS] 门禁输入完整性: 三个输入齐全（expectedBranch←.vscode/ai-collab.local.json,
        baselineCommit←.vscode/ai-collab.local.json, watchPaths←.vscode/ai-collab.local.json）
```

- 覆盖层文件被忽略：`git check-ignore -v .vscode/ai-collab.local.json` → `.gitignore:30`
- 受跟踪配置零改动：`git status --porcelain .vscode/` 输出 0 行
- 部分覆盖场景（`test_partial_overlay_reports_sources`）：三项输入按「覆盖层优先、受跟踪兜底」
  合并，且 `sources` 逐字段标出来源；`test_overlay_cannot_hide_tracked_values` 断言覆盖层
  只影响同名字段，不会连带清空受跟踪配置里的其他字段
- `test_local_overlay_overrides_tracked_config` 额外断言覆盖层**不改写**受跟踪文件内容

### 3. 缺口 C · 开发日志可入库

```
$ git check-ignore -q <path>
logs/claude-code/2026-11/day.md            NOT ignored
logs/collaboration_state.json              IGNORED  <- .gitignore:45:logs/*
logs/governance_coverage_observe.jsonl     IGNORED  <- .gitignore:45:logs/*
logs/workspace_forensics/r.json            IGNORED  <- .gitignore:45:logs/*
```

`test_dev_log_really_addable` 不只信 `check-ignore`：在一个临时 git 仓库里复制本仓
`.gitignore`，实际 `git add logs/claude-code/2026-11/day.md` 成功进索引，而
`git add logs/collaboration_state.json` 如预期失败。这是「能入库」的实证，不是规则字面推断。

### 4. 开工检查首次五项全绿

```
$ python3 -m ai_collab.cli governance preflight
[PASS] 必读清单声明: 已声明 4 条，核验通过 4/4
[PASS] 状态机时效: 2026-11-16T04:55:44.106028
[PASS] 门禁输入完整性: 三个输入齐全（...←.vscode/ai-collab.local.json）
[PASS] HEAD 治理登记: 边界后合并提交 1 个，未登记 0 个
[PASS] 显式 ACK 证据: 1 条
preflight: PASS
exit=0
```

上一轮这项在本仓是「三项 FAIL 且其中两项结构上不可能绿」。现在全绿，且绿色来自真实装备，
不是把检查项删掉。

### 5. 测试结论

全套回归仍用两侧同环境对照法（基线取 `origin/main @ 64b56ac` 快照，先 `git init` 成真实仓库）：

| 侧 | 结果 |
| --- | --- |
| 基线 | `50 failed, 3069 passed, 8 skipped` |
| 当前 | `50 failed, 3084 passed, 8 skipped` |
| 新增失败（`comm -13`） | 空 |
| 新增通过（`comm -23`） | 空 |
| `cmp` | **IDENTICAL** |

净增 15 = `tests/unit/test_governance_gaps.py` 的用例数。`tests/unit/test_governance_ledger.py`
保持 42 条全过（其中 2 条按新语义做了调整，见风险 3）。

`ruff format --check .` → `327 files already formatted`；`ruff check .` → `All checks passed!`。

## 风险

1. **必读声明是「读的那一刻」的快照，不是「读懂」的证明。**
   哈希能证明文件没被改过，不能证明读的人真的理解了。这条门禁把「裸自证」升级为
   「可核验的版本绑定」，但它仍只是合规链条的第一环，不能替代评审。
   若要进一步加强，需要把声明与具体工单/评审动作绑定（后续 change）。

2. **覆盖层是每台机器各自的，无法在 CI 里复现。**
   `ai-collab.local.json` 不进库是刻意的（否则会话基线会分发给所有人），代价是 CI 上
   `preflight` 的门禁输入完整性项仍需各自装备，或改用 CI 自己的基线。这不是漏洞，
   是把「会话本地状态」和「团队共享配置」分开后的必然结果。

3. **两条既有单测按新语义调整过，属于有意的行为变更。**
   - `test_guard_input_report_names_missing_inputs` 原来断言整字典相等，本 change 给
     `guard_input_report` 增加了 `sources` / `values` 两个可观测字段，故改为断言关键结论。
     整字典相等会把「新增可观测字段」误判成回归，这是脆弱断言，不是回归。
   - `test_acceptance_a6_preflight_passes_with_all_inputs` 原来手写旧格式会话文件，新语义下
     旧格式按不合法处理，故改为经 `ack_required_reads()` 生成。这是「测试跟随规格」，
     不是放宽门禁——同文件的 `test_legacy_session_format_is_rejected` 反过来守住旧格式必须红。

4. **`.gitignore` 改动会让开发日志开始出现在所有人的 `git status` 里。**
   这是修复目标而非副作用。但意味着其他会话若在 `logs/claude-code/` 下有临时草稿，
   合入后会突然显示为未跟踪文件。已确认其他 `logs/` 路径（状态机、观测、取证、handoff）
   的忽略状态未变。

5. **本 change 的合入同样是一个 merge commit，会被覆盖率门禁拦下，需先登记。**
   流程已在上一轮验证过：`merge → declare-commit → 提交登记表 → 复跑 → archive`。
   本 change 的生效边界仍是 `4d04acd`，因此只需登记这一次新的合并提交。

## 回滚

三条缺口彼此独立，可分别回退，互不牵连：

- **缺口 A**：删除 `.ai_collab_session.json` 并把 `preflight` 的必读项判回「路径名成员判定」。
  回退后该项会回到「结构上恒 FAIL」的状态，属于已知退化，不是新问题。
- **缺口 B**：删除 `.vscode/ai-collab.local.json`，`guard_input_report()` 恢复只读受跟踪配置。
  受跟踪配置全程零改动，所以回退不涉及任何已提交内容。
- **缺口 C**：把 `.gitignore` 的 `logs/*` + 两条取反改回 `logs/`。回退后开发日志重新不可入库，
  已入库的日志文件不受影响（仍在索引里）。
- **整体**：`git revert <本 change 的提交>`。新增测试文件、change 工件、结果报告均为新增文件；
  两条被调整的既有用例随 revert 一并恢复。
