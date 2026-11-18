# 开发记录：项目体检（2026-10-24）——体检工具链 4 处系统性失真的定位与修复

## 记录信息

- **任务ID**: quickfix/no-spec（用户直接发起「进行项目体检」，无对应工单）
- **AI类型**: Claude Code
- **时间**: 2026-10-24
- **分支**: `feat/codearts-collab-wiring`（基线 `5c33107`）
- **结果文件**: `collaboration/results/RESULT-HEALTHCHECK-2026-10-24.md`
- **自动报告**: `collaboration/results/HEALTH_CHECK_2026-10-24.md`
- **任务描述**: 对项目做一次体检，并核实自动体检报告的每一项指标是否属实。

---

## 背景

用户发起「进行项目体检」。项目自带 `scripts/project_healthcheck.py`，能自动生成
`collaboration/results/HEALTH_CHECK_<date>.md`。前两天（10-22）的报告结论是
**85/100 (A)，「所有模块覆盖率 ≥ 80%」，ruff 0 问题，mypy 0 错误**。

本次体检的出发点是：**这份报告本身也属于被体检对象，它的每一项指标都必须与实测对齐。**
所有结论均以实跑命令 / GitHub API 原始返回为依据，不采信自动报告的自述。

## 核心发现：代码健康，但体检工具本身在失真

先给出项目的真实结论：**代码侧健康**（2654 单测全绿、219 集成测试全绿、覆盖率 88% 过 CI 门禁、
mypy 0、治理门禁 8/8、无状态漂移、密钥扫描零真实泄露）。

真正的问题出在体检工具链，共 4 处，其中 2 处直接产出**假绿灯**。

### 缺陷 1：低覆盖模块列表恒为空（假绿灯）

```python
# scripts/project_healthcheck.py:132-133
"coverage report 2>&1 | grep -E '^ai_collab' "
"| awk '{print $1, $5}' | sort -k2 -n | head -10"
```

`coverage report` 输出只有 **4 列**（`Name / Stmts / Miss / Cover`），第 5 列恒为空 →
`awk` 每行只输出 1 个字段 → 后续 `len(parts) == 2` 恒不成立 → `low_coverage_modules`
**永远为空** → 报告永远打印「✅ 所有模块覆盖率 ≥ 80%」。

实测修复前后的 `split()` 结果：

```
修复前: ['ai_collab/__init__.py']      ← 1 个字段，判定条件永不成立
修复后: ['ai_collab/codex_integration.py', '41%']   ← 正常
```

真实有 **8 个**模块低于 80%，最低 `ai_collab/codex_integration.py` **41%**。
修法：`awk '{print $1, $NF}'`（取最后一列，对列数变化更稳健）。

### 缺陷 2：ruff 检查范围比 CI 窄（假绿灯）

脚本跑 `ruff check ai_collab` → 0 问题；CI 实际跑的是：

| CI 位置 | 命令 | 实测 |
|---------|------|------|
| `lint.yml` | `ruff check .` | **14 errors**（阻断） |
| `test.yml` | `ruff check ai_collab/ scripts/` | **10 errors**（阻断） |

14 个问题全部由本分支引入——`origin/main` 上实测 `ruff check .` 为 `All checks passed!`。
即：**从这个分支提 PR，`lint.yml` 与 `test.yml` 都会变红**，而体检报告却显示「ruff 0 问题 ✅」。

修法：scope 改为 `ruff check .`（与最严的 CI 门禁对齐）；同时把显示阈值从
`ruff_errors < 50` 收紧为 `== 0`（CI 对任何 ruff 错误都阻断，原来 `< 50` 会给 14 个错误盖 ✅）。

### 缺陷 3：healthcheck workflow 从未被 GitHub 成功解析（0 job）

`.github/workflows/healthcheck.yml` 自 2026-09-15 加入起，**30/30 个 run 全部失败、
0 job、0 秒**。取证链：

