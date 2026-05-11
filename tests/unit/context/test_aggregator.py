"""
测试多源知识聚合功能
"""

from datetime import datetime

import pytest

from ai_collab.context.aggregator import ContextAggregator
from ai_collab.integrations.multi_source import (
    AggregatedKnowledge,
    KnowledgeAggregator,
    KnowledgeSource,
)


class TestKnowledgeSource:
    """测试知识源数据模型"""

    def test_create_knowledge_source(self):
        """测试创建知识源"""
        source = KnowledgeSource(
            source_id="test_001", source_type="notebooklm", content="Test content", confidence=0.8
        )

        assert source.source_id == "test_001"
        assert source.source_type == "notebooklm"
        assert source.content == "Test content"
        assert source.confidence == 0.8
        assert isinstance(source.created_at, datetime)

    def test_knowledge_source_serialization(self):
        """测试知识源序列化"""
        source = KnowledgeSource(
            source_id="test_002",
            source_type="file",
            content="Test content 2",
            confidence=0.9,
            metadata={"key": "value"},
        )

        # 序列化
        data = source.to_dict()
        assert data["source_id"] == "test_002"
        assert data["source_type"] == "file"
        assert data["confidence"] == 0.9

        # 反序列化
        restored = KnowledgeSource.from_dict(data)
        assert restored.source_id == source.source_id
        assert restored.content == source.content
        assert restored.confidence == source.confidence

    def test_invalid_confidence(self):
        """测试无效置信度"""
        with pytest.raises(ValueError):
            KnowledgeSource(
                source_id="test_003", source_type="notebooklm", content="Test", confidence=1.5
            )

    def test_invalid_source_type(self):
        """测试无效源类型"""
        with pytest.raises(ValueError):
            KnowledgeSource(
                source_id="test_004", source_type="invalid", content="Test", confidence=0.8
            )


class TestKnowledgeAggregator:
    """测试知识聚合引擎"""

    @pytest.fixture
    def aggregator(self):
        """创建聚合器"""
        return KnowledgeAggregator()

    @pytest.fixture
    def sample_sources(self):
        """创建示例源"""
        return [
            KnowledgeSource(
                source_id="src_001",
                source_type="notebooklm",
                content="Python is a programming language",
                confidence=0.9,
            ),
            KnowledgeSource(
                source_id="src_002",
                source_type="file",
                content="Python is widely used for data science",
                confidence=0.8,
            ),
            KnowledgeSource(
                source_id="src_003",
                source_type="api",
                content="Python supports multiple paradigms",
                confidence=0.7,
            ),
        ]

    def test_add_source(self, aggregator):
        """测试添加源"""
        source = KnowledgeSource(
            source_id="test_001", source_type="notebooklm", content="Test content", confidence=0.8
        )

        source_id = aggregator.add_source(source)
        assert source_id == "test_001"
        assert len(aggregator.sources) == 1

    def test_aggregate(self, aggregator, sample_sources):
        """测试聚合"""
        # 添加源
        for source in sample_sources:
            aggregator.add_source(source)

        # 执行聚合
        result = aggregator.aggregate("Python", max_sources=3)

        assert isinstance(result, AggregatedKnowledge)
        assert len(result.sources) > 0
        assert result.overall_confidence > 0
        assert "Python" in result.content

    def test_deduplicate(self, aggregator):
        """测试去重"""
        sources = [
            KnowledgeSource(
                source_id="src_001",
                source_type="notebooklm",
                content="Same content",
                confidence=0.9,
            ),
            KnowledgeSource(
                source_id="src_002",
                source_type="file",
                content="Same content",  # 重复内容
                confidence=0.8,
            ),
            KnowledgeSource(
                source_id="src_003", source_type="api", content="Different content", confidence=0.7
            ),
        ]

        deduplicated = aggregator.deduplicate(sources)
        assert len(deduplicated) == 2
        assert deduplicated[0].source_id == "src_001"
        assert deduplicated[1].source_id == "src_003"

    def test_cross_validate(self, aggregator):
        """测试交叉验证"""
        sources = [
            KnowledgeSource(
                source_id="src_001",
                source_type="notebooklm",
                content="Python programming language features",
                confidence=0.9,
            ),
            KnowledgeSource(
                source_id="src_002",
                source_type="file",
                content="Python programming language features",
                confidence=0.8,
            ),
            KnowledgeSource(
                source_id="src_003",
                source_type="api",
                content="Cooking recipes and ingredients",
                confidence=0.7,
            ),
        ]

        validation = aggregator.cross_validate(sources)

        assert len(validation) == 3
        # 验证结果应该是布尔值
        assert all(isinstance(v, bool) for v in validation.values())
        # 前两个源内容相同,应该一致
        assert validation["src_001"]
        assert validation["src_002"]

    def test_calculate_confidence(self, aggregator):
        """测试置信度计算"""
        sources = [
            KnowledgeSource(
                source_id="src_001", source_type="notebooklm", content="Content 1", confidence=0.9
            ),
            KnowledgeSource(
                source_id="src_002", source_type="file", content="Content 2", confidence=0.8
            ),
        ]

        knowledge = AggregatedKnowledge(
            content="Merged content",
            sources=sources,
            cross_validation={"src_001": True, "src_002": True},
            overall_confidence=0.0,
        )

        confidence = aggregator.calculate_confidence(knowledge)

        # 置信度应该在合理范围内
        assert 0 < confidence <= 1.0
        # 应该高于平均置信度
        assert confidence > 0.85

    def test_empty_aggregation(self, aggregator):
        """测试空聚合"""
        result = aggregator.aggregate("query", max_sources=0)

        assert result.content == ""
        assert len(result.sources) == 0
        assert result.overall_confidence == 0.0


class TestContextAggregator:
    """测试上下文聚合管理器"""

    @pytest.fixture
    def context_aggregator(self):
        """创建上下文聚合器"""
        return ContextAggregator()

    @pytest.fixture
    def setup_sources(self, context_aggregator):
        """设置源"""
        sources = [
            context_aggregator.extract_knowledge(
                source_type="notebooklm", content="Python is a programming language", confidence=0.9
            ),
            context_aggregator.extract_knowledge(
                source_type="file", content="Python is used for data science", confidence=0.8
            ),
            context_aggregator.extract_knowledge(
                source_type="api", content="Python supports OOP", confidence=0.7
            ),
        ]
        return [s.source_id for s in sources]

    def test_extract_knowledge(self, context_aggregator):
        """测试提取知识"""
        source = context_aggregator.extract_knowledge(
            source_type="notebooklm", content="Test content", confidence=0.8
        )

        assert source.source_type == "notebooklm"
        assert source.content == "Test content"
        assert source.confidence == 0.8
        assert source.source_id.startswith("notebooklm_")

    def test_aggregate_from_sources(self, context_aggregator, setup_sources):
        """测试从源聚合"""
        result = context_aggregator.aggregate_from_sources(
            sources=setup_sources, context=None, max_sources=3
        )

        assert isinstance(result, AggregatedKnowledge)
        assert len(result.sources) > 0
        assert result.overall_confidence > 0

    def test_merge_knowledge_weighted(self, context_aggregator):
        """测试加权合并"""
        sources = [
            KnowledgeSource(
                source_id="src_001",
                source_type="notebooklm",
                content="High confidence content",
                confidence=0.9,
            ),
            KnowledgeSource(
                source_id="src_002",
                source_type="file",
                content="Low confidence content",
                confidence=0.3,
            ),
        ]

        result = context_aggregator.merge_knowledge(sources, strategy="weighted")

        # 应该只包含高置信度的源
        assert len(result.sources) == 1
        assert result.sources[0].source_id == "src_001"

    def test_merge_knowledge_all(self, context_aggregator):
        """测试全部合并"""
        sources = [
            KnowledgeSource(
                source_id="src_001", source_type="notebooklm", content="Content 1", confidence=0.9
            ),
            KnowledgeSource(
                source_id="src_002", source_type="file", content="Content 2", confidence=0.3
            ),
        ]

        result = context_aggregator.merge_knowledge(sources, strategy="all")

        # 应该包含所有源
        assert len(result.sources) == 2

    def test_create_context(self, context_aggregator, setup_sources):
        """测试创建上下文"""
        context_id = context_aggregator.create_context(query="Python", sources=setup_sources)

        assert context_id.startswith("ctx_")
        assert context_id in context_aggregator.contexts

    def test_execute_aggregation(self, context_aggregator, setup_sources):
        """测试执行聚合"""
        # 创建上下文
        context_id = context_aggregator.create_context(query="Python", sources=setup_sources)

        # 执行聚合
        result = context_aggregator.execute_aggregation(context_id, max_sources=3)

        assert isinstance(result, AggregatedKnowledge)
        assert len(result.sources) > 0

        # 检查上下文已更新
        context = context_aggregator.get_context(context_id)
        assert context.result is not None

    def test_get_context(self, context_aggregator):
        """测试获取上下文"""
        context_id = context_aggregator.create_context(query="test", sources=["src_001"])

        context = context_aggregator.get_context(context_id)
        assert context is not None
        assert context.query == "test"

    def test_list_contexts(self, context_aggregator):
        """测试列出上下文"""
        context_aggregator.create_context("query1", ["src_001"])
        context_aggregator.create_context("query2", ["src_002"])

        contexts = context_aggregator.list_contexts()
        assert len(contexts) == 2

    def test_empty_merge(self, context_aggregator):
        """测试空合并"""
        result = context_aggregator.merge_knowledge([])

        assert result.content == ""
        assert len(result.sources) == 0
        assert result.overall_confidence == 0.0


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        # 1. 创建上下文聚合器
        ctx_agg = ContextAggregator()

        # 2. 提取知识
        source1 = ctx_agg.extract_knowledge(
            source_type="notebooklm",
            content="Python is a high-level programming language",
            confidence=0.9,
            metadata={"source": "notebook1"},
        )

        source2 = ctx_agg.extract_knowledge(
            source_type="file",
            content="Python is widely used in data science and AI",
            confidence=0.85,
            metadata={"file": "readme.md"},
        )

        source3 = ctx_agg.extract_knowledge(
            source_type="api",
            content="Python supports multiple programming paradigms",
            confidence=0.8,
            metadata={"api": "wikipedia"},
        )

        # 3. 创建上下文
        context_id = ctx_agg.create_context(
            query="What is Python?",
            sources=[source1.source_id, source2.source_id, source3.source_id],
        )

        # 4. 执行聚合
        result = ctx_agg.execute_aggregation(context_id, max_sources=3)

        # 5. 验证结果
        assert isinstance(result, AggregatedKnowledge)
        assert len(result.sources) > 0
        assert result.overall_confidence > 0.7
        assert "Python" in result.content

        # 6. 验证交叉验证
        assert len(result.cross_validation) > 0
        assert all(isinstance(v, bool) for v in result.cross_validation.values())

    def test_multi_source_deduplication(self):
        """测试多源去重"""
        aggregator = KnowledgeAggregator()

        # 添加重复内容
        sources = [
            KnowledgeSource(
                source_id=f"src_{i}",
                source_type="notebooklm",
                content="Same content from different sources",
                confidence=0.8 + i * 0.05,
            )
            for i in range(5)
        ]

        for source in sources:
            aggregator.add_source(source)

        # 聚合
        result = aggregator.aggregate("query", max_sources=5)

        # 应该只保留一个
        assert len(result.sources) == 1
        # 应该保留置信度最高的
        assert result.sources[0].confidence == 1.0

    def test_confidence_calculation_with_validation(self):
        """测试带验证的置信度计算"""
        aggregator = KnowledgeAggregator()

        # 添加一致的源
        sources = [
            KnowledgeSource(
                source_id="src_001",
                source_type="notebooklm",
                content="Python is a programming language",
                confidence=0.9,
            ),
            KnowledgeSource(
                source_id="src_002",
                source_type="file",
                content="Python is a programming language",
                confidence=0.85,
            ),
            KnowledgeSource(
                source_id="src_003",
                source_type="api",
                content="Python is a programming language",
                confidence=0.8,
            ),
        ]

        for source in sources:
            aggregator.add_source(source)

        result = aggregator.aggregate("Python", max_sources=3)

        # 高置信度 + 多源 + 验证通过 = 高综合置信度
        assert result.overall_confidence > 0.9
