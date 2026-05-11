# Tasks

## 1. Implementation
- [x] 1.1 新增自动回执桥接脚本（testing 候选识别、完成态门禁复用、状态收口、审计落盘）
- [x] 1.2 在 CLI 增加 `receipt` 命令，支持配置默认值与参数覆盖
- [x] 1.3 在初始化配置中增加 `receipt` 默认配置段
- [x] 1.4 更新协作协议文档，补充回执桥接命令与输出路径
- [x] 1.5 补齐单元测试（脚本行为、CLI 命令与路由）

## 2. Quality Gates
- [x] 2.1 `pytest -q tests/unit/test_agent_receipt_bridge.py tests/unit/test_cli.py`
- [x] 2.2 `python3 -m ai_collab.cli receipt --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-agent-receipt-bridge --strict`
