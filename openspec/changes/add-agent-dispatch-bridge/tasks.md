# Tasks

## 1. Implementation
- [x] 1.1 新增自动派单桥接脚本（候选识别、指令包生成、派发状态/历史落盘）
- [x] 1.2 在 CLI 增加 `dispatch` 命令，支持配置默认值与参数覆盖
- [x] 1.3 在初始化配置中增加 `dispatch` 默认配置段
- [x] 1.4 补齐单元测试（脚本行为、CLI 命令与路由）

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_cli.py`
- [x] 2.2 `python3 -m ai_collab.cli dispatch --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-agent-dispatch-bridge --strict`
