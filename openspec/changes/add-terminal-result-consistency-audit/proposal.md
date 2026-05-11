## Why
我们刚刚在 ACK/closeout 治理收尾时发现 `TASK-TD-20260318-SPAWN-AGENT-CLI-DIAGNOSTICS-CODEARTS-096` 存在控制面状态与结果报告状态头不一致的问题：`collaboration_state.json` 已判定为 `failed`，但 `result_file` 仍写成 `completed`。这类分裂不会被现有 ACK 门禁直接拦住，只能靠人工巡查发现，容易造成 operator 误判和规则漂移。

## What Changes
- 新增终态任务的 `state/result` 一致性审计能力，扫描任务状态与结果报告状态头是否一致
- 为合法 takeover 场景提供白名单解释口径：`ai_type != assignee` 本身不算异常，审计重点放在终态 state 与 result header 的一致性
- 输出机器可读报告与 Markdown 摘要，供 controller/operator 用于 closeout 巡检
- 支持在发现不一致时返回非零退出码，便于后续接入日常巡检或门禁

## Impact
- Affected specs: `task-governance`
- Affected code: `ai_collab/cli.py`, 新增或扩展审计模块, `tests/unit/test_cli.py` 及相关单测
