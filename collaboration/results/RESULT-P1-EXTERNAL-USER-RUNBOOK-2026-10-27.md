# RESULT-P1-EXTERNAL-USER-RUNBOOK-2026-10-27

**状态**: completed
**任务**: `TASK-P1-EXTERNAL-USER-RUNBOOK-001`（把 W-D1 排演材料变成一场可以照着跑完的真人外部用户会话）
**执行**: Claude Code（AGENT_EXEC）
**分支**: `docs/external-user-session-runbook`
**日期**: 2026-10-27

---

## 一句话结论

W-D1（排演）攒下的材料此前是**散件**，不是「一场会话」——
没有主持人视角的流程、没有「现场看什么」、也没说清它和 L2 第 1 轮的关系
（两件事都要人，分两场做要约两次人）。
本工单把它们收成一份**主持人操作手册**
（[`docs/EXTERNAL_USER_SESSION_RUNBOOK.md`](../../docs/EXTERNAL_USER_SESSION_RUNBOOK.md)），
并给手册加了机器守护（引用的交付物还在不在、链接通不通、
**手册教的参数名工具认不认**、七条红线有没有被删），
四条守护**逐条做过变异验证**。
**材料侧到此不再欠账——缺的只是「人」和「一次真机发送」。**

> **附带**：把工单契约校验脚本的通配符修对之后，它第一次扫到了全部 23 个工单，
> 也因此翻出 **5 条存量契约违规**（与本工单无关、此前从未被机器验过）。
> 这 5 条已**全部补齐并留痕**，门禁现在是绿的（`invalid=0`，退出码 0）。
> 详见 §执行命令 §5。

---

## 一、这次改了什么、没改什么

### 改了

| 文件 | 改动 |
|---|---|
| `docs/EXTERNAL_USER_SESSION_RUNBOOK.md`（新增） | 主持人操作手册，10 节：是什么/不是什么、**一场拿两份证据**、角色分工与铁律、前置准备、现场流程、**静默观察清单 D0–D7**、记录怎么写、判定口径与收口、七条红线、一页纸速查 |
| `docs/EXTERNAL_USER_ONBOARDING.md` | 适配**两种交付形态**：预构建交付包（默认）与自己编译（备选）。原文假设试用者会敲 `npm run build`——真人外部用户大概率不会 |
| `docs/REAL_MACHINE_REGRESSION.md` | §4 加「和 W-D2 一起跑更省事」；§6.2 缺口 #13 与 §7 指向新手册，口径统一为「**材料已备齐，缺的只是人**」；修正一处「5 个断点里有 4 个是绿的」的口径（实为 6 个断点、5 个在模拟层与真机探针里全绿） |
| `collaboration/results/external-user/README.md` | 加一条指向手册的说明（记录格式归本目录，**怎么把这一场跑起来**归手册） |
| `tests/unit/test_external_user_runbook.py`（新增） | 5 条守护，见 §三 |
| `scripts/verify_task_file_contracts.py` | **修一个真缺陷**：通配符写成 `TASK_*.md`（下划线），而本仓工单文件名是 `TASK-P1-…-001.md`（连字符）⇒ 不带参数跑时它一个工单都找不到，打印「没找到工单文件」就退出。这个 bug 此前不可见，因为脚本只被显式传 `--task-id` 用过，而那条路径绕开了它。**另修一处**：原先在第一个不合规工单上直接抛异常退出，后面 20 来个工单一条都没验到——「只报第一个错」等于「只看了第一个」 |
| **4 个存量工单文件 + 1 个存量结果文件** | 补齐通配符修好之后翻出来的 5 条**存量**契约违规（详见 §执行命令 §5），全部**补齐并留痕** |
| `memory/` | CodeArts 记忆源更新 `project_route_decision.md`（材料侧已备齐、缺的只是人）+ 刷新镜像 |

### 没做（边界必须写清楚）

