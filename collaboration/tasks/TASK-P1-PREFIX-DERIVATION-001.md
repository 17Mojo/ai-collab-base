---
task_id: TASK-P1-PREFIX-DERIVATION-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_ARCH
reviewer: user
status_updated_at: 2026-10-23T11:20:00+08:00
created_at: 2026-10-23T10:30:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_ack_prefix_derivation.py tests/unit/test_ack_prefix_consistency.py tests/unit/test_agent_receipt_bridge.py tests/unit/test_cli_ack.py -q"
  - "python3 -m pytest tests/unit/test_codearts_bridge_deliver.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/ scripts/"
result_file: collaboration/results/RESULT-PREFIX-DERIVATION-2026-10-23.md
---

# TASK-P1-PREFIX-DERIVATION-001：ACK 前缀派生路径分叉修复

## 背景

用户指示：**"处理后续工作"** —— 指上一轮 X 前缀分析（开发日志 §18.3）列出的
后续动作清单。

§18.3 当时写下的一条后续动作是：

> **修派生路径分叉（真缺陷）**：`ai_collab/cli/_cli_main.py` 的 `cmd_ack` 已经
> `manager.get_task(task_id)` 拿得到 `assignee_role`，改成与 `resolve_hints` 同源
> （角色优先）即可，让 AGENT_ARCH 的 ACK 真正带 `X.ACK`。

**这条描述本身是错的**（见「纠正」一节）：CLI ACK 路径早在 `229062d` 就已经是
角色优先了。真正的分叉在**回执桥接路径**。本工单按真证重做。

## 真证：分叉到底在哪

`logs/agent_ack_bridge_state.json` 的实测记录（修复前）：

| task_id | assignee | 工单角色 | 记录的 ACK 行 | 应为 |
|---|---|---|---|---|
| TASK-P1-GOV-CONVERGE-001 | claude_code | AGENT_ARCH | `C.ACK\|...` | `X.ACK\|...` |
| TASK-P1-PREFIX-DISJOINT-001 | claude_code | AGENT_ARCH | `C.ACK\|...` | `X.ACK\|...` |
| TASK-P0-CONSENSUS-ENGINE-001 | codearts_agent | AGENT_EXEC | `A.ACK\|...`（result 路径指向已删除的 `hermes_target/`） | 前缀对，路径错 |

三条记录的 `assignee_role` 字段**全是 `None`** —— 角色在写入链路里被整个丢掉了。

## 根因：三处，而不是一处

| # | 位置 | 缺陷 |
|---|---|---|
| 1 | `scripts/agent_receipt_bridge.py::ack_prefix_for()` | 纯 provider 优先，**完全不认识角色** |
| 2 | `scripts/agent_receipt_bridge.py::run_receipt()` 收口写记录 | 用 provider 前缀拼 `ack_line`，且记录里**不写** `assignee_role` |
| 3 | `ai_collab/ack_protocol.py::upsert_ack_bridge_item()` | 用角色算了 `ack_line` 前缀，但**记录里不落** `assignee_role` → 下一次只拿到 provider 的写入会把前缀降级回去 |

补一处次要缺陷：

| # | 位置 | 缺陷 |
|---|---|---|
| 4 | `ai_collab/cli/_cli_main.py::cmd_ack()` 工单不存在分支 | 拿不到工单角色时，不复用历史 ACK 记录里的角色 |

## 目标

1. 两条派生路径（CLI ACK / 回执桥接）对同一组 (provider, role) 给出**同一个前缀**；
2. 角色必须**落进 ACK 记录**，否则下一次写入会降级前缀；
3. 顺带修 `scripts/codearts_bridge_deliver.py::_remove_from_cron_store()` 的
   **锁纪律缺陷**（见下）；
4. 用不变量测试锁住 1–3。

## 附带修复：cron 兜底删除的锁纪律

上一轮的僵尸 cron 文件级清理里，`_remove_from_cron_store()` 有三处缺陷：

| 缺陷 | 后果 |
|---|---|
| `lock_path.exists()` 只**检测**不获取，`finally` 里却 `unlink()` 掉 | **删掉 kernel 自己持有的锁** —— kernel 会以为自己没在写，与本进程并发写同一份存储 |
| 注释写「自己创建过就清掉」，代码判断的却是「存在」 | 注释与实现不符（commit message 不撒谎原则） |
| 临时文件名固定 `scheduled_tasks.json.tmp` | 与 kernel 自己的临时文件可能撞名 |

## 验收命令

见 frontmatter。

## 风险与回滚

见结果文件 `collaboration/results/RESULT-PREFIX-DERIVATION-2026-10-23.md`。
