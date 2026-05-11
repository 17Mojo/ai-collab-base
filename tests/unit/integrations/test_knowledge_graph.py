"""
测试知识图谱功能
"""

from datetime import datetime

import pytest

from ai_collab.context.graph import GraphContextManager
from ai_collab.integrations.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelation,
    NodeType,
    RelationType,
)


class TestKnowledgeNode:
    """测试知识节点"""

    def test_create_node(self):
        """测试创建节点"""
        node = KnowledgeNode(
            node_id="node_001",
            content="Python is a programming language",
            node_type=NodeType.CONCEPT,
        )

        assert node.node_id == "node_001"
        assert node.content == "Python is a programming language"
        assert node.node_type == NodeType.CONCEPT
        assert isinstance(node.created_at, datetime)

    def test_node_distance(self):
        """测试节点距离计算"""
        node1 = KnowledgeNode(
            node_id="node_001",
            content="Content 1",
            node_type=NodeType.CONCEPT,
            embeddings=[1.0, 0.0, 0.0],
        )

        node2 = KnowledgeNode(
            node_id="node_002",
            content="Content 2",
            node_type=NodeType.CONCEPT,
            embeddings=[0.0, 1.0, 0.0],
        )

        distance = node1.distance_to(node2)
        assert 0 <= distance <= 1

    def test_node_serialization(self):
        """测试节点序列化"""
        node = KnowledgeNode(
            node_id="node_001",
            content="Test content",
            node_type=NodeType.DOCUMENT,
            embeddings=[0.5, 0.5],
            metadata={"key": "value"},
        )

        # 序列化
        data = node.to_dict()
        assert data["node_id"] == "node_001"
        assert data["node_type"] == "document"

        # 反序列化
        restored = KnowledgeNode.from_dict(data)
        assert restored.node_id == node.node_id
        assert restored.content == node.content


class TestKnowledgeRelation:
    """测试知识关系"""

    def test_create_relation(self):
        """测试创建关系"""
        relation = KnowledgeRelation(
            source_id="node_001",
            target_id="node_002",
            relation_type=RelationType.REFERS_TO,
            weight=0.8,
        )

        assert relation.source_id == "node_001"
        assert relation.target_id == "node_002"
        assert relation.relation_type == RelationType.REFERS_TO
        assert relation.weight == 0.8

    def test_relation_reverse(self):
        """测试关系反转"""
        relation = KnowledgeRelation(
            source_id="node_001",
            target_id="node_002",
            relation_type=RelationType.DEPENDS_ON,
            weight=0.9,
        )

        reversed_rel = relation.reverse()
        assert reversed_rel.source_id == "node_002"
        assert reversed_rel.target_id == "node_001"
        assert reversed_rel.weight == 0.9

    def test_relation_serialization(self):
        """测试关系序列化"""
        relation = KnowledgeRelation(
            source_id="node_001",
            target_id="node_002",
            relation_type=RelationType.SIMILAR_TO,
            weight=0.7,
        )

        data = relation.to_dict()
        assert data["source_id"] == "node_001"
        assert data["relation_type"] == "similar_to"

        restored = KnowledgeRelation.from_dict(data)
        assert restored.source_id == relation.source_id


