# RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24

- **状态**: completed
- **任务**: TASK-P1-PR2-CODEARTS-REVIEW-001
- **change_id**: add-concurrent-workspace-guard
- **复核角色**: AGENT_TEST（CodeArts）
- **复核对象**: PR #2 `feat/codearts-collab-wiring` → `main`，复核时 HEAD = `ef34309`（PR 状态 OPEN / MERGEABLE，CI 全绿）
- **复核方式**: 独立实测（不采信 PR 描述自述数字），正向 + 反向验证
- **执行日期**: 2026-10-24

---

## 复核结论

**有条件通过**。

五块交付（① 并发守护 CLI 门禁 ② Phase 4 项目边界 ③ OpenSpec 落地 ④ CI 隔离修复
⑤ 记忆纠错）以及追加的 ⑥ 派单链新鲜度修复，**实现均成立**；四项破坏性实测
（R2.3 / R3.4 / R4.2 / R5.5.2）全部按预期暴露破坏并已还原，工作区无残留改动。
结论不给「通过」的唯一原因：**验收命令 3（全量测试）首次执行出现 1 条性能阈值失败**，
以及**两项守护断言不足 + 一处守护有效性在本机不可复现**（详见「发现的问题清单」）。
这些均不构成功能缺陷，不阻断合并；但需作者知悉并在下轮补齐。

判定依据：6 条验收命令中 5 条首跑通过，第 3 条首跑 rc=1（性能阈值边界抖动）、
重跑 rc=0（3014 passed / 6 skipped / 0 failed）。

---

## 执行命令

### 验收命令（6 条，逐条实跑）

1. `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py tests/unit/test_concurrent_guard_reuse.py tests/unit/test_project_boundary_guard.py tests/unit/test_consensus_engine_concurrency.py -q`
   → rc=0，`50 passed in 12.01s`
2. `python3 -m pytest tests/unit/test_ci_isolation_guard.py -q`
   → rc=0，`1 passed in 0.74s`
3. `python3 -m pytest tests/ -q`
   → 首跑 rc=1，`1 failed, 3013 passed, 6 skipped in 48.94s`（失败项见「验证结果 · 验收命令 3」）
   → 重跑 rc=0，`3014 passed, 6 skipped in 50.22s`
4. `python3 -m ruff check .`
   → rc=0，`All checks passed!`
5. `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`
   → rc=0，`契约校验结果: checked=13 skipped=0 invalid=0`；`终态结果一致性: audited=12 consistent=12 mismatch=0 unparseable=0 missing_result=0`
6. `python3 scripts/scan_secrets_pii.py --workspace .`
   → rc=0，`[OK] no secrets found`

### 复核过程用到的命令

```bash
python3 -m ai_collab.cli concurrent guard --help
python3 -m ai_collab.cli concurrent guard --workspace . --expected-branch feat/codearts-collab-wiring
python3 -m ai_collab.cli concurrent guard --workspace . --expected-branch nonexistent-branch
openspec validate add-concurrent-workspace-guard --strict
openspec status --change add-concurrent-workspace-guard
openspec update --force
sh scripts/verify_agent_config_sync.sh
python3 scripts/sync_agent_memory.py --check
python3 -m pytest tests/unit/test_dispatch_trigger_freshness.py tests/unit/test_agent_dispatch_bridge.py tests/unit/test_ack_watchdog.py -q
python3 -m ai_collab.cli run --include-pending
python3 -m ai_collab.cli sessions health
```

### 反向验证用到的命令（临时改动 → 实测 → 立刻还原）

```bash
# R2.3：把 report_file / history_file 写死本仓根
python3 -m pytest tests/unit/test_concurrent_guard_reuse.py -q
git checkout -- ai_collab/concurrent_guard.py && git status --short

# R4.2：移除 test_codearts_bridge_deliver.py 里的 resolve_credentials 打桩
python3 -m pytest tests/unit/test_ci_isolation_guard.py -q
git checkout -- tests/unit/test_codearts_bridge_deliver.py && git status --short

# R5.5.2：删除 scripts/agent_dispatch_bridge.py 的 "generated_at": report_timestamp,
python3 -m pytest tests/unit/test_dispatch_trigger_freshness.py tests/unit/test_agent_dispatch_bridge.py tests/unit/test_ack_watchdog.py -q
git checkout -- scripts/agent_dispatch_bridge.py && git status --short
```

---

## 验证结果

### 验收命令 3 的失败项定位（全量首跑）

- 失败用例：`tests/perf/test_performance_baseline.py::test_state_update_performance`
- 断言原文：`AssertionError: Single state update took 0.101s, threshold is 0.1s`（超出 0.001s / 1%）
- 单条重跑 3 次：全绿
- 全量重跑一次：rc=0，`3014 passed, 6 skipped`
- 归因：**性能阈值边界抖动**，非功能回归。旁证：PR 未改 `tests/perf/`；
  PR 对 `ai_collab/state_manager.py` 的改动是新增 `assignee_role` 字段 + 新增
  `update_task_contract()` 方法 + workspace 归一化，与单次状态更新的耗时无实质关联；
  PR 的 CI 门禁只跑 `tests/unit/`（`.github/workflows/test.yml:56`）与
  `tests/integration/`（`test.yml:76`），**不跑 `tests/perf/`**，因此该阈值在 PR 门禁里不可见。

### R1 复核①：并发守护实现与 CLI 门禁

- R1.1 通过。`concurrent guard --help` 真实存在（退出码 0）。真实调用两次：
  - 期望分支一致 → `allowed: True` / `risk_level: low` / 退出码 0；
  - 期望分支不一致 → `allowed: False` / `risk_level: high` /
    `violation: branch drift: expected=nonexistent-branch actual=feat/codearts-collab-wiring` /
    退出码 2。
  自洽性成立：`allowed is True` ⇔ `violations` 为空（两种情形都实测到）。
- R1.2 通过（**限定在并发守护改动范围内**）。实现只读 `.vscode/ai-collab.json`：
  `_cli_main.py::cmd_concurrent_guard` → `VSCodeIntegration.get_project_config()`
  → `ai_collab/integrations/vscode.py:90` 读 `<workspace>/.vscode/ai-collab.json`；
  `concurrentGuard` 段实测存在（enabled / expectedBranch / requireBaselineCommit /
  baselineCommit / watchPaths / sessionStartedAt / foreignChangeSeverity /
  aheadWarnThreshold / report / history）。
  `git show 4684652 --stat -- config/` 输出为空 —— 并发守护 commit 未碰 `config/`。
  **需要如实标注**：PR 全量范围内 `config/agent-orchestration.json` 确有 570 行改动、
  schema/template 各 4 行改动，来源是角色前缀命名空间收敛三个 commit
  （`229062d` / `e88e1c8` / `5b9160e`），与并发守护无关；工单 R1.2 的字面断言若按
  「整个 PR」解读则不成立，按「并发守护这块改动」解读则成立。
- R1.3 **有条件通过**：8 条 Requirement 全部有实现，7 条有守护用例；**2 个场景缺守护断言**
  （实现本身正确，见问题清单 #3、#4）。另有一处**有实现无需求**：`concurrentGuard.enabled=false`
  的降级语义（实现 + 用例都有，spec 未描述，见问题清单 #5）。
- R1.4 通过（1 处笔误、1 处文档不完整，见问题清单 #6、#7）。`PROTOCOL.md` 第十四章与实现一致：
  14.2/14.3/14.4 点名的三个检测函数签名与实现完全一致；
  14.5 分层表（drift/stale = git 真证 → 硬门禁可阻断；foreign = mtime 启发式 → 软警告不阻断）
  与 `_run_concurrent_guard_gate` 的分层实现一致（实测：foreign 只进 `warnings`，
  `allowed` 仍为 True）；
  14.6 评级表（high→False / medium→True / low→True）与 `assess_concurrent_risk` 一致。

### R2 复核②：Phase 4 项目边界用例

- R2.1 通过：`tests/unit/test_concurrent_guard_reuse.py` → `4 passed`。
- R2.2 **独立判定：争议不成立**（详见下节「R2.2 争议点的独立复现」）。
- R2.3 通过，破坏有效：把 `report_file` / `history_file` 改成写死本仓根后，
  `test_default_report_path_stays_inside_guarded_workspace` 变红
  （`1 failed, 3 passed`），**其余 3 条旧用例仍绿** —— 与工单期望一致，
  说明「覆盖缺口」结论成立且新增守护确实卡在正确位置。
  立刻 `git checkout -- ai_collab/concurrent_guard.py` 还原，`git status --short`
  中已无该文件，还原后重跑 `4 passed`，与还原前备份 `diff` 结果 `IDENTICAL`。
- R2.4 通过。`test_consensus_engine_concurrency.py` 钉的是**当前行为**：
  `test_same_topic_concurrency_may_recompute` 用屏障确定性复现「provider 被调用 5 次」，
  注释明写「这是当前契约，不是 bug」——**没有**把「同 topic 并发只算一次」当成期望。
  `git show e6fb352 -- ai_collab/engines/consensus_engine.py` 显示改动为
  `+16 / -1`，全部落在 `generate_consensus` 的 docstring 上，
  并发语义**零改动**（缓存字典仍是无锁实例级 dict）。
- R2.5 判定**可接受**，理由如下：
  - 扫整个工作树（`PROJECT_ROOT.rglob("*")`）比契约文字「仓库根目录」**更严**，是正向偏离；
  - 跳过 `logs/` 可接受：`logs/` 是 gitignored 的运行时产物目录（门禁报告、开发日志落点），
    且 `testpaths = ["tests"]` 已把 pytest 收集面收窄到 `tests/`，
    跳过 `logs/` 不影响「防外部项目副本被收集」这一核心目的；
    代价是 `logs/` 下若藏外部项目副本不会被这条守护点名（风险已极低，且 `logs/` 不入库）；
  - 另跳过 `.git` / `node_modules` / `__pycache__` / 各类缓存目录，均属合理。

### R2.2 争议点的独立复现

争议：`tests/unit/test_concurrent_guard_reuse.py` 的 docstring 与
`TASK-P2-CONCURRENT-GUARD-PHASE4-001.md` R4 曾写「不传 `guard_config` 就会写进**本仓**的
`logs/workspace_forensics/`」——与实现不符。

我的独立实测（自写探针脚本，构造目录名不含 `ai_collab` 的外部 mini git repo，
**不传** `guard_config`）：

```
report_file  = /var/folders/.../tmpXXXX/shared-workspace-sample/logs/workspace_forensics/concurrent_guard_latest.json
history_file = /var/folders/.../tmpXXXX/shared-workspace-sample/logs/workspace_forensics/concurrent_guard_history.jsonl
report 落在被治理工作区内 = True
report 落在本仓内 = False
默认落点目录 = /var/folders/.../tmpXXXX/shared-workspace-sample/logs/workspace_forensics
本仓 report 文件之前存在 = True  之后存在 = True  mtime 未变 = True

[绝对路径语义] report_file = /Users/raymondna/Documents/AI-collab/ai-collab-base/logs/workspace_forensics/r22_probe_absolute.json
绝对路径时落在本仓内 = True
```

**判定：争议不成立**（即「不传 guard_config 会写进本仓」是错的）。
落点规则是 `workspace / report_rel`（`ai_collab/concurrent_guard.py`）：
相对路径落在**被治理工作区**内部；绝对路径按调用方给的位置落
（pathlib 语义：右操作数为绝对路径时左操作数被丢弃）——这与工单给出的「实现事实」描述一致。
commit `cf7907a` 已把该错误表述从 docstring 与工单里纠正掉，本次复核确认其纠正到位。
（探针产生的临时文件已删除。）

### R3 复核③：OpenSpec 落地（`414f091`）

- R3.1 通过：`openspec validate add-concurrent-workspace-guard --strict` → `Change 'add-concurrent-workspace-guard' is valid`，rc=0。
- R3.2 通过：`openspec status --change add-concurrent-workspace-guard` → `Progress: 4/4 artifacts complete`
  （proposal / specs / design / tasks 全 `[x]`）。
  注：`openspec status` 不带参数会报错（1.11.0 要求 `--change` 或 `--all`），
  工单原文的 `openspec status` 需要补参数才能跑通。
- R3.3 通过（**工单表述需订正**）。用 `yaml.safe_load` 断言：
  - `operations.apply.guidance` → `list[str]`（2 项）
  - `operations.archive.guidance` → `list[str]`（2 项）
  - `rules` 本身是**按工件类型分组的 dict**（proposal / specs / design / tasks），
    其每个子键的值均为 `list[str]`（3/4/3/3 项）——**不是** `list[str]`。
  即工单「`rules` 必须是字符串数组」的措辞与实际结构不符（工单的表述问题，非实现缺陷）。
  `openspec doctor` 输出 `Root: ok`、`References: (none declared)`，**无告警**，
  即不存在「块标量被静默忽略」的情形。
- R3.4 通过，且强于工单期望：备份 CLAUDE.md → `openspec update --force`（rc=0，
  更新 claude / codeartsagent 两个工具）→ CLAUDE.md 的「# OpenSpec Instructions」段
  **仍在**，且 `md5` 前后完全一致、`diff` 结果「CLAUDE.md 完全一致（未被改动）」
  —— 整份文件根本未被触碰。随后 `git checkout -- CLAUDE.md` 还原，
  `git status --short` 与操作前基线逐行相同。
- R3.5 通过：`openspec/specs/` 为**空目录**（0 个文件），
  `openspec/changes/add-concurrent-workspace-guard/` 仍在 —— **PR 没有提前归档**，
  复核对象未消失。

### R4 复核④：CI 隔离修复（`6855455`）

- R4.1 通过：`python3 -m pytest tests/unit/test_ci_isolation_guard.py -q` → `1 passed`。
- R4.2 **本机原样执行不成立，加强版成立**（详见问题清单 #1）：
  - 按工单原样操作（移除 `resolve_credentials` 打桩后跑守护）→ 守护**仍绿**
    （`1 passed`），与工单/commit 声称的「期望失败」不符；
  - 定位原因：本机环境注入了 `OPENCODE_SERVER_PASSWORD`（CodeArts kernel 注入），
    守护子进程只改 `HOME`、**未清理凭据类环境变量**，于是撤掉打桩后
    `resolve_credentials` 仍能从 env 拿到密码 → 用例照常通过；
  - 加强版实测（额外 `env -u OPENCODE_SERVER_PASSWORD -u CODEARTS_KERNEL_PASSWORD`，
    更贴近 CI runner 真实条件）：
    - 撤掉打桩 → `FAILED tests/unit/test_codearts_bridge_deliver.py::test_purge_residue_cli_flag_runs_purge`，
      `assert 2 == 0`，`1 failed, 147 passed` —— **与 commit message 记载的数字完全一致**；
    - 还原打桩后同一命令 → `148 passed`。
  结论：**守护本身有效**，但其「本地自检」能力有缺口（见问题清单 #1）。
