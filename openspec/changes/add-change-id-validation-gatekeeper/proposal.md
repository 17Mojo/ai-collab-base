# 增加工单 change_id 强校验门禁

## Why

S3 已完成历史任务契约迁移，但 `change_id` 目前仅校验“非空字符串”，无法保证与真实 OpenSpec 变更绑定。  
这会导致工单虽然字段齐全，却可能绑定无效变更编号，破坏治理可追溯性。

## What Changes

- 在任务契约校验中新增 `change_id` 强校验：
  - 允许白名单标签：`bugfix/no-spec`、`legacy/task-contract-migration`
  - 其他值必须匹配 OpenSpec change 命名规范并对应存在的 change 目录（含 archive）
- 保持现有 `tasks validate-contract` 与 implementing 门禁逻辑不变，仅提升校验严格度
- 补充单元测试，覆盖“合法 change_id / 非法 change_id”两类场景

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/state_manager.py`
  - `tests/unit/test_state_manager.py`
- 风险:
  - 非法 change_id 的旧工单会在校验中暴露，需要人工修正或迁移
