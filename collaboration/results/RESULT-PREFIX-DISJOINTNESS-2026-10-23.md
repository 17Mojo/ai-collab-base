# RESULT-PREFIX-DISJOINTNESS-2026-10-23

**任务**：`TASK-P1-PREFIX-DISJOINT-001`
**执行方**：Claude Code（AGENT_ARCH）
**状态**：completed

---

## 一、根因

`X` 这个字母被**两套命名空间各自独立征用**，谁都不知道对方也用了它：

| 命名空间 | 权威来源 | `X` 的含义 |
|---|---|---|
| 角色命名空间 | `config/agent-orchestration.json` 的 `command_prefixes` | `X.RUN → AGENT_ARCH` |
| provider 命名空间 | provider 兜底前缀表（4 处副本） | `codex → X` |

### 引入时间与演化（git 证据）

| 时间 | commit | 事件 | `X` 的含义 |
|---|---|---|---|
| 2026-05-11 | `e76d7ee` 初版 | provider 兜底表 `{"claude_code":"C","codearts_agent":"A","codex":"X"}` | **X = codex** |
| v3.0 | `77df0a5` 动态角色编排 | 角色命名空间引入：`A.RUN→AGENT_ARCH`、`X.RUN→AGENT_EXEC`、`C.RUN→AGENT_TEST` | **X = AGENT_EXEC**（与 provider 侧同字母、不同义，无人核对） |
| 2026-10-22 | `229062d` 命名空间收敛 | 为对齐 provider 侧把 A/X 对调 → `A.RUN→AGENT_EXEC`、`X.RUN→AGENT_ARCH` | **X = AGENT_ARCH**；codex 的兜底 X 未同步，撞车形成 |

provider 侧的前缀约定是"取 provider 名字里的一个字母"
（clau**d**e→C、codearts_**a**gent→A、code**x**→X）；
角色侧也是单字母。**两套命名空间共用同一个字母池，
交集是必然的，不是偶然。** codex 的 X 只是第一个撞上来的。

### 撞车的实际后果

`X.ACK` 的发送方无法判定：

1. codex 作为 provider 回 ACK → `X.ACK`
2. claude_code 扮演 AGENT_ARCH 回 ACK → 角色前缀优先 → 同样 `X.ACK`
3. `cmd_ack --task-id none` 默认 `assignee=codex`，发全局 noop 广播
   `X.ACK|task=none|status=noop|result=none` —— 与真实角色 ACK **同形**

另外两处"解析不出来 → X"的终极兜底
（`role_prefix.py` 与 `ack_protocol.py`）把"我不知道"
伪装成了 AGENT_ARCH 这个真实角色。

## 二、"X 前缀是否还有必要"

| 场景 | 判定 | 理由 |
|---|---|---|
| `AGENT_ARCH` 的角色前缀 `X.RUN` | **保留** | 协议表面：A/C/X 三元组已成文（PROTOCOL §6.1、派发指南、菜单规范）；改它会动用户的肌肉记忆 |
| `codex` 的 provider 兜底前缀 `X` | **不再必要** | codex 未绑定任何角色、`connection_status=unavailable`、实际不参与派发；这个 X 是初版"名字取字母"约定的化石，且恰好与角色池撞车 |
| "解析不出来"的兜底 `X` | **必须去掉** | 它让未知量伪装成真实角色，比撞车本身更危险 |

## 三、改动

### 3.1 前缀分配

| provider | 改前 | 改后 | 理由 |
|---|---|---|---|
| `codearts_agent` | A | A（不变） | 绑定的正是 AGENT_EXEC，与角色前缀一致 |
| `claude_code` | C | C（不变） | 绑定的 AGENT_TEST，与角色前缀一致 |
| `codex` | **X** | **O** | 未绑定任何角色，必须避开角色字母池 {A, C, X} |
| 未知 provider 兜底 | **X** | **Z** | 保留字母，表示"未解析"，不冒充任何角色 |

改动落点（`codex` 的兜底前缀共 4 处配置 + 5 处代码）：

