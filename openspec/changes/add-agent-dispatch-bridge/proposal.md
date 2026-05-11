# 增加自动派单桥接（Agent Dispatch Bridge）

## Why

当前协作链路在治理与验收上已经稳定，但“派单指令下发”仍依赖人工复制粘贴，导致：
- 人工触点偏多，吞吐受限
- 指令模板不一致，回报质量波动
- 难以追踪“是否已派发、是否重复派发”

需要一个轻量自动化桥接层，把 `planning/pending` 任务转成可执行的 Agent 指令包与可审计派发记录。

## What Changes

- 新增自动派单脚本：
  - 扫描工单状态，识别待派发候选
  - 生成按 Agent 分组的派单指令 Markdown
  - 写入派发状态文件与历史快照（支持去重与可选重派）
- 在 CLI 中新增 `dispatch` 命令，统一入口执行桥接脚本。
- 新增测试覆盖（脚本行为 + CLI 路由/参数）。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `scripts/agent_dispatch_bridge.py`
  - `ai_collab/cli.py`
  - `tests/unit/test_agent_dispatch_bridge.py`
  - `tests/unit/test_cli.py`
- 风险:
  - 初版只做“生成与记录”，不直接驱动外部会话执行；仍需人工发送一次。
