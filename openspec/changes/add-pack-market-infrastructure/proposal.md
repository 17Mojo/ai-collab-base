## Why

当前项目需要 Pack 市场功能，支持：
- Pack 发布与发现
- 用户评分与反馈
- 分类筛选与搜索

缺乏统一规范会导致实现不一致、难以审计，且无法与现有 Pack 规范体系（requirement-conversion、runtime-style、lifecycle）形成闭环。

## What Changes

- 新增 Pack 市场数据模型（PackListing, PackRating, UserFeedback）
- 新增 Pack 市场存储层（SQLite）
- 新增 Pack 市场管理接口（list/search/filter）
- 定义评分与反馈规范约束
- 与 prompt-pack-lifecycle 状态对接

## Impact

- Affected specs: `pack-market`（新增）
- Affected code:
  - `src/ai_collab/pack/market.py`
  - `src/ai_collab/pack/market_store.py`
  - `src/ai_collab/pack/market_api.py`
  - `tests/unit/pack/test_market.py`
- 风险控制:
  - 评分系统需要防止滥用（单用户评分限制）
  - 反馈需要审核机制（status 字段）
  - 与现有 Pack 规范保持一致（不可变性、生命周期）
