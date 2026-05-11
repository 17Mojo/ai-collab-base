# Tasks

## 1. Implementation
- [x] 1.1 在 CLI 增加 `hygiene` 命令（统一执行门禁 + stage-safe 流程）
- [x] 1.2 增加 `workspaceHygiene` 配置读取与默认值
- [x] 1.3 在 `receipt` 成功收口后接入即时治理触发（可配置开关）
- [x] 1.4 增加定时轮询执行入口（controller/daemon 模式可调用）
- [x] 1.5 增加治理快照记录（治理前后统计 + 候选清单摘要）

## 2. Quality Gates
- [x] 2.1 `python3 -m pytest -q tests/unit/test_cli.py tests/unit/test_safe_stage.py`
- [x] 2.2 `python3 -m ai_collab.cli hygiene --dry-run`
- [x] 2.3 `python3 -m ai_collab.cli receipt --dry-run`
- [x] 2.4 `python3 -m ai_collab.cli tasks validate-contract --scope active --strict`

## 3. OpenSpec Validation
- [x] 3.1 `openspec validate add-workspace-hygiene-automation --strict`