| 没做 | 为什么 |
|---|---|
| **没有跑真人外部用户会话** | 需要**一个真人外部用户**（不是本团队的人）。本工单交付的是「怎么跑」，不是「跑完了」 |
| **没有跑 L2 第 1 轮** | 需要人拿已登录账号在机器前点发送。手册已把「同一场同时干两件事」写清，但**跑没跑是人的事** |
| **没有改任何运行时代码** | 本工单只动文档、测试与一个脚本的通配符 |
| **没有替试用者写记录** | 记录里的每一句「他的感受」必须来自他本人。手册 §8 把这条列为红线 |
| **没有把路线门禁关掉** | `real_machine_regression.py verify` 明说「第一个外部用户」不在它的证据范围内；门禁的关闭条件是**人**给的判断 |
| **没有把这个校验脚本接进 CI** | `scripts/verify_task_file_contracts.py` **不在任何 workflow 里**（现有 workflow：build / healthcheck / lint / mypy-gate / nightly / security / test）。它是个**人工跑的**门禁——本仓的工单契约一致性目前**靠人记得跑**，不靠 CI 拦 |
| **没有顺手改 8 个工单文件里的陈旧 `status:`** | 有 8 个工单文件的 frontmatter 写着非 `completed` 的状态，而它们的结果文件都写着 `completed`。**校验脚本根本不读文件里的 `status:`**（它无条件把所有工单驱动到 `completed`），所以这**不是门禁问题**——是文件里的那个字段陈旧，而工作本身确已完成。改 8 处历史状态字段是一笔与本工单无关的大 diff，且会掩盖「状态字段由谁维护」这个更根本的问题。**记在风险表里，不在本工单里顺手改** |

---

## 二、手册里几个不显然的设计

| 设计 | 为什么 |
|---|---|
| **D0–D7 静默观察清单** | 6 个已修断点各自对应一个**外部可见症状**（「框里有字但按钮是灰的」）。主持人**盯着症状看**，但**不告诉试用者**——告诉他就把这次证据作废了 |
| **一场会话拿两份证据** | 试用者的主观反馈（人证）＋ 观测器抓的机器时间线（机证）。L2 观测器**不注入、不点发送**，发送由试用者本人做——这是「探针永不发送」红线的唯一合法例外形式：**发送是人做的** |
| **交付包明确「不给什么」** | 不给仓库（给他代码，他就从用户变成开发者）、不给缺陷清单（知道坑在哪就会绕过去）、不给任何提示（「记得先登录哦」会消灭我们要观察的那类卡点） |
| **L2 登记用已存在的 run** | `record` 要求 run 先存在；另起一份新 run 只登记 L2 的话，`verify` 会报「平台 X 缺 L1 记录」。手册因此指向 `RMR-2026-10-26-01`（已有 qianwen 的 L1 pass 与 L2 not-run，重登记就地替换） |
| **`verify` 退出码 2 是正常的** | 一场只覆盖一个平台 ⇒ 其余平台仍未跑完 ⇒ 退出码 2 = 一致但没跑完。手册写明了，免得主持人把它当成失败 |
| **L1 自检必须带 `--profile-dir`** | 没登录态的话探针只会撞登录墙，那个结论对「试用者能不能跑通」毫无参考价值 |

---

## 三、守护（每条都做过变异验证）

`tests/unit/test_external_user_runbook.py`（5 条）：

| 守护 | 变异验证（改坏它，守护必须变红） |
|---|---|
| 手册存在、不是骨架、必需章节齐 | — |
| 手册引用的 9 个交付物都在 | 移走 `packs/examples/external-user-smoke.json` ⇒ **红** |
| 相对链接都指得到真实文件 | 把一条链接改成不存在的文件名 ⇒ **红** |
| **手册教的参数名，工具真的解析** | 把 `l2-model.mjs` 里的 `raw === "--wait-for-login"` 改成 `--wait-until-login` ⇒ **红** |
| 七条红线没被删 | 删掉「不代劳」那条 ⇒ **红** |

> 参数那条守护第一版**是假绿的**：它只检查参数名**字符串**在源码里出现过，
> 而 `--wait-for-login` 在注释里也写着 ⇒ 改名后仍然绿。
> 改成只认三种解析形态（`raw === "--flag"` / `raw.startsWith("--flag=")` /
> `add_argument("--flag"`）之后，变异才被抓住。

