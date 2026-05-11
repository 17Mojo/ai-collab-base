# Agent Session Dispatch Payload（自动生成）

- Trigger: `AUTO DISPATCH SYNC`
- Assignee: `claude_code` (Claude)
- GeneratedAt: `2026-04-12T21:35:11.719784`
- SourceOrders: `collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md`

## 新鲜度校验（必须执行）

在执行任务前，必须先校验本 payload 的新鲜度：

```bash
# 1. 检查 dispatch report 中的 generated_at
cat logs/task_dispatch_report.json | grep generated_at

# 2. 对比本 payload 的 GeneratedAt 与 dispatch report
# 如果时间差 > 5 分钟，则 payload 已过期

# 3. 如果 payload 已过期，执行一键修复：
python3 -m ai_collab.cli trigger --phrase '2X DISPATCH Claude' --target claude_code
```

**判定规则**：
- ✅ 新鲜：时间差 ≤ 5 分钟
- ⚠️  过期：时间差 > 5 分钟

**过期处理**：
1. 立即停止执行
2. 执行一键修复命令重新生成 payload
3. 使用新生成的 payload 继续执行

请将本文件完整发送到对应 Agent 会话，避免手工抽段造成漏项。

## 会话执行约束（必须遵守）

- 收到 `C.RUN` 后必须先读取本文件，再执行任务块。
- 系统级 RUN 只允许执行：`python3 -m ai_collab.cli run`（内置工作区门禁）。
- 禁止改为执行全局串联命令：`python3 -m ai_collab.cli dispatch && python3 -m ai_collab.cli receipt && python3 -m ai_collab.cli benefit`。
- 完成后仅回复一行 ACK；优先使用任务块中的 `python3 -m ai_collab.cli ack ...` 生成并原样回复：`C.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`。

## 发送给 `Claude` (`claude_code`)

### TASK-W2-DAY2-PACK-RATING-001

```text
【执行指令 | TASK-W2-DAY2-PACK-RATING-001】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY2-PACK-RATING-001 --ai claude_code --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
pytest tests/unit/cli/test_pack_rating.py -v

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-W2-DAY2-PACK-RATING-001.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY2-PACK-RATING-001 --ai claude_code --status testing --note "result ready for codex review"

5) 生成 ACK 协议行（工具输出，原样回复）
python3 -m ai_collab.cli ack --task-id TASK-W2-DAY2-PACK-RATING-001 --ai claude_code --status ok
```

### TASK-W2-DAY3-PACK-VERSION-001

```text
【执行指令 | TASK-W2-DAY3-PACK-VERSION-001】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY3-PACK-VERSION-001 --ai claude_code --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
pytest tests/unit/pack/test_version.py -v

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-W2-DAY3-PACK-VERSION-001.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY3-PACK-VERSION-001 --ai claude_code --status testing --note "result ready for codex review"

5) 生成 ACK 协议行（工具输出，原样回复）
python3 -m ai_collab.cli ack --task-id TASK-W2-DAY3-PACK-VERSION-001 --ai claude_code --status ok
```

### TASK-W2-DAY4-PACK-TEMPLATE-001

```text
【执行指令 | TASK-W2-DAY4-PACK-TEMPLATE-001】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY4-PACK-TEMPLATE-001 --ai claude_code --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
pytest tests/unit/pack/test_template.py -v

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-W2-DAY4-PACK-TEMPLATE-001.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-W2-DAY4-PACK-TEMPLATE-001 --ai claude_code --status testing --note "result ready for codex review"

5) 生成 ACK 协议行（工具输出，原样回复）
python3 -m ai_collab.cli ack --task-id TASK-W2-DAY4-PACK-TEMPLATE-001 --ai claude_code --status ok
```
