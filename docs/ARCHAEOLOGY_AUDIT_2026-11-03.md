# AI Collab Base — 代码考古（2026-11-03 对账版）

> 对账对象：`docs/ARCHAEOLOGY_CODE_INVENTORY.md`（992 行，初版 2026-05-18/19）
> 对账基准：磁盘真值 + `git log`，HEAD = `932f7cf`（`fix/global-state-reclaim`）
> 方法：旧文档每条断言回源验证，不采信任何自述。修正处标 🔧。
>
> **2026-11-03 08:39 追加校验（见 §9）**：已在 `main`（`d7938ef`）上复跑全部静态校验，并用 Playwright 真机加载扩展做了端到端验证。§4.1 的根因判断据此**推翻重写**（🔧），§4.2 与 README 加载指引问题获得真机证据。

---

## 0. 一句话结论

仓库已完成从「Python 单栈」到「双栈 + 治理层」的转向，但 **Python 校验层与 Chrome 执行层用的是两套互不相交的步骤类型协议**（交集只剩 `local`）——16 个官方示例包 **0 个能过项目自己的校验器**（`main` 上 17 个仍 0 个通过），13 个在 Chrome 扩展侧执行到一半抛 `Unknown step type`。旧考古文档约 1/3 内容已随 `src/` 删除与 `chrome-extension` 重构而失效。

**另一条独立的 P0**：`README.md:105` 教用户加载 `chrome-extension/` 源码目录，真机实测 content script **零注入**（`Cannot use import statement outside a module`），须加载 `dist/`。外部用户照 README 走会在第一步得到「装好了但什么都不发生」。

---

## 1. 时间线考古

### 1.1 三段式节奏

| 阶段 | 区间 | 提交数 | 主导事项 |
|---|---|---|---|
| 奠基 | 2026-05 | 8 | Prompt Pack v2.0 骨架、动态角色编排 v3.0 |
| **空白** | 2026-06 ~ 2026-08 | **0** | 无提交（三个月静默） |
| 爆发 | 2026-09 | 84 | 死代码清理、覆盖率攻坚、CI 体系、Vite 化 |
| 爆发 | 2026-10 | 133 | 派单链路、真机回归、治理门禁、全局状态回收 |

总提交 225，首次提交 `e76d7ee` 2026-05-11，末次 `932f7cf` 2026-10-26。
`main` 已到 2026-10-27（`d7938ef`），**工作区落后 26 个提交**（见 §4.6）。

### 1.2 关键转折提交

| 日期 | 提交 | 事件 | 影响 |
|---|---|---|---|
| 05-11 | `e76d7ee` | Initial commit | packs 与 validator 同批诞生，此后命运分岔 |
| 09-15 | `7d2cc9d` | 死代码清理 -4836 行 + 4 bug + 81 测试 | CHANGELOG 记录的主要质量事件 |
| 09-15 | `51b5b07` | 覆盖率靠 omit 提到 86% | 口径问题：omit 抬数字，非真覆盖 |
| 09-19 | `a39a76a` | ruff pyupgrade 全仓 | 引入 PEP604 注解，版本声明自此失真（§4.4） |
| **09-20** | **`6030087`** | **删除 `src/`（3,564 行）** | **旧考古文档 1.2 / 8.8 / 8.12 三节当场作废** |
| 09-20 | `9e0c8b7` | 归档 36 个一次性调试脚本（4,643 行） | chrome-extension 已完成 Vite 重构 |
| 10-25 | `71c9eac` | 修真机适配器选择器漂移 | 首次让「能检测漂移」具备资格 |
| 10-25 | `061cc8b` | Pack 执行链路接通（5 处断点） | 修了「看不到 Pack」，**未修 step type**（§4.2） |

### 1.3 作者分布（值得记一笔）

```
214  AI-Collab Auditor   ← 95.1%
 30  17Mojo
 22  Raymondna
 14  ai-collab
  1  Trae AI
```

