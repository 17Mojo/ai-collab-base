# RESULT-HEALTHCHECK-2026-10-24：项目体检——修复体检工具链失真 + 全量指标复核

- **状态**: completed
- **任务 ID**: 无对应工单（用户于 2026-10-24 直接发起「进行项目体检」）
- **change_id**: bugfix/no-spec
- **角色**: AGENT_EXEC（claude_code）
- **复核方**: AGENT_TEST（claude_code 自检 + GitHub REST API 实测取证）
- **完成时间**: 2026-10-24T10:13+08:00
- **基线 commit**: `5c33107`（分支 `feat/codearts-collab-wiring`）

## 执行命令

```bash
# 1. 测试与覆盖率（真机实跑）
python3 -m pytest tests/unit -q --no-header -p no:warnings
python3 -m pytest tests/integration -q --no-header -p no:warnings
python3 -m coverage report | grep -E '^TOTAL'

# 2. 静态检查（按 CI 的两个 scope 分别实测）
python3 -m ruff check ai_collab
python3 -m ruff check ai_collab/ scripts/
python3 -m ruff check .
python3 -m mypy ai_collab

# 3. 治理 / 记忆同步 / 状态漂移
sh scripts/verify_agent_config_sync.sh
python3 scripts/reconcile_state_drift.py --workspace .
python3 scripts/validate_collaboration_governance.py --workspace .

# 4. 密钥扫描
python3 scripts/scan_secrets_pii.py --workspace .

# 5. CI 侧取证（GitHub REST API）
gh api repos/17Mojo/ai-collab-base/actions/workflows
gh api "repos/17Mojo/ai-collab-base/actions/workflows/healthcheck.yml/runs?per_page=100"
gh api repos/17Mojo/ai-collab-base/actions/runs/39755237465
gh api repos/17Mojo/ai-collab-base/check-suites/107741311102
curl -sS https://github.com/17Mojo/ai-collab-base/actions/runs/39755237465   # 取 GitHub 原始报错

# 6. 体检脚本自证（修复后重跑）
python3 scripts/project_healthcheck.py
python3 scripts/project_healthcheck.py   # 连跑两次验证评分幂等
```

### 实施摘要

本轮体检的核心结论是：**项目本身的代码质量是健康的，但「体检工具本身」存在 4 处系统性失真，其中 2 处会直接产出假绿灯。** 已修复的 4 处全部落在工具链（`scripts/project_healthcheck.py` + `.github/workflows/healthcheck.yml`），未触碰 `ai_collab/` 生产代码。

| # | 缺陷 | 失真表现 | 修复 |
|---|------|---------|------|
| 1 | `coverage report` 是 4 列，脚本用 `awk '{print $1, $5}'` 取第 5 列 | `$5` 恒为空 → 低覆盖模块列表**恒为空** → 报告永远打印「✅ 所有模块覆盖率 ≥ 80%」，实际有 8 个模块低于 80% | 改用 `awk '{print $1, $NF}'` |
| 2 | ruff 检查范围 `ruff check ai_collab` 比 CI 窄 | 报告「ruff: 0 个问题 ✅」，而 CI 的 `ruff check .` 实为 **14 个问题**（阻断级） | scope 改为 `ruff check .`，并把显示阈值从 `< 50` 收紧为 `== 0` |
| 3 | `.github/workflows/healthcheck.yml` 的 `if:` 用双引号字符串字面量 | **GitHub 表达式解析器拒绝该文件**，workflow 自 2026-09-15 起从未跑成功过（30/30 run 失败、0 job） | 双引号改单引号，与仓库内已验证可用的 `test.yml:66` 写法一致 |
| 4 | 脚本把**自己的输出文件**计入未跟踪文件 | 同日第二次运行必然比第一次少 20 分（85 → 65），同一份代码两个分数 | 未跟踪统计排除 `collaboration/results/HEALTH_CHECK_*` |

附带修复：`fail-on-low-score` job 缺 `actions/checkout` 与 artifact 下载，`health_output.md` 永远不存在，`[ "" -lt 60 ]` 会让该 job 恒定失败；已补 `actions/download-artifact@v4` 并加空值守卫。

### 后续批次（用户 2026-10-24 决策后追加执行）

