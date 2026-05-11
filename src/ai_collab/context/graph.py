"""
图谱上下文管理器

集成知识图谱到上下文管理系统中。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_collab.integrations.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
    NodeType,
    RelationType,
)


@dataclass
class GraphContext:
    """图谱上下文"""

    context_id: str
    query: str
    relevant_nodes: List[str]
    enriched_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "context_id": self.context_id,
            "query": self.query,
            "relevant_nodes": self.relevant_nodes,
            "enriched_data": self.enriched_data,
            "created_at": self.created_at.isoformat(),
        }


class GraphContextManager:
    """图谱上下文管理器"""

    def __init__(self, graph: Optional[KnowledgeGraph] = None):
        """
        初始化图谱上下文管理器

        Args:
            graph: 知识图谱实例
        """
        self._graph = graph or KnowledgeGraph()
        self._contexts: Dict[str, GraphContext] = {}

    def enrich_context(self, context: Any, max_nodes: int = 10) -> Dict[str, Any]:
        """
        使用图谱增强上下文

        Args:
            context: 上下文对象
            max_nodes: 最大节点数

        Returns:
            增强后的上下文数据
        """
        # 提取上下文中的关键信息
        query = self._extract_query(context)

        # 查找相关节点
        relevant_nodes = self._graph.find_similar_nodes(query, top_k=max_nodes)

        # 构建增强数据
        enriched_data = {
            "query": query,
            "relevant_nodes": [
                {
                    "node_id": node.node_id,
                    "content": node.content,
                    "type": node.node_type.value,
                    "metadata": node.metadata,
                }
                for node in relevant_nodes
            ],
            "key_nodes": [],
        }

        # 添加关键节点
        key_nodes = self._graph.find_key_nodes(top_k=5)
        for node_id, score in key_nodes:
            node = self._graph.get_node(node_id)
            if node:
                enriched_data["key_nodes"].append(
                    {"node_id": node_id, "content": node.content, "importance": score}
                )

        # 添加节点关系
        enriched_data["relations"] = []
        for node in relevant_nodes[:3]:  # 只处理前3个节点
            relations = self._graph.get_relations(node.node_id, direction="out")
            for relation in relations[:3]:  # 每个节点最多3个关系
                target_node = self._graph.get_node(relation.target_id)
                if target_node:
                    enriched_data["relations"].append(
                        {
                            "source": node.content[:30],
                            "target": target_node.content[:30],
                            "type": relation.relation_type.value,
                            "weight": relation.weight,
                        }
                    )

        return enriched_data

    def find_relevant_knowledge(
        self, query: str, context: Any, max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        查找相关知识

        Args:
            query: 查询字符串
            context: 上下文对象
            max_depth: 最大遍历深度

        Returns:
            相关知识列表
        """
        # 查找相似节点
        similar_nodes = self._graph.find_similar_nodes(query, top_k=5)

        results = []
        for node in similar_nodes:
            # BFS 遍历获取相关节点
            related_nodes = self._graph.bfs(node.node_id, max_depth=max_depth)

            # 构建知识项
            knowledge_item = {
                "node_id": node.node_id,
                "content": node.content,
                "type": node.node_type.value,
                "related": [
                    {"node_id": n.node_id, "content": n.content, "type": n.node_type.value}
                    for n in related_nodes[1:]  # 排除自己
                ],
            }

            results.append(knowledge_item)

        return results

    def build_from_documents(
        self, documents: List[Dict[str, Any]], extract_entities: bool = True
    ) -> KnowledgeGraph:
        """
        从文档构建知识图谱

        Args:
            documents: 文档列表
            extract_entities: 是否提取实体

        Returns:
            知识图谱实例
        """
        for i, doc in enumerate(documents):
            # 创建文档节点
            doc_node = KnowledgeNode(
                node_id=f"doc_{i}",
                content=doc.get("content", ""),
                node_type=NodeType.DOCUMENT,
                metadata=doc.get("metadata", {}),
            )
            self._graph.add_node(doc_node)

            # 提取概念
            if extract_entities:
                concepts = self._extract_concepts(doc.get("content", ""))
                for j, concept in enumerate(concepts):
                    # 创建概念节点
                    concept_node = KnowledgeNode(
                        node_id=f"concept_{i}_{j}", content=concept, node_type=NodeType.CONCEPT
                    )
                    self._graph.add_node(concept_node)

                    # 创建包含关系
                    relation = KnowledgeRelation(
                        source_id=doc_node.node_id,
                        target_id=concept_node.node_id,
                        relation_type=RelationType.CONTAINS,
                    )
                    self._graph.add_relation(relation)

        return self._graph

    def create_context(self, query: str, max_nodes: int = 10) -> str:
        """
        创建图谱上下文

        Args:
            query: 查询字符串
            max_nodes: 最大节点数

        Returns:
            上下文ID
        """
        # 查找相关节点
        relevant_nodes = self._graph.find_similar_nodes(query, top_k=max_nodes)

        # 生成上下文ID
        context_id = self._generate_context_id(query)

        # 创建上下文
        context = GraphContext(
            context_id=context_id, query=query, relevant_nodes=[n.node_id for n in relevant_nodes]
        )

        self._contexts[context_id] = context

        return context_id

    def get_context(self, context_id: str) -> Optional[GraphContext]:
        """获取上下文"""
        return self._contexts.get(context_id)

    def get_graph(self) -> KnowledgeGraph:
        """获取知识图谱"""
        return self._graph

    def _extract_query(self, context: Any) -> str:
        """从上下文提取查询"""
        if isinstance(context, dict):
            return context.get("query", context.get("content", ""))
        elif hasattr(context, "query"):
            return context.query
        elif hasattr(context, "content"):
            return context.content
        else:
            return str(context)

    def _extract_concepts(self, content: str) -> List[str]:
        """提取概念"""
        # 简单实现: 提取关键词
        import re

        words = re.findall(r"\b[A-Z][a-z]{2,}\b", content)  # 大写开头的词
        return list(set(words))[:10]  # 最多10个概念

    def _generate_context_id(self, query: str) -> str:
        """生成上下文ID"""
        import hashlib

        timestamp = datetime.now().isoformat()
        hash_input = f"{query}:{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"graph_ctx_{hash_value}"