---

## 执行命令

以下 6 条即工单契约里的 `acceptance_commands`，逐字执行，全部通过：

### 1. `python3 -m pytest tests/unit/test_external_user_runbook.py -q`

```
.....                                                                    [100%]
5 passed in 0.02s
```

### 2. `python3 -m pytest tests/ -q`

```
3066 passed, 7 skipped in 48.34s
```

（7 个 skip 是既有的诚实跳过：本地没有后端数据库、没有 `.trae/skills`、
集成测试要 `127.0.0.1:8000` 后端在跑。）

### 3. `python3 -m ruff check .`

```
All checks passed!
```

### 4. `python3 scripts/scan_secrets_pii.py --workspace .`

```
[OK] no secrets found
```

### 5. `python3 scripts/verify_task_file_contracts.py`

```
已登记并收口：TASK-P0-CONSENSUS-ENGINE-001
已登记并收口：TASK-P1-CLI-EXITCODE-001
…
已登记并收口：TASK-P1-EXTERNAL-USER-RUNBOOK-001
…
契约校验: checked=23 invalid=0 skipped=0

终态结果一致性审计: audited=23 consistent=23 mismatch=0 unparseable=0 missing_result=0

结论： 全部通过
```

退出码 `0`。

> **这一条第一次跑是红的**：脚本的通配符是 `TASK_*.md`（下划线），
> 而本仓工单文件名是 `TASK-P1-…-001.md`（连字符）⇒ 它打印
> 「没找到工单文件」就退出了。已修（见 §一），现在能扫到全部 23 个工单。
>
> 修完之后它**暴露了另一个问题**：本工单自己的结果文件当时还没写，
> 于是收口 `completed` 时被结果门禁挡住——这正是那道门禁该有的行为。

#### 通配符修好之后，它把 5 个**存量**违规翻了出来

通配符一改，脚本从「扫到 0 个工单」变成「扫到 23 个」，于是这 5 条
**与本工单无关、此前从未被机器验过**的存量违规第一次露出来：

```
契约校验: checked=23 invalid=4 skipped=0
  - TASK-P1-PREFIX-DISJOINT-001   missing=['primary_skill']  invalid=['support_skills']
  - TASK-P1-PREFIX-DERIVATION-001 missing=['primary_skill']  invalid=['support_skills']
  - TASK-P0-CONSENSUS-ENGINE-001  missing=['change_id']
  - TASK-P1-DISPATCH-MODEL-FALLBACK-001                  invalid=['change_id']
收口失败 1 个工单（结果文件门禁没过）：
  - TASK-P1-PREFIX-DISJOINT-001: result_file missing acceptance_commands=[python3 -m pytest tests/unit/test_ack_prefix_consistency.py tests/unit/test_role_prefix.py tests/unit/test_dispatch_trigger.py -q]
结论： 有问题
```

5 条全部**补齐并留痕**（不是把门禁放宽，也不是跳过）：

| # | 工单 | 违规 | 处置 | 取值依据 |
|---|---|---|---|---|
| 1 | `TASK-P1-DISPATCH-MODEL-FALLBACK-001` | `change_id: feature/no-spec` 不在白名单 | 改为 `bugfix/no-spec` | 该工单自己的结果文件 §0「门禁修正留痕」**已经**记着当年用 CLI 改成了 `bugfix/no-spec`——**状态库改了，工单文件没跟着改**，脚本按文件读又把非法值推了回去 |
| 2 | `TASK-P0-CONSENSUS-ENGINE-001` | `change_id` 字段整个缺失 | 补 `bugfix/no-spec` | 工单正文 2026-10-23 收口说明自己写着：原值指向已删的外部提案，「本仓的变更提案一律是 `bugfix/no-spec` 之类的本仓标识」 |
| 3 | `TASK-P1-PREFIX-DERIVATION-001` | 缺 `primary_skill`、空 `support_skills` | 补 `backend-architect` + `[testing, documentation]` | 同族工单 `TASK-P1-GOV-CONVERGE-001`（同为 `claude_code` / `AGENT_ARCH` / `reviewer=user`）的既有写法 |
| 4 | `TASK-P1-PREFIX-DISJOINT-001` | 同上 | 同上 | 同上 |
| 5 | `RESULT-PREFIX-DISJOINTNESS-2026-10-23.md` | 结果文件缺工单 `acceptance_commands[0]`（**合并写法**）的逐字命中 | 把该命令逐字补进「执行命令」验收块首位 | 回执桥接做**整串子串比对**，拆开写不算命中 |