| 文件 | 位置 |
|---|---|
| `config/agent-orchestration.json` | `provider_registry.codex` + 3 个 `snapshots[].config_copy` |
| `ai_collab/role_prefix.py` | `FALLBACK_ACK_PREFIX` + 终极兜底 |
| `ai_collab/ack_protocol.py` | `_ACK_PREFIX` + 终极兜底 |
| `ai_collab/orchestration.py` | `DEFAULT_FALLBACK_ACK_PREFIX`（codex / codex_cli） |
| `ai_collab/dispatch_trigger.py` | `RUN_HINT` / `ACK_HINT` |
| `scripts/agent_receipt_bridge.py` | `ack_prefix_for()` |

**没有改任何角色前缀** —— `A`/`C`/`X` 三个角色前缀原样保留。

### 3.2 不变量测试（防止复发）

`tests/unit/test_ack_prefix_consistency.py` 新增 4 条（首轮；二次排查又加 7 条，见 §3.4）：

| 测试 | 守住的规则 |
|---|---|
| `test_provider_prefix_never_collides_with_unbound_role_prefix` | provider 兜底前缀只能与**它实际绑定的那个角色**共用字母 |
| `test_codex_prefix_is_outside_role_letter_pool` | codex 的前缀不在角色字母池里 |
| `test_unknown_provider_fallback_is_not_a_role_letter` | 终极兜底不是任何角色前缀 |
| `test_no_two_providers_share_the_same_prefix` | 两个 provider 不共用同一前缀 |

### 3.3 文档陈旧映射修正

`229062d` 那次改名只动了配置，**协议文档没跟上**，一直写着旧映射：

| 文件 | 改前 | 改后 |
|---|---|---|
| `collaboration/PROTOCOL.md` §3.2 / §6.1 | `X.RUN → AGENT_EXEC`、`A.RUN → AGENT_ARCH` | `A.RUN → AGENT_EXEC`、`X.RUN → AGENT_ARCH` |
| `collaboration/COLLABORATION_GUIDELINES.md` §3 / §4.1 | 同上 | 同上 |
| `collaboration/guides/MENU_INTERACTION_SPEC.md` | 同上 | 同上 |
| `collaboration/guides/USAGE_SCENARIOS_GUIDE.md` | `X.RUN → AGENT_EXEC` | `A.RUN → AGENT_EXEC` |

### 3.4 二次排查发现的 3 处残留（同一根因：`229062d` 只改了 1 份副本）

改完前缀分配后复查全仓，发现 `229062d` 那次 A/X 对调**只改了
`config/agent-orchestration.json` 一份**，同一份映射在仓库里还有 3 个副本
带着旧值。按「配置类改动须同时验静态接线与行为级加载」的要求逐个处理：

| 编号 | 位置 | 性质 | 处置 |
|---|---|---|---|
| **Gap A** | `ai_collab/orchestration.py` `DEFAULT_COMMAND_PREFIXES`、`config/agent-orchestration.template.json`、3 个快照的 `config_copy.command_prefixes`、`config/agent-orchestration.schema.json` 描述文本 | **活的功能 bug** | 已修 |
| **Gap B** | `README.md`、`CLAUDE.md`、`rules/AI-COLLABORATION-STANDARDS.md`、`collaboration/guides/USAGE_SCENARIOS_GUIDE.md`、`docs/ARCHAEOLOGY_CODE_INVENTORY.md` | 文档漂移 | 已修 |
| **Gap C** | `state_manager.TASK_CONTRACT_DEFAULT_ROLE_BY_ASSIGNEE["codex"]="AGENT_TEST"` | 角色派生层的语义边界 | **不改，钉死语义**（见下） |

#### Gap A 详述：为什么这是真 bug 而不是文档问题