class TestKnowledgeGraph:
    """测试知识图谱"""

    @pytest.fixture
    def graph(self):
        """创建图谱"""
        return KnowledgeGraph()

    @pytest.fixture
    def setup_graph(self, graph):
        """设置图谱"""
        # 添加节点
        nodes = [
            KnowledgeNode("node_001", "Python programming", NodeType.CONCEPT),
            KnowledgeNode("node_002", "Data science", NodeType.CONCEPT),
            KnowledgeNode("node_003", "Machine learning", NodeType.CONCEPT),
            KnowledgeNode("node_004", "Deep learning", NodeType.CONCEPT),
        ]

        for node in nodes:
            graph.add_node(node)

        # 添加关系
        relations = [
            KnowledgeRelation("node_001", "node_002", RelationType.IS_RELATED),
            KnowledgeRelation("node_002", "node_003", RelationType.IS_RELATED),
            KnowledgeRelation("node_003", "node_004", RelationType.IS_RELATED),
        ]

        for relation in relations:
            graph.add_relation(relation)

        return graph

    def test_add_node(self, graph):
        """测试添加节点"""
        node = KnowledgeNode("node_001", "Test", NodeType.CONCEPT)

        assert graph.add_node(node)
        assert not graph.add_node(node)  # 重复添加

    def test_get_node(self, graph):
        """测试获取节点"""
        node = KnowledgeNode("node_001", "Test", NodeType.CONCEPT)
        graph.add_node(node)

        retrieved = graph.get_node("node_001")
        assert retrieved is not None
        assert retrieved.content == "Test"

        assert graph.get_node("non_existent") is None

    def test_remove_node(self, setup_graph):
        """测试移除节点"""
        assert setup_graph.remove_node("node_001")
        assert setup_graph.get_node("node_001") is None
        assert not setup_graph.remove_node("node_001")

    def test_find_nodes_by_type(self, setup_graph):
        """测试按类型查找节点"""
        nodes = setup_graph.find_nodes_by_type(NodeType.CONCEPT)
        assert len(nodes) == 4

    def test_find_similar_nodes(self, setup_graph):
        """测试查找相似节点"""
        similar = setup_graph.find_similar_nodes("Python", top_k=2)
        assert len(similar) > 0
        assert similar[0].node_id == "node_001"

    def test_add_relation(self, graph):
        """测试添加关系"""
        node1 = KnowledgeNode("node_001", "A", NodeType.CONCEPT)
        node2 = KnowledgeNode("node_002", "B", NodeType.CONCEPT)
        graph.add_node(node1)
        graph.add_node(node2)

        relation = KnowledgeRelation("node_001", "node_002", RelationType.IS_RELATED)
        assert graph.add_relation(relation)

    def test_get_relations(self, setup_graph):
        """测试获取关系"""
        relations = setup_graph.get_relations("node_001", direction="out")
        assert len(relations) == 1
        assert relations[0].target_id == "node_002"

    def test_bfs(self, setup_graph):
        """测试 BFS"""
        nodes = setup_graph.bfs("node_001", max_depth=2)
        assert len(nodes) > 0
        assert nodes[0].node_id == "node_001"

    def test_dfs(self, setup_graph):
        """测试 DFS"""
        nodes = setup_graph.dfs("node_001", max_depth=2)
        assert len(nodes) > 0
        assert nodes[0].node_id == "node_001"

    def test_get_shortest_path(self, setup_graph):
        """测试最短路径"""
        path = setup_graph.get_shortest_path("node_001", "node_003")
        assert len(path) == 3
        assert path[0] == "node_001"
        assert path[-1] == "node_003"

    def test_calculate_pagerank(self, setup_graph):
        """测试 PageRank"""
        pagerank = setup_graph.calculate_pagerank()

        assert len(pagerank) == 4
        assert all(0 <= score <= 1 for score in pagerank.values())
        # PageRank 值应该合理分布
        # 有更多入链的节点应该有更高的分数
        assert pagerank["node_004"] > pagerank["node_001"]

    def test_find_key_nodes(self, setup_graph):
        """测试查找关键节点"""
        key_nodes = setup_graph.find_key_nodes(top_k=2)

        assert len(key_nodes) == 2
        assert all(isinstance(score, float) for _, score in key_nodes)

    def test_to_graphviz(self, setup_graph):
        """测试 GraphViz 导出"""
        dot = setup_graph.to_graphviz()

        assert "digraph KnowledgeGraph" in dot
        assert "node_001" in dot


