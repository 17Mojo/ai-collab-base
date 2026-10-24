---
task_id: TASK-P1-HEALTHCHECK-TOOL-HARDEN-001
change_id: bugfix/no-spec
status: planning
priority: P1
assignee: codearts_agent
assignee_role: AGENT_EXEC
reviewer: claude_code
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-24T10:45:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_scan_secrets_pii.py tests/unit/test_project_healthcheck.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 scripts/scan_secrets_pii.py --workspace ."
result_file: collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md
---

# TASK-P1-HEALTHCHECK-TOOL-HARDEN-001：体检工具链加固（密钥扫描器去噪 + 体检脚本两处假绿）

> **本工单由 Claude Code（AGENT_ARCH）定义契约，CodeArts（AGENT_EXEC）实现。**
> 契约已逐条写死语义，实现方**不需要再做需求判断**，照做即可。
> 复核方：Claude Code（AGENT_TEST）。
>
> **基线（Claude Code 侧已落地，不要重做、也不要回退）：**
> - commit `9b054c0` 已修 `scripts/project_healthcheck.py` 的 4 处失真
>   （`awk $5`→`$NF`、ruff scope `ai_collab`→`.`、显示阈值 `< 50`→`== 0`、
>   未跟踪统计排除自身产物）与 `.github/workflows/healthcheck.yml` 的
>   双引号 `if:` 修复。
> - commit `4af0efd` 已把 `ruff check .` 的 14 条清零，当前 `ruff check .`
>   是 **All checks passed**。你新增的代码**不得**引入新的 ruff 问题。

## 一、背景与真证

本轮做了一次全项目体检（结果见 `collaboration/results/RESULT-HEALTHCHECK-2026-10-24.md`）。
体检结论是：**项目代码本身健康**（2654 单测全绿、覆盖率 88%、mypy 0、治理门禁 8/8），
问题出在**体检工具链本身**。其中 4 处已由 Claude Code 修复，**本工单处理剩余 3 处**。

### 真证 1：密钥扫描器 100% 是噪声，CI 的 secrets-scan 形同虚设

```bash
$ python3 scripts/scan_secrets_pii.py --workspace .
[password_literal] chrome-extension/node_modules/@playwright/cli/node_modules/.../index-DFFMH0k4.js:49 - password:!0,range:!0,...
... 共 237 条 ...
[FAIL] 237 findings
rc=1
```

237 条命中**逐条判读后全是误报，零真实泄露**：

| 来源 | 条数 | 性质 |
|------|------|------|
| `chrome-extension/node_modules/**`、`tests/playwright/node_modules/**` | 205 | JS bundle 里的 `password:!0` 之类的压缩产物 |
| 源码里的变量名与函数签名 | 30 | `password = resolve_credentials(...)`、`password: str`、`password=None` |
| 测试夹具 | 1 | `tests/unit/test_codearts_bridge_deliver.py:923` 的 `PASSWORD=s3cret-password-value` |
| `logs/openspec_backup/.../tasks.md:16` | 1 | `sk-contract-migration-command` —— 任务 ID 冒充的 key |

三个叠加的根因：

1. **没有目录排除**。后缀白名单含 `.js`/`.ts`（`scan_secrets_pii.py:68`），
   于是 `node_modules` 里的 JS bundle 全被扫进来。
2. **占位符判定用错了对象**。`is_placeholder()`（`:37-39`）拿的是
   `match.group(0)`——**整段匹配文本**——而不是规则捕获到的**值**。
   于是 `password="pw"` 这种测试夹具因为整段里没有 `"pw"` 指示词而漏网。
3. **`password_literal` 规则过宽**（`:26`）。`password\s*[=:]\s*["\']?([^\s"\'<{]+)["\']?`
   把 `password = resolve_credentials(...)` 这类**标识符**也当成命中。

同时 CI 里这一步被 `|| true` 吞掉了（`.github/workflows/lint.yml:38`
`python scripts/scan_secrets_pii.py --workspace . || true`），所以噪声既没被
消除、也没被暴露——**门禁是假的**。

> **注意**：解除 `|| true` 由 Claude Code 在复核你的交付后执行，**不在你的范围内**
> （见 R6 禁止清单）。你只负责让扫描器本身输出干净。