> **第 5 条顺带修正了一处无出处的数字**：该结果文件原写「前缀相关用例
> **54 passed**」，实际是 **45 passed**。逐 commit 复验（检出 `e88e1c8` /
> `5b9160e` / `2f72286` / `4af0efd` / `61afa3f` 逐个跑同一条命令）⇒
> 分别是 38 / 45 / 45 / 45 / 45，**54 在任何一个 commit 上都没出现过**。
> 按实测值更正并留痕。
>
> **一个容易被误判的点**：`update_task_contract` 的 `_set_str` / `_set_list`
> **跳过 None 与空值**。所以「工单文件里某字段是空的」这件事，
> **从状态库那侧永远修不好**——脚本从文件推送，空值等于没推。
> 唯一的修法是**改工单文件本身**。这也是这 5 条必须落在文件里、而不是
> 落在状态库里的原因。

### 6. `bash scripts/verify_agent_config_sync.sh`

```
== V1 治理门禁 ==
PASS  governance validation (AGENTS.md + required files)
== V2 镜像幂等 check ==
PASS  memory mirror in sync
== V3 漂移检测->修复闭环 ==
PASS  drift detected (expected nonzero)
PASS  drift repaired after sync
== V4 单测 ==
PASS  unit tests (tests/unit/test_sync_agent_memory.py)
== V5 AGENTS.md 必读文件纯路径行 ==
PASS  AGENTS.md 4 required refs as bare paths
== V6 gitignore 白名单 ==
PASS  memory/MEMORY.md trackable
== V7 @import 接线 ==
PASS  CLAUDE.md -> @memory/MEMORY.md wired

TOTAL: pass=8 fail=0
```

---

## 验证结果

| 验收项 | 结果 |
|---|---|
| 手册能不能**照着跑完**一场真人会话 | 是——从选人、构建、自检、打包，到现场流程、观察清单、记录、登记、收口，逐段可执行 |
| 手册里的命令**跑得起来吗** | 是——三条命令的**参数名逐个**与工具源码对账，并由守护持续钉住 |
| 手册引用的交付物**都还在吗** | 是——9 个引用路径全部存在，由守护钉住 |
| 手册会不会教人**代劳** | 不会——七条红线写在 §8，并由守护钉住（删一条就红） |
| 排演材料**是不是真的变成了可执行指南** | 是——不再是散件，是一场有准备、流程、观察点、记录口径与收口动作的会话 |
| W-D2 **跑了吗** | **没有**——需要一个真人外部用户 |
| L2 第 1 轮 **跑了吗** | **没有**——需要人在机器前登录并点发送 |

### 测试结论

- **新增守护 5 条**：全部通过，且**逐条做过变异验证**（改坏被守护的东西，对应守护确实变红）。
- **全量单测**：3066 passed / 7 skipped（skip 均为既有的诚实跳过）。
- **工单契约门禁**：`checked=23 invalid=0` / `audited=23 consistent=23` / 退出码 0。
  门禁现在**扫得到全部 23 个工单**（此前扫到 0 个），也因此把 5 条存量违规翻了出来——
  **补齐后重跑是绿的**，不是把检查关掉。
- **本轮改动没有触碰任何运行时代码**——扩展侧不重跑扩展测试是合理的，
  但**跑了**以防万一：`node tests/run-tests.mjs` 与适配器矩阵在本轮之前
  （PR #5）已全绿，本轮未改动 `chrome-extension/` 下任何文件。
- **未验证的部分**：手册**本身**没被真人使用过——这是它要解决的那件事，
  只有 W-D2 那一场能验。