| 批次 | 内容 | 状态 |
|------|------|------|
| 1.1 | `ruff check .` 的 14 条 → 0（含 `scripts/sync_agent_memory.py` 的 9 条；用户已把该文件的执行权交回 Claude Code） | ✅ commit `4af0efd` |
| 2.1 / 5.1 / 5.2 | 密钥扫描器去噪 + `check_git()` origin/main 存在性 + `check_health_rules()` 精确计数 | 🔄 已派单 CodeArts（`TASK-P1-HEALTHCHECK-TOOL-HARDEN-001`） |
| 1.2 | 推送 70+ 个未推送 commit 并修正 upstream | ⏳ 待执行 |
| 4.2 | `add-concurrent-workspace-guard` Phase 2+3 与 Phase 4 分别开工单 | ⏳ 待执行 |
| 2.2 | 解除 `lint.yml:38` 的 `\|\| true` | ⏳ 待 CodeArts 交付并复核后再做 |

## 验证结果

### 1. 缺陷 3 根因：GitHub 侧原始报错（实测抓取）

```
Invalid workflow file: .github/workflows/healthcheck.yml#L1
(Line: 55, Col: 13): Unexpected symbol: '"pull_request"'.
  Located at position 22 within expression: github.event_name == "pull_request",
(Line: 69, Col: 9):  Unexpected symbol: '"pull_request"'.
  Located at position 22 within expression: github.event_name == "pull_request"
```

位置 22 正是双引号字符串字面量的起始处。旁证链：

| 证据 | 结论 |
|------|------|
| 同仓 `test.yml:66` 用单引号 `if: matrix.python-version == '3.12'` → 该 workflow 在 CI 正常跑通 | 单引号写法在本仓库已被 GitHub 接受 |
| 该文件通过 PyYAML + ruamel YAML 1.2 strict + 禁重复键 + schemastore `github-workflow.json` 全套本地校验 | **不是 YAML 问题**，是表达式解析层 |
| GitHub 注册的 workflow `name` 回落成路径 `.github/workflows/healthcheck.yml` | GitHub 没能读到文件里的 `name:` 键 |
| 全部 30 个 run 的 `event` 均为 `push`，但文件里**没有** `push` 触发器 | GitHub 完全没采用文件里的 `on:` 块 |
| run 恒为 `failure` + `0s` + `total_count: 0` jobs；check suite `latest_check_runs_count: 0` | 0-job 合成失败 run = 文件级无效的标准签名 |
| workflow `updated_at` 停在 2026-09-15T19:25:41，此后未再刷新 | GitHub 从未成功解析过该文件 |
| 文件与 GitHub 副本字节一致（2272B，sha256 前缀 `24f734bb`），无 BOM / CRLF / TAB / 控制字符 / 异体引号 | 排除传输与编码损坏 |

修复后本地复核：PyYAML（含禁重复键）+ ruamel YAML 1.2 strict + schemastore JSON Schema 三项全过，`on` 键在 YAML 1.2 下确为字符串 `"on"`；全仓已无双引号 `if:` 残留。

### 2. 缺陷 1 修复前后对比（同一份 `.coverage` 数据）

修复前 `awk '{print $1, $5}'` 的实际输出经 `split()` 后**每个元素只有 1 个字段**，故 `len(parts) == 2` 恒不成立，低覆盖列表恒为空。修复后真实结果：

| 模块 | 覆盖率 |
|------|--------|
| `ai_collab/codex_integration.py` | 41% |
| `ai_collab/missing_ack_monitor.py` | 65% |
| `ai_collab/prompt_pack/sharing.py` | 65% |
| `ai_collab/integrations/dispatch_notebooklm.py` | 67% |
| `ai_collab/orchestration.py` | 68% |
| `ai_collab/activation_handler.py` | 69% |
| `ai_collab/integrations/vscode.py` | 73% |
| `ai_collab/context/graph.py` | 78% |

### 3. 缺陷 4 修复前后评分对比（同一工作区、同一份代码）

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 当日首次运行 | 85/100 (A) | 85/100 (A) |
| 当日第二次运行 | 65/100 (C) | 85/100 (A) ✅ |

修复前第二次运行掉 20 分的唯一原因是脚本把自己当天/前次的输出算成未跟踪文件，评分与代码状态脱钩。
修复后评分的唯一输入变成**工作区状态本身**，不再受「工具当天是否已经跑过」影响——同一工作区状态下
连跑两次，评分与内容完全一致（幂等），已实测。

当前工作区再次运行得到 **65/100 (C)**，这不是回归，而是评分如实反映了两个**真实**条件：
本 RESULT 交付文件尚未入库（-20）、分支领先 `origin/main` 未推送（-15）。
待该文件入库后评分回到 85/100 (A)。

### 4. 项目真实健康指标（全部实测）