### 真证 2：`check_git()` 在缺 `origin/main` 引用时静默判「✅ 已同步」

`scripts/project_healthcheck.py:89`（**已因基线 commit 上移，以下为改写后的行号，请按符号定位**）：

```python
rc, out, _ = run("git log --oneline origin/main..HEAD 2>/dev/null")
ahead = out.split("\n") if out and out.strip() else []
```

本地没有 `origin/main` 引用时，`git log` 报错被 `2>/dev/null` 吞掉、输出为空，
与「确实没有领先 commit」**不可区分**，于是 `render_markdown()` 会打印
「✅ 与 origin/main 同步」——**假绿灯**。本仓当前 `origin/main` 存在，
不影响本次结论，但这是个已确认的潜在入口。

### 真证 3：`check_health_rules()` 只查「长期经验」四字出现次数 ≥1

报告标题宣称的是「**CLAUDE.md 含 3 条长期经验**」，实际只做了
`grep -c '长期经验' CLAUDE.md`（只要出现 ≥1 次就判 ✅）。实测 CLAUDE.md
第 292 行的章节标题是：

```
## 从 2026-09-15 覆盖率任务提炼的 3 条长期经验
### 经验 1：改代码前先看测试在守护什么
### 经验 2：发现字段名错配 → 系统性排查，不要只修一处
### 经验 3：commit message 不撒谎，诚实标注限制
```

所以可以精确计数（实测为 **3**）：

```bash
$ grep -c '^### 经验 [0-9]' CLAUDE.md
3
```

## 二、目标

1. 密钥扫描器在本仓真实工作区上输出 **0 条误报**，同时**不降低**对真实密钥的检出能力。
2. `check_git()` 在无法计算领先量时**明确报「未知」**，不再输出假绿灯。
3. `check_health_rules()` 精确统计经验条数，报告口径与实际一致。
4. 三项改动都有单测守护。

## 三、详细契约（逐条实现，不要自行发挥）

### R1 `scripts/scan_secrets_pii.py`：目录排除

新增模块级常量：

```python
EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
```

在 `scan_workspace()` 的遍历循环里，**在读文件之前**跳过：

```python
for path in workspace.rglob("*"):
    if not path.is_file():
        continue
    if EXCLUDED_DIRS & set(path.parts):
        continue
    ...
```

> 用 `set(path.parts)` 判定，可同时覆盖 `a/node_modules/b` 这类嵌套路径。

### R2 `scripts/scan_secrets_pii.py`：`password_literal` 规则改两段式

把现有那一条 `password_literal` 拆成两条：

```python
{
    "rule_id": "password_literal",
    # A 段：引号字面量（高置信度）
    "pattern": re.compile(r'''(?i)password\s*[=:]\s*(["'])([^"'\n]{3,})\1'''),
    "placeholder_indicators": [
        "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
        "pw", "none", "secret", "test", "from-file", "env-provided",
        "resolve_credentials", "os.environ",
    ],
},
{
    "rule_id": "password_literal_bare",
    # B 段：裸值，仅当高熵（>=12 位、含数字且含字母）才算命中
    "pattern": re.compile(r'''(?i)password\s*[=:]\s*([A-Za-z0-9][A-Za-z0-9\-]{11,})'''),
    "placeholder_indicators": [
        "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
        "resolve_credentials", "os.environ",
    ],
},
```

**B 段的高熵判定**放在占位符判定**之后**，作为额外闸门：

```python
if rule["rule_id"] == "password_literal_bare":
    if not (any(ch.isdigit() for ch in value) and any(ch.isalpha() for ch in value)):
        continue
```

> 这样 `password = resolve_credentials(...)`（含下划线与括号，本就不匹配 B 段
> 正则）与 `PASSWORD=env-provided-pw`（含指示词）都不会命中。

### R3 `scripts/scan_secrets_pii.py`：占位符判定改用「捕获到的值」

`is_placeholder()` 的入参改为规则**捕获到的值**，而不是整段匹配文本：

```python
# 判定用捕获组：优先取最后一个捕获组（值），无捕获组时退回 group(0)
value = match.group(match.lastindex) if match.lastindex else match.group(0)
if is_placeholder(value, rule["placeholder_indicators"]):
    continue
```

