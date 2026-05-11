## Why

当前 `codex` 工作流需要手工串联 `plan -> progress -> run -> sync` 四条命令，操作成本高且容易遗漏同步步骤。

## What Changes

- 新增 `python3 -m ai_collab.cli codex exec` 子命令，一次执行完整流水线：
  - 动态角色规划（plan）
  - 生成进度文件（progress）
  - 调用 Codex 执行（run）
  - 回写协作状态（sync）
- 复用现有参数（`--intent`、`--model`、`--step`、`--max-timeout`、`--task-id` 等）。
- 更新 README 与集成文档，补充新命令与使用建议。
- 增加 CLI 单元测试，验证成功和失败分支。

## Impact

- Affected specs: `codex-collaboration`（新增）
- Affected code:
  - `ai_collab/cli.py`
  - `README.md`
  - `docs/CC_CLAUDE_CODEX_INTEGRATION.md`
  - `tests/unit/test_cli_codex_exec.py`