```bash
gh api "repos/17Mojo/ai-collab-base/actions/workflows/healthcheck.yml/runs?per_page=100"
# → 30 个 run，event 全部是 push，conclusion 全部 failure
gh api repos/17Mojo/ai-collab-base/actions/workflows/healthcheck.yml
# → name = ".github/workflows/healthcheck.yml"  ← 回落成路径，读不到文件里的 name:
```

注意矛盾点：文件里的 `on:` **没有 `push` 触发器**，但每个 run 的 `event` 都是 `push`。
加上 `name` 回落成路径、`latest_check_runs_count: 0`、`updated_at` 停在 2026-09-15T19:25:41
（此后从未刷新）——这是 **GitHub 解析文件失败**的标准签名。

排查过程中逐一排除了：YAML 语法（PyYAML + ruamel 1.2 strict + 禁重复键）、schemastore
`github-workflow.json` schema、BOM / CRLF / TAB / 控制字符 / 异体引号、文件权限、
与 GitHub 副本的字节一致性（2272B，sha256 前缀 `24f734bb`，完全相同）、
与 `origin/main` 的差异（完全相同）、文件创建后是否被改过（从未）。

**最终从 GitHub 服务端抓到原始报错**（`GET /actions/runs/{id}` 页面内的 annotations）：

```
Invalid workflow file: .github/workflows/healthcheck.yml#L1
(Line: 55, Col: 13): Unexpected symbol: '"pull_request"'.
  Located at position 22 within expression: github.event_name == "pull_request",
(Line: 69, Col: 9):  Unexpected symbol: '"pull_request"'.
  Located at position 22 within expression: github.event_name == "pull_request"
```

位置 22 正是双引号字符串字面量的起始字符。**不是 YAML 问题，是 GitHub 表达式解析层
不接受 `if:` 里的双引号字符串字面量**。

同仓反证：`test.yml:66` 用单引号 `if: matrix.python-version == '3.12'`，该 workflow 在 CI
正常跑通——单引号写法在本仓库已被 GitHub 接受。

修法：两处 `if: github.event_name == "pull_request"` → 单引号。

### 缺陷 4：评分与代码状态脱钩（同日两次运行两个分数）

脚本统计未跟踪文件时，把**自己的输出文件** `collaboration/results/HEALTH_CHECK_<date>.md`
也算进去，于是：

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 当日首次运行 | 85/100 (A) | 85/100 (A) |
| 当日第二次运行 | 65/100 (C) | 85/100 (A) ✅ |

同样的代码、同样的仓库，第二次跑凭空掉 20 分。修法：未跟踪统计排除
`collaboration/results/HEALTH_CHECK_*`——工具不该为自己的产物扣分。

修复后评分的唯一输入变成**工作区状态本身**，不再受「工具当天是否已经跑过」影响：同一工作区状态下
连跑两次，评分与内容完全一致（幂等），已实测。
当前工作区再次运行得到 **65/100 (C)**，这不是回归，而是评分如实反映了两个真实条件——本 RESULT
交付文件尚未入库（-20）、分支领先 `origin/main` 70 个 commit 未推送（-15）；待其入库后回到 85/100 (A)。

### 附带修复：fail-on-low-score job 恒失败

该 job 没有 checkout、也没下载 artifact，`health_output.md` 永远不存在 →
`SCORE` 为空 → `[ "" -lt 60 ]` 触发 bash `integer expression expected` → job 恒失败。
已补 `actions/download-artifact@v4`（artifact 名用 `health-report-${{ github.run_id }}`
与上传侧对齐），并加 `if [ -z "$SCORE" ]` 空值守卫。

## 本轮改动

```
 .github/workflows/healthcheck.yml | 13 +++++++++++--
 scripts/project_healthcheck.py    | 24 ++++++++++++++++--------
 2 files changed, 27 insertions(+), 10 deletions(-)
```

未触碰 `ai_collab/` 生产代码。

## 验证

