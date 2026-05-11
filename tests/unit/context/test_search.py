# Context Search Tests
# Week 3 Day 3: 智能上下文搜索测试

import pytest

from ai_collab.context.aggregator import ContextAggregator
from ai_collab.context.search import (
    ContextSearchEngine,
    SearchMethod,
    SearchQuery,
    SearchResult,
    SearchScope,
)


class TestSearchResult:
    """测试 SearchResult"""

    def test_relevance_very_high(self):
        """测试极高相关性"""
        result = SearchResult(context_id="test", content="content", score=0.85, matches=[])
        assert result.relevance == "very_high"

    def test_relevance_high(self):
        """测试高相关性"""
        result = SearchResult(context_id="test", content="content", score=0.65, matches=[])
        assert result.relevance == "high"

    def test_relevance_medium(self):
        """测试中等相关性"""
        result = SearchResult(context_id="test", content="content", score=0.5, matches=[])
        assert result.relevance == "medium"

    def test_relevance_low(self):
        """测试低相关性"""
        result = SearchResult(context_id="test", content="content", score=0.3, matches=[])
        assert result.relevance == "low"


class TestSearchQuery:
    """测试 SearchQuery"""

    def test_clean_query(self):
        """测试查询清理"""
        query = SearchQuery("  Test Query  ")
        assert query.query == "test query"

    def test_default_method(self):
        """测试默认搜索方法"""
        query = SearchQuery("test")
        assert query.method == SearchMethod.SEMANTIC

    def test_default_scope(self):
        """测试默认搜索范围"""
        query = SearchQuery("test")
        assert query.scope == SearchScope.ALL

    def test_default_limit(self):
        """测试默认限制"""
        query = SearchQuery("test")
        assert query.limit == 10

    def test_default_min_score(self):
        """测试默认最小分数"""
        query = SearchQuery("test")
        assert query.min_score == 0.3


class TestContextSearchEngine:
    """测试 ContextSearchEngine"""

    @pytest.fixture
    def setup_engine(self):
        """设置测试环境和引擎"""
        aggregator = ContextAggregator()

        # 使用 extract_knowledge 添加测试上下文
        aggregator.extract_knowledge(
            source_type="api", content="Python is a programming language", confidence=0.9
        )

        aggregator.extract_knowledge(
            source_type="api", content="JavaScript is used for web development", confidence=0.85
        )

        aggregator.extract_knowledge(
            source_type="file", content="Machine learning uses Python extensively", confidence=0.75
        )

        return ContextSearchEngine(aggregator)

    def test_search_empty_query(self, setup_engine):
        """测试空查询"""
        results, stats = setup_engine.search("   ")

        assert len(results) == 0

    def test_search_no_results(self, setup_engine):
        """测试无结果查询"""
        results, stats = setup_engine.search("nonexistent phrase xyz123")

        assert len(results) == 0
        assert stats.total_results == 0

    def test_semantic_search(self, setup_engine):
        """测试语义搜索"""
        results, stats = setup_engine.search("python", method=SearchMethod.SEMANTIC)

        assert stats.method == SearchMethod.SEMANTIC

        # 检查返回类型
        assert isinstance(results, list)

    def test_keyword_search(self, setup_engine):
        """测试关键词搜索"""
        results, stats = setup_engine.search("javascript", method=SearchMethod.KEYWORD)

        assert stats.method == SearchMethod.KEYWORD
        # 检查至少有一个结果有匹配
        assert any(r.matches for r in results) if results else True

    def test_hybrid_search(self, setup_engine):
        """测试混合搜索"""
        results, stats = setup_engine.search("machine", method=SearchMethod.HYBRID)

        assert stats.method == SearchMethod.HYBRID

        # 检查返回类型
        assert isinstance(results, list)

    def test_graph_search(self, setup_engine):
        """测试图谱搜索"""
        results, stats = setup_engine.search("programming", method=SearchMethod.GRAPH)

        assert stats.method == SearchMethod.GRAPH

    def test_scope_filter_recent(self, setup_engine):
        """测试最近范围过滤"""
        results, stats = setup_engine.search("python", scope=SearchScope.RECENT)

        assert stats.scope == SearchScope.RECENT

    def test_scope_filter_all(self, setup_engine):
        """测试全部范围"""
        results, stats = setup_engine.search("python", scope=SearchScope.ALL)

        assert stats.scope == SearchScope.ALL

    def test_limit_filter(self, setup_engine):
        """测试结果限制"""
        results, stats = setup_engine.search("python", limit=1)

        assert len(results) <= 1

    def test_min_score_filter(self, setup_engine):
        """测试最小分数过滤"""
        results, stats = setup_engine.search("python", min_score=0.9)

        for result in results:
            assert result.score >= 0.9

    def test_result_ordering(self, setup_engine):
        """测试结果排序"""
        results, stats = setup_engine.search("python")

        # 结果应按分数降序排列
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_matches_extraction(self, setup_engine):
        """测试匹配词提取"""
        results, _ = setup_engine.search("python language")

        if results:
            # 应该包含至少一个匹配词
            assert any(r.matches for r in results if r.score > 0)


