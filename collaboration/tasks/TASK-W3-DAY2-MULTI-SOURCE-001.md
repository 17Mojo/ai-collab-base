# TASK-W3-DAY2-MULTI-SOURCE-001

Week 3 Day 2: 多源知识聚合

---

## 任务信息

- **Task ID**: `TASK-W3-DAY2-MULTI-SOURCE-001`
- **优先级**: P0
- **复杂度**: 中高
- **预计耗时**: 2h
- **负责人**: codearts_agent
- **状态**: implementing

---

## 任务描述

实现多源知识聚合功能，支持：
1. 多源知识抽取
2. 知识去重和合并
3. 交叉验证机制
4. 置信度计算

## 实现要求

### 1. 数据模型 ([src/ai_collab/integrations/multi_source.py](src/ai_collab/integrations/multi_source.py))

**核心类**:

```python
@dataclass
class KnowledgeSource:
    """知识源"""
    source_id: str
    source_type: str  # notebooklm/file/api
    content: str
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class AggregatedKnowledge:
    """聚合知识"""
    content: str
    sources: List[KnowledgeSource]
    cross_validation: Dict[str, bool]
    overall_confidence: float
```

**核心引擎**:

```python
class KnowledgeAggregator:
    """知识聚合引擎"""

    def add_source(self, source: KnowledgeSource) -> str
    def aggregate(self, query: str, max_sources: int = 5) -> AggregatedKnowledge
    def deduplicate(self, sources: List[KnowledgeSource]) -> List[KnowledgeSource]
    def cross_validate(self, sources: List[KnowledgeSource]) -> Dict[str, bool]
    def calculate_confidence(self, knowledge: AggregatedKnowledge) -> float
```

### 2. 上下文集成 ([src/ai_collab/context/aggregator.py](src/ai_collab/context/aggregator.py))

**上下文聚合管理器**:

```python
class ContextAggregator:
    """上下文聚合管理器"""

    def aggregate_from_sources(self, sources: List[str], context: Any) -> AggregatedKnowledge
    def extract_knowledge(self, source_type: str, content: str) -> KnowledgeSource
    def merge_knowledge(self, sources: List[KnowledgeSource]) -> AggregatedKnowledge
```

### 3. 测试 ([tests/unit/context/test_aggregator.py](tests/unit/context/test_aggregator.py))

**测试类**:

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| TestKnowledgeSource | 3 | 源数据模型 |
| TestKnowledgeAggregator | 10 | 聚合引擎核心 |
| TestContextAggregator | 5 | 上下文集成 |

**总测试数**: 18

---

## 验收标准

- ✅ 知识源抽取正常
- ✅ 去重算法有效
- ✅ 交叉验证准确
- ✅ 置信度计算合理
- ✅ 上下文集成功能正常
- ✅ 测试覆盖率 >= 80%
- ✅ 所有测试通过 (18/18)

---

## 执行步骤

1. 创建多源知识引擎 `src/ai_collab/integrations/multi_source.py`
2. 实现去重和交叉验证算法
3. 创建上下文聚合管理器 `src/ai_collab/context/aggregator.py`
4. 编写测试
5. 运行验收命令

---

## 验收命令

```bash
# 运行单元测试
PYTHONPATH=. python3 -m pytest tests/unit/context/test_aggregator.py -v

# 运行覆盖率检查
PYTHONPATH=. python3 -m pytest tests/unit/context/test_aggregator.py --cov=src.ai_collab.integrations.multi_source --cov-report=term
```

---

## 依赖关系

- 依赖 `src/ai_collab/integrations/knowledge_graph.py` (Day 1 完成)
- 依赖 `src/ai_collab/integrations/notebooklm.py` (知识源)

---

## 预期输出

- `src/ai_collab/integrations/multi_source.py` (多源知识引擎)
- `src/ai_collab/context/aggregator.py` (上下文聚合管理器)
- `tests/unit/context/test_aggregator.py` (测试文件)
- `collaboration/results/RESULT_TASK-W3-DAY2-MULTI-SOURCE-001.md` (结果报告)

---

**任务创建时间**: 2026-04-06 10:00
**任务状态**: implementing
