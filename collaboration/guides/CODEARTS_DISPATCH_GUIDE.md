# CodeArts 任务派发标准流程

## 概述

本文档固化 Claude Code → CodeArts 任务派发的标准流程，避免重复调查和调试。

**当前形态（2026-10-22 重写）**：整条链路已由 CLI + adapter + bridge 打通，
**不需要手工造 payload 文件**。旧版本文档描述的
`payload_codearts_agent_latest.json` / `collaboration/dispatch/payloads/` 一套
是历史遗留，当前链路不再读取，已删除。

---

## 全链路概览

```text
工单（collaboration/tasks/TASK_*.md + 控制面状态）
  │
  ├─ cli dispatch ──────────────► AGENT_DISPATCH_ORDERS_latest.md
  │                                （按执行方分组：## 发送给 `CodeArts`）
  │
  ├─ cli trigger --phrase "2X DISPATCH CodeArts"
  │                             ──► AGENT_TRIGGER_codearts_agent_latest.md
  │                                  （触发词 A.RUN / ACK 前缀 A.ACK）
  │
  ├─ 对方执行 A.RUN → 读 payload → 干活
  │
  ├─ 对方回 ACK：A.ACK|task=<id>|status=ok|result=<paths>
  │      └─ cli receipt ────────► testing → completed
  │
  └─ 若 120s 内无 ACK：
        cli ack-watchdog ──────► 自动重派 + 刷新 payload
        cli sessions health ───► 干预工单（intervention queue）
        cli sessions codearts-pull
                               ──► CODEARTS_PULL_EVENT_*.md
                                    └─ bridgeCommand（默认投递通道）
                                         └─ CodeArts Doer kernel 收到任务
```

一键入口（dispatch + trigger 串起来）：

```bash
python3 -m ai_collab.cli 2x codearts
```

---

## 派发清单（Checklist）

### 1. 任务文件准备

```text
collaboration/tasks/TASK_*.md
```

任务文件需包含契约段（PROTOCOL §7.3）：

- `change_id` — 关联的 OpenSpec 变更
- `assignee_role` — 角色代号（`AGENT_EXEC` 等）
- `assignee_provider` — provider（`codearts_agent` 等）
- 验收命令（可执行）
- 风险与回滚说明

**角色代号决定命令前缀**。当前编排：

| 角色 | provider | 触发词 | ACK 前缀 |
|------|----------|--------|----------|
| `AGENT_EXEC` | `codearts_agent` | `A.RUN` | `A.ACK` |
| `AGENT_ARCH` | `claude_code` | `X.RUN` | `X.ACK` |
| `AGENT_TEST` | `claude_code` | `C.RUN` | `C.ACK` |

权威来源是 `config/agent-orchestration.json` 的 `command_prefixes`；
`ai_collab/role_prefix.py` 负责把角色/provider 两套命名空间收敛成一套。

> ⚠️ **已知残留**：未绑定的 `codex` provider 兜底前缀也是 `X`，
> 与 `AGENT_ARCH` 的 `X.RUN` 撞车。目前 `codex` 没有绑定角色席位，
> 实际不影响派发；等它被绑定时需要重新分配前缀。

### 2. 控制面注册

```bash
python3 -m ai_collab.cli tasks register \
  --task-id TASK-P0-XXX-001 \
  --ai codearts_agent \
  --assignee codearts_agent \
  --assignee-role AGENT_EXEC \
  --change-id <change_id> \
  --description "任务描述" \
  --files ai_collab/xxx.py \
  --result-file collaboration/results/RESULT-P0-XXX-001.md \
  --acceptance-commands "pytest -q tests/unit/test_xxx.py"
```

### 3. 结果文件契约段（先补齐再派发）

结果文件必须含以下段落，否则收口门禁不通过：

```markdown
## 执行命令
## 验证结果
## 风险
## 回滚
```

### 4. 派发