class TestGraphContextManager:
    """测试图谱上下文管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器"""
        graph = KnowledgeGraph()

        # 添加节点
        nodes = [
            KnowledgeNode("node_001", "Python programming", NodeType.CONCEPT),
            KnowledgeNode("node_002", "Data science", NodeType.CONCEPT),
            KnowledgeNode("node_003", "Machine learning", NodeType.CONCEPT),
        ]

        for node in nodes:
            graph.add_node(node)

        # 添加关系
        relations = [
            KnowledgeRelation("node_001", "node_002", RelationType.IS_RELATED),
            KnowledgeRelation("node_002", "node_003", RelationType.IS_RELATED),
        ]

        for relation in relations:
            graph.add_relation(relation)

        return GraphContextManager(graph)

    def test_enrich_context(self, manager):
        """测试增强上下文"""
        context = {"query": "Python"}
        enriched = manager.enrich_context(context, max_nodes=5)

        assert "query" in enriched
        assert "relevant_nodes" in enriched
        assert len(enriched["relevant_nodes"]) > 0

    def test_find_relevant_knowledge(self, manager):
        """测试查找相关知识"""
        knowledge = manager.find_relevant_knowledge("Python", context=None, max_depth=2)

        assert len(knowledge) > 0
        assert "node_id" in knowledge[0]
        assert "content" in knowledge[0]

    def test_build_from_documents(self):
        """测试从文档构建图谱"""
        manager = GraphContextManager()

        documents = [
            {"content": "Python is a programming language"},
            {"content": "Data science uses Python"},
        ]

        graph = manager.build_from_documents(documents, extract_entities=False)

        assert len(graph._nodes) == 2

    def test_create_context(self, manager):
        """测试创建上下文"""
        context_id = manager.create_context("Python", max_nodes=5)

        assert context_id.startswith("graph_ctx_")
        assert context_id in manager._contexts

    def test_get_context(self, manager):
        """测试获取上下文"""
        context_id = manager.create_context("Python")
        context = manager.get_context(context_id)

        assert context is not None
        assert context.query == "Python"


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 创建图谱
        graph = KnowledgeGraph()

        # 2. 添加节点
        nodes = [
            KnowledgeNode("concept_001", "Python", NodeType.CONCEPT),
            KnowledgeNode("concept_002", "Programming", NodeType.CONCEPT),
            KnowledgeNode("doc_001", "Python Tutorial", NodeType.DOCUMENT),
        ]

        for node in nodes:
            graph.add_node(node)

        # 3. 添加关系
        relations = [
            KnowledgeRelation("concept_001", "concept_002", RelationType.IS_RELATED),
            KnowledgeRelation("doc_001", "concept_001", RelationType.CONTAINS),
        ]

        for relation in relations:
            graph.add_relation(relation)

        # 4. 遍历图谱
        related = graph.bfs("concept_001", max_depth=2)
        assert len(related) > 0

        # 5. 计算重要性
        pagerank = graph.calculate_pagerank()
        assert len(pagerank) == 3

        # 6. 查找关键节点
        key_nodes = graph.find_key_nodes(top_k=2)
        assert len(key_nodes) == 2

    def test_graph_serialization(self):
        """测试图谱序列化"""
        graph = KnowledgeGraph()

        # 添加数据
        node = KnowledgeNode("node_001", "Test", NodeType.CONCEPT)
        graph.add_node(node)

        # 序列化
        data = graph.to_dict()
        assert len(data["nodes"]) == 1

        # 反序列化
        restored = KnowledgeGraph.from_dict(data)
        assert len(restored._nodes) == 1
        assert restored.get_node("node_001") is not None

    def test_context_manager_workflow(self):
        """测试上下文管理器工作流"""
        # 1. 创建管理器
        manager = GraphContextManager()

        # 2. 从文档构建图谱
        documents = [
            {"content": "Python is a programming language"},
            {"content": "Machine learning uses Python"},
        ]

        manager.build_from_documents(documents, extract_entities=False)

        # 3. 创建上下文
        manager.create_context("Python")

        # 4. 增强上下文
        manager.enrich_context({"query": "Python"})

        # 5. 查找知识
        knowledge = manager.find_relevant_knowledge("Python", None)

        assert len(knowledge) > 0
