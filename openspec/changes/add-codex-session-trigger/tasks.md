## 1. Implementation
- [x] 1.1 扩展 trigger/2x 目标解析，支持 Codex 目标与 `2x codex`
- [x] 1.2 生成 Codex 专属 payload 文件 `collaboration/monitoring/AGENT_TRIGGER_codex_latest.md`
- [x] 1.3 在协议文档中新增 `X.RUN / X.ACK` 语义、noop 规则与新鲜度校验说明
- [x] 1.4 对齐 CLI/触发链路的默认输出与审计日志，确保 Codex 目标可追踪

## 2. Quality Gates
- [x] 2.1 `python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_dispatch_trigger.py`
- [x] 2.2 `python3 -m ai_collab.cli trigger --phrase "2X DISPATCH CODEX" --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli 2x codex --dry-run`
- [x] 2.4 `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-codex-session-trigger --strict`
