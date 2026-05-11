# 增加暗语触发派单指令包（2X Trigger）

## Why

当前自动派单链路已经可生成统一指令包，但“把指令准确发到 Claude / CodeArts 会话”仍依赖人工在大文件中复制粘贴，容易出现错位、漏段、发错会话等失误。

需要提供一个轻量“暗语触发”入口，让操作者用短指令（如 `2X DISPATCH`）快速生成按 Agent 拆分的会话派单文本，并保留触发审计记录。

## What Changes

- 新增 CLI `trigger` 命令，解析暗语（默认激活词 `2X`）并触发派单流程。
- 新增 CLI 极简命令层 `2x`，支持 `2x claude / 2x codearts / 2x all` 快速映射到 trigger 流程。
- 增加 `2x all` 智能收口：当无 `planning/pending` 但存在 `testing` 任务时自动执行 `receipt`，减少人工胶水步骤。
- 复用现有 `dispatch` 桥接，生成最新派单指令包后，自动拆分为：
  - Claude 会话派单文件
  - CodeArts 会话派单文件
- 新增触发审计日志（report + history），记录暗语、目标 Agent、输出文件和时间戳。
- 增加单元测试覆盖暗语解析、派单拆分输出和 CLI 路由。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/cli.py`
  - `ai_collab/dispatch_trigger.py`（新增）
  - `2x`（快捷入口脚本，调用 CLI 2x 子命令）
  - `tests/unit/test_dispatch_trigger.py`（新增）
  - `tests/unit/test_cli.py`
- 风险:
  - 初版仍是“生成可发送文本”，不直接自动发送到外部 Agent 聊天会话（避免不可控外发）。