> 现有的 `openai_api_key` / `google_api_key` / `github_token` / `us_ssn` 四条规则
> 都没有捕获组，`match.lastindex` 为 `None`，会退回 `group(0)`，行为不变。

### R4 `scripts/scan_secrets_pii.py`：白名单文件机制

新增白名单文件 `config/secrets-scan-allowlist.txt`（**新建**），
每行一条豁免，格式为 `<文件相对路径>:<行号>:<豁免原因>`，`#` 开头为注释：

```
# 密钥扫描豁免清单
# 格式: <文件相对路径>:<行号>:<原因>
tests/unit/test_codearts_bridge_deliver.py:923:测试夹具常量，非真实凭据
```

在 `scan_workspace()` 里，命中后**先查白名单**再决定是否记为 finding：

```python
allow = _load_allowlist(workspace)
...
key = f"{rel_path}:{line_num}"
if key in allow:
    continue
```

`_load_allowlist()` 的实现要求：

- 白名单文件不存在时返回空集合（**不报错**），保证脚本在没有该文件的
  环境（以及既有单测的 `tmp_path`）里仍可运行。
- 文件不存在 / 读失败 → 返回空集合。
- 路径相对于 workspace 根（即与 finding 里的 `file` 字段同一基准）。
- 原因字段只用于**给人看**，脚本不校验其内容。

### R5 `scripts/project_healthcheck.py`：`check_git()` 补 origin/main 存在性判断

在 `check_git()` 里，`git log origin/main..HEAD` **之前**加：

```python
rc, out, _ = run("git rev-parse --verify origin/main 2>/dev/null")
has_origin_main = rc == 0 and bool(out)
```

并在返回的 dict 里加上 `"has_origin_main": has_origin_main`。

`render_markdown()` 里把 Git 状态那段的三分支改成：

```python
if g["ahead_of_origin"]:
    lines.append(f"- ⚠️ **领先 origin/main {len(g['ahead_of_origin'])} 个 commit** (未推送)")
elif g.get("has_origin_main"):
    lines.append("- ✅ 与 origin/main 同步")
else:
    lines.append("- ⚠️ **未知**（本地无 origin/main 引用，无法计算领先量）")
```

### R6 `scripts/project_healthcheck.py`：`check_health_rules()` 精确计数

`check_health_rules()` 里把「长期经验」的判定从字样出现改为**条数**统计：

```python
rc, out, _ = run("grep -c '^### 经验 [0-9]' CLAUDE.md 2>/dev/null || echo 0")
try:
    rules_count = int(out) if out.strip().isdigit() else 0
except ValueError:
    rules_count = 0
```

返回 dict 增加 `"claude_md_rules_count": rules_count`，
`claude_md_has_rules` 改为 `rules_count >= 3`。

`render_markdown()` 里那一行改为显示**实际条数**：

```python
lines.append(f"- **CLAUDE.md 含 {h.get('claude_md_rules_count', 0)} 条长期经验**: "
             f"{'✅' if h['claude_md_has_rules'] else '🔴'}")
```

> 判定门槛保持 `>= 3`（与 CLAUDE.md 实际条目数一致），不要改成 `> 0`。

### R7 测试（新建或扩展）

1. **新建** `tests/unit/test_project_healthcheck.py`，至少覆盖：
   - `check_git()` 在无 `origin/main` 引用时 `has_origin_main` 为 False、
     且 `render_markdown()` 输出的是「未知」而不是「✅ 与 origin/main 同步」；
   - `check_health_rules()` 统计出的条数与 `grep -c '^### 经验 [0-9]' CLAUDE.md` 一致；
   - `check_coverage_breakdown()` 在构造的 `coverage report` 输出（4 列）下
     能正确取出低覆盖模块（**防回归**：守 `$NF` 不是 `$5`）。
2. **扩展** `tests/unit/test_scan_secrets_pii.py`，至少覆盖：
   - `node_modules` 下的文件被跳过（构造 `tmp_path/node_modules/x.js` 写入假密钥，
     断言 `has_findings` 为 False）；
   - 引号字面量 `password="pw"` 这类测试夹具不算命中；
   - 白名单条目生效（构造白名单文件，断言对应 finding 被豁免）；
   - **既有 3 条用例必须继续通过**（真实密钥仍被检出、占位符仍被忽略、SSN 仍被检出）。