**这个仓库本质上是 AI 自提交的仓库。** 治理文档的可信度因此不能按「人类工程团队惯例」推定，只能逐条实测——这正是本对账的意义。

---

## 2. 当前真实结构

### 2.1 代码规模（vs 旧文档）

| 指标 | 旧文档（2026-05） | 现值（2026-11-03） | 变化 |
|---|---|---|---|
| Python 文件 | ~336 | **314** | -22 |
| Python 总行 | ~117,939 | **117,509** | -430 |
| `ai_collab/` | 113 文件 | **100 文件 / 42,747 行** | -13 |
| `src/` | 58 文件 | **0 文件**（仅 6 个 .pyc + egg-info） | 🔧 **全灭** |
| JS 文件（去 node_modules） | ~70 | **84** | +14 |
| 最大 Python 文件 | `_cli_main.py` 5,026 行 | **5,776 行** | +750 |

### 2.2 四层结构

```
chrome-extension/    84 JS   Vite 工程（src/background, src/platforms, src/content, src/utils）
ai_collab/          100 py   核心库：engines / pack / context / integrations / cli / hooks
local-backend/       28 py   FastAPI + SQLite
tests/              169 py   单元 / 集成 / e2e / playwright
── 治理层 ──
memory/              34 md   共享记忆镜像（CodeArts 单向同步）
collaboration/       18 tasks + 26 results
docs/                11 md   REAL_MACHINE_REGRESSION / FACTS / 本文件
```

### 2.3 双源码目录已终结

🔧 **旧文档 1.2 节整节作废。** 原文称「`ai_collab/`(113) 与 `src/ai_collab/`(58) 并存，`orchestration.py` 仅存于 `src/`」。

现状：
- `src/` 下 **0 个 .py**，只剩 `__pycache__/`（6 个 .pyc）与 `ai_collab_system.egg-info/`（5 个元数据）
- `ai_collab/orchestration.py` **存在**，874 行 / 34KB
- 删除提交：`6030087 chore: remove dead src/ directory (3,564 lines)`

旧文档 8.12 节那份「58 个文件逐一名录」现在指向一个不存在的目录。

---

## 3. 旧考古文档逐条对账

| # | 旧断言 | 现值 | 判定 |
|---|---|---|---|
| 1.2 | `src/` 与 `ai_collab/` 双源码并存 | `src/` 已无源码 | 🔧 作废 |
| 1.3 | Python ~336 文件 / 117,939 行 | 314 / 117,509 | 🔧 过期 |
| 2.x | `chrome-extension/background/` | `chrome-extension/src/background/` | 🔧 路径全废 |
| 8.1 | Chrome 侧只实现 local/ai，schema 定义 6 种 | **成立，且已量化：13/16 示例包受影响** | ✅ 成立（加强） |
| 8.2 | Soul Engine 双数据源（`style_db.py`） | `ai_collab/engines/style_db.py` **不存在** | 🔧 作废 |
| 8.3 | CLI 有 `input()` 会 hang | `orchestration.py` 仍有 6 处 `input()` | ✅ 成立 |
| 8.9 | `email-auto-reply.json` / `email_auto_reply.json` 重复 | 只剩 1 个 | 🔧 已修 |
| 8.10 | `ai_collab/cli_commands/` 是 `cli/` 子集 | 目录已删（09-15） | 🔧 作废 |
| 8.12 | `src/ai_collab/` 58 文件清单 | 目录不存在 | 🔧 作废 |

**统计：8 条抽样断言中，2 条仍成立、6 条已失效。** 失效主因是两份文档各自跟随不同的演进节奏。

---

## 4. 硬缺陷（全部有实测证据）

### 4.1 【P0】官方示例包 0/16 过不了自己的校验器

实测（`ai_collab.pack.schema_validator.validate_pack`，strict=True/False 结果一致）：

```
总计 16   通过 0   失败 16
```

错误分两类：