`OrchestrationConfig.load()` 在工作区缺 `config/agent-orchestration.json` 时，
会拿 `config/agent-orchestration.template.json` 去冷启动。
模板里 `A.RUN→AGENT_ARCH` / `X.RUN→AGENT_EXEC` 是 `229062d` **之前**的倒挂映射，
于是**任何新工作区冷启动都会拿回倒挂版本** —— 正好把 `229062d` 想修掉的
语义（`A.RUN` = 执行位）又装回去。实测（改动前）：

```text
/tmp/prefix_bootstrap_probe → {'A.RUN': 'AGENT_ARCH', 'X.RUN': 'AGENT_EXEC', ...}
```

改动后重跑同一探针：

```text
/tmp/prefix_probe → {'A.RUN': 'AGENT_EXEC', 'X.RUN': 'AGENT_ARCH', 'C.RUN': 'AGENT_TEST'}
```

同理，`config/agent-orchestration.json` 里 3 个快照的 `config_copy`
是**回滚目标**（`rollback_to_snapshot()` 整份恢复 `config_copy`），
带着倒挂映射就等于"回滚 = 装回 bug"，一并对齐。

新增 4 条不变量测试守住这四处副本：

| 测试 | 守住的规则 |
|---|---|
| `test_builtin_default_prefixes_match_live_config` | 内置兜底默认值 == 仓库配置 |
| `test_template_prefixes_match_live_config` | 冷启动模板 == 仓库配置 |
| `test_snapshot_rollback_targets_match_live_config` | 每个快照的回滚目标 == 仓库配置 |
| `test_workspace_bootstrapped_from_template_matches_live_config` | **行为级**：空工作区从模板冷启动后拿到的映射 == 仓库配置 |

`docs/FACTS.generated.md` 里的旧映射**不手改** —— 该文件由
`scripts/gen_facts.sh` 自动生成（"自动生成，请勿手工编辑"），
夜间 CI 会重新生成它作为漂移信号。

#### Gap C 详述：为什么判定为「不改，但钉死语义」

`state_manager._default_assignee_role()` 在编排配置里**找不到该 provider 的绑定**时，
退到静态兜底表 `TASK_CONTRACT_DEFAULT_ROLE_BY_ASSIGNEE`。codex 在编排配置里
**没有绑定任何角色**，于是被派到 `AGENT_TEST` —— 而 `AGENT_TEST` 的在位者
是 `claude_code`。后果：codex 的工单派生出角色字母 `C`，与 claude_code
的 `AGENT_TEST` 席位同字母。

**判定：这不是字母池不重叠的违规，不改。** 三条理由：

1. **角色字母标识的是「席位」不是「厂商」。** 同一个席位换人坐，前缀当然不变 ——
   `resolve_hints("codex", AGENT_TEST)` 与 `resolve_hints("claude_code", AGENT_TEST)`
   都返回 `("C.RUN", "C.ACK")` 是**语义正确**的：两者都声明"我此刻坐 AGENT_TEST 席"。
2. **不产生误路由。** ACK 归属靠 `task_id` 判定
   （`scripts/agent_receipt_bridge.py` 的 `has_explicit_ack` 按 `task_id` + `source` 匹配），
   仓库里**不存在「前缀 → provider」的反向查找**；派发路由靠触发短语
   （`2X DISPATCH CODEX`），也不靠前缀字母。
3. **改掉的方案都更糟。** 把 codex 从静态表删掉 → 工单落进
   `TASK_CONTRACT_DEFAULT_ASSIGNEE_ROLE = "AGENT_EXEC"` → codex 冒充**正在被使用的**
   执行位（codearts_agent 的席位），比现在占用一个"咨询位"危害大。

唯一真实隐患：codex 一旦启用（当前 `connection_status=unavailable`、从未派发），
它 payload 里的 `C.RUN` 会指向 claude_code 占的席位。
已用 3 条测试把当前语义钉死，让以后要改它的人是有意为之：