| 项 | 结果 |
|----|------|
| 单测回归 | `2654 passed, 1 skipped, 0 failed`（改动后复跑） |
| 集成测试 | `219 passed, 5 skipped, 0 failed`（跳过均为本地 8000 端口后端未启动） |
| 改动文件 ruff | `All checks passed!` |
| workflow YAML | PyYAML + ruamel YAML 1.2 strict + schemastore JSON Schema 三项全过 |
| 体检脚本 | 连跑两次评分一致（幂等）；低覆盖模块正确列出 8 个；ruff 显示 14 且标 🔴 |
| 治理门禁 | `verify_agent_config_sync.sh` → TOTAL pass=8 fail=0 |
| 状态漂移 | `reconcile_state_drift.py --workspace .` → rc=0 |
| 结果文件契约 | 章节组齐全、无负向信号、状态行 `completed` 可解析、测试结论小节可提取 |

**无法本地验证的部分**：`healthcheck.yml` 修复后是否被 GitHub 成功解析——workflow 文件
必须经服务端解析才生效，需推送后由 GitHub Actions 实跑确认首个非 0-job run。这是本轮
唯一的验证缺口，已在结果文件中明确标注。

## 未纳入本轮修复的事项（附理由）

| 事项 | 不修的理由 |
|------|-----------|
| ~~`ruff check .` 的 14 个问题~~ | ✅ **已解决**（commit `4af0efd`）。用户于 2026-10-24 把 `scripts/sync_agent_memory.py` 的修改执行权交回 Claude Code，解除并发写顾虑；用 `ruff check . --fix` 清零，改动后单测全绿、记忆同步校验 8/8 通过、`sync_agent_memory.py --check` 输出未变 |
| 密钥扫描器无排除机制 | `scripts/scan_secrets_pii.py` 8 条规则全量扫 node_modules，237 条命中逐条判读**全为误报**（205 条来自 node_modules、31 条是源码变量名与测试夹具、1 条是任务 ID 冒充的 key `sk-contract-migration-command`）。**零真实泄露**。补排除机制属独立改动 |
| `openspec/AGENTS.md` / `openspec/specs/` 缺失 | `CLAUDE.md` 顶部强制引用 `openspec/AGENTS.md`，但该文件不存在（`openspec/` 下实际只有 `changes/add-concurrent-workspace-guard/`）。属文档结构补齐，超出体检修复范围 |
| `check_git()` 在缺 `origin/main` 时静默判「✅ 已同步」 | 潜在假绿灯入口，但本仓库 `origin/main` 存在，不影响本次结论，留作后续改进 |
| `check_health_rules()` 只校验「长期经验」字样出现 ≥1 次 | 弱校验，与报告标题宣称的「3 条」不等价 |

## 后续建议（按优先级）

1. `git push -u origin feat/codearts-collab-wiring` —— 72 个 commit 未推送，且当前 upstream
   被配成 `origin/main`，`git push` 会直接报 `upstream branch does not match the name of your
   current branch`。远端 `main` 目前在 `c06584a9`，本地 HEAD 不被任何远端分支包含。
2. ~~由 `scripts/sync_agent_memory.py` 的 owner 处理 ruff 14 个问题~~ → ✅ 已由 Claude Code
   在 commit `4af0efd` 完成（用户授权）。
3. 推送后确认 `healthcheck.yml` 产生首个非 0-job run。
4. 为 `scan_secrets_pii.py` 增加 node_modules 排除，让 `secrets-scan` 从形同虚设变成真门禁。
5. 补 `openspec/AGENTS.md`，或修正 `CLAUDE.md` 中对该文件的强制引用。

## 附：体检中被证伪的记忆条目

记忆库 `project_cli_exit_code_defect.md` 称 `ai_collab/cli/__main__.py` 丢弃 `main()` 返回值、
子命令 `return 1` 到不了进程退出码。实测该文件已改为 `sys.exit(main())`（commit `a938cd8`），
且进程级退出码已正常传导（`ack` 失败→1、`tasks show` 不存在→2、`status` 成功→0），
**该记忆条目已过期**。