> 构造 `coverage report` 输出时注意：**它只有 4 列**
> （`Name Stmts Miss Cover`），这正是原 bug 的成因。

### R8 范围限制（硬约束）

| 允许修改 | 禁止修改 |
|---------|---------|
| `scripts/scan_secrets_pii.py` | `.github/workflows/lint.yml`（解除 `\|\| true` 由 Claude Code 做） |
| `scripts/project_healthcheck.py` | `.github/workflows/healthcheck.yml`（本轮已修好，勿动） |
| `tests/unit/test_scan_secrets_pii.py` | `ai_collab/` 下任何文件 |
| `tests/unit/test_project_healthcheck.py`（新建） | `scripts/sync_agent_memory.py`、`scripts/codearts_bridge_deliver.py` |
| `config/secrets-scan-allowlist.txt`（新建） | `config/agent-orchestration.json` 及其 schema/template |
| `collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md`（新建） | `collaboration/tasks/` 下任何已有工单 |
| | `memory/` 下任何文件（只读镜像，由 `scripts/sync_agent_memory.py` 从 CodeArts 源生成） |
| | `logs/` 下任何文件 |
| | `pyproject.toml`、`requirements.txt` |

### R9 文档与口径

- 结果文件必须写清「改造前后命中条数对比」和**白名单里每一条豁免的理由**。
- 若你在实现中偏离了本契约的任一条，**必须在结果文件的「风险」段写明偏离点与理由**，
  不要静默改动语义。
- 报告口径：改造后的扫描器是**降低误报**，不是**降低检出能力**。
  如果你为了降噪削弱了某条规则的检出能力，必须在「风险」段明确写出——
  这是本工单最需要被复核的一点。

## 四、验收标准

- [ ] `python3 -m pytest tests/unit/test_scan_secrets_pii.py tests/unit/test_project_healthcheck.py -q` 全绿
- [ ] `python3 -m pytest tests/ -q` 全绿（全仓不得有回归）
- [ ] `python3 -m ruff check .` → `All checks passed!`（**零新增**）
- [ ] `python3 scripts/scan_secrets_pii.py --workspace .` → 输出 `[OK] no secrets found`，退出码 0
- [ ] `git diff --name-only` **不含** R8 禁止清单里的任何文件
- [ ] 结果文件含「执行命令 / 验证结果 / 测试结论 / 风险 / 回滚」各段
      （缺任一段，`tasks validate-contract` 会判失败）
- [ ] 结果文件头部的 `- **状态**: completed` 在**前 40 行内**

## 五、完成后回复（ACK）

**ACK 必须由 CLI 生成，禁止手写**（手写 ACK 会被回执桥接判为「非显式 ACK」而拒绝收口）：

```bash
python3 -m ai_collab.cli ack \
  --task-id TASK-P1-HEALTHCHECK-TOOL-HARDEN-001 \
  --status ok \
  --result-file collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md
```

把该命令**原样输出**的一行回复回来（形如
`A.ACK|task=TASK-P1-HEALTHCHECK-TOOL-HARDEN-001|status=ok|result=collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md`）。

## 六、执行注意

- **写文件请用 bash heredoc**（`cat > 文件 <<'EOF' ... EOF`）。本会话的
  `write`/`edit` 工具在 CodeArts 侧会卡死并中止会话，不要尝试。
- **不要派生子代理**，本工单不需要。
- 修改 `scripts/project_healthcheck.py` 时注意：基线 commit `9b054c0` 已经改过
  这个文件（`awk $5`→`$NF`、ruff scope、显示阈值、未跟踪统计排除自身产物），
  **那些改动是基线，不要回退**；你只加 R5/R6 两处。

## 七、参考

- 本轮体检全量结论：`collaboration/results/RESULT-HEALTHCHECK-2026-10-24.md`
- 体检脚本：`scripts/project_healthcheck.py`
- 密钥扫描器：`scripts/scan_secrets_pii.py`
- 既有守护用例：`tests/unit/test_scan_secrets_pii.py`
- 协议：`collaboration/PROTOCOL.md`（§7.3 收口要求）