| 错误族 | 典型信息 | 涉及 |
|---|---|---|
| 顶层字段缺失 | `Missing required field: generation_params / optimization / example_library` | 8 个包 |
| 质量指标结构不符 | `$.quality_metrics.metrics.<x>.name: Missing required metric field: name` | 12 个包 |

**根因 🔧 已推翻重写（2026-11-03 08:45，见 §9.3）。**

原判断是「validator 收紧了，样本没跟上」。实测证明这只是一半——真正的根因是**三套步骤类型协议互不相交**：

```
Python Enum / 校验器白名单 : local analysis generation validation fusion tracking  (6 种，无 ai)
Chrome 执行器              : local ai                                             (2 种，无 analysis 等)
                             ↑
                    交集只有 {local}
```

`external-user-smoke.json`（专为外部用户做的那份）报错是 `Invalid step type: ai`——**它不是漏填字段，是被校验器拒了一个 Chrome 唯一能用的类型**。演进时序只是表象：

```
validator → 553188d → 76a20e5 → 001c7b4 → 0e1f257   （4 次收紧）
packs/    → 88cd0eb（仅 1 次 cleanup）              （0 次回灌）
```

真正的问题是：**Schema 层与 Chrome 执行层从未对齐过协议**，样本只是这个裂缝最显眼的落点。

### 4.2 【P0】16 个示例包中 13 个在 Chrome 侧不可执行

Chrome 执行器 `pack-executor.js:476` 与 `:520` 两处 switch 只有两个分支：

```js
switch (step.type) {
  case "local": ...
  case "ai":    ...
  default: throw new Error(`Unknown step type: ${step.type}`);
}
```

而 `schema_v2.py:31` 定义 6 种：LOCAL / ANALYSIS / GENERATION / VALIDATION / FUSION / TRACKING。

实测 `workflow.steps[].type` 分布：

```
local 21 | generation 17 | ai 12 | analysis 11 | fusion 8 | validation 7 | tracking 6
```

**13/16 个包含 ≥1 个 Chrome 不认识的 type**，最重的 `travel_planner_north_guide.json` 8 步里 7 步不可执行。
`main` 上的 `061cc8b` 修了 5 处断点（`pack.id`、`loadPack()` 未调用、`SEND_TO_AI` 无处理分支等），**没有触及 step type**——这条裂痕在最新代码上依然开着。

### 4.3 【P1】`ai_collab_intro.json` 用了枚举**名称**而非值

该包 4 步全写成大写：`LOCAL / ANALYSIS / GENERATION / VALIDATION`。

实测：

```
'local'    -> StepType.LOCAL
'LOCAL'    -> FAIL ValueError: 'LOCAL' is not a valid StepType
```

`schema_v2.py:723` 是 `type=StepType(step["type"])`，**无 `lower()` 归一化**——该包在 Python 侧同样会炸，且 `schema_validator.py:103` 的白名单全是小写，必判 `Invalid step type`。

### 4.4 【P1】Python 版本声明虚假

| 声明位置 | 内容 |
|---|---|
| `pyproject.toml:6` | `requires-python = ">=3.8"` |
| `pyproject.toml` classifiers | 列出 3.8 / 3.9 / 3.10 / 3.11 / 3.12 |
| `README.md` | Python 3.8+ |

实际：

- `a39a76a`（pyupgrade）引入 PEP604 `str | None` 语法 → **3.8/3.9 无法解析**
- 54 个文件用 PEP604，其中 **28 个没有 `from __future__ import annotations` 兜底**
- CI 矩阵只测 `["3.10", "3.11", "3.12"]`，3.8/3.9 **从未被验证过**

结论：真实下限是 **3.10**。`requires-python` 应改为 `>=3.10`，或把 28 个文件补 future import（后者无收益，前者是正解）。

### 4.5 【P2】129 个 `node_modules` 文件被 git 跟踪

```
tracked: 129 个 chrome-extension/node_modules/*  (5.3 MB)
.gitignore:121 已有 chrome-extension/node_modules/   ← 对已跟踪文件无效
```

`chore/untrack-node-modules` 分支已开（ahead=1），未合入。