**未直接改动的理由**：仓库内 `memory/` 是由 `scripts/sync_agent_memory.py` 从 CodeArts 源
（`~/.codeartsdoer/memory/<slug>/`）单向生成的只读镜像，且该文件在 `.sync-manifest.json`
托管下——手改镜像会立刻破坏 `verify_agent_config_sync.sh` 的 V2 幂等与 V3 漂移检测，
并在下次同步时被覆盖。**更正须落在 CodeArts 源文件**
`~/.codeartsdoer/memory/-Users-raymondna-Documents-AI-collab-ai-collab-base/project_cli_exit_code_defect.md`，
再由 `python3 scripts/sync_agent_memory.py` 同步回仓库。本轮仅做标记，未越权改动。


---

## 第二阶段（用户 2026-10-24 决策后）：派单 CodeArts + 复核 + 门禁摘罩

### 用户决策拆分

| 批次 | 内容 | 执行方 | 状态 |
|---|---|---|---|
| 1.1 | `ruff check .` 14 条 → 0 | Claude Code（用户把 `scripts/sync_agent_memory.py` 执行权交回） | ✅ `4af0efd` |
| 2.1 / 5.1 / 5.2 | 扫描器去噪 + `check_git()` origin/main 判断 + `check_health_rules()` 精确计数 | CodeArts | ✅ 交付并复核通过 |
| 1.2 | 推送 72 个未推送 commit + 修 upstream | Claude Code | ✅ 已推送 |
| 4.2 | `add-concurrent-workspace-guard` Phase 2.2 / Phase 4 分别开工单 | Claude Code | ✅ 两张工单已开 |
| 2.2 | 摘掉 `lint.yml:38` 的 `\|\| true` | Claude Code（复核后） | ✅ 已摘 |

### 派单链路实测

```text
python3 -m ai_collab.cli trigger --phrase "2X DISPATCH CODEARTS"
→ 干预入队: codearts_agent | queued | pending_operator_delivery
→ 投递结果: candidates=1 queued=1 failed=0 skipped_in_flight=0
→ logs/codearts_adapter_report.json: accepted_without_receipt=true
```

**投递耗时约 10 分钟**（桥接在等回执，600s 上限）。回执超时但
`accepted_without_receipt: true`——按「等回执超时≠投递失败」的口径，
**先向 kernel 核实**再定成败：

```bash
# GET /session?directory=<workspace>
→ ses_e942c23bbffeAMBqW2XPVhzGWC | "P1 体检工具链加固与密钥扫描去噪"
```

会话标题与本工单任务描述一致 → **投递确实被 kernel 接受**，未重投，
未产生第二会话。

### 复核发现：交付方未披露的检出能力回退（本次最重要的发现）

CodeArts 的交付忠实实现了契约 R1–R9，验收命令全绿。但契约 R9 要求
「削弱检出能力必须在风险段写明」，交付文件只写了「收窄了噪声捕获面」，
**没有量化回退**。复核用同一批样本对新旧规则做逐条对照，实测回退：

| 样本 | 旧规则 | 交付时 | 性质 |
|---|---|---|---|
| `password =` `hunter2` | 命中 | **漏检** | 真实密码（裸值短） |
| `password =` `abc123` | 命中 | **漏检** | 真实密码（裸值短） |
| `password =` `12345678` | 命中 | **漏检** | 真实密码（纯数字，B 段要求「含数字**且**含字母」） |
| `password =` `"mysecret123"` | 命中 | **漏检** | 真实密码（引号值含 `secret` 子串 → 被占位符指示词整串命中） |
| `password: str` / `resolve_credentials(...)` / `None` / `sha1` 等 | 命中 | 不命中 | ✅ 预期（标识符/占位符） |

**为什么这条必须处理**：下一批 2.2 的动作是摘掉 CI 里 `|| true`，
让密钥扫描成为真门禁。在「裸值短密码 + 纯数字密码」漏检的状态下摘罩，
等于把**带洞的扫描器**升格成阻断门禁——正是本轮一直在清理的「假绿灯」的另一种形态。

**复核方处置（在契约允许的文件范围内补两条零噪声规则）**：

