## Why

Pack Market 的 SQLite 存储层缺少 feedback_type 的 CHECK 约束，导致绕过 Python 层直接写入数据库时可能插入非法值。rating 已有 CHECK 约束 (rating >= 1 AND rating <= 5)，但 feedback_type 缺失对应的枚举约束。

这是 Support (CodeArts) 在边界验证测试中发现的典型问题：Python dataclass 有 `__post_init__` 验证，但 SQLite 层缺少补充防线。

## What Changes

- 新增 SQLite CHECK 约束: `feedback_type IN ('bug', 'suggestion', 'request')`
- 补充边界测试: 测试非法 feedback_type 直接写入数据库
- 更新 OpenSpec spec delta: 记录约束规范

## Impact

- Affected specs: `pack-market` (MODIFIED)
- Affected code:
  - `src/ai_collab/pack/market_store.py` (line 84: 添加 CHECK 约束)
  - `tests/unit/pack/test_market.py` (补充边界测试)
- 风险控制:
  - 数据库 schema 变更需要迁移脚本（新表创建自动应用，现有数据库需重建）
  - 向后兼容：现有合法数据不受影响