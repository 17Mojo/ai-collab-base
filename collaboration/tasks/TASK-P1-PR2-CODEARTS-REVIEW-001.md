---
task_id: TASK-P1-PR2-CODEARTS-REVIEW-001
change_id: add-concurrent-workspace-guard
status: planning
priority: P1
assignee: codearts_agent
assignee_role: AGENT_TEST
reviewer: claude_code
primary_skill: testing
support_skills:
  - documentation
created_at: 2026-10-24T16:20:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py tests/unit/test_concurrent_guard_reuse.py tests/unit/test_project_boundary_guard.py tests/unit/test_consensus_engine_concurrency.py -q"
  - "python3 -m pytest tests/unit/test_ci_isolation_guard.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 scripts/scan_secrets_pii.py --workspace ."
result_file: collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md
---

# TASK-P1-PR2-CODEARTS-REVIEW-001：复核 PR #2（并发工作区守护 + OpenSpec 落地 + CI 隔离修复）

> **本工单是复核工单，不是实现工单。**
> 你是 **AGENT_TEST（CodeArts）**，职责是**独立验证** PR #2 的交付是否成立，
> 不是重写它。Claude Code 是 **AGENT_EXEC + AGENT_ARCH**，是本 PR 的作者。
> 复核结论会直接决定 PR #2 是否合并（`gh pr merge 2 --rebase`）。

## 一、被复核对象

| 项 | 值 |
|---|---|
| PR | #2 `feat/codearts-collab-wiring` → `main` |
| 标题 | feat(guard): 并发工作区守护落地（OpenSpec 全阶段 + CLI 门禁 + 记忆纠错） |
| 分支 HEAD | `9dcb064` |
| 当前工作区 | 与你**同一个** working tree（`/Users/raymondna/Documents/AI-collab/ai-collab-base`） |

PR 覆盖 18 个 commit，实质是 5 块交付：

| 块 | 代表 commit | 实质内容 |
|---|---|---|
| ① Phase 2.2 并发守护 CLI 门禁 | `4684652` | `ai_collab/concurrent_guard.py` + `_run_concurrent_guard_gate` + `concurrent guard` 子命令 + `.vscode/ai-collab.json` 的 `concurrentGuard` 段 |
| ② Phase 4 项目边界 | `e6fb352` | `tests/unit/test_project_boundary_guard.py` / `test_consensus_engine_concurrency.py` / `test_concurrent_guard_reuse.py` + `consensus_engine.py` docstring |
| ③ OpenSpec 规范驱动落地 | `414f091` | `openspec/config.yaml` + change 工件（proposal/design/tasks/spec）+ `CLAUDE.md` 改接线 + `.claude/skills/openspec-*`、`.claude/commands/opsx/*` |
| ④ CI 隔离修复（本地绿、CI 红） | `6855455` | `tests/unit/test_codearts_bridge_deliver.py` 隔离 fixture + 新增 `tests/unit/test_ci_isolation_guard.py` |
| ⑤ 记忆纠错 | `04bca05` | `memory/project_cli_exit_code_defect.md` → `project_cli_exit_code.md`（缺陷实为已修，条目被证伪） |

## 二、复核的总原则

1. **不要信 PR 描述里的任何自述数字**（覆盖率、通过率、条数）——一律**自己跑一遍**。
2. **每一条「已通过」的声明都要有一个可复现的输出**。贴命令 + 贴真实输出（哪怕是失败）。
3. **反向验证（negative test）优先于正向验证**：能把实现改坏、让用例变红，
   才证明用例真的在守护；正向全绿只能证明「没崩」。
4. **发现不一致就直接写进结果文件**，不要在代码里替作者修——修是作者的事，
   复核是复核方的职责（本工单 R6 已把写权限限制在结果文件）。
5. 结论**必须给「通过 / 有条件通过 / 不通过」三档之一**，并写明依据。

## 三、详细复核契约

### R1 复核①：并发守护实现与 CLI 门禁

- R1.1 跑 `python3 -m ai_collab.cli concurrent guard --help`，确认子命令真实存在；
  跑一次真实调用，确认退出码与 `allowed` / `risk_level` 自洽
  （`allowed is True` ⇔ `violations` 为空）。
- R1.2 **核对配置源**：实现读的是 `.vscode/ai-collab.json` 的 `concurrentGuard` 段，
  **不是** `config/agent-orchestration.json`。请打开实现确认**只有前者**被读，
  并确认 `config/agent-orchestration.json` 及其 schema/template **未被本次改动**。
- R1.3 核对 `openspec/changes/add-concurrent-workspace-guard/specs/concurrent-workspace-safety/spec.md`
  的每一条 `### Requirement:` 是否都有**实现 + 守护用例**对应。
  列出「有需求无实现」或「有实现无需求」的条目。
- R1.4 核对 `collaboration/PROTOCOL.md` 第十四章与实现的一致性（文档说的门禁语义
  与代码实际行为是否一致）。

### R2 复核②：Phase 4 项目边界用例（含已发现的一处文档与实现不一致）