- R4.3 通过：**删除断言 0 条，无放宽**。逐条看 `git show 6855455` 的 diff：
  - 新增 autouse fixture `_isolated_kernel_root`（把 `KERNEL_CONFIG_ROOT` 钉到 tmp 内假 kernel，
    pid 用当前进程 pid）；新增 68 行隔离守护文件；
  - `test_setup_credentials_writes_credential_file_without_echoing_password` 的 3 处断言
    **仅改字面量**（`s3cret-password-value` → `dummy-s3cret-password-value`），
    断言条数、断言语义、断言强度均未变（仍断言写入内容、不回显、权限 600）；
  - `test_purge_residue_cli_flag_runs_purge` 是**新增**打桩（不是删除断言）。
- R4.4 通过，结论：改用占位符**比行号锚定更稳**。
  `scripts/scan_secrets_pii.py` 的 `placeholder_indicators` 含 `dummy-`
  （第 44/53/64/75 行等），因此 `dummy-s3cret-password-value` 被扫描器直接判为占位符跳过，
  该文件不再需要任何**位置耦合**的白名单条目。
  对比：原条目 `tests/unit/test_codearts_bridge_deliver.py:923` 是行号锚定——
  本次在上方插入 fixture 就已真实失效过一次（扫描器重新报出），属于「必然再次失效」的结构。
  代价与收益对称：将来若有人再把夹具密码改成不含占位符特征的值，扫描器会重新报出
  —— 那正是**期望行为**（真问题暴露），而不是像行号锚定那样静默错位。

### R5 复核⑤：记忆纠错（`04bca05`）

- R5.1 通过：`sh scripts/verify_agent_config_sync.sh` → `TOTAL: pass=8 fail=0`
  （V1 治理门禁 / V2 镜像幂等 / V3 漂移检测→修复闭环 / V4 单测 / V5 必读文件纯路径 /
  V6 gitignore 白名单 / V7 @import 接线 全部 PASS）。
- R5.2 通过，**两点均自行打开代码确认**，未只读记忆：
  - `ai_collab/cli/__main__.py:20` 实测内容正是 `sys.exit(main())`（行号精确匹配）；
  - 进程级复验（跑命令看 `$?`）：
    `tasks list` → 0；`ack --task-id NOPE-XXX`（缺参）→ 1；`tasks show --task-id NOPE` → 2。
    即子命令 `return 1` **已**能传到进程退出码，条目所称的缺陷确已由 `a938cd8` 修复，
    条目正文与代码事实一致；旧的被证伪条目 `memory/project_cli_exit_code_defect.md`
    已不存在。
- R5.3 通过：`memory/` 是只读镜像，本次改动**没有**手改镜像绕过源——
  `04bca05` 的记忆变更全部发生在**源目录** `~/.codeartsdoer/memory/...`，
  仓库镜像由 `scripts/sync_agent_memory.py` 重新生成（commit message 记载
  「synced 31 file(s)」，MEMORY.md 索引随之更新）。
  当前 `python3 scripts/sync_agent_memory.py --check` → `[OK] memory mirror in sync (34 file(s))`，rc=0。

### R5.5 复核⑥：派单链新鲜度校验修复（`bdc302f`）

- R5.5.1 通过：`python3 -m pytest tests/unit/test_dispatch_trigger_freshness.py tests/unit/test_agent_dispatch_bridge.py tests/unit/test_ack_watchdog.py -q` → `49 passed`。
- R5.5.2 通过，破坏有效：删除 `scripts/agent_dispatch_bridge.py` 里的
  `"generated_at": report_timestamp,` 后，
  `FAILED tests/unit/test_agent_dispatch_bridge.py::test_dispatch_report_exposes_generated_at_for_freshness_check`
  与 `FAILED ...::test_dispatch_report_generated_at_passes_freshness_check`（`KeyError: 'generated_at'`），
  `2 failed, 47 passed` —— **恰好是新增的 2 条桥接用例变红**，与工单期望一致。
  立刻 `git checkout -- scripts/agent_dispatch_bridge.py` 还原，重跑 `49 passed`，
  与还原前备份 `diff` 结果 `IDENTICAL`。
