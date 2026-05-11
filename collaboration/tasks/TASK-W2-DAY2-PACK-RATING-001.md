---
name: Task - Week 2 Day 2 - Track A
description: Pack 评价系统实现
assignee: claude_code
estimated_hours: 2
priority: P0
change_id: add-session-orchestration-control-plane
reviewer: codex
primary_skill: cli-dev
---

# TASK-W2-DAY2-PACK-RATING-001

## 任务描述

Track A Day 2: Pack 评价系统 - 实现用户对 Pack 的评价功能

## 实施步骤

### 1. 评价 CLI 命令 (1h)

创建以下 CLI 命令组 `pack rating`:

- `pack rating add <pack_id> <score> [--title] [--content]` - 添加评价
  - 评分范围: 1-5
  - 支持标题和详细内容
  - 自动更新 Pack 平均评分

- `pack rating get <pack_id>` - 获取 Pack 评分信息
  - 平均评分
  - 评价总数
  - 评分分布

- `pack rating reviews <pack_id>` - 列出 Pack 评价
  - 分页支持
  - 按时间排序

- `pack rating delete <rating_id>` - 删除评价
  - 仅限评价作者

### 2. 评价统计增强 (0.5h)

增强市场 API 统计功能:

- 评分分布图 (1-5 星各数量)
- 近期评价趋势
- 高质量评价筛选 (4+ 星且带内容)

### 3. 测试与集成 (0.5h)

- CLI 命令测试
- 集成到 `PackMarketAPI`
- 确保与 Day 1 存储层兼容

## 验收标准

```bash
# CLI 命令可用
python3 -m ai_collab.cli pack rating add test_pack 5 --title "Great" --content "Excellent work"

# 评分统计准确
python3 -m ai_collab.cli pack rating get test_pack

# 评价列表正常
python3 -m ai_collab.cli pack rating reviews test_pack
```

## 交付物

- `src/ai_collab/cli/pack_rating.py` (CLI 命令)
- 测试文件 `tests/unit/cli/test_pack_rating.py`
- 结果报告 `RESULT_TASK-W2-DAY2-PACK-RATING-001.md`

## 依赖

- 依赖: TASK-W2-DAY1-PACK-MARKET-001 ✅
- 数据模型: `PackRating`, `PackStatus`
- 存储层: `PackMarketStore`

## 风险

**低风险**: 已有市场基础设施，仅需添加 CLI 层