- R2.1 跑 `tests/unit/test_concurrent_guard_reuse.py`，确认 4 条全绿。
- R2.2 **独立判定下列争议点**（Claude Code 侧初步观测，**需要你独立复现或证伪**）：
  - 争议：`tests/unit/test_concurrent_guard_reuse.py` 的 docstring 与
    `TASK-P2-CONCURRENT-GUARD-PHASE4-001.md` R4 注意事项曾写「不传 `guard_config`
    就会写进**本仓**的 `logs/workspace_forensics/`」——**与实现不符**。
  - 实现事实：落点是 `workspace / report_rel`；**相对路径**落在被治理工作区内部，
    **绝对路径**按调用方给的位置落（pathlib 语义：右操作数绝对 → 左操作数被丢弃）。
  - 请用**你自己的脚本**实测「不传 `guard_config` 时报告落在哪」，
    并给出你的判定（成立 / 不成立 + 你的实测输出）。
- R2.3 **反向验证新补的守护**：
  把 `ai_collab/concurrent_guard.py` 里的
  `report_file = workspace / report_rel` 临时改成写死本仓根（例如
  `Path(__file__).resolve().parents[1] / report_rel`），
  跑 `tests/unit/test_concurrent_guard_reuse.py`，
  记录**哪几条用例变红**，然后**立刻还原**（`git checkout -- ai_collab/concurrent_guard.py`）
  并用 `git status --short` 证明已还原。
  期望：只有 `test_default_report_path_stays_inside_guarded_workspace` 变红。
  若**三条旧用例也变红或都不红**，如实记录——这直接关系到「覆盖缺口」结论是否成立。
- R2.4 复核 `tests/unit/test_consensus_engine_concurrency.py` 钉的是
  「**当前行为**」而不是「理想行为」：确认用例**没有**把「同 topic 并发只算一次」
  当成期望（当前实现是无锁 dict，同 topic 并发**会**重复计算）。
  确认 `ai_collab/engines/consensus_engine.py` 的改动**只有 docstring**，
  并发语义**零改动**（`git diff` 核对）。
- R2.5 复核 `tests/unit/test_project_boundary_guard.py` 的断言强度：
  它扫的是**整个工作树**（比契约文字「仓库根目录」更严），且**跳过 `logs/`**。
  判断这两处放宽是否可接受，理由写进结果文件。

### R3 复核③：OpenSpec 落地（`414f091`）

- R3.1 `openspec validate add-concurrent-workspace-guard --strict` → 必须 valid。
  （若 `openspec` 不在 PATH，用绝对路径 `/opt/homebrew/bin/openspec`。）
- R3.2 `openspec status` → 4/4 工件齐备。
- R3.3 **验证 `openspec/config.yaml` 的结构**：`rules` 与 `operations.*.guidance`
  的值**必须是字符串数组**（不是块标量）。块标量会被静默忽略并报 doctor 警告。
  用 `python3 -c "import yaml,sys; d=yaml.safe_load(open('openspec/config.yaml')); ..."`
  自行断言每个条目是 `list[str]`。
- R3.4 **验证 `CLAUDE.md` 的新接线能扛住 `openspec update --force`**：
  OpenSpec CLI 1.11.0 会**删除**带 `<!-- OPENSPEC:START/END -->` 标记的块。
  当前 `CLAUDE.md` 的「# OpenSpec Instructions」是**无标记**的手写段。
  请**实测**：备份 `CLAUDE.md` → 跑 `openspec update --force` → 确认该段仍在
  → `git checkout -- CLAUDE.md` 还原并用 `git status --short` 证明已还原。
- R3.5 确认 `openspec/specs/` 目录当前**为空**（尚无 main spec）——
  归档（`openspec archive`）才是生成 `openspec/specs/concurrent-workspace-safety/spec.md`
  的那一步。确认 PR **没有**提前归档（归档会清空 `changes/`，让复核对象消失）。

### R4 复核④：CI 隔离修复（`6855455`）—— **本 PR 风险最高的一块**

这块修的是「本地绿、CI 红」：7 条用例依赖本机 CodeArts kernel 凭据，CI runner 上必红。

- R4.1 跑 `python3 -m pytest tests/unit/test_ci_isolation_guard.py -q` → 全绿。
- R4.2 **反向验证隔离守护真的有效**：
  把 `tests/unit/test_codearts_bridge_deliver.py` 里的
  `resolve_credentials` 打桩（`monkeypatch.setattr(bridge, "resolve_credentials", ...)`）
  去掉，然后跑 `tests/unit/test_ci_isolation_guard.py`，
  期望**失败**（出现 `1 failed`）。之后**立刻还原**并用 `git status --short` 证明已还原。
- R4.3 **确认没有「删断言换绿」**：`git show 6855455 --stat` + 逐条看 diff，
  确认既有测试的**断言没有被删除或放宽**，只是**加了隔离 fixture 与打桩**。
  明确列出：本次改动**删除**了哪些断言（应为 0 条）。