### 4.6 【P0】工作区落后 main 26 个提交，且分叉结构混乱

```
merge-base(HEAD, main) = 71c9eac
HEAD (fix/global-state-reclaim) 独有 6 个提交
main 独有 26 个提交   ← 包含 061cc8b / fc9143b / 508f588 等 4 个 extension 修复
```

当前 checkout 的 `fix/global-state-reclaim` 日期（10-26）**早于** main（10-27），但 ahead=6。任何人此刻在 HEAD 上判断「项目状态」都会漏掉 main 上 26 个提交的事实——包括 4 个真机缺陷修复。

### 4.7 【P0】顺序执行路径不回写 `execution.output`，包内上下文传递整体失效

> 2026-11-03 10:40 追加。这是本轮复核新发现的引擎级缺陷，比 §4.1 的协议问题更直接地否决「Pack 能跑」。

`chrome-extension/src/background/pack-executor.js` 中 `execution.output[...]` 全库**只有一处写入**：

| 位置 | 所在函数 | 覆盖范围 |
|---|---|---|
| `:450` | `_executeWorkflowWithBranching` | 仅当 `steps.some(s => s.branches?.length > 0)` |
| `:386-393` | 顺序路径（`hasBranches === false`） | **无任何回写** |

`execute()` 在 `:377-379` 判定 `hasBranches`；为 false 时走 `:386` 的顺序 `for` 循环，该循环只做 `execution.steps.push(stepResult)`（`:388`）与失败抛出（`:390-392`），**不写 `execution.output`**。

后果：任何无分支的 Pack，`execution.output` 全程为 `{}` ⇒ `_buildPrompt` 的 `{...output, ...input}` 只剩 `input` ⇒ 所有跨步骤 `{{变量}}` 必然残留。与调用方传不传参无关。

可复现证据（同一 Pack、四象限，全部走 `execute()` 真入口）：

| 引擎 | 传参 | 残留提示词 |
|---|---|---|
| 现状 | `input === undefined`（popup 真实形态） | 6/6 |
| 现状 | 手动传 `topic` | 4/6 |
| 补回写（3 行） | `input === undefined` | 3/6 |
| 补回写（3 行） | 手动传 `topic` | 0/6 |

修法与分支路径对齐，见 `docs/PLAN_2026-11-03.md` §1.5。

> **方法论警告（自查）**：本轮之前我用自写的 `probe-full.mjs` 得到过「0/6 残留」的乐观结论，那是假象——该脚本在循环里手动做了 `execution.output[...] = r.output`，替引擎补了它没做的事。验引擎行为必须从 `execute()` 这一真实入口进，不要在探针里重演引擎的收尾动作。

> **状态更新（2026-11-03 11:20）**：已修复并独立复验。`pack-executor.js:390-392` 补上 3 行回写后，`execution.output` 正常累积 8 个键，7 条提示词残留 **0/7**、`[object Object]` 污染 **0/7**；Playwright 真机端到端确认提示词带用户输入落进目标页输入框。附带的 `input_fields` 渲染方案与遗留项（含「测试是 cwd 依赖的」）见 `docs/PLAN_2026-11-03.md` §1.6。

---

## 5. 结构性技术债

### 5.1 上帝模块 `_cli_main.py`（5,776 行）

单文件承载 `cmd_activate / cmd_check / cmd_tasks(316行) / cmd_ack / cmd_sessions(337行) / cmd_patches / cmd_conflicts / cmd_logs / cmd_init(205行) / cmd_clean / cmd_status` 全部子命令。

`CLAUDE.md` 自己承认覆盖率「受 `_cli_main.py`（2605 行 63%）等 CLI/集成入口结构性限制」——但该文件此后从 2,605 涨到 5,776 行（**+122%**），限制在恶化而非收敛。

### 5.2 命名撞车（活代码，不是死代码）

```
ai_collab/session_auto_register.py      351 行  2026-09-20
ai_collab/session_autoregistration.py   241 行  2026-05-11
```

两者**都在用**，职责不同（前者从 workspace 锚点观察同步，后者从 shell hook 注册会话），且被同一文件 `hooks/stop_check.py:29-30` 同时导入：

```python
from ai_collab.session_auto_register import record_hook_session_observation
from ai_collab.session_autoregistration import register_claude_session_from_hook
```

两模块名只差一个下划线位置。这是可维护性债，**不是**冗余——删任何一个都会断功能。

### 5.3 本地陈旧产物（未入库，但污染工作区）

```
logs/collaboration_state.json.backup           201,899 B  (2026-05-13)
logs/collaboration_state.json.stale-20260513       148 B
logs/collaboration_state.json.stale-20260513.bak   148 B
logs/monitoring_backup/     74 项
logs/tasks_backup/         249 项
logs/backups/               72 项
```

均被 `.gitignore` 挡住，**不进仓库**，但会让 `ls logs/` 这类粗粒度扫描得出错误印象。清理即可，无风险。

### 5.4 文档时间线倒错

`CLAUDE.md:289` 写 `**更新时间**: 2026-03-01`，而仓库首提交是 2026-05-11。文档自称比仓库早两个月诞生——模板残留，非实质错误，但会误导时间线判断。

---

## 6. 经检验为真的部分

只挑刺不看优点是失职。以下经实测确认**做得对**：

1. **治理层诚实度高。** `docs/REAL_MACHINE_REGRESSION.md:248` 的 7 条已知缺口全部如实标注「未验证/未修复」，并明文规定：

   > 表格里写「未验证」的项目**都不许**在别处被当成「已通过」引用。

   这条纪律在本仓是真的被执行了，`EXTERNAL_USER_SESSION_GAPS.md` 里 not-run 项也照此标注。

2. **测试隔离技术含量高。** `tests/conftest.py:58` 的 `isolated_home` fixture 把整个套件的 `HOME`/`USERPROFILE` 指向逐用例临时目录，从**路径解析层**止住全局状态污染，而不是打补丁。注释里写清了「为什么每个用例一个独立 HOME」——这层思考少见。

3. **`src/` 清理是真删。** `6030087` 净减 3,564 行，不是移入 archive。

4. **校验器向 schema 对齐是真动作。** 4 次收紧都有明确 commit，`PackSchemaValidator.VALID_STEP_TYPES` 与 `StepType` Enum 完全一致（实测 `py_enum == py_validator`）。问题是它从没对齐过 Chrome 侧（§9.3）。

5. **CI 分层合理。** 7 个 workflow 各司其职（build/lint/mypy-gate/test/security/nightly/healthcheck），mypy 有独立阻塞门禁。

---

## 7. 未验证项（如实标注，不冒充结论）

> 🔧 2026-11-03 08:52 更新：原第 2、4 项**已在 §9 验掉**，从下表移除。仍有两项未验证。

| 项 | 为什么没验 | 影响 |
|---|---|---|
| Python 测试未能复跑 | 本机只有 3.14（`miniforge3 base`）与 3.13（image_flow）、3.10（vqa，无 pytest）。3.14 下 `pytest --collect-only` 直接挂起至超时（SIGTERM），已排除 conftest 网络/睡眠/子进程因素 | 无法确认 0 fail 现状；§4.1 的「无测试守护」由 grep 推定，非运行结论 |
| coverage gate ≥85% 未验证 | 依赖测试复跑 | 只确认 workflow 里配置了阈值，未确认真实值 |

**以下原列于此、现已验证：**

| 原未验证项 | 结论 | 位置 |
|---|---|---|
| Chrome 扩展未实测运行 | ✅ 已用 Playwright 真机加载并端到端执行 Pack | §9.2 / §9.3 |
| main 上 26 个提交是否改变 §4.1/4.2 结论 | ✅ 已复跑，结论不变或加强（0/17、13/17） | §9.1 |

