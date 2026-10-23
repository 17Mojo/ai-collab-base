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

`tests/unit/test_ack_prefix_consistency.py` 新增 4 条：

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

---

## 执行命令

```bash
# 验证命令
python3 -m pytest tests/unit/test_ack_prefix_consistency.py \
                 tests/unit/test_role_prefix.py \
                 tests/unit/test_dispatch_trigger.py -q
python3 -m pytest tests/ -q
python3 -m ruff check ai_collab/ scripts/
python3 -m mypy ai_collab/role_prefix.py ai_collab/ack_protocol.py \
          ai_collab/dispatch_trigger.py ai_collab/orchestration.py
```

## 验证结果

| 项 | 结果 |
|---|---|
| 前缀相关用例（3 个文件） | **45 passed** |
| 全量测试 | **2797 passed, 6 skipped**（较改动前 2787 +10：4 条不变量 + 6 条投递残留体检） |
| ruff（改动涉及的 10 个文件） | 无新增问题（4 条告警在 HEAD 上已存在，行号位移而已） |
| mypy（6 个源文件） | 无新增问题（1 条 `agent_receipt_bridge.py:187` 在 HEAD 上已存在） |
| 行为级复验 | `resolve_hints("codex")` → `("O.RUN","O.ACK")`；`resolve_hints("claude_code", assignee_role="AGENT_ARCH")` → `("X.RUN","X.ACK")`；`resolve_ack_prefix("nobody")` → `"Z"` |
| codex 派单 payload | `build_handoff_payload(assignee="codex")` 里不再出现 `X.ACK|`，只有 `O.ACK|` |

## 风险

| 风险 | 影响 | 处置 |
|---|---|---|
| 外部系统仍在按 `X.ACK` 识别 codex | 若有 codex 侧的历史脚本硬编码 `X.ACK`，新发的 `O.ACK` 会被认不出 | codex `connection_status=unavailable` 且未绑定角色，无在途任务；仓库内已全量 grep 确认无残留（仅本任务涉及的副本） |
| 协议表面变更 | codex 的 ACK 前缀变了 | codex 不参与实际派发（未绑定角色）；角色前缀一个都没动 |
| 未知 provider 的兜底从 `X` 变 `Z` | 极端情况下会发出 `Z.ACK` | 这正是意图：`Z` 不冒充任何角色；且比 `X` 更能被看出"未解析" |
| 文档修正涉及 4 个协议文档 | 若别处仍引用旧映射，可能不一致 | 已 grep 全仓 `X.RUN → AGENT_EXEC`，剩余命中（`MENU_INTERACTION_SPEC.md:680` 等）本就写的是 `AGENT_ARCH`，无需改 |

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