```bash
# 完整链路（推荐）
python3 -m ai_collab.cli 2x codearts

# 或分步
python3 -m ai_collab.cli dispatch
python3 -m ai_collab.cli trigger --phrase "2X DISPATCH CodeArts" --target codearts_agent
```

派发前会过**工作区门禁**（`workspace-guard`）：source 域不干净会被拦下。
先提交自己的改动再派发。

### 5. 收口

```bash
# 对方回 ACK 后
python3 -m ai_collab.cli receipt
```

---

## 自动投递（bridge）机制

`.vscode/ai-collab.json` 的 `sessionOrchestration.codeartsAdapter`：

```json
{
  "enabled": true,
  "bridgeCommand": "python3 scripts/codearts_bridge_deliver.py --workspace {workspace} --event-file {event_file} --artifact-file {artifact_file} --intervention-id {intervention_id} --session-id {session_id} --assignee {assignee} --reason-code {reason_code}",
  "deliveryStatusOnSuccess": "queued_for_delivery",
  "eventDir": "collaboration/monitoring/codearts_pull_events"
}
```

`bridgeCommand` 占位符由 adapter 在调用前做 `str.format` 替换。
**改了 command 字符串必须同步改测试**
（`tests/unit/test_codearts_bridge_deliver.py` 会校验它是合法的 format 模板）。

### 投递通道

`scripts/codearts_bridge_deliver.py` 支持两条通道：

| 通道 | 机制 | 适用 |
|------|------|------|
| `cron`（默认） | `GET/POST /cag/cron/tasks` → `POST /cag/cron/tasks/fire` | 首选。kernel 自己建会话，不需要预置 CodeArts 会话 |
| `session` | `POST /session/{id}/message` | 已有活跃 CodeArts 会话时更快 |

手动试跑：

```bash
python3 scripts/codearts_bridge_deliver.py \
  --workspace . \
  --event-file collaboration/monitoring/codearts_pull_events/CODEARTS_PULL_EVENT_*.md \
  --artifact-file collaboration/monitoring/session_interventions/*.md \
  --intervention-id <id> --session-id <sid> \
  --assignee codearts_agent --reason-code ack_silence_after_run \
  --dry-run
```

### 凭据

kernel 走 HTTP Basic 认证（用户名默认 `codearts`）。密码按以下顺序解析：

1. 环境变量 `OPENCODE_SERVER_PASSWORD` / `CODEARTS_KERNEL_PASSWORD`
2. `~/.codeartsdoer/kernel-bridge.env` 里的 `OPENCODE_SERVER_PASSWORD`
3. `--allow-process-env-discovery`：从本机 kernel 进程环境读取（**默认关闭，需显式开启**）

三者都拿不到时 bridge **大声失败**（`缺少 kernel 密码`），不会静默降级。

#### 一次性凭据引导（推荐）

**由用户本人在本机终端执行一次**：

```bash
# 注意：要在仓库根目录下执行（脚本路径是相对的）
cd /Users/raymondna/Documents/AI-collab/ai-collab-base
python3 scripts/codearts_bridge_deliver.py --workspace . --setup-credentials
```

或者用绝对路径，在哪个目录跑都行：

```bash
python3 /Users/raymondna/Documents/AI-collab/ai-collab-base/scripts/codearts_bridge_deliver.py \
  --workspace /Users/raymondna/Documents/AI-collab/ai-collab-base \
  --setup-credentials
```

它会：

1. 发现正在运行的 kernel，取出它的 Basic Auth 密码
2. 写入 `~/.codeartsdoer/kernel-bridge.env`（权限 `0600`）
3. **不回显密码**（只打印"凭据已写入…密码未回显"）
4. 立即退出，**不做任何投递**

执行完这条命令后，日常投递走上面第 2 条（凭据文件）的常规路径，
**不再需要** `--allow-process-env-discovery`。