| 测试 | 钉住的语义 |
|---|---|
| `test_derived_role_follows_orchestration_bindings` | 有绑定的 provider，派生角色必须是它占的席位之一 |
| `test_unbound_provider_derives_the_static_fallback_seat` | 无绑定的 provider 退到静态兜底表（codex → AGENT_TEST） |
| `test_role_letter_identifies_the_seat_not_the_vendor` | 角色字母标识席位（codex/claude_code 同为 AGENT_TEST 时同字母）；但无角色声明时 codex 走自己的 `O` |

#### 顺带清理的死代码

`ai_collab/role_prefix.py` 的 `FALLBACK_ROLE_BY_PROVIDER` 与
`resolve_role_for_provider()` **零调用者**（全仓 grep `.py`/`.md`/`.json` 确认），
且是 provider→role 映射的**第三份副本**（另两份在 `state_manager` 与编排配置）。
它承载的正是 codex→`AGENT_TEST` 那条陈旧断言，留着只会多一个漂移源。
已删除 —— 这类"映射散落多处"正是本次字母池事故的成因。

---

## 执行命令

```bash
# 验收命令（与工单 acceptance_commands 逐字一致，回执桥接会做子串校验）
python3 -m pytest tests/unit/test_ack_prefix_consistency.py tests/unit/test_role_prefix.py tests/unit/test_dispatch_trigger.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/ scripts/

# 补充验证
python3 -m pytest tests/unit/test_ack_prefix_consistency.py -q
python3 -m pytest tests/unit/test_role_prefix.py tests/unit/test_dispatch_trigger.py -q
python3 -m pytest tests/unit --cov=ai_collab --cov-report=term -q
python3 -m mypy ai_collab/
```

> **2026-10-27 补齐（结果工件门禁）**：本文件原先只写了**拆开**的
> `python3 -m pytest tests/unit/test_ack_prefix_consistency.py -q`，
> 而工单 `acceptance_commands[0]` 是**合并**写法
> （三个文件一次跑完）。回执桥接做的是**整串子串比对**，
> 拆开写不算命中 ⇒ 收口 `completed` 时被结果工件门禁挡住。
> 现把工单那条命令**逐字**补在验收块首位。
>
> 同时修正一处**实测数字**：原表里写「前缀相关用例（3 个文件）**54 passed**」，
> 实际是 **45 passed**。2026-10-27 逐 commit 复验（`git worktree` 检出
> `e88e1c8` / `5b9160e` / `2f72286` / `4af0efd` / `61afa3f` 逐个跑
> 同一条命令）⇒ 分别是 38 / 45 / 45 / 45 / 45，**54 在任何一个 commit
> 上都没出现过**。原数字无出处，按实测值更正。

## 测试结论

| 项 | 结果 |
|---|---|
| 前缀相关用例（3 个文件） | **45 passed**（二次排查后新增 9 条：4 条副本一致性 + 3 条角色派生 + 死代码清理后的回归；原写 54，实测无出处，2026-10-27 逐 commit 复验后更正） |
| 全量测试 | **2488 passed, 1 skipped**（`tests/unit` 口径；覆盖率 **88%** ≥ 门禁 85%） |
| ruff（`ai_collab/` `scripts/`） | 无新增问题 —— 与 HEAD 逐行 diff **完全一致**（10 条告警全在未触碰的 `sync_agent_memory.py` / `codearts_bridge_deliver.py`） |
| mypy（`ai_collab/`） | **Success: no issues found in 100 source files** |
| 行为级复验 | `resolve_hints("codex")` → `("O.RUN","O.ACK")`；`resolve_hints("claude_code", assignee_role="AGENT_ARCH")` → `("X.RUN","X.ACK")`；`resolve_ack_prefix("nobody")` → `"Z"` |
| codex 派单 payload | `build_handoff_payload(assignee="codex")` 里不再出现 `X.ACK|`，只有 `O.ACK|` |
| **模板冷启动（Gap A 行为级）** | 空工作区从 `agent-orchestration.template.json` 冷启动 → `{'A.RUN': 'AGENT_EXEC', 'X.RUN': 'AGENT_ARCH', 'C.RUN': 'AGENT_TEST'}`，与仓库配置一致 |

## 风险

