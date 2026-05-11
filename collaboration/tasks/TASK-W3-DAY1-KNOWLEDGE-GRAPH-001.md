# TASK-W3-DAY1-KNOWLEDGE-GRAPH-001

Week 3 Day 1: NotebookLM 知识图谱

---

## 任务信息

- **Task ID**: `TASK-W3-DAY1-KNOWLEDGE-GRAPH-001`
- **优先级**: P0
- **复杂度**: 中高
- **预计耗时**: 1.5h
- **负责人**: codearts_agent
- **状态**: pending

---

## 任务描述

实现 NotebookLM 知识图谱系统，支持：
1. 知识节点定义和管理
2. 知识关系映射
3. 图谱遍历算法
4. 关键节点识别

---

## 实现要求

### 1. 数据模型 ([src/ai_collab/integrations/knowledge_graph.py](src/ai_collab/integrations/knowledge_graph.py))

**核心类**:

```python
from enum import Enum
from typing import Dict, List, Set, Optional

class NodeType(Enum):
    """节点类型"""
    CONCEPT = "concept"       # 概念节点
    DOCUMENT = "document"     # 文档节点
    ENTITY = "entity"         # 实体节点
    REFERENCE = "reference"   # 引用节点

class RelationType(Enum):
    """关系类型"""
    CONTAINS = "contains"         # 包含关系
    REFERS_TO = "refers_to"       # 引用关系
    IS_RELATED = "is_related"     # 相关关系
    DEPENDS_ON = "depends_on"     # 依赖关系
    SIMILAR_TO = "similar_to"     # 相似关系

@dataclass
class KnowledgeNode:
    """知识节点"""
    node_id: str
    content: str
    node_type: NodeType
    embeddings: Optional[List[float]]
    metadata: Dict[str, Any]

    def distance_to(self, other: 'KnowledgeNode') -> float
    def to_dict(self) -> Dict[str, Any]

@dataclass
class KnowledgeRelation:
    """知识关系"""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float  # 关系权重 0-1

    def reverse(self) -> 'KnowledgeRelation'
    def to_dict(self) -> Dict[str, Any]
```

**图谱引擎**:

```python
class KnowledgeGraph:
    """知识图谱引擎"""

    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._relations: Dict[str, List[KnowledgeRelation]] = {}

    # 节点操作
    def add_node(self, node: KnowledgeNode) -> bool
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]
    def remove_node(self, node_id: str) -> bool
    def find_nodes_by_type(self, node_type: NodeType) -> List[KnowledgeNode]
    def find_similar_nodes(self, query: str, top_k: int = 10) -> List[KnowledgeNode]

    # 关系操作
    def add_relation(self, relation: KnowledgeRelation) -> bool
    def get_relations(self, node_id: str, direction: str = "both") -> List[KnowledgeRelation]
    def remove_relation(self, source_id: str, target_id: str) -> bool

    # 图谱遍历算法
    def bfs(self, start_id: str, max_depth: int = 2) -> List[KnowledgeNode]
    def dfs(self, start_id: str, max_depth: int = 2) -> List[KnowledgeNode]
    def get_shortest_path(self, source: str, target: str) -> List[str]

    # 节点重要性计算
    def calculate_pagerank(self, damping: float = 0.85, iterations: int = 100) -> Dict[str, float]
    def calculate_betweenness(self) -> Dict[str, float]
    def find_key_nodes(self, top_k: int = 5) -> List[tuple[str, float]]

    # 可视化数据导出
    def to_graphviz(self) -> str
```

---

### 2. 上下文集成 ([src/ai_collab/context/graph.py](src/ai_collab/context/graph.py))

**知识图谱上下文管理器**:

```python
class GraphContextManager:
    """图谱上下文管理器"""

    def __init__(self, graph: KnowledgeGraph):
        self._graph = graph

    def enrich_context(self, context: Any, max_nodes: int = 10) -> Dict[str, Any]:
        """使用图谱增强上下文"""

    def find_relevant_knowledge(self, query: str, context: Any) -> List[Dict[str, Any]]:
        """查找相关知识"""

    def build_from_documents(self, documents: List[str]) -> KnowledgeGraph:
        """从文档构建知识图谱"""
```

---

### 3. 测试 ([tests/unit/integrations/test_knowledge_graph.py](tests/unit/integrations/test_knowledge_graph.py))

**测试类**:

| 测试类 | 测试数量 | 覆盖内容 |
|--------|---------|---------|
| TestKnowledgeNode | 3 | 节点数据序列化/距离计算 |
| TestKnowledgeRelation | 3 | 关系数据/反转 |
| TestKnowledgeGraph | 12 | CRUD/BFS/DFS/PageRank |
| TestGraphContextManager | 4 | 上下文增强/知识查找 |

**总测试数**: 22

---

## 验收标准

- ✅ 节点和关系数据模型完整
- ✅ 图谱遍历算法正确 (BFS/DFS)
- ✅ PageRank 算法实现正确
- ✅ 关键节点识别准确
- ✅ 上下文集成功能正常
- ✅ 测试覆盖率 ≥ 80%
- ✅ 所有测试通过 (22/22)

---

## 执行步骤

1. 创建数据模型 `src/ai_collab/integrations/knowledge_graph.py`
2. 实现知识图谱引擎
3. 实现遍历算法 (BFS/DFS)
4. 实现 PageRank 和重要性计算
5. 创建上下文管理器
6. 编写测试
7. 运行验收命令

---

## 验收命令

```bash
# 运行单元测试
pytest tests/unit/integrations/test_knowledge_graph.py -v

# 运行覆盖率检查
pytest tests/unit/integrations/test_knowledge_graph.py --cov=src.ai_collab.integrations.knowledge_graph --cov-report=term
```

---

## 依赖关系

- 依赖 `src/ai_collab/context/schema.py` (Context 数据结构)
- 可选择集成 `src/ai_collab/integrations/notebooklm.py` (知识抽取)

---

## 预期输出

- `src/ai_collab/integrations/knowledge_graph.py` (知识图谱引擎)
- `src/ai_collab/context/graph.py` (图谱上下文管理器)
- `tests/unit/integrations/test_knowledge_graph.py` (测试文件)
- `collaboration/results/RESULT_TASK-W3-DAY1-KNOWLEDGE-GRAPH-001.md` (结果报告)

---

**任务创建时间**: 2026-04-05 19:50
**任务状态**: pending
