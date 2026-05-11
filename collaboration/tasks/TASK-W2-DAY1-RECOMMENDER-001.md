---
task_id: TASK-W2-DAY1-RECOMMENDER-001
change_id: add-session-orchestration-control-plane
status: completed
assignee: codearts_agent
reviewer: claude
primary_skill: machine_learning
support_skills: ["testing", "data_structures"]
acceptance_commands: "pytest tests/unit/context/test_recommender.py -v --cov=src/ai_collab/context/recommender"
created_at: 2026-04-05T08:00:00
estimated_hours: 1.5
priority: P0
---

# TASK-W2-DAY1-RECOMMENDER-001

## 任务描述

Track B Day 1: 推荐引擎基础 - 实现基于场景的上下文推荐算法

## 详细任务

### B1.1 推荐数据模型设计 (30min)

**位置**: `src/ai_collab/context/recommender.py`

**数据模型**:

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RecommendationType(Enum):
    """推荐类型"""
    FILE = "file"  # 文件推荐
    CONTEXT = "context"  # 上下文推荐
    NEXT_ACTION = "next_action"  # 下一步操作

@dataclass
class RecommendationScore:
    """推荐分数"""
    score: float  # 0.0 - 1.0
    reason: str  # 推荐原因
    confidence: float  # 置信度

@dataclass
class Recommendation:
    """推荐项"""
    rec_id: str
    rec_type: RecommendationType
    item_id: str  # file path / context id
    title: str
    description: str
    score: RecommendationScore
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RecommendationHistory:
    """推荐历史"""
    history_id: str
    recommendations: List[Recommendation] = field(default_factory=list)
    context_scenario: str
    accepted_ids: List[str] = field(default_factory=list)  # 用户接受的推荐
    timestamp: datetime = field(default_factory=datetime.now)
```

### B1.2 推荐算法实现 (45min)

**位置**: `src/ai_collab/context/recommender.py`

**功能**:
- `recommend_files(scenario, active_files)` - 基于场景推荐文件
- `recommend_context(scenario, user_history)` - 基于历史推荐上下文
- `recommend_next(current_context)` - 推荐下一步操作

**算法**:
1. 基于场景的文件频率分析
2. 基于文件扩展名的相关性
3. 基于文件目录的相关性

### B1.3 推荐接口 (15min)

**位置**: `src/ai_collab/context/recommender.py`

**接口**:
- `ContextRecommender` 类
- `get_recommendations()` - 获取推荐列表
- `accept_recommendation()` - 用户接受推荐
- `reject_recommendation()` - 用户拒绝推荐

## 验收标准

- ✅ 推荐数据模型完成
- ✅ 推荐算法实现
- ✅ 推荐准确度 ≥ 75%
- ✅ 测试覆盖率 ≥ 80%

## 验收命令

```bash
pytest tests/unit/context/test_recommender.py -v --cov=src/ai_collab/context/recommender
```

## 交付物

- src/ai_collab/context/recommender.py
- tests/unit/context/test_recommender.py

---

**创建人**: Claude (技术合伙人)
**执行人**: codearts_agent
**预计开始**: 2026-04-06
**预计完成**: 2026-04-06