| 风险 | 影响 | 处置 |
|---|---|---|
| 外部系统仍在按 `X.ACK` 识别 codex | 若有 codex 侧的历史脚本硬编码 `X.ACK`，新发的 `O.ACK` 会被认不出 | codex `connection_status=unavailable` 且未绑定角色，无在途任务；仓库内已全量 grep 确认无残留（仅本任务涉及的副本） |
| 协议表面变更 | codex 的 ACK 前缀变了 | codex 不参与实际派发（未绑定角色）；角色前缀一个都没动 |
| 未知 provider 的兜底从 `X` 变 `Z` | 极端情况下会发出 `Z.ACK` | 这正是意图：`Z` 不冒充任何角色；且比 `X` 更能被看出"未解析" |
| 文档修正涉及 4 个协议文档 | 若别处仍引用旧映射，可能不一致 | 已 grep 全仓 `X.RUN → AGENT_EXEC`，剩余命中只剩**历史记录**（本 RESULT / 任务工单的沿革表）与 `docs/FACTS.generated.md`（自动生成，不手改），二者都是应当保留的 |
| **改模板会改变新工作区的冷启动结果**（Gap A） | 依赖旧倒挂映射写脚本的人会受影响 | 旧映射是 `229062d` 已废弃的语义；仓库配置本来就是新映射，模板与它对齐属于**消除分叉**。已加 4 条不变量测试锁住「四处副本 == 仓库配置」 |
| **3 个快照的 `config_copy` 被改写** | 快照不再保留改动前的原样 | 快照的职责是**回滚目标**（`rollback_to_snapshot()` 整份恢复 `config_copy`），不是审计档案；审计靠 git 历史与 `history` 事件。带着倒挂映射的快照 = "回滚即装回 bug"，故一并对齐 |
| **删除 `FALLBACK_ROLE_BY_PROVIDER` / `resolve_role_for_provider()`** | 若外部有脚本 import 这两个符号会断 | 全仓 grep（`.py`/`.md`/`.json`）零引用，`ai_collab/__init__.py` 也未导出；均为仓内私有实现细节 |

## 回滚

```bash
# 回滚本任务全部改动
git revert <本任务提交>

# 若只回滚前缀分配（保留测试与文档修正）
#   把 codex 的兜底前缀从 O 改回 X：
#   - config/agent-orchestration.json 的 4 处 "fallback_ack_prefix": "O" → "X"
#   - ai_collab/role_prefix.py / ack_protocol.py / orchestration.py /
#     dispatch_trigger.py / scripts/agent_receipt_bridge.py 里的 codex 前缀
#   - 同步把 ai_collab/role_prefix.py 的 UNKNOWN_PROVIDER_PREFIX 改回 "X"

# 若只回滚 Gap A（模板/默认值的倒挂映射）
#   - config/agent-orchestration.template.json 的 A.RUN/X.RUN 换回
#   - ai_collab/orchestration.py 的 DEFAULT_COMMAND_PREFIXES 换回
#   - config/agent-orchestration.json 的 3 个快照 config_copy.command_prefixes 换回
#   ⚠️ 这会把「新工作区冷启动拿到倒挂映射」这个 bug 装回去，
#     且 4 条副本一致性不变量测试会失败（预期行为：回滚等于撤销修复）。
```

回滚后需同步跑：
`python3 -m pytest tests/unit/test_ack_prefix_consistency.py -q`
（不变量测试会失败 —— 因为它守的正是被回滚掉的那条规则，
这是预期行为：回滚等于撤销修复）。

---

## 配套产出

| 产出 | 位置 |
|---|---|
| 任务工单 | `collaboration/tasks/TASK-P1-PREFIX-DISJOINT-001.md` |
| 开发日志 | `logs/claude-code/2026-10/2026-10-22_codearts-collab-wiring.md` §13 |
| 派发指南（前缀表已更新） | `collaboration/guides/CODEARTS_DISPATCH_GUIDE.md` |

---

**相关提交**：（见 `git log --oneline -3`）
