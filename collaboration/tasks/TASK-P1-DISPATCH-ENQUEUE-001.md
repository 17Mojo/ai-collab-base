---
task_id: TASK-P1-DISPATCH-ENQUEUE-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_ARCH
reviewer: user
primary_skill: planning-with-files
support_skills:
  - testing
  - documentation
created_at: 2026-10-23T11:30:00+08:00
status_updated_at: 2026-10-23T13:10:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_dispatch_intervention_wiring.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ai_collab/"
result_file: collaboration/results/RESULT-DISPATCH-ENQUEUE-2026-10-23.md
---

# TASK-P1-DISPATCH-ENQUEUE-001：派单即入队即送达

## 背景

干预队列（`ai_collab/intervention_queue.py`）原本**只有**
`ai_collab/session_health.py` 的 ACK 静默看门狗会写。
派单本身**不产生任何可投递的东西** —— 第一轮投递只能等下一轮
`cli sessions health` 跑起来、且看门狗判定「ACK 静默 > 120s」之后才发生。

实测链路证实了这一点：2026-10-23 00:47 那次真机投递
（`candidate_count=1, queued_count=1`）发生在 `sessions health` 那一轮，
不是派单那一刻。

## 目标

1. 派单当场把触发 payload 挂进干预队列；
2. 入队后立刻跑一次适配器完成投递 —— 首轮送达不等 120s；
3. 两条容易踩的坑用不变量测试锁住：
   - 状态不能是「在途」（会被适配器跳过）；
   - 同一 assignee 不得开出第二条干预（会在对方开出两个并发会话）。

## 改动

- `ai_collab/cli/_cli_main.py`
  - `_generate_trigger_payload_files()` 额外返回 `payload_files` 映射；
  - 新增 `_enqueue_dispatch_interventions()`（派单即入队）；
  - 新增 `_deliver_dispatch_interventions()`（派单即送达）；
  - `cmd_trigger()` 接上两步，结果写进触发报告。
- `ai_collab/cli/__init__.py`：导出两个新函数。
- `tests/unit/test_dispatch_intervention_wiring.py`（新建，10 条）。

## 验收命令

见 frontmatter。

## 风险与回滚

见结果文件 `collaboration/results/RESULT-DISPATCH-ENQUEUE-2026-10-23.md`。
