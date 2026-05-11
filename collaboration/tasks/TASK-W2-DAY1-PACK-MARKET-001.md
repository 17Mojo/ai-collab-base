---
task_id: TASK-W2-DAY1-PACK-MARKET-001
change_id: add-pack-market-infrastructure
status: pending
assignee: claude_code
reviewer: claude
primary_skill: backend_development
support_skills: ["testing", "database"]
acceptance_commands: "pytest tests/unit/pack/test_market.py -v --cov=src/ai_collab/pack/market"
created_at: 2026-04-05T08:00:00
estimated_hours: 2
priority: P0
---

# TASK-W2-DAY1-PACK-MARKET-001

## 任务描述

Track A Day 1: Pack 市场基础架构 - 数据模型 + 存储层 + 管理接口

## 详细任务

### A1.1 Pack 市场数据模型设计 (45min)

**位置**: `src/ai_collab/pack/market.py`

**数据模型**:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

class PackStatus(Enum):
    """Pack 状态"""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

@dataclass
class PackListing:
    """市场 Pack 列表项"""
    pack_id: str
    pack_name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    status: PackStatus = PackStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class PackRating:
    """Pack 评价"""
    rating_id: str
    pack_id: str
    user_id: str
    rating: int  # 1-5
    title: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class UserFeedback:
    """用户反馈"""
    feedback_id: str
    pack_id: str
    user_id: str
    feedback_type: str  # bug, suggestion, request
    content: str
    created_at: datetime = field(default_factory=datetime.now)
```

### A1.2 Pack 市场存储层 (45min)

**位置**: `src/ai_collab/pack/market_store.py`

**功能**:
- SQLite 表设计
- PackListing CRUD
- PackRating CRUD
- 搜索索引

### A1.3 Pack 市场管理接口 (30min)

**位置**: `src/ai_collab/pack/market_api.py`

**接口**:
- `list_packs()` - 列出所有 Pack
- `get_pack(pack_id)` - 获取 Pack 详情
- `search_packs(query)` - 搜索 Pack
- `filter_by_category(category)` - 按分类筛选

## 验收标准

- ✅ 数据模型定义完成
- ✅ SQLite 表创建成功
- ✅ CRUD 操作正常工作
- ✅ 基础查询接口可用
- ✅ 测试覆盖率 ≥ 80%

## 验收命令

```bash
pytest tests/unit/pack/test_market.py -v --cov=src/ai_collab/pack/market
```

## 交付物

- src/ai_collab/pack/market.py
- src/ai_collab/pack/market_store.py
- src/ai_collab/pack/market_api.py
- tests/unit/pack/test_market.py
- data/packs_market.db (SQLite)

---

**创建人**: Claude (技术合伙人)
**执行人**: claude_code
**预计开始**: 2026-04-06
**预计完成**: 2026-04-06