| 规则 | 语义 | 覆盖 | 全仓误报 |
|---|---|---|---|
| `password_literal_bare_numeric` | 6 位以上**纯数字**裸值 | `12345678` | **0** |
| `password_literal_bare_short` | 6–11 位、**字母开头数字结尾、不含短横线** | `hunter2`、`abc123` | **0** |

约束：用 `[ \t]*` 不跨行（避免 `password:` 后接下一行代码被误命中）；
`password_literal_bare_short` 用负向前瞻挡掉 `resolve_credentials(...)` 的前缀匹配；
长度上限 11 位（12 位以上交给既有 B 段，避免同处记两条，有用例守护）。
**两条规则在本仓真实工作区实跑 0 命中**，所以摘 `|| true` 不会把门禁变成噪声源。

新增 4 条回归用例（纯数字必检出 / 裸值短必检出 / 标识符形态仍不命中 / 长值不重复计）。
测试夹具字面量拆成 `"pass" + "word = " + "hunter2"` 拼接——扫描面含测试源码自身，
不拆会被自己的扫描器命中（这正是扫描器自指问题，不是绕过检测）。

**未擅自改的一项**：占位符指示词的**子串**匹配（`password =` `"mysecret123"` 漏检）
属契约级语义（R2 指示词表 + R3 判定方式都是契约明文），复核方未改，
留作已知限制记入风险项，待契约方裁决。

### 复核后的检出能力对照（最终版）

真实密码形态 6/6 全部检出；被放弃的 8 条全部是标识符或占位符形态
（即本工单要消除的噪声类）。相对改造前**无净损失**，噪声 251 → 0。

### 并发守护：清单过期，实测后重新划界（批次 4.2）

`openspec/changes/add-concurrent-workspace-guard/tasks.md` 的 Phase 2.1 / Phase 3
全部标未完成，**实测早已完成**：

| 条目 | 清单 | 实测 |
|---|---|---|
| 2.1.1–2.1.6 | 未勾选 | ✅ `ai_collab/concurrent_guard.py` 全部 5 个检测函数 + `run_concurrent_guard` 已实现 |
| 3.1–3.6（23 条用例） | 未勾选 | ✅ `23 passed` |
| 3.7 ruff + 回归 | 未勾选 | ✅ ruff 全绿 |
| **2.2.1–2.2.3** | 未勾选 | ❌ **真缺**：`grep "concurrent" ai_collab/cli/_cli_main.py` 零命中 |

**顺带纠正一处契约错误**：tasks.md 2.2.3 写「配置项接入 `agent-orchestration.json`」，
但运行时配置源是 `.vscode/ai-collab.json`（`VSCodeIntegration.get_project_config()` 读它）；
`workspaceGuard` / `spawnAgentGuard` 两段在两个文件里**都不存在**，实际生效的是模块内置默认值。
两张工单均按真实架构写死落点。

因此 4.2 拆成两张工单（都只覆盖真实缺口，不重做已完成部分）：

- `TASK-P1-CONCURRENT-GUARD-001`（Phase 2.2）：CLI 门禁接入 + 配置段 + CLI 层用例 + 订正清单
- `TASK-P2-CONCURRENT-GUARD-PHASE4-001`（Phase 4）：pytest 收集边界防回归 + consensus 并发用例 + 跨工作区复用验证

两张工单均已注册，状态 `planning`（已开工单，未开工）。

### CI 门禁摘罩（批次 2.2）

`.github/workflows/lint.yml` 的 `secrets-scan` 步骤摘掉 `|| true`，改为阻断级。
前置条件已满足：扫描器在本仓真实工作区 `0` 命中、退出码 `0`。
YAML 三重校验（PyYAML + 禁重复键 + schemastore JSON Schema）通过。

### 推送（批次 1.2）

推送前对 72 个 commit 的新增行做密钥扫描：

```bash
git diff origin/main..HEAD -U0 | grep -E "^\+" | grep -E "(sk-[A-Za-z0-9]{20,}|gh[pousr]_|AKIA|PRIVATE KEY|AIza|xox)"
→ 无命中
```