> 🔒 **为什么必须由用户自己跑**：这条命令会把本机 kernel 的密码落盘。
> 如果由 AI 助手代跑，密码就会进入 AI 会话上下文、shell 历史与对话记录，
> 等于绕过了凭据保护本身。AI 侧只负责写好这条命令、验证它可用，
> 执行动作留给用户。
>
> 凭据文件在 `~/.codeartsdoer/` 下，**不在仓库内**，不会被提交。

### 首次投递的时间点

codearts pull adapter 只消费 **intervention**，intervention 由 session_health 产生。
所以**第一次自动投递要等 ACK 超时阈值（默认 120s）之后**。
想立刻验证，用 `--dry-run` 手跑 bridge，或直接手动把 payload 贴给 CodeArts。

### 在途不重复投递（重要）

`queued_for_delivery` 的语义是「**已交给传输通道，等对方 ACK**」——
它既不是终态，也**不是**待投递状态。

pull adapter 默认**跳过**在途的 intervention，报告里会显式给出：

```text
skipped_in_flight_count: 1
skipped_in_flight_ids: ['intervention-fd04852f...']
```

只有投递失败（`failed`）才会自动重试。「对方收到没回」由 ACK watchdog
告警 + 重派机制处理，不是靠重复投递。

> ⚠️ 这条规则是踩过坑才加的：修复前每跑一次 `sessions health` 就会把
> 同一条 intervention 重投一次，在 CodeArts 那边建出一个个新会话，
> 并发改同一个工作区（实测 22:01 一次、22:55 又一次）。

**重派时会重新武装在途项**：跳过是「默认不重投」，但「ACK watchdog 判定
要重派」是一个**明确的**再发一次决定——这时如果不做重新武装，payload 刷新了
却送不出去，派单链路在最后一步断掉。所以 watchdog 判定 `redispatch` 时会
把该执行方的在途 intervention 重新武装成待投递，报告里给出：

```text
rearmed_count: 1
rearmed_by_assignee: {'codearts_agent': ['intervention-...']}
```

只动在途项：终态不动，失败项不动（本来就会自动重试），别家执行方不动。
**只告警不重派时不碰**——那是运维决定要不要重投。

运维确实需要重投时，显式开口子：

```bash
python3 -m ai_collab.cli sessions codearts-pull --force-redeliver
python3 -m ai_collab.cli sessions health --force-redeliver
```

### payload 必须带任务契约（重要）

派单 payload 的任务块必须自带**任务契约**，不能只有「任务 ID + 改状态的命令」：

```markdown
### TASK-P0-XXX-001

**任务描述**: <description>
**涉及文件**: `<file>`
**结果文件**（必须写）: `<result_file>`
**change_id**: `<change_id>`
**角色**: `AGENT_EXEC`（codearts_agent）
**任务工单**: `collaboration/tasks/TASK-P0-XXX-001.md`

#### 执行步骤
1. 先把状态翻成 implementing
2. 按任务描述实现，产出结果文件
3. 逐条跑验收命令
4. 写完结果文件后回一行 ACK
```

> ⚠️ **这一段是踩过坑才加的**（2026-10-22 真机实测）：payload 之前只有
> 任务 ID、改状态的命令和验收命令，**没有描述、没有结果文件路径**。
> 接收方只能从任务 ID 和验收命令里的文件名反推要做什么。
> 实测中 CodeArts 为此花了 5 分 27 秒、61 个回合翻仓库，
> **一个交付文件都没产出**。
>
> 任务记录里本来就有 `description` / `files` / `result_file` / `change_id` /
> `assignee_role`——`scripts/agent_dispatch_bridge.py` 的
> `_task_contract_lines()` 负责把它们渲染进任务块。

### payload 必须带工具约束（重要）

CodeArts 会话里有两个工具会把**整个会话卡死并中止**：

| 工具 | 实测表现 |
|---|---|
| `write` / `edit` | 工具状态永远停在 `running`，**文件不落盘**，会话随后中止 |
| `task`（派生子代理） | 报 `MessageAbortedError`，父会话与子会话一起中止 |

