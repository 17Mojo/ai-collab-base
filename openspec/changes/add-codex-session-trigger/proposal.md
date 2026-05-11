## Why

当前协作协议已经正式定义了 Claude 的 `C.RUN` 与 CodeArts 的 `A.RUN`，但 Codex 侧仍缺少同等级的会话暗语。这会带来两个问题：

- 操作人需要记忆“Codex 例外规则”，增加心智负担。
- 调度协议在三方之间不对称，容易让 `RUN / noop / ACK` 的理解发生偏差。

需要为 Codex 增加正式的会话暗语 `X.RUN`，并让它在协议、派发产物和 ACK 格式上都与现有体系对齐。

## What Changes

- 在协作协议中新增 Codex 会话暗语 `X.RUN`，用于启动 Codex 当前轮次任务。
- 新增 Codex 回执格式 `X.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`。
- 扩展 trigger / 2x 派发链路，支持 Codex 目标与 `AGENT_TRIGGER_codex_latest.md` 产物。
- 约束 `X.RUN` 与 `C.RUN / A.RUN` 一样，执行前必须先进行 payload 新鲜度校验。
- 定义 Codex 的 `noop` 行为：当无 Codex 待执行任务时，返回 `X.ACK|task=none|status=noop|result=none`。
- 补充 CLI、触发链路与协议的单元测试，确保三类会话暗语行为一致。

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/cli.py`
  - `ai_collab/dispatch_trigger.py`
  - `collaboration/PROTOCOL.md`
  - `tests/unit/test_cli.py`
  - `tests/unit/test_dispatch_trigger.py`
- 风险:
  - 扩展 trigger 目标后，需要避免 Codex 与控制面默认行为互相混淆。
  - 需要明确 `X.RUN` 是“Codex 会话执行暗语”，不是替代 `run` CLI 命令。