---

## 风险

| 风险 | 影响面 | 现状 |
|---|---|---|
| **手册没被真人跑过** | 手册里可能有「读得懂但做不到」的步骤 | 已在 §0 明写「排演不能代替这一场」；D0–D7 就是为第一次跑设计的观察点。**第一次跑很可能要修手册** |
| **真人外部用户仍未找到** | 路线 A/B 决策门禁的最后一环仍然空着 | 材料侧不再欠账；缺的只是「人」 |
| **L2 第 1 轮仍未跑** | 缺口 #5（「回复等待链路」未验证）仍开着 | 观测器已交付并与 W-D2 合场；`RMR-2026-10-26-01` 里 10 个平台的 L2 都已登记为 `not-run` 并写明原因 |
| **手册会被当成「说明书」发给试用者** | 试用者看到「不代劳」这类内部约定 ⇒ 他知道我们在测什么 ⇒ 证据作废 | §2、§3.5、§8 三处都写明「手册是给主持人的」；给试用者的只有 `EXTERNAL_USER_ONBOARDING.md` |
| **主持人忍不住伸手帮忙** | 这一场直接作废 | §2 铁律 + §8 红线 + D0–D7；速查页压在最后一段 |
| **千问以外的平台仍未经模型级注入复验** | 缺口 #12：非 Slate 框架的编辑器模型机制未验证 | 已记在 `REAL_MACHINE_REGRESSION.md` §6.2 #12；手册**优先选千问**正是因为它验得最深 |
| **契约校验脚本没接进 CI** | 工单契约违规再次溜过去时，**没人会知道**——直到有人手工跑这个脚本 | 已在 §「没做」写明。本仓现有 workflow 不含它；要接进 CI 属于另一次改动（且它会写状态文件，接 CI 前要先想清楚隔离） |
| **8 个工单文件的 `status:` 字段陈旧** | 读工单文件的人可能以为这些工单还没完 | **不影响门禁**（脚本不读文件里的 `status:`），也不影响一致性审计（审计比的是状态库 vs 结果文件）。工作本身已完成——结果文件齐全且写着 `completed`。留待专门一轮清理 |
| **补齐的 5 条存量违规改变了别人的历史工件** | 5 条都动了**别人**的工单/结果文件 | 全部**补齐并留痕**，没有一条是「放宽校验」或「跳过」。取值全部来自仓内既有证据（结果文件 §0、工单正文收口说明、同族工单写法），不是猜的。唯一的数字更正是把无出处的「54 passed」改成实测的「45 passed」，并附逐 commit 复验记录 |

---

## 回滚

- **文档**：`docs/EXTERNAL_USER_SESSION_RUNBOOK.md`（新增）、
  `docs/EXTERNAL_USER_ONBOARDING.md`、`docs/REAL_MACHINE_REGRESSION.md`、
  `collaboration/results/external-user/README.md`。
  回滚 = 回退这些文件；手册是**新增**的，删掉即回到本工单之前的状态。
- **脚本**：`scripts/verify_task_file_contracts.py` 的通配符修复可独立回滚，
  但**不建议**回滚——回滚后脚本会退回「一个工单都找不到」的状态。
- **测试**：`tests/unit/test_external_user_runbook.py`（新增）与被守护的文档**必须同进同退**，
  否则守护会因手册缺失而红。
- **记忆**：`memory/project_route_decision.md` 是 CodeArts 记忆源
  （`~/.codeartsdoer/memory/<仓库 slug>/`）的**镜像**——
  回滚镜像会被下次同步覆盖，**要改必须改源**。
- **记录**：真人外部用户的试用记录**不随代码回滚**——它是事实记录。
- **5 条存量违规的补齐**（4 个工单文件 + 1 个结果文件）：
  回滚这些改动会把 5 条违规**放回去**，门禁会重新变红
  （`invalid=4` + 1 条收口失败）。若要回滚，**连带**回滚
  `scripts/verify_task_file_contracts.py` 的通配符修复——
  否则脚本会扫到 23 个工单并把违规报出来。这一对**同进同退**。
