# RESULT — 范例三负向对照（TASK-EXAMPLE3-ACK-E2E-002）

> 这是**故意造的负向对照**，不是真实缺陷。
> 目的：证明 ACK / 回执 / 一致性审计三处门禁不是空转，而是真的能判错。

- **状态**: cancelled

## 执行命令

```bash
python3 -m ai_collab.cli tasks register \
  --task-id TASK-EXAMPLE3-ACK-E2E-002 --ai claude_code \
  --description "负向对照..." \
  --result-file collaboration/results/RESULT-EXAMPLE3-ACK-E2E-002-DOES-NOT-EXIST.md --apply

python3 -m ai_collab.cli dispatch --include-pending
python3 -m ai_collab.cli ack --task-id TASK-EXAMPLE3-ACK-E2E-002 --ai claude_code --status ok
python3 -m ai_collab.cli tasks update --task-id TASK-EXAMPLE3-ACK-E2E-002 --status testing --apply
python3 -m ai_collab.cli receipt
python3 -m ai_collab.cli tasks update --task-id TASK-EXAMPLE3-ACK-E2E-002 --status completed --apply
```

## 验证结果

### 测试结论

四条门禁对「缺产物」全部正确报错，负向对照成立：

| 门禁 | 实际输出 | 判定 |
|---|---|---|
| `ack` | `X.ACK\|task=TASK-EXAMPLE3-ACK-E2E-002\|status=ok\|result=...DOES-NOT-EXIST.md` | **不校验产物**（如实记录，不拦） |
| `receipt` | `result_file not found: ...DOES-NOT-EXIST.md`（`category: result_file_not_found`） | ✅ 拦下 |
| `tasks update --status completed` | `错误: 任务结果门禁失败: ... result_file not found` | ✅ 拦下 |
| `audit-result-consistency` | `type=missing_result_file state=cancelled result=<unparseable>` | ✅ 判出 |

顺带证实三件事实：

1. `ack` 是**声明**不是验收——它会对不存在的产物照发成功行。
2. 写入门禁**阻止**缺产物任务进入终态 ⇒ 一致性审计的 `missing_result_file` 分支
   在正常路径下不可达，只在「事后删除产物」时可达。
3. 任务停在 `testing` 且已 ACK 时，**看门狗（视为已 ACK 而排除）与一致性审计（非终态不扫）
   双双漏掉它**——这是当前状态机的一个真实盲区。

## 风险

- 本任务为造数据，`collaboration_state.json` 中留有一条 `cancelled` 记录，属**预期内**。
- 该记录的存在使一致性审计的参数面多一条 `audited`，不影响 `consistent` 判定。

## 回滚

```bash
python3 -m ai_collab.cli tasks update --task-id TASK-EXAMPLE3-ACK-E2E-002 --status cancelled --apply
rm -f collaboration/results/RESULT-EXAMPLE3-ACK-E2E-002-NEGATIVE-CONTROL.md
```

（`logs/collaboration_state.json` 未纳入版本控制，删除该条记录不影响仓库。）