| 维度 | 实测值 | 判定 |
|------|--------|------|
| 单元测试 | 2654 passed / 0 failed / 1 skipped（30.68s） | ✅ |
| 集成测试 | 219 passed / 0 failed / 5 skipped（跳过原因：本地 8000 端口后端未启动） | ✅ |
| 覆盖率 TOTAL | 15264 stmts / 1796 miss / **88%** | ✅ 过 CI 的 ≥85% 门禁 |
| 低于 80% 的模块 | **8 个**（最差 `codex_integration.py` 41%） | ⚠️ 已被修复后的体检脚本正确暴露 |
| `ruff check ai_collab` | 0 | ✅ |
| `mypy ai_collab` | 0 | ✅ |
| `ruff check .`（CI lint.yml 口径） | **0**（修复后） | ✅ 修复前 14 条已由 commit `4af0efd` 清零 |
| `ruff check ai_collab/ scripts/`（CI test.yml 口径） | 0（修复后） | ✅ 同上 |
| 治理门禁 `verify_agent_config_sync.sh` | V1–V7 全 PASS，TOTAL pass=8 fail=0 | ✅ |
| 状态漂移 `reconcile_state_drift.py` | rc=0，无漂移 | ✅ |
| 密钥扫描 | 237 条命中，逐条判读**全为误报**，零真实泄露 | ⚠️ 噪声见风险项 |
| 测试/代码比 | 1.21 | ✅ |

`ruff` 14 个问题的构成：`scripts/sync_agent_memory.py` 9（UP032 ×8 + W292）、`scripts/codearts_bridge_deliver.py` 1（UP012）、`tests/unit/test_role_prefix.py` 2（F401 + W292）、`tests/unit/test_sync_agent_memory.py` 2（UP032 + W292），全部可 `ruff check . --fix` 自动修复。

**已于 commit `4af0efd` 全部修复**：用户于 2026-10-24 明确把 `scripts/sync_agent_memory.py`
的修改执行权交回 Claude Code（原顾虑是共享工作区下的并发写冲突，属跨 Agent 改同一文件的
风险，已由用户裁决解除）。修复方式为 `ruff check . --fix`，**零手工改写业务逻辑**；其中
`sync_agent_memory.py` 的 9 条全为 f-string 格式化偏好（UP032）与文件末尾换行（W292），
`test_role_prefix.py` 的 F401 是未使用的 import。修复后复验：

| 验证项 | 结果 |
|--------|------|
| `python3 -m ruff check .` | `All checks passed!` |
| `python3 -m pytest tests/unit -q` | 2654 passed / 1 skipped / 0 failed |
| `sh scripts/verify_agent_config_sync.sh` | TOTAL pass=8 fail=0 |
| `python3 scripts/sync_agent_memory.py --check` | 镜像仍与 CodeArts 源一致（证明 f-string 改写未改变输出字节） |

> 修复后 `memory/.sync-manifest.json` 被 `verify_agent_config_sync.sh` 的 V3 漂移检测改写，
> 已 `git checkout` 还原——该文件受 `.sync-manifest.json` 托管，不应由验证脚本改动。

### 5. Git 状态

- 本地分支 `feat/codearts-collab-wiring` 领先 `origin/main` **72 个 commit**，全部未推送。
- 远端 `main` 当前在 `c06584a9`；远端另有 `ci/security-and-nightly-2026-09`、`refactor/slimming-2026-09-20` 两个分支，**均不含本地 HEAD**。
- 当前分支 upstream 被配成 `origin/main`，与分支名不符，`git push` 直接报错：
  `fatal: The upstream branch of your current branch does not match the name of your current branch.`

### 测试结论

**通过。** 本轮全部改动为 CI 配置与体检脚本的行为修正，不触及 `ai_collab/` 生产代码路径。

- 回归：`python3 -m pytest tests/unit -q` → **2654 passed, 1 skipped, 0 failed**（改动后复跑，全绿）
- 集成：`python3 -m pytest tests/integration -q` → **219 passed, 5 skipped, 0 failed**（5 条跳过均为本地后端未启动）
- 静态：改动文件 `python3 -m ruff check scripts/project_healthcheck.py` → All checks passed；全仓 `python3 -m ruff check .` → All checks passed（14 条已清零）
- YAML：改动 workflow 通过 PyYAML + ruamel YAML 1.2 strict + schemastore JSON Schema 三项校验
- 体检脚本：修复后连跑两次，评分与内容一致（幂等），覆盖率分解列出 8 个低覆盖模块，ruff 显示 14 个问题且标 🔴
- 治理：`sh scripts/verify_agent_config_sync.sh` → TOTAL pass=8 fail=0；`reconcile_state_drift.py --workspace .` → rc=0

**未覆盖项**：`healthcheck.yml` 的实际运行结果无法在本地验证——workflow 文件要经 GitHub 服务端解析后才会生效，需推送后由 GitHub Actions 实跑确认首个非 0-job run。

