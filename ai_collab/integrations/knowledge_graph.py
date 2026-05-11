"""
NotebookLM 知识图谱引擎

支持知识节点管理、关系映射、图谱遍历和关键节点识别。
"""

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class NodeType(Enum):
    """节点类型"""

    CONCEPT = "concept"  # 概念节点
    DOCUMENT = "document"  # 文档节点
    ENTITY = "entity"  # 实体节点
    REFERENCE = "reference"  # 引用节点


class RelationType(Enum):
    """关系类型"""

    CONTAINS = "contains"  # 包含关系
    REFERS_TO = "refers_to"  # 引用关系
    IS_RELATED = "is_related"  # 相关关系
    DEPENDS_ON = "depends_on"  # 依赖关系
    SIMILAR_TO = "similar_to"  # 相似关系


@dataclass
class KnowledgeNode:
    """知识节点"""

    node_id: str
    content: str
    node_type: NodeType
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def distance_to(self, other: "KnowledgeNode") -> float:
        """
        计算与另一个节点的距离

        Args:
            other: 另一个节点

        Returns:
            距离值 (0-1)
        """
        if not self.embeddings or not other.embeddings:
            return 1.0

        if len(self.embeddings) != len(other.embeddings):
            return 1.0

        # 余弦距离
        dot_product = sum(a * b for a, b in zip(self.embeddings, other.embeddings))
        norm_a = math.sqrt(sum(a * a for a in self.embeddings))
        norm_b = math.sqrt(sum(b * b for b in other.embeddings))

        if norm_a == 0 or norm_b == 0:
            return 1.0

        similarity = dot_product / (norm_a * norm_b)
        distance = 1 - similarity

        return max(0.0, min(1.0, distance))

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "node_type": self.node_type.value,
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeNode":
        """从字典反序列化"""
        return cls(
            node_id=data["node_id"],
            content=data["content"],
            node_type=NodeType(data["node_type"]),
            embeddings=data.get("embeddings"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class KnowledgeRelation:
    """知识关系"""

    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0  # 关系权重 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证权重"""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be between 0 and 1, got {self.weight}")

    def reverse(self) -> "KnowledgeRelation":
        """
        反转关系

        Returns:
            反转后的关系
        """
        # 反转关系类型
        reverse_map = {
            RelationType.CONTAINS: RelationType.CONTAINS,  # 包含关系是对称的
            RelationType.REFERS_TO: RelationType.REFERS_TO,  # 引用关系反转
            RelationType.IS_RELATED: RelationType.IS_RELATED,  # 相关关系是对称的
            RelationType.DEPENDS_ON: RelationType.DEPENDS_ON,  # 依赖关系反转
            RelationType.SIMILAR_TO: RelationType.SIMILAR_TO,  # 相似关系是对称的
        }

        return KnowledgeRelation(
            source_id=self.target_id,
            target_id=self.source_id,
            relation_type=reverse_map.get(self.relation_type, self.relation_type),
            weight=self.weight,
            metadata=self.metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeRelation":
        """从字典反序列化"""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            weight=data.get("weight", 1.0),
            metadata=data.get("metadata", {}),
        )


class KnowledgeGraph:
    """知识图谱引擎"""

    def __init__(self):
        """初始化知识图谱"""
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._relations: Dict[str, List[KnowledgeRelation]] = defaultdict(list)
        self._reverse_relations: Dict[str, List[KnowledgeRelation]] = defaultdict(list)

    # 节点操作

    def add_node(self, node: KnowledgeNode) -> bool:
        """
        添加节点

        Args:
            node: 知识节点

        Returns:
            是否成功
        """
        if node.node_id in self._nodes:
            return False

        self._nodes[node.node_id] = node
        return True

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """
        获取节点

        Args:
            node_id: 节点ID

        Returns:
            知识节点或None
        """
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """
        移除节点

        Args:
            node_id: 节点ID

        Returns:
            是否成功
        """
        if node_id not in self._nodes:
            return False

        # 移除节点
        del self._nodes[node_id]

        # 移除相关关系
        if node_id in self._relations:
            del self._relations[node_id]
        if node_id in self._reverse_relations:
            del self._reverse_relations[node_id]

        # 移除其他节点指向该节点的关系
        for source_id in list(self._relations.keys()):
            self._relations[source_id] = [
                r for r in self._relations[source_id] if r.target_id != node_id
            ]

        for target_id in list(self._reverse_relations.keys()):
            self._reverse_relations[target_id] = [
                r for r in self._reverse_relations[target_id] if r.source_id != node_id
            ]

        return True

    def find_nodes_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        """
        按类型查找节点

        Args:
            node_type: 节点类型

        Returns:
            节点列表
        """
        return [node for node in self._nodes.values() if node.node_type == node_type]

    def find_similar_nodes(self, query: str, top_k: int = 10) -> List[KnowledgeNode]:
        """
        查找相似节点

        Args:
            query: 查询字符串
            top_k: 返回数量

        Returns:
            相似节点列表
        """
        # 简单实现: 按内容相似度排序
        query_lower = query.lower()
        scored_nodes = []

        for node in self._nodes.values():
            # 计算内容重叠度
            content_lower = node.content.lower()
            if query_lower in content_lower or content_lower in query_lower:
                score = 1.0
            else:
                # 计算词重叠
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                if query_words and content_words:
                    overlap = len(query_words & content_words)
                    score = overlap / max(len(query_words), len(content_words))
                else:
                    score = 0.0

            scored_nodes.append((node, score))

        # 排序并返回 top_k
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        return [node for node, score in scored_nodes[:top_k] if score > 0]

    # 关系操作

    def add_relation(self, relation: KnowledgeRelation) -> bool:
        """
        添加关系

        Args:
            relation: 知识关系

        Returns:
            是否成功
        """
        if relation.source_id not in self._nodes or relation.target_id not in self._nodes:
            return False

        # 检查是否已存在
        for existing in self._relations[relation.source_id]:
            if (
                existing.target_id == relation.target_id
                and existing.relation_type == relation.relation_type
            ):
                return False

        self._relations[relation.source_id].append(relation)
        self._reverse_relations[relation.target_id].append(relation)

        return True

    def get_relations(self, node_id: str, direction: str = "both") -> List[KnowledgeRelation]:
        """
        获取节点的关系

        Args:
            node_id: 节点ID
            direction: 方向 (out/in/both)

        Returns:
            关系列表
        """
        if direction == "out":
            return self._relations.get(node_id, [])
        elif direction == "in":
            return self._reverse_relations.get(node_id, [])
        else:
            out_relations = self._relations.get(node_id, [])
            in_relations = self._reverse_relations.get(node_id, [])
            return out_relations + in_relations

    def remove_relation(self, source_id: str, target_id: str) -> bool:
        """
        移除关系

        Args:
            source_id: 源节点ID
            target_id: 目标节点ID

        Returns:
            是否成功
        """
        if source_id not in self._relations:
            return False

        original_len = len(self._relations[source_id])
        self._relations[source_id] = [
            r for r in self._relations[source_id] if r.target_id != target_id
        ]

        if target_id in self._reverse_relations:
            self._reverse_relations[target_id] = [
                r for r in self._reverse_relations[target_id] if r.source_id != source_id
            ]

        return len(self._relations[source_id]) < original_len

    # 图谱遍历算法

    def bfs(self, start_id: str, max_depth: int = 2) -> List[KnowledgeNode]:
        """
        广度优先搜索

        Args:
            start_id: 起始节点ID
            max_depth: 最大深度

        Returns:
            遍历的节点列表
        """
        if start_id not in self._nodes:
            return []

        visited = set()
        queue = deque([(start_id, 0)])
        result = []

        while queue:
            node_id, depth = queue.popleft()

            if node_id in visited or depth > max_depth:
                continue

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)

            # 添加邻居节点
            for relation in self._relations.get(node_id, []):
                if relation.target_id not in visited:
                    queue.append((relation.target_id, depth + 1))

            for relation in self._reverse_relations.get(node_id, []):
                if relation.source_id not in visited:
                    queue.append((relation.source_id, depth + 1))

        return result

    def dfs(self, start_id: str, max_depth: int = 2) -> List[KnowledgeNode]:
        """
        深度优先搜索

        Args:
            start_id: 起始节点ID
            max_depth: 最大深度

        Returns:
            遍历的节点列表
        """
        if start_id not in self._nodes:
            return []

        visited = set()
        result = []

        def _dfs(node_id: str, depth: int):
            if node_id in visited or depth > max_depth:
                return

            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)

            # 访问邻居节点
            for relation in self._relations.get(node_id, []):
                _dfs(relation.target_id, depth + 1)

            for relation in self._reverse_relations.get(node_id, []):
                _dfs(relation.source_id, depth + 1)

        _dfs(start_id, 0)
        return result

    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """
        获取最短路径

        Args:
            source: 源节点ID
            target: 目标节点ID

        Returns:
            路径节点ID列表
        """
        if source not in self._nodes or target not in self._nodes:
            return []

        if source == target:
            return [source]

        # BFS 寻找最短路径
        visited = {source}
        queue = deque([(source, [source])])

        while queue:
            node_id, path = queue.popleft()

            # 检查邻居
            neighbors = set()
            for relation in self._relations.get(node_id, []):
                neighbors.add(relation.target_id)
            for relation in self._reverse_relations.get(node_id, []):
                neighbors.add(relation.source_id)

            for neighbor in neighbors:
                if neighbor == target:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    # 节点重要性计算

    def calculate_pagerank(self, damping: float = 0.85, iterations: int = 100) -> Dict[str, float]:
        """
        计算 PageRank

        Args:
            damping: 阻尼系数
            iterations: 迭代次数

        Returns:
            节点ID到PageRank值的映射
        """
        if not self._nodes:
            return {}

        n = len(self._nodes)
        node_ids = list(self._nodes.keys())

        # 初始化
        pagerank = {node_id: 1.0 / n for node_id in node_ids}

        # 计算出度
        out_degree = {}
        for node_id in node_ids:
            out_degree[node_id] = len(self._relations.get(node_id, []))

        # 迭代计算
        for _ in range(iterations):
            new_pagerank = {}

            for node_id in node_ids:
                # 计算入链贡献
                incoming_sum = 0.0
                for relation in self._reverse_relations.get(node_id, []):
                    source_id = relation.source_id
                    if out_degree[source_id] > 0:
                        incoming_sum += pagerank[source_id] / out_degree[source_id]

                # PageRank 公式
                new_pagerank[node_id] = (1 - damping) / n + damping * incoming_sum

            pagerank = new_pagerank

        return pagerank

    def calculate_betweenness(self) -> Dict[str, float]:
        """
        计算介数中心性

        Returns:
            节点ID到介数中心性的映射
        """
        if not self._nodes:
            return {}

        betweenness = {node_id: 0.0 for node_id in self._nodes}

        # 对每对节点计算最短路径
        node_ids = list(self._nodes.keys())
        for i, source in enumerate(node_ids):
            for target in node_ids[i + 1 :]:
                path = self.get_shortest_path(source, target)
                if len(path) > 2:
                    # 中间节点的介数增加
                    for node_id in path[1:-1]:
                        betweenness[node_id] += 1.0

        # 归一化
        n = len(node_ids)
        if n > 2:
            normalize = (n - 1) * (n - 2) / 2
            for node_id in betweenness:
                betweenness[node_id] /= normalize

        return betweenness

    def find_key_nodes(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        查找关键节点

        Args:
            top_k: 返回数量

        Returns:
            (节点ID, 重要性分数) 列表
        """
        # 计算 PageRank
        pagerank = self.calculate_pagerank()

        # 排序
        sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)

        return sorted_nodes[:top_k]

    # 可视化数据导出

    def to_graphviz(self) -> str:
        """
        导出为 GraphViz DOT 格式

        Returns:
            DOT 格式字符串
        """
        lines = ["digraph KnowledgeGraph {"]

        # 添加节点
        for node_id, node in self._nodes.items():
            label = node.content[:20].replace('"', '\\"')
            lines.append(f'    "{node_id}" [label="{label}", type="{node.node_type.value}"];')

        # 添加关系
        added_edges = set()
        for source_id, relations in self._relations.items():
            for relation in relations:
                edge_key = (source_id, relation.target_id)
                if edge_key not in added_edges:
                    lines.append(
                        f'    "{source_id}" -> "{relation.target_id}" [label="{relation.relation_type.value}", weight="{relation.weight}"];'
                    )
                    added_edges.add(edge_key)

        lines.append("}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "relations": [
                relation.to_dict()
                for relations in self._relations.values()
                for relation in relations
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """从字典反序列化"""
        graph = cls()

        for node_data in data.get("nodes", []):
            node = KnowledgeNode.from_dict(node_data)
            graph.add_node(node)

        for relation_data in data.get("relations", []):
            relation = KnowledgeRelation.from_dict(relation_data)
            graph.add_relation(relation)

        return graph