同期所有 `bash` / `read` / `todowrite` 调用都正常完成 —— 说明工具链本身没坏，
坏的是这两个调用。于是 payload 必须写明规避方式：

```markdown
#### 执行环境约束（真机实测，必须遵守）

- `write` / `edit`：实测会话在 `write` 调用上永久挂起，文件没有落盘，会话随后中止。
- `task`（派生子代理）：实测报 `MessageAbortedError`，父会话与子会话一起中止。

**写文件一律用 bash（heredoc）**：

```bash
cat > path/to/file.py <<'EOF'
...文件内容...
EOF
```

写完立刻自检，确认文件真的落盘了：

```bash
ls -l path/to/file.py && wc -l path/to/file.py
```

自己直接做完，不要派生子代理。
```

- `scripts/agent_dispatch_bridge.py` 的 `_execution_constraints_lines()` 负责渲染，
  **只对 `codearts_agent`** 生效（别家执行方不该看到这段）。
- `ai_collab/session_health.py` 的**干预正文**也带同一句 ——
  干预正文是对方会话看到的第一条消息，约束必须出现在最前面，
  而不是只藏在 payload 里等对方自己读到。

> ⚠️ **这一段也是踩过坑才加的**（2026-10-22→23 真机实测）：
> 前三次投递的会话全部以 `MessageAbortedError`（或无错误停住）结束、零产出。
> 复盘元数据发现，两个会话分别死在 `task` 与 `write` 调用上，
> 而 `hermes_target/` 与仓库里没有任何文件被写出来 —— 它就卡在写文件那一步。
> 加上约束后的投递（00:47:35）一次成功：54 个用例、95% 覆盖率。

### 重新投递的干净做法（不需要 --force-redeliver）

对方没产出、又不能重复投在途项时，**不要**直接上 `--force-redeliver`
（那会绕过在途保护、可能造成并发会话）。干净的做法是**刷新派单状态**：

```bash
python3 -m ai_collab.cli dispatch --target codearts_agent   # 刷新 dispatched_at
sleep 150                                                     # 等过 120s 静默阈值
python3 -m ai_collab.cli sessions health                     # 生成新干预
```

链路会自己走完：`dispatch` 刷新 `dispatched_at` → 旧干预被判失效并置为
`resolved`（**不再有在途项**）→ 静默阈值重新计时 → `health` 生成新干预 →
pull adapter 走常规路径自动投递 → bridge → kernel → 对方新会话。

实测（2026-10-23 00:45→00:53）：`dispatch` 00:45:17 → 新干预 00:47:35 →
对方会话建立 → 00:50:36 交付测试文件 → 00:53:11 交付结果文件 → 收口。
全程无 `--force-redeliver`、无并发会话。

### kernel 响应格式不统一（排查时必读）

kernel 的序列化**不统一**：

| 路由 | 返回格式 |
|---|---|
| `/cag/cron/tasks` | 标准 JSON |
| `/session`、`/session/{id}/message` | **Python 字面量格式**（单引号、`True`/`None`），不是合法 JSON |

bridge 已用 `parse_kernel_payload()` 兼容两种格式。若你直接用 curl 排查，
`/session` 的输出要按字面量解析，不要用 `json.loads`——
之前 bridge 把这类响应截断到 2000 字符，导致 9 个会话只剩第一条，
排查时完全看不出对方做了什么。

---

## 常见问题排查

### 问题 1：CodeArts 返回 `noop`

| 原因 | 排查 |
|------|------|
| 任务未注册 | `python3 -m ai_collab.cli tasks list` |
| payload 不存在 | 检查 `collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md` |
| payload 内容是"当前无待派发任务" | 派单指令包没有按执行方分组 → 查 `AGENT_DISPATCH_ORDERS_latest.md` 是否有 `## 发送给 \`CodeArts\`` 段 |
| 触发词与 ACK 前缀对不上 | 查工单 `assignee_role` 与 `config/agent-orchestration.json` 的 `command_prefixes` |