- R5.5.3 通过（新写法）：payload 里现在教的是
  `cat logs/task_dispatch_report.json | grep -E 'generated_at|timestamp'`，
  在真实报告上实测 rc=0、输出含 `generated_at` 与 `timestamp` 两行（值相同）。
  **如实标注**：工单/commit 称旧写法 `grep -E '"(generated_at|timestamp)"'` 会报
  `syntax error near unexpected token ')'`；我在本机用 bash 与 `sh -c` 两种方式实测旧写法
  **rc=0 也能跑通**，未能复现该报错。修复本身（改用无引号转义的写法）仍然更稳，
  但「旧写法必然语法报错」这一具体断言在本机不成立。
- R5.5.4 通过，端到端自证：跑 `python3 -m ai_collab.cli run --include-pending`（rc=0）后，
  `collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md` 的 `GeneratedAt`
  = `2026-10-24T19:06:08.579112`，`logs/task_dispatch_report.json` 的 `generated_at`
  = `2026-10-24T19:06:08.572227`，**时间差 0.007 秒（0.00 分钟）≤ 5 分钟** → 判定「新鲜」。
  旁证：`python3 -m ai_collab.cli sessions health` → 8 sessions / 7 healthy / 1 unhealthy，
  唯一 incident 是 `missing_explicit_ack`（claude_code 侧任务 ACK 缺失），
  **已无 `stale_payload` 假告警**。

### 本轮复核自身的执行环境约束遵守情况

- 全程未使用 `write` / `edit` 工具写文件（一律 bash heredoc），未派生子代理；
- 每次反向验证后立即 `git checkout --` 还原并以 `git status --short` 举证；
- 未改 `ai_collab/` 下任何 `.py` 的最终内容、未改 `openspec/` 下任何工件、
  未改 `collaboration/tasks/` 下任何已有工单、未改 `memory/` 下任何文件、
  未改 `config/` 下任何文件、未 commit / push / 合并 PR。

---

## 测试结论

- 6 条验收命令：5 条首跑通过；第 3 条（全量）首跑 rc=1，重跑 rc=0。
  **首跑唯一失败项是性能阈值边界抖动**（0.101s vs 阈值 0.1s，单条重跑 3 次全绿，
  全量重跑全绿），与本 PR 复核对象无功能关联。
- 反向验证 4 项（R2.3 / R3.4 / R4.2 / R5.5.2）：3 项按预期直接暴露破坏
  （R2.3 → 1 条变红、R5.5.2 → 2 条变红、R4.2 → 加强版 1 failed 147 passed），
  1 项（R3.4）表现为「破坏目标根本不存在」（`openspec update --force` 压根不碰 CLAUDE.md）；
- 守护有效性判定：并发守护的复用守护、派单新鲜度守护**确实在守护**；
  CI 隔离守护**有效但自检能力有缺口**（本机 env 未隔离，见问题清单 #1）；
- 全仓套件规模：3014 passed / 6 skipped / 0 failed（重跑口径）；
- PR #2 的 CI 现状：lint / mypy / health / bandit / python-tests(3.10,3.11,3.12) /
  secrets-scan / coverage(>=85%) / pip-audit / pack-validation / chrome-extension-tests
  **全部 SUCCESS**。

### 发现的问题清单