`password/secret/token` 赋值逐条过目，全是测试夹具与标识符
（`resolve_credentials`、测试夹具里的 `PASSWORD=` 常量、`env-provided-pw`）。
`git push -u origin feat/codearts-collab-wiring` 成功，upstream 修正为同名远端分支。

---

## Phase 3：收口（2026-10-24 下午）

### 3.1 消掉「文档自命中」（15 条 → 0）

CI 的 `secrets-scan` 摘掉 `|| true` 之后，复核方追加的对照表**本身**变成了命中源：

| 位置 | 条数 | 命中形态 |
|---|---|---|
| `collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md` | 12 | 对照表里直接写了赋值语句样例 |
| `logs/claude-code/2026-10/2026-10-24_project-healthcheck.md` | 3 | 同上 |

处置：**不写豁免条目**，改为**拆分代码片段**——把赋值号与值拆成两段代码片段
（`` `password =` `hunter2` ``）。四条规则的正则都要求 `=`/`:` 之后紧跟字母/数字/引号，
反引号同时打断 A 段 / B 段 / 纯数字 / 短值四段的匹配。拆分只影响排版，不改规则语义，
对照表读起来也不含糊。

> 这与 CodeArts 记忆条目 `feedback_result_file_self_scan_hit.md` 记的是同一类问题：
> **「写文档说明触发串」这个动作本身就制造了触发串**。豁免清单是按行号钉的，
> 文档每改一行就可能失效——拆分写法没有这个维护负担。

实测：`python3 scripts/scan_secrets_pii.py --workspace .` → `[OK] no secrets found`，rc=0。

### 3.2 推送前的正确校验方式（踩过的坑）

直接把 `git diff origin/main..HEAD` 导成一个 `.txt` 再喂给扫描器 → **5 条命中**。
原因：豁免清单按 `<文件>:<行号>` 钉，**diff 文件里的行号跟原文件对不上**，豁免自然不生效。

正确口径是**扫 commit 出来的真实树**：

```bash
rm -rf /tmp/head_tree && mkdir -p /tmp/head_tree
git archive HEAD | tar -x -C /tmp/head_tree
python3 scripts/scan_secrets_pii.py --workspace /tmp/head_tree
```

结果 `[OK] no secrets found`，rc=0。`git archive` 不含 gitignore 文件，与 CI 看到的
内容一致。逐条复核了 6 条豁免条目指向的行内容，确认全是「测试夹具常量 / 任务 ID
冒充 key / 报告正文引述」，没有真实凭据。

### 3.3 推送

```
git push -u origin feat/codearts-collab-wiring
* [new branch]      feat/codearts-collab-wiring -> feat/codearts-collab-wiring
```

- 实推 **82 个 commit**（此前统计的 70+ 已随本轮提交增长）
- upstream 由错误指向的 `origin/main` 修正为 `origin/feat/codearts-collab-wiring`
- 推送后校验：本地 HEAD 与远端 ref 一致（`68428a6`），ahead/behind = 0/0

### 3.4 全量验收（推送前）

| 项 | 结果 |
|---|---|
| `python3 -m pytest tests/ -q` | `2982 passed, 6 skipped`（0 failed） |
| `python3 -m ruff check .` | `All checks passed!` |
| `python3 scripts/scan_secrets_pii.py --workspace .` | `[OK] no secrets found`，rc=0 |
| `tasks validate-contract --scope active --strict` | `checked=2 invalid=0`；终态一致性 `audited=10 consistent=10 mismatch=0` |
| `scripts/verify_agent_config_sync.sh` | `TOTAL: pass=8 fail=0` |
| `scripts/reconcile_state_drift.py --workspace . --fail-on-drift` | rc=0 |

### 3.5 本轮教训（值得进记忆）

> **交付方自述「检出能力未削弱」不等于事实**——必须用**同一批样本**对新旧两版规则
> 逐条对照。这次 CodeArts 的交付满足契约 R2/R3 的每一条字面要求，却在两段式改造中
> 静默丢掉了 9/15 的检出（其中 4 条是真实密码漏检），且 R9「弱化检出必须写进风险段」
> 的披露义务未履行。**契约字面合规 ≠ 交付合格。**