**仍未覆盖的盲区（新增）**：真机只测了 `chatglm.cn` 一个站点、`dist` 一个产物。其余 9 个平台适配器、L1/L2 回归矩阵仍按 `REAL_MACHINE_REGRESSION.md` §6 的口径保持「未验证」。

---

## 8. 建议动作（按优先级）

> 🔧 **本节已被 §9.5 取代。** 下表基于 HEAD 的静态分析，§9.5 依据真机证据重排了优先级并新增两条 P0。保留此处以留痕。

| 优先级 | 动作 | 目标文件 | 判定标准 |
|---|---|---|---|
| **P0** | 在 `main` 上（不是当前 HEAD）重跑 §4.1 校验脚本，确认断层仍在 | `docs/ARCHAEOLOGY_AUDIT_2026-11-03.md` §4.1 | 输出 `通过 N/16` |
| **P0** | 决定示例包去向：回灌到当前 schema，或显式标 `@deprecated` 并移出 `packs/examples/` | `packs/examples/*.json` | 二选一，不许中间态 |
| **P0** | Chrome 侧补 4 种 step type 分支，或明确写死「Chrome 只支持 local/ai」并在导入时前置拦截 | `pack-executor.js:476,520` | 导入非法 type 时应报错而非执行到一半抛异常 |
| **P1** | `pyproject.toml:6` 改 `requires-python = ">=3.10"`，classifiers 删 3.8/3.9 | `pyproject.toml` | 与 CI 矩阵一致 |
| **P1** | 加一条守护测试：`validate_all_packs("packs/examples/")` 必须全过 | `tests/unit/` | 该测试现在应**红**，红了才证明它在守护；已落地 2026-11-05（`test_pack_files_gate.py`） |
| **P1** | 合入 `chore/untrack-node-modules` | `.git` | `git ls-files \| grep -c node_modules` == 0 |
| **P2** | 拆 `_cli_main.py`，先把最大的 `cmd_sessions` / `cmd_tasks` 抽到独立模块 | `ai_collab/cli/` | 单文件降到 3,000 行以下 |
| **P2** | 二选一给 `session_auto_register` 改名（如 `session_observation_sync`） | `ai_collab/` | 与 `session_autoregistration` 不再视觉混淆 |
| **P3** | 清理 `logs/` 下 4 类备份目录 | `logs/` | 无风险，纯卫生 |

---

## 9. 追加校验：main 复跑 + chrome-extension 真机（2026-11-03 08:39–08:52）

### 9.0 方法

在 `/tmp/aicb-main-verify` 建独立 `git worktree` checkout `main`（`d7938ef`），不触碰工作区的未提交改动。校验完成后 worktree 已删除，工作区 `git status` 与校验前一致。

工作区（`932f7cf`）与 `main`（`d7938ef`）的实际差异：

| 路径 | 差异 |
|---|---|
| `packs/` + `ai_collab/pack/` | **仅 +1 文件**（`external-user-smoke.json`，89 行） |
| `chrome-extension/` | **73 文件 / +44,153 行 / -249 行** |

> 第二行是个警告：我第一轮关于扩展的结论是读 `932f7cf` 得出的，而 `main` 上扩展代码量是它的数倍。凡涉及 `chrome-extension` 的判断，**必须注明基于哪个 commit**。

### 9.1 静态校验：main 上全部结论不变或加强

| 项 | HEAD `932f7cf` | main `d7938ef` | 判定 |
|---|---|---|---|
| 示例包自校验通过 | 0 / 16 | **0 / 17**（新增 `external-user-smoke.json`，仍不过） | 加强 |
| Chrome 侧不可执行的包 | 13 / 16 | **13 / 17** | 加强 |
| PEP604 文件 / 无 future 保护 | 54 / 28 | **54 / 28** | 不变 |
| `requires-python` | `>=3.8` | **`>=3.8`** | 不变 |
| 被跟踪的 node_modules 文件 | 129 | **129** | 不变 |

**新增包 `external-user-smoke.json` 的失败原因极关键**——它是 `38d28aa` 为外部用户试用专门加的、被 `tests/unit/test_external_user_runbook.py:30` 守护的那一份：

