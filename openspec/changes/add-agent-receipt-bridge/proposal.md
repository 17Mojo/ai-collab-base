# 增加自动回执桥接（Agent Receipt Bridge）

## Why

S9 第一步已实现自动派单，但 `testing -> completed` 仍依赖人工逐条核验并改状态，导致：
- 收口动作重复、吞吐受限
- 完成态节奏不稳定，易出现“结果已交付但任务未收口”
- 过程审计分散，不利于量化自动化收益

需要补齐“自动回执桥接”，将 testing 任务在满足证据门禁时自动收口并留痕。

## What Changes

- 新增自动回执脚本：
  - 检测 `testing` 状态候选任务
  - 复用完成态门禁（结果文件存在且章节完整）进行预校验
  - 自动执行 `testing -> completed`（支持 dry-run）
  - 写入回执报告、历史快照、回执状态与摘要
- 在 CLI 中新增 `receipt` 命令统一调用桥接脚本。
- 在初始化配置中增加 `receipt` 默认配置段。
- 补齐单元测试（脚本行为 + CLI 参数/路由）。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `scripts/agent_receipt_bridge.py`
  - `ai_collab/cli.py`
  - `tests/unit/test_agent_receipt_bridge.py`
  - `tests/unit/test_cli.py`
  - `.vscode/ai-collab.json`
  - `collaboration/PROTOCOL.md`
- 风险控制：
  - 仅对 `testing` 且满足门禁任务自动收口
  - 对存在 open patch 或 action_required 结论的任务自动跳过