| # | 问题 | 证据 | 建议动作 | 严重度 |
|---|------|------|----------|--------|
| 1 | CI 隔离守护只隔离 `HOME`，**未清理凭据类环境变量**，导致「撤掉打桩守护仍绿」——工单 R4.2 与 commit message 声称的反向验证结果在本机不可复现 | 原样执行守护 → `1 passed`；本机 env 存在 `OPENCODE_SERVER_PASSWORD`；加 `env -u OPENCODE_SERVER_PASSWORD -u CODEARTS_KERNEL_PASSWORD` 后 → `1 failed, 147 passed` | 在 `tests/unit/test_ci_isolation_guard.py` 的子进程 env 中显式剔除 `OPENCODE_SERVER_PASSWORD` / `CODEARTS_KERNEL_PASSWORD` 等凭据变量，使守护在本机即可复现 CI 条件 | 中 |
| 2 | 全量套件首跑出现 `tests/perf/test_performance_baseline.py::test_state_update_performance` 超阈值 0.001s；且 PR 的 CI 门禁**不跑 `tests/perf/`**（`test.yml` 只跑 unit + integration），该类性能回归在 PR 门禁里不可见 | `AssertionError: Single state update took 0.101s, threshold is 0.1s`；单条重跑 3 次全绿；全量重跑 `3014 passed` | 二选一：① 把 `tests/perf/` 纳入 PR 门禁（可加宽阈值或标 flaky 重试）；② 保持现状但在 PR 描述中声明性能基线用例不在 PR 门禁范围 | 低 |
| 3 | spec Requirement「工作区 git 上下文采集」的**重命名路径归一化**场景无守护用例（`concurrent_guard._normalize_porcelain_path` 全仓无用例命中） | `grep -rn "_normalize_porcelain_path" tests/` 无命中；`grep -rn "old.py\|-> new" tests/` 只命中 `test_workspace_guard_extra.py`（测的是另一个模块的 `_normalize_path`）；**实现行为正确**：实测 `dirty_paths == ['new.py']`（原始 porcelain 行为 `R  old.py -> new.py`） | 补一条针对 `inspect_git_context` 的重命名归一化用例 | 低 |
| 4 | spec Requirement「检测结论落盘留痕」的**「连续运行两次 → 历史 2 行且每行可解析 JSON」**场景无守护断言（现有用例只断言「一次运行 → 1 行」） | `test_concurrent_guard.py:334` 只跑一次并断言文件存在；`test_concurrent_guard_cli.py:271` 断言 `len(lines) == 1`；**实现行为正确**：实测连续两次运行后历史 2 行、每行可解析 JSON | 补一条「连续两次运行 → 历史 2 行 → 逐行 json.loads 成功」的用例 | 低 |
| 5 | `concurrentGuard.enabled=false` 的降级语义**有实现、有用例、无需求**（spec 未描述该开关） | 实现 `ai_collab/concurrent_guard.py` `run_concurrent_guard` 中 `if not enabled or force: allowed = True`；用例 `test_disabled_allows` / `test_config_can_disable_guard`；spec 全文无 `enabled` 描述 | 在 spec 的「CLI 门禁」需求补一条场景：配置 `enabled=false` 时跳过阻断 | 低 |
| 6 | `collaboration/PROTOCOL.md` 14.3 有笔误：`gitF rev-parse HEAD` | `sed -n '467,540p' collaboration/PROTOCOL.md` | 改为 `git rev-parse HEAD` | 低 |
| 7 | PROTOCOL 14.5 分层表写 G3「不可阻断」，但实现允许通过 `foreignChangeSeverity: "high"` 让它进 `violations` 并阻断（spec 已描述该配置行为，PROTOCOL 未提） | `assess_concurrent_risk`：`if foreign_change_severity == "high": violations.append(...)`；spec「严重级别配置为 high」场景 | PROTOCOL 14.5 表格补一句「默认 warning 不阻断；配置为 high 时按违规阻断」 | 低 |
| 8 | 派单模板 / 工单把结果文件四段契约标注为「PROTOCOL §7.3 契约」，但 PROTOCOL §7.3 实际是**绑定规则**（change_id / assignee_role / assignee_provider），不含四段契约 | `awk '/7\.3/,/^## 八、/' collaboration/PROTOCOL.md` → §7.3 为「绑定规则（强制）」；四段契约实际出处是派单模板与各工单的验收标准（如 `openspec/config.yaml` 的 `operations.apply.guidance`） | 把派单模板与工单里的「PROTOCOL §7.3 契约」改为「结果文件四段契约（见 `openspec/config.yaml` operations.apply.guidance）」 | 低 |
| 9 | 工单 R3.3 与 R3.2 的表述与工具实际用法不符：`rules` 是分组 dict 而非 `list[str]`；`openspec status` 需带 `--change` | `yaml.safe_load` 实测 + `openspec status` 无参时报 `Missing required option --change` | 订正工单表述（属工单文本问题，不在本次改动范围） | 低 |