- R4.4 复核 `config/secrets-scan-allowlist.txt`：本次删掉了一条**行号锚定**的
  白名单（`tests/unit/test_codearts_bridge_deliver.py:923`），改为把夹具里的假密码
  改名成含占位符特征的值。判断这个做法是否比行号锚定**更稳**（行号会随文件
  变动而失效——本次就真的失效过一次），给出结论。

### R5 复核⑤：记忆纠错（`04bca05`）

- R5.1 `sh scripts/verify_agent_config_sync.sh` → 应 8/8 PASS。
- R5.2 **核对记忆条目与代码事实是否一致**：条目声称
  `ai_collab/cli/__main__.py:20` 是 `sys.exit(main())`，且缺陷已由 `a938cd8` 修复。
  请**自己打开代码确认**这两点，不要只读记忆。
- R5.3 确认 `memory/` 是**只读镜像**（由 `scripts/sync_agent_memory.py` 从
  `~/.codeartsdoer/memory/` 单向同步），本次改动**没有**手改镜像而绕过源。

### R6 权限边界（硬约束）

| 允许 | 禁止 |
|------|------|
| 写 `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md` | 改 `ai_collab/` 下任何 `.py` 的**最终内容** |
| 跑测试 / 跑 CLI / 跑 openspec / 跑脚本 | 改 `openspec/` 下任何工件 |
| **临时**改文件做反向验证（必须在结果文件里写清改了什么） | 改 `collaboration/tasks/` 下任何已有工单 |
| 跑 `git status --short` 证明工作区已还原 | 改 `memory/` 下任何文件 |
| | 改 `config/` 下任何文件 |
| | 提交（commit）/ 推送 / 改 PR |
| | 合并 PR（合并由 Claude Code 在你复核通过后执行） |

> **反向验证的还原纪律**：每次临时改动后**立刻** `git checkout -- <file>` 还原，
> 并在结果文件里附 `git status --short` 的输出作为证据。
> 结束时 `git status --short` **不得**出现除结果文件与工单以外的任何改动。
> 注意：本次工作区**本来就有**两处既存改动（`memory/.sync-manifest.json`、
> `collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md`），
> 那不是你的改动，别动、别还原。

### R7 结果文件契约

结果文件 `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md` 必须：

- 头部 **前 40 行内**含一行 `- **状态**: completed`（若你判定不通过，
  状态写 `blocked` 并说明——**不要**写「不通过但状态 completed」）。
- 含 `## 执行命令` / `## 验证结果` / `## 测试结论` / `## 风险` / `## 回滚` 各段标题。
- **逐条原样**贴出本工单「验收标准」里的 6 条 acceptance_commands
  （字符串要**逐字**出现在文件里，否则 `tasks update --status completed` 会被门禁拒收）。
- **不要**在文件里出现 `- [ ]`（未勾选复选框会被门禁当成负面信号拒收）。
- 有一节明确写「**复核结论**：通过 / 有条件通过 / 不通过」，并列出
  「发现的问题清单」（每条含：问题、证据、建议动作、严重度）。
- 对 R2.2 的争议点给出**你独立复现**的判定与证据。

## 四、验收标准

- [ ] 6 条 acceptance_commands 全部实跑并原样出现在结果文件里
- [ ] R2.2 / R2.3 / R3.4 / R4.2 四项**反向验证或破坏性实测**都做了，
      且都附了还原证据
- [ ] R3.3 用 `yaml.safe_load` 断言过 `openspec/config.yaml` 的数组结构
- [ ] 给出三档之一的复核结论 + 问题清单
- [ ] `git status --short` 里除本工单允许的改动外无残留

### Acceptance Commands

- `python3 -m pytest tests/unit/test_concurrent_guard.py tests/unit/test_concurrent_guard_cli.py tests/unit/test_concurrent_guard_reuse.py tests/unit/test_project_boundary_guard.py tests/unit/test_consensus_engine_concurrency.py -q`
- `python3 -m pytest tests/unit/test_ci_isolation_guard.py -q`
- `python3 -m pytest tests/ -q`
- `python3 -m ruff check .`
- `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`
- `python3 scripts/scan_secrets_pii.py --workspace .`

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-PR2-CODEARTS-REVIEW-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md
```

把该命令**原样输出**的一行回复回来。

## 六、参考

- PR #2：<https://github.com/17Mojo/ai-collab-base/pull/2>
- OpenSpec change：`openspec/changes/add-concurrent-workspace-guard/`
  （`proposal.md` / `design.md` / `tasks.md` / `specs/concurrent-workspace-safety/spec.md`）
- 核心实现：`ai_collab/concurrent_guard.py`
- 门禁接线：`ai_collab/cli/_cli_main.py`（`_run_concurrent_guard_gate`）
- 设计文档：`docs/CONCURRENT_GUARD_DESIGN.md`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求、第十四章）
- 既有结果文件（被复核对象的自述，**要核对而不是采信**）：
  `collaboration/results/RESULT-P2-CONCURRENT-GUARD-PHASE4-2026-10-24.md`、
  `collaboration/results/RESULT-P1-CONCURRENT-GUARD-2026-10-24.md`