```
[ERROR] $.workflow.steps[0].type: Invalid step type: ai
[INFO]  $.example_library: No examples defined
```

顶层字段一个不缺（含 `generation_params` / `optimization` / `example_library`），唯一 ERROR 是 **`ai` 不在校验器白名单里**。

### 9.2 真机校验：扩展能跑，但 README 的加载指引是错的

环境：Playwright 1.59 + Chromium（`chromium-1248`），在 `main` 的 `chrome-extension` 上 `npm run build`，产物 `dist/`。

#### 构建

```
[1/5] Cleaned output directories
[2/5] Building Content Script (IIFE)...    ✓ 15 modules → 31.02 kB
[3/5] Building Service Worker (ESM)...     ✓ 17 modules → 109.04 kB
[4/5] Merging build outputs...             ✓
[5/5] Copying static assets...             ✓ 16 files, 3 icons
=== Build Complete ===  Output directory: dist/
```

构建脚本自己打印：`Load in Chrome: ... → select dist/`

#### 加载 `dist/`（正确路径）

| 检查项 | 结果 |
|---|---|
| Service Worker 注册 | ✅ `service-worker.js` |
| SW 运行环境 | ✅ `chrome.storage` / `chrome.runtime` / `onMessage` 均在 |
| `popup.html` | ✅ 200，title=`Prompt Pack` |
| popup JS 错误 | ✅ 无 |
| `pack-editor.html` / `settings.html` / `style-editor.html` | ✅ 全部 200 |
| 扩展自报错误 | ✅ `hasErrors: false` |
| **content script 注入真实站点** | ✅ **成功** |

真机日志（`https://chatglm.cn/`）：

```
log: [Prompt Pack] Content Script initialized
log: [Prompt Pack] Using adapter: chatglm.cn
```

#### 加载 `chrome-extension/` 源码目录（README 的路径）

| 检查项 | 结果 |
|---|---|
| Service Worker 注册 | ✅ 起来（`type: module` 是 MV3 支持的） |
| **content script 注入** | ❌ **失败** |
| 页面报错 | **`Cannot use import statement outside a module`** |

#### 结论：`README.md:105` 是错的

```
README.md:105    4. 选择 `chrome-extension/` 目录          ← 错，content script 静默失败
build.js 输出    Load unpacked → select dist/              ← 对
```

源码布局下 `manifest.json` 的 `content_scripts.js` 指向 `src/content/content-script.js`，该文件第 16–34 行是 ESM `import`，而 **MV3 的 content_scripts 不支持 ESM**（`type: module` 只对 `background.service_worker` 生效）。

**危害在于它的静默程度**：扩展装上了、图标在、Service Worker 正常、`chrome://extensions` 不报错，但 content script 在页面上一个都没注入。外部用户按 README 走完会得到一个「看起来装好了但什么都不发生」的扩展——这正是 `docs/EXTERNAL_USER_SESSION_RUNBOOK.md` 里 W-D1 排演要防的场景，而 README 恰恰在第一步把他带进坑里。

### 9.3 端到端：`analysis` 与 `ai` 的真实差别

用扩展自己的消息通道实测（`IMPORT_PACKS` → `EXECUTE_PACK`），不模拟 UI。

**A. `douyin_video_script.json`**（`local,analysis,generation,validation,fusion,tracking`）

```
导入: {"imported":["douyin-video-script"],"errors":[]}
执行: success=false
  step_1_input      type=local     success=true    ← local 过了
  step_2_analysis   type=analysis  success=false   ← "Unknown step type: analysis"
  step_3~6          未执行
```

**B. `external-user-smoke.json`**（单步 `ai`）

```
导入: {"imported":["external-user-smoke"],"errors":[]}
执行: success=false
  step_1_echo  type=ai  error="Could not establish connection. Receiving end does not exist."
```