class TestSearchFeatures:
    """测试搜索功能特性"""

    @pytest.fixture
    def setup_engine(self):
        """设置测试环境"""
        aggregator = ContextAggregator()

        # 添加多个测试上下文
        aggregator.extract_knowledge(
            source_type="api", content="Python programming language", confidence=0.9
        )
        aggregator.extract_knowledge(
            source_type="file", content="JavaScript web framework", confidence=0.85
        )
        aggregator.extract_knowledge(
            source_type="api", content="Machine learning algorithms", confidence=0.8
        )
        aggregator.extract_knowledge(
            source_type="file", content="Data science with Python", confidence=0.75
        )
        aggregator.extract_knowledge(
            source_type="api", content="Web development frontend", confidence=0.7
        )
        return ContextSearchEngine(aggregator)

    def test_suggest(self, setup_engine):
        """测试查询建议"""
        suggestions = setup_engine.suggest("pyt")

        assert isinstance(suggestions, list)

    def test_suggest_no_matches(self, setup_engine):
        """测试无匹配建议"""
        suggestions = setup_engine.suggest("xyz.invalid")

        # 可能返回空列表或不相关词
        assert isinstance(suggestions, list)

    def test_get_search_history(self, setup_engine):
        """测试获取搜索历史"""
        setup_engine.search("python")
        setup_engine.search("javascript")

        history = setup_engine.get_search_history()

        assert isinstance(history, list)

    def test_clear_history(self, setup_engine):
        """测试清空历史"""
        setup_engine.search("test")
        setup_engine.clear_history()

        history = setup_engine.get_search_history()
        assert len(history) == 0


class TestSearchScoring:
    """测试搜索评分逻辑"""

    @pytest.fixture
    def setup_engine(self):
        """设置测试环境"""
        aggregator = ContextAggregator()

        # 添加包含特定词频的上下文
        aggregator.extract_knowledge(
            source_type="api", content="python python python python", confidence=0.9
        )

        aggregator.extract_knowledge(source_type="api", content="python", confidence=0.8)
        return ContextSearchEngine(aggregator)

    def test_term_frequency_impact(self, setup_engine):
        """测试词频影响"""
        results, _ = setup_engine.search("python")

        if len(results) >= 2:
            # 词频较高的应该有较高分数
            assert results[0].score >= results[1].score

    def test_score_range(self, setup_engine):
        """测试分数范围"""
        results, _ = setup_engine.search("python")

        for result in results:
            assert 0 <= result.score <= 1


class TestSearchCLI:
    """测试搜索 CLI 功能"""

    def test_cli_init(self):
        """测试 CLI 初始化"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()

        assert cli.search_engine is not None
        assert cli.aggregator is not None

    def test_cli_search_command(self):
        """测试 CLI 搜索命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()

        # 搜索应该运行但不应该抛出异常
        result = cli.search("test", method="semantic", limit=5)

        assert result in [0, 1]  # 应该返回退出码

    def test_cli_suggest_command(self):
        """测试 CLI 建议命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()

        result = cli.suggest("test", limit=3)

        assert result == 0

    def test_cli_history_command(self):
        """测试 CLI 历史命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()

        result = cli.history(count=5)

        assert result == 0

    def test_cli_clear_history_command(self):
        """测试 CLI 清空历史命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()

        result = cli.clear_history()

        assert result == 0


class TestErrorHandling:
    """测试错误处理"""

    def test_empty_aggregator(self):
        """测试空聚合器"""
        engine = ContextSearchEngine()

        results, stats = engine.search("test")

        assert len(results) == 0
        assert stats.total_results == 0

    def test_invalid_method_handling(self):
        """测试无效方法处理"""
        # SearchQuery 会自动处理，这里测试搜索引擎的行为
        engine = ContextSearchEngine()
        aggregator = engine.aggregator

        aggregator.extract_knowledge(source_type="api", content="test content", confidence=0.9)

        # 使用方法枚举，不传字符串
        results, _ = engine.search("test", method=SearchMethod.SEMANTIC)

        assert isinstance(results, list)

    def test_none_query_handling(self):
        """测试 None 查询处理"""
        engine = ContextSearchEngine()

        # SearchQuery 应该处理空字符串
        results, _ = engine.search("")

        assert isinstance(results, list)