## 风险

| 级别 | 事项 | 说明 |
|------|------|------|
| 高 | ~~`ruff check .` 14 个问题会让本分支的 PR 变红~~ | ✅ **已解决**：commit `4af0efd` 用 `ruff check . --fix` 清零，改动前后单测全绿、记忆同步校验 8/8 通过 |
| 高 | 72 个 commit 未推送，且 upstream 配错 | 任何远端协作方看不到这 72 个 commit；`git push` 需显式 `git push -u origin feat/codearts-collab-wiring` |
| 中 | 8 个模块覆盖率低于 80% | 最低 `codex_integration.py` 41%。覆盖率**门禁**（TOTAL ≥85%）是通过的，缺口在模块粒度，不阻断 CI |
| 中 | 密钥扫描器无排除机制 | `scripts/scan_secrets_pii.py` 8 条规则全量扫 `chrome-extension/node_modules/**` 与 `tests/playwright/node_modules/**`，237 条命中中 205 条来自 node_modules、31 条来自源码变量名与测试夹具（`password="pw"` 等）、1 条为任务 ID 冒充的 key（`sk-contract-migration-command`）。**无真实泄露**，但 CI 的 `secrets-scan` 步骤目前被 `|| true` 掩盖，等于形同虚设。建议补 node_modules 排除 |
| 中 | `openspec/AGENTS.md` 与 `openspec/specs/` 不存在 | `CLAUDE.md` 顶部强制要求「Always open `@/openspec/AGENTS.md`」，但该文件缺失；`openspec/` 下实际只有 `changes/add-concurrent-workspace-guard/`。根 `AGENTS.md` 存在（治理门禁 V1/V5 通过） |
| 中 | `add-concurrent-workspace-guard` 只有 Phase 1 落地 | Phase 2–4 全部未开工，且 `collaboration/tasks/` 下无对应工单，与「无工单不得开工」的流程约定存在缺口 |
| 低 | `pip-audit` 本地未安装 | 体检报告显示 `skipped`。依赖审计在 CI `security.yml` 中正常执行，但该步骤带 `continue-on-error: true`，失败不阻断 |
| 低 | `check_health_rules()` 只校验 CLAUDE.md 中「长期经验」字样出现 ≥1 次 | 与报告标题宣称的「含 3 条长期经验」不等价，属弱校验，本轮未改 |
| 低 | `check_git()` 在本地缺少 `origin/main` 引用时会静默判为「✅ 与 origin/main 同步」 | 假绿灯的潜在入口，本轮未改（本仓库当前 `origin/main` 存在，不影响本次结论） |

## 回滚

本轮改动集中在 2 个文件，可用单条命令整体回滚：

```bash
git checkout -- .github/workflows/healthcheck.yml scripts/project_healthcheck.py
```

分项回滚：

| 变更 | 回滚方式 |
|------|---------|
| workflow `if:` 双引号→单引号 | `sed -i '' "s/== 'pull_request'/== \"pull_request\"/" .github/workflows/healthcheck.yml`（仅两处） |
| workflow `fail-on-low-score` 补 artifact 下载 + 空值守卫 | 删除 `Download health report` step 与 `if [ -z "$SCORE" ]` 分支 |
| `awk '{print $1, $5}'` → `'{print $1, $NF}'` | `sed -i '' "s/{print \\\$1, \\\$NF}/{print \\\$1, \\\$5}/" scripts/project_healthcheck.py` |
| ruff scope `ai_collab` → `.` | `sed -i '' 's/ruff check \./ruff check ai_collab/' scripts/project_healthcheck.py` |
| ruff/mypy 显示阈值 `< 50` → `== 0` | `sed -i '' "s/== 0 else '🔴'/< 50 else '⚠️'/g" scripts/project_healthcheck.py` |
| 未跟踪统计排除自身产物 | 恢复 `check_git()` 中 `untracked` 的原始单行列表推导式 |

回滚后体检脚本会恢复「假绿灯」行为（恒报「所有模块 ≥ 80%」、ruff 恒报 0），故不建议整体回滚。

**已提交的 commit**：
- `9b054c0` fix(healthcheck): 修复体检工具链 4 处系统性失真，报告不再产出假绿灯
- `4af0efd` style(ruff): 清零 ruff check . 的 14 条，使本分支 PR 不再撞红 lint.yml

**待推送**：本分支领先 `origin/main` **72 个 commit**，全部未推送；upstream 被错配为 `origin/main`，
需 `git push -u origin feat/codearts-collab-wiring`（属用户已批准的批次 1.2）。
