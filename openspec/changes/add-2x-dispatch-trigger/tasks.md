# Tasks

## 1. Implementation
- [x] 1.1 新增暗语解析与派单拆分模块（2X trigger parser + orders splitter）
- [x] 1.2 在 CLI 增加 `trigger` 命令，支持 `--phrase`、`--target`、`--copy` 等参数
- [x] 1.3 将触发结果写入 report/history，输出按 Agent 会话文件
- [x] 1.4 增加极简命令层 `2x`（`2x claude / 2x codearts / 2x all`）并映射 trigger
- [x] 1.5 增加仓库级 `2x` 快捷脚本，直接调用 CLI 子命令
- [x] 1.6 增加 `2x all` 智能收口（无待派发任务时自动 receipt，支持 --dispatch-only 关闭）

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_dispatch_trigger.py tests/unit/test_cli.py`
- [x] 2.2 `python3 -m ai_collab.cli trigger --phrase "2X DISPATCH" --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli 2x all --dry-run`
- [x] 2.4 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-2x-dispatch-trigger --strict`
