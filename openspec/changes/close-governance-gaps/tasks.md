# Implementation Tasks

> 勾选均附实测证据（命令 + 关键输出），集中列在文末 E1–E6。

## Phase 0 · 立项

- [x] 0.1 从最新 `origin/main` 开独立 worktree 与分支，确认主工作区在途改动零影响（E1）
- [x] 0.2 产出 `proposal.md` / `specs/governance-coverage/spec.md` / `tasks.md`（E1）
- [x] 0.3 `openspec validate close-governance-gaps --strict` 零错误（E1）

## Phase 1 · 缺口 A：必读清单从裸自证改为可核验声明

- [x] 1.1 `governance.ack_required_reads()`：计算 `sha256` + 字节数写入会话文件（E2）
- [x] 1.2 `governance.verify_required_reads()`：重算比对，返回
      `declared / verified / stale / missing / legacy`（E2）
- [x] 1.3 `preflight` 必读项改为消费 1.2，过期与缺失均不通过并点名（E2）
- [x] 1.4 `sessions ack-reads` CLI：唯一写入入口，必读文件缺失时拒绝生成（E2）
- [x] 1.5 测试：一致通过 / 改文件后 stale / 旧格式不合法 / 文件缺失 / 无主体拒绝（E3）

## Phase 2 · 缺口 B：会话级配置覆盖层

- [x] 2.1 `.vscode/ai-collab.local.json` 字段级覆盖合并（E4）
- [x] 2.2 `guard_input_report()` 读合并结果，并逐字段标注来源（E4）
- [x] 2.3 `.gitignore` 新增覆盖层与会话文件（E4）
- [x] 2.4 测试：全覆盖 / 部分覆盖 / 覆盖层不得改写受跟踪文件（E3）

## Phase 3 · 缺口 C：开发日志可入库

- [x] 3.1 `logs/` → `logs/*` + `!logs/claude-code/` + `!logs/claude-code/**`（E5）
- [x] 3.2 `git check-ignore -v` 逐条验证正反两侧（E5）
- [x] 3.3 回归用例：临时仓库复制本仓 `.gitignore`，实际 `git add` 成功 / 失败各一侧（E3）

## Phase 4 · 装备本仓并首次让 preflight 全绿

- [x] 4.1 生成 `.vscode/ai-collab.local.json`（真实分支 / 基线 / 监视路径）（E6）
- [x] 4.2 `sessions ack-reads` 生成本会话声明（E6）
- [x] 4.3 `governance preflight` 五项全 PASS，`exit=0`（E6）
- [x] 4.4 受跟踪 `.vscode/ai-collab.json` 零改动，两个会话文件不进待提交变更（E6）

## Phase 5 · 回归与收口

- [x] 5.1 全套 pytest 两侧同环境对照，FAILED 集合 IDENTICAL（E6）
- [x] 5.2 `ruff format --check .` / `ruff check .`（E6）
- [x] 5.3 `openspec validate close-governance-gaps --strict`（E1）
- [x] 5.4 结果报告四段 + 状态行 + 6 条 `acceptance_commands` 原样出现（E6）
- [x] 5.5 ACK 由 CLI 生成、任务状态经 CLI 变更（E6）
- [x] 5.6 提交带 pathspec、开 PR、登记合入提交、归档（E6）

## 明确不在本 change 范围

- 规则文本修改（`PROTOCOL` / `AI-COLLABORATION-STANDARDS`）
- 会话注册表与 `assignee_provider → session_id + model_id` 语义迁移
- 11 月已合并 PR 的追溯登记
- `logs/` 下其他子目录（`workspace_forensics` / `handoff` / 状态文件）的入库策略

## 偏离与理由

- **既有断言 `guard_input_report(ws) == {"complete": True, "missing": []}` 改为关键结论断言**。
  理由：本 change 给报告增加 `sources` / `values` 两个可观测字段，整字典相等会把「新增字段」
  误判成回归。改的是断言粒度，不是放宽判定。
- **A6 用例的会话文件改为经 `ack_required_reads()` 生成**。理由：新语义下旧格式（只有路径名）
  按不合法处理，测试必须跟随规格；反向由 `test_legacy_session_format_is_rejected` 守住。

---

## 实测证据

**E1 · 立项与规格校验**
```
$ openspec validate close-governance-gaps --strict
Change 'close-governance-gaps' is valid
```

**E2 · 可核验必读声明**
```
$ python3 -m ai_collab.cli sessions ack-reads --session-id sess-close-gov-gaps-20261116
必读清单声明已写入:
  file: .ai_collab_session.json
  declared: 4  verified: 4
  verify: PASS  已声明 4 条，核验通过 4/4
```
改过必读文件后：
```
verify_required_reads() → ok=False, stale=['collaboration/PROTOCOL.md']
detail: 已声明 4 条，核验通过 3/4；内容已变更（需重读）: ['collaboration/PROTOCOL.md']
```
旧格式声明：
```
verify_required_reads() → ok=False, legacy=True
detail: 声明缺少哈希字段（旧格式），请经 sessions ack-reads 重新生成
```

**E3 · 新增用例**
```
$ python3 -m pytest tests/unit/test_governance_gaps.py -q
15 passed
$ python3 -m pytest tests/unit/test_governance_ledger.py -q
42 passed
```

**E4 · 覆盖层**
```
$ python3 -m ai_collab.cli governance preflight
[PASS] 门禁输入完整性: 三个输入齐全（expectedBranch←.vscode/ai-collab.local.json,
        baselineCommit←.vscode/ai-collab.local.json, watchPaths←.vscode/ai-collab.local.json）
$ git status --porcelain .vscode/          → 0 行（受跟踪配置零改动）
$ git check-ignore -v .vscode/ai-collab.local.json
.gitignore:30:.vscode/ai-collab.local.json	.vscode/ai-collab.local.json
```

**E5 · 忽略规则正反两侧**
```
logs/claude-code/2026-11/day.md            NOT ignored
logs/collaboration_state.json              IGNORED  <- .gitignore:45:logs/*
logs/governance_coverage_observe.jsonl     IGNORED  <- .gitignore:45:logs/*
logs/workspace_forensics/r.json            IGNORED  <- .gitignore:45:logs/*
```
并且实测可入库（临时仓库 + 本仓 `.gitignore`）：`git add logs/claude-code/2026-11/day.md`
进索引成功，`git add logs/collaboration_state.json` 失败。

**E6 · 开工检查五项全绿 + 回归对照**
```
$ python3 -m ai_collab.cli governance preflight
[PASS] 必读清单声明: 已声明 4 条，核验通过 4/4
[PASS] 状态机时效: 2026-11-16T04:55:44.106028
[PASS] 门禁输入完整性: 三个输入齐全（...）
[PASS] HEAD 治理登记: 边界后合并提交 1 个，未登记 0 个
[PASS] 显式 ACK 证据: 1 条
preflight: PASS   (exit=0)

baseline(/tmp/gov-gaps-baseline, origin/main 64b56ac 快照 + git init): 50 failed, 3069 passed, 8 skipped
current (/tmp/wt-gov-gaps):                                          50 failed, 3084 passed, 8 skipped
comm -13 / comm -23 → 均为空；cmp → IDENTICAL；净增 15 = 新增用例数

$ ruff format --check .  → 327 files already formatted
$ ruff check .           → All checks passed!
```
