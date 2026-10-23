---
task_id: TASK-P1-PREFIX-DISJOINT-001
change_id: bugfix/no-spec
status: testing
priority: P1
assignee: claude_code
assignee_role: AGENT_ARCH
reviewer: user
status_updated_at: 2026-10-23T08:40:00+08:00
created_at: 2026-10-23T08:00:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_ack_prefix_consistency.py tests/unit/test_role_prefix.py tests/unit/test_dispatch_trigger.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/ scripts/"
result_file: collaboration/results/RESULT-PREFIX-DISJOINTNESS-2026-10-23.md
---

# TASK-P1-PREFIX-DISJOINT-001：ACK 前缀字母池不相交

## 背景

用户提问：**codex 仍解析到与 AGENT_ARCH 冲突的 X 前缀，"X 前缀"是否还有必要？**

调查发现这是**同一个字母被两套命名空间各自独立征用**的历史遗留，
并且 `X` 还在两处充当"解析不出来"的终极兜底。

### 字母是怎么撞上的（git 证据）

| 时间 | commit | 事件 | 当时 `X` 的含义 |
|---|---|---|---|
| 2026-05-11 | `e76d7ee` 初版 | provider 兜底表落定 `{"claude_code":"C","codearts_agent":"A","codex":"X"}` | **X = codex**（provider 兜底） |
| v3.0 | `77df0a5` 动态角色编排 | 引入角色命名空间 `A.RUN→AGENT_ARCH`、`X.RUN→AGENT_EXEC`、`C.RUN→AGENT_TEST` | **X = AGENT_EXEC**（角色前缀）——与 provider 侧同字母、不同义 |
| 2026-10-22 | `229062d` 命名空间收敛 | 为对齐 provider 侧把 A/X 对调：`A.RUN→AGENT_EXEC`、`X.RUN→AGENT_ARCH` | **X = AGENT_ARCH** —— codex 的 provider 兜底 X 没跟着动，撞车形成 |

provider 侧的前缀约定其实是"取名字里一个字母"（clau**d**e→C、codearts_**a**gent→A、
code**x**→X），角色侧也是单字母，两边字母池却是同一批 —— **必然**会有交集。

### 撞车的实际后果

`X.ACK` 无法判定发送方：

- codex 作为 provider 回 ACK → `X.ACK`
- claude_code 扮演 AGENT_ARCH 回 ACK → 角色前缀优先 → 也是 `X.ACK`

且 `cmd_ack --task-id none` 默认 `assignee=codex`，发的是全局 noop 广播
`X.ACK|task=none|status=noop|result=none` —— 与真实角色 ACK 同形。

## 目标

1. 让**角色字母池**与**provider 字母池**不相交，且用不变量测试锁住；
2. 去掉"解析不出来 → X"这个把"我不知道"伪装成真实角色的兜底；
3. 回答"X 前缀是否还有必要"：
   - 作为 **AGENT_ARCH 的角色前缀**：保留（协议表面，A/C/X 三元组已成文）；
   - 作为 **codex 的 provider 兜底前缀**：不再必要（codex 未绑定任何角色，
     `connection_status=unavailable`，实际不参与派发），改用角色池之外的 `O`。

## 执行步骤

1. `codex` 的 provider 兜底前缀 `X` → `O`（4 处配置 + 5 处代码副本）；
2. 解析不出 provider 时的终极兜底 `X` → 保留字母 `Z`；
3. 新增不变量测试：provider 兜底前缀不得撞上"它并未扮演"的角色前缀；
4. 同步修正协议文档里 `229062d` 遗留的陈旧映射（`X.RUN → AGENT_EXEC`）；
5. 跑全量测试 + ruff + mypy。

## 验收命令

见 frontmatter。

## 风险与回滚

见结果文件 `collaboration/results/RESULT-PREFIX-DISJOINTNESS-2026-10-23.md`。