B 的失败是**预期行为**（没有打开 AI 页面标签，内容脚本不在），关键在于它**走过了 switch**、进入了通讯阶段。A 的失败是**执行器根本不认识这个类型**。

> 这就是 §4.1 根因的实证：`ai` 被 Chrome 接受但被 Python 校验器拒绝；`analysis` 被 Python 接受但被 Chrome 拒绝。两边唯一的公共类型是 `local`。

### 9.4 顺带发现

1. **`dist/` 有 8 个文件双份。** `dist/popup.html` 与 `dist/public/popup.html` 内容 md5 完全一致（popup / pack-editor / settings / style-editor 的 html+js 共 8 个）。manifest 只引用扁平那份，`dist/public/` 是死产物。不影响运行，但让产物体积翻倍、且让人误以为存在两套页面。

2. **Pack 的 ID 不在 `id` 字段。** 真机取到的对象是 `{metadata:{pack_id:"douyin-video-script"}, ...}`，直接读 `pack.id` 得 `undefined`。这与 `061cc8b` 修的断点 1（"popup 用不存在的 `pack.id`"）是同一类陷阱——**修过一次，但字段本身仍无单一来源**。

3. **worktree 里检出了残缺 node_modules。** 因 129 个文件被 git 跟踪，`git worktree add` 会在新目录里造出一个 5.3 MB / 129 文件的假 `node_modules`。任何人在此基础上跑 `npm run build` 会因依赖不全失败，而不是提示「请先 npm install」。这是 §4.5 从「仓库脏」升级为「会误导构建」的实际后果。

### 9.5 修正后的动作清单

§8 的表据此调整，**优先级按真机证据重排**：

| 优先级 | 动作 | 依据 |
|---|---|---|
| **P0** | 改 `README.md:105` → `dist/`，并补一句「先 `npm run build`」 | §9.2 真机，外部用户第一步就卡 |
| **P0** | 统一步骤类型协议：三选一 —— ① Chrome 补 4 种分支；② Schema 收编 `ai`；③ 显式声明「Pack 分 Python 执行档 / Chrome 执行档」 | §9.3 真机，交集只剩 `local` |
| **P0** | 示例包按新协议回灌，或移出 `packs/examples/` | §9.1，0/17 |
| **P1** | `pyproject.toml:6` → `>=3.10` | §9.1，54/28 与 CI 矩阵不匹配 |
| **P1** | 加 `validate_all_packs("packs/examples/")` 守护测试（现在应红） | §9.1，无测试守护→已落地 2026-11-05（`test_pack_files_gate.py`） |
| **P1** | 合入 `chore/untrack-node-modules`；顺带解决 worktree 假依赖 | §9.4.3，会误导构建 |
| **P2** | 修 `build.js` 的 `dist/public/` 双份复制 | §9.4.1 |
| **P2** | Pack ID 统一为单一字段来源 | §9.4.2 |

---

## 附：本次对账用到的可复现命令

```bash
# §4.1 示例包自校验
python3 -c "
import sys, glob; sys.path.insert(0,'.')
from ai_collab.pack.schema_validator import validate_pack
ok=[f for f in sorted(glob.glob('packs/examples/*.json')) if validate_pack(f).is_valid]
print(f'通过 {len(ok)}/16', ok)"

# §4.2 步骤类型分布
python3 -c "
import json,glob,collections
c=collections.Counter()
for f in glob.glob('packs/examples/*.json'):
    d=json.load(open(f,encoding='utf-8'))
    for s in (d.get('workflow') or {}).get('steps') or []: c[s.get('type')]+=1
print(dict(c))"

# §4.4 PEP604 无 future 保护统计
for f in $(grep -rl "str | None" --include=*.py ai_collab/); do
  head -15 "$f" | grep -q "from __future__ import annotations" || echo "$f"; done | wc -l

# §4.6 分叉状态
git rev-list --count HEAD..main   # 26
git rev-list --count main..HEAD   # 6
```

---

*本文件由对账生成。所有数字均来自当次磁盘实测，未引用任何文档自述。*