### 问题 2：`错误: 派单指令包不存在`

`trigger` 找不到 `--orders` 指定的那份指令包。检查：

- `cli dispatch` 是否真的写出了文件（路径由 `dispatch.orders` 配置或 `--orders` 决定）
- `trigger` 用的 `dispatch.orders` 与 `dispatch` 写出的路径是否一致

### 问题 3：bridge 报 `缺少 kernel 密码`

跑一次引导命令即可（**用户本人执行**，注意要在仓库根目录或用绝对路径）：

```bash
cd /Users/raymondna/Documents/AI-collab/ai-collab-base
python3 scripts/codearts_bridge_deliver.py --workspace . --setup-credentials
```

也可以手动创建 `~/.codeartsdoer/kernel-bridge.env` 写入
`OPENCODE_SERVER_PASSWORD=<password>`。详见上文「一次性凭据引导」。

> 若报 `can't open file '.../scripts/codearts_bridge_deliver.py'`，
> 说明当前目录不在仓库里 —— 脚本路径是相对的。

### 问题 4：workspace guard 拦截派发

```
source domain is not clean: source_dirty=19
```

共享工作区里还有未提交的 source 域改动。先提交再派发：

```bash
python3 -m ai_collab.cli stage-safe      # 按域安全暂存
git commit -m "..."
```

---

## 文件位置速查表

| 文件类型 | 位置 | 必需 |
|----------|------|------|
| 任务文件 | `collaboration/tasks/TASK_*.md` | ✅ |
| 结果文件 | `collaboration/results/RESULT_*.md` | ✅ |
| 派单指令包 | `collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md` | 自动 |
| 派单 payload | `collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md` | 自动 |
| 干预工件 | `collaboration/monitoring/session_interventions/*.md` | 自动 |
| pull event | `collaboration/monitoring/codearts_pull_events/*.md` | 自动 |
| 桥接审计副本 | `collaboration/monitoring/codearts_inbox/*.md` | 投递成功后生成 |
| 控制面状态 | `logs/collaboration_state.json` | 自动 |
| 派单状态 | `logs/agent_dispatch_state.json` | 自动 |
| 回执状态 | `logs/agent_receipt_state.json` | 自动 |

---

## 相关文件

| 用途 | 路径 |
|------|------|
| 桥接实现 | `scripts/codearts_bridge_deliver.py` |
| 派单桥接（任务契约渲染） | `scripts/agent_dispatch_bridge.py` |
| 前缀收敛 | `ai_collab/role_prefix.py` |
| CodeArts adapter | `ai_collab/adapters/codearts_adapter.py` |
| 干预队列（在途/重新武装） | `ai_collab/intervention_queue.py` |
| ACK watchdog（重派判定） | `ai_collab/ack_watchdog.py` |
| 干预正文（工具约束） | `ai_collab/session_health.py` |
| 编排配置 | `config/agent-orchestration.json` |
| Adapter 配置 | `.vscode/ai-collab.json` |
| 桥接测试 | `tests/unit/test_codearts_bridge_deliver.py` |
| 派单测试 | `tests/unit/test_agent_dispatch_bridge.py` |

---

**更新时间**: 2026-10-23
**维护者**: Claude Code (AGENT_ARCH)
**变更说明**: 全链路重写。原文档描述的手工 JSON payload 流程已废弃。
2026-10-23 补充真机实测结论：在途不重复投递、重派时重新武装、
payload 必须带任务契约、kernel 响应格式不统一。
2026-10-23（晚）补充：payload 必须带工具约束（write/edit、task 会带死会话）、
重新投递的干净做法（刷新派单状态而非 --force-redeliver）。
2026-10-23 已真机验证一次完整交付：54 个用例、95% 覆盖率、结果文件四段齐备。
