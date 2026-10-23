---
name: 任务契约 change_id 白名单与非法值的修正方式
description: ai_collab 任务契约校验器对 change_id 只认 bugfix/no-spec、legacy/task-contract-migration 或 openspec 真实变更；工单写 feature/no-spec 会被 tasks update 拒收（invalid=[change_id]），需用 --change-id 修正并留痕
type: project
from: Agent
---

## 事实

- **任务契约校验器对 `change_id` 有白名单**：只接受 `bugfix/no-spec`、`legacy/task-contract-migration`，或 openspec 的真实变更 id；**`feature/no-spec` 不在白名单**。
- **症状**：工单元数据写 `change_id: feature/no-spec` 时，`python3 -m ai_collab.cli tasks update --task-id <ID> --ai <agent> --status implementing` 被拒，报错形如 `invalid=[change_id]`，任务状态翻不到 `implementing`。
- **修正手段**：CLI 支持 `--change-id` 参数，可在 update 时把元数据改写为白名单值（例：`--change-id bugfix/no-spec`，同为「无 spec」标签），随后再正常翻状态。**该修正必须写进结果文件留痕**（说明工单原值、修正后的值、原因）。

**Why**: 2026-10-23 执行 `TASK-P1-DISPATCH-MODEL-FALLBACK-001` 派单时踩到：工单写的 `feature/no-spec` 不被契约校验器认可，导致「翻状态」这一步就被挡住。校验器只认 `bugfix/no-spec` / `legacy/task-contract-migration` / openspec 真实变更三种形态，其余一律拒收。工单模板与校验器白名单之间存在口径差，新写的工单容易再次踩坑。

**How to apply**:
1. 收到派单工单、准备 `tasks update` 报 `invalid=[change_id]` 时，先定位校验器白名单再决定取值，不要盲改工单源文件。
2. 优先用 CLI 的 `--change-id` 参数修正（保持元数据可追溯），不要直接编辑 `collaboration/tasks/*.md` 绕过流程。
3. 修正动作属「对工单契约的改写」，必须在结果文件的 `## 执行命令` / `## 风险` 段留痕，供复核方裁决。
4. 派单场景下「先翻状态再动手」是固定顺序；状态翻不动说明是契约校验问题，不是环境或权限问题。