---

## 风险

1. **合并风险低**：五块交付的实现均经独立实测与破坏性实测验证，功能面无缺陷发现；
   PR #2 的 CI 全绿，合并本身不会引入功能性回归。
2. **CI 隔离守护的本地自检缺口（问题 #1）**：守护在**真 CI runner**（env 干净）上有效，
   但在装了 CodeArts kernel 的开发机上**测不出**同类依赖——这削弱了「提交前就暴露」
   的原始设计意图。建议尽快补 env 隔离，否则「本地自检」只是一次性的。
3. **性能基线类回归不可见（问题 #2）**：`tests/perf/` 不在 PR 门禁内，
   未来任何让状态写入变慢的改动都不会被 PR 挡住。
4. **守护断言强度不足（问题 #3/#4）**：这两处是**「实现正确但用例没钉住」**——
   今天是对的，但将来有人改坏 `_normalize_porcelain_path` 或历史追加逻辑，
   现有守护不会变红。属于「假绿」风险而非当前缺陷。
5. **文档与实现的三处细微不一致（问题 #6/#7/#8）**：不触发运行时行为，
   但会误导后续读者（例如按 PROTOCOL 表格认为 G3 永不阻断）。
6. **工作区残留说明**：本次复核结束后 `git status --short` 中除本结果文件外，
   仅剩 `collaboration/monitoring/` 下 8 个**由 CLI 自动刷新的摘要文件**
   （`ACK_REMEDIATION_SUMMARY_latest.md`、`ACK_WATCHDOG_SUMMARY_latest.md`、
   `AUTOMATION_BENEFIT_DASHBOARD_latest.md`、`CODEARTS_ADAPTER_SUMMARY_latest.md`、
   `MISSING_ACK_SUMMARY_latest.md`、`SESSION_INTERVENTION_SUMMARY_latest.md`、
   `SESSION_REGISTRY_SUMMARY_latest.md`、`TASK_RESULT_CONSISTENCY_SUMMARY_latest.md`）
   —— 它们是 `tasks update` / `run` / `sessions health` 等 CLI 命令的**自动刷新产物**，
   不是本次复核的实质改动，也不影响代码与门禁；
   `memory/.sync-manifest.json` 的时间戳变动是 `verify_agent_config_sync.sh`（V3 漂移修复闭环）
   的副作用，已还原。**除此之外无任何残留改动。**

---

## 回滚

- 本次复核**未修改任何实现代码**（最终内容零改动），**未 commit / push / 合并 PR**，
  因此**无需代码回滚**。
- 唯一的仓库改动是本结果文件：
  `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-001` 对应的
  `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md`。
  如需撤销：`rm collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md`
  （该文件尚未提交，撤销不影响历史）。
- 反向验证期间的临时改动已全部用 `git checkout -- <file>` 还原并逐次举证：
  `ai_collab/concurrent_guard.py`（R2.3）、`tests/unit/test_codearts_bridge_deliver.py`（R4.2）、
  `scripts/agent_dispatch_bridge.py`（R5.5.2）、`CLAUDE.md`（R3.4，还原为 no-op——
  `openspec update --force` 未改动该文件）。
- 若后续决定**不合并** PR #2：`git branch -D feat/codearts-collab-wiring`（本地）+
  `gh pr close 2`（远端）；工作区与 `main` 未被本 PR 改动，无需 `git revert`。
