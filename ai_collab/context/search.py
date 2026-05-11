# Context Search Engine
# Week 3 Day 3: 智能上下文搜索

"""
智能上下文搜索引擎
支持语义搜索、上下文匹配、结果排序
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..integrations.multi_source import AggregatedKnowledge as AggregatedContext
from ..integrations.multi_source import KnowledgeSource as ContextItem
from .aggregator import ContextAggregator


class SearchMethod(Enum):
    """搜索方法"""

    SEMANTIC = "semantic"  # 语义搜索
    KEYWORD = "keyword"  # 关键词搜索
    HYBRID = "hybrid"  # 混合搜索
    GRAPH = "graph"  # 图谱搜索


class SearchScope(Enum):
    """搜索范围"""

    ALL = "all"  # 全部上下文
    RECENT = "recent"  # 最近添加的
    HIGH_CONFIDENCE = "high_confidence"  # 高置信度
    BY_SOURCE = "by_source"  # 按源过滤


@dataclass
class SearchResult:
    """搜索结果"""

    context_id: str
    content: str
    score: float  # 相关性分数 0-1
    matches: List[str]  # 匹配的关键词
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def relevance(self) -> str:
        """相关性等级"""
        if self.score >= 0.8:
            return "very_high"
        elif self.score >= 0.6:
            return "high"
        elif self.score >= 0.4:
            return "medium"
        else:
            return "low"


@dataclass
class SearchQuery:
    """搜索查询"""

    query: str
    method: SearchMethod = SearchMethod.SEMANTIC
    scope: SearchScope = SearchScope.ALL
    limit: int = 10
    min_score: float = 0.3
    filters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """清理查询字符串"""
        self.query = self.query.strip().lower()


@dataclass
class SearchStats:
    """搜索统计"""

    total_results: int
    filtered_results: int
    execution_time_ms: float
    method: SearchMethod
    scope: SearchScope


class ContextSearchEngine:
    """上下文搜索引擎"""

    def __init__(self, aggregator: Optional[ContextAggregator] = None):
        """初始化搜索引擎

        Args:
            aggregator: 上下文聚合器
        """
        self.aggregator = aggregator or ContextAggregator()
        self._search_stats: List[SearchStats] = []

    def search(self, query_str: str, **kwargs) -> Tuple[List[SearchResult], SearchStats]:
        """执行搜索

        Args:
            query_str: 查询字符串
            **kwargs: 额外参数

        Returns:
            搜索结果和统计信息
        """

        query = SearchQuery(query_str, **kwargs)

        # 获取搜索上下文
        history = self.aggregator.get_history(limit=100)

        if not history:
            return [], SearchStats(0, 0, 0, query.method, query.scope)

        # 生成候选向量
        candidates = self._extract_candidates(history)

        # 根据方法搜索
        if query.method == SearchMethod.SEMANTIC:
            results = self._semantic_search(query, candidates)
        elif query.method == SearchMethod.KEYWORD:
            results = self._keyword_search(query, candidates)
        elif query.method == SearchMethod.HYBRID:
            results = self._hybrid_search(query, candidates)
        elif query.method == SearchMethod.GRAPH:
            results = self._graph_search(query, candidates)
        else:
            results = self._semantic_search(query, candidates)

        # 过滤范围
        if query.scope != SearchScope.ALL:
            results = self._filter_by_scope(results, query.scope, history)

        # 过滤分数
        results = [r for r in results if r.score >= query.min_score]

        # 限制数量
        results = results[: query.limit]

        stats = SearchStats(
            total_results=len(results),
            filtered_results=len(candidates) - len(results),
            execution_time_ms=0,  # 实际执行时记录
            method=query.method,
            scope=query.scope,
        )

        return results, stats

    def _extract_candidates(self, history: List[AggregatedContext]) -> Dict[str, ContextItem]:
        """提取候选项

        Args:
            history: 上下文历史

        Returns:
            候选项字典 {context_id: context_item}
        """
        candidates = {}

        for ctx in history:
            # 如果是 AggregationContext 且有结果
            if hasattr(ctx, "result") and ctx.result:
                # 从结果中提取源作为候选项
                for source in ctx.result.sources:
                    candidates[source.source_id] = source
            # 如果是 AggregatedKnowledge (可以直接作为候选项组)
            elif hasattr(ctx, "sources"):
                for source in ctx.sources:
                    candidates[source.source_id] = source

        return candidates

    def _semantic_search(
        self, query: SearchQuery, candidates: Dict[str, ContextItem]
    ) -> List[SearchResult]:
        """语义搜索

        Args:
            query: 搜索查询
            candidates: 候选项

        Returns:
            搜索结果
        """
        results = []
        query_terms = query.query.split()

        for item_id, item in candidates.items():
            content = item.content.lower()

            # 计算 TF-IDF 风格的相似度
            score = self._calculate_tfidf_score(query_terms, content)

            if score > 0:
                # 查找匹配的关键词
                matches = [term for term in query_terms if term in content]

                results.append(
                    SearchResult(
                        context_id=item.id,
                        content=item.content,
                        score=score,
                        matches=matches,
                        metadata=item.metadata,
                    )
                )

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _keyword_search(
        self, query: SearchQuery, candidates: Dict[str, ContextItem]
    ) -> List[SearchResult]:
        """关键词搜索

        Args:
            query: 搜索查询
            candidates: 候选项

        Returns:
            搜索结果
        """
        results = []
        query_terms = query.query.split()

        for item_id, item in candidates.items():
            content = item.content.lower()

            # 计算准确匹配的分数
            score = 0.0
            matches = []

            for term in query_terms:
                term_count = content.count(term)
                if term_count > 0:
                    # 词频 * 词长权重
                    matches.append(term)
                    score += (term_count * len(term)) / len(content) * 10

            if score > 0:
                results.append(
                    SearchResult(
                        context_id=item.id,
                        content=item.content,
                        score=min(score, 1.0),
                        matches=matches,
                        metadata=item.metadata,
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _hybrid_search(
        self, query: SearchQuery, candidates: Dict[str, ContextItem]
    ) -> List[SearchResult]:
        """混合搜索（语义 + 关键词）

        Args:
            query: 搜索查询
            candidates: 候选项

        Returns:
            搜索结果
        """
        # 获取两种搜索结果
        semantic_results = {r.context_id: r for r in self._semantic_search(query, candidates)}
        keyword_results = {r.context_id: r for r in self._keyword_search(query, candidates)}

        # 合并结果
        combined = {}

        for context_id, result in semantic_results.items():
            combined[context_id] = result.score

        for context_id, result in keyword_results.items():
            if context_id in combined:
                # 加权平均
                combined[context_id] = combined[context_id] * 0.6 + result.score * 0.4
            else:
                combined[context_id] = result.score

        # 生成最终结果
        results = []
        for context_id, item in candidates.items():
            if context_id in combined:
                score = combined[context_id]

                # 重新计算匹配
                query_terms = query.query.split()
                matches = [term for term in query_terms if term in item.content.lower()]

                results.append(
                    SearchResult(
                        context_id=context_id,
                        content=item.content,
                        score=score,
                        matches=matches,
                        metadata=item.metadata,
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _graph_search(
        self, query: SearchQuery, candidates: Dict[str, ContextItem]
    ) -> List[SearchResult]:
        """图谱搜索（通过知识图谱关联）

        Args:
            query: 搜索查询
            candidates: 候选项

        Returns:
            搜索结果
        """
        # 获取知识图谱
        graph = self.aggregator.get_aggregator().get_graph()

        # 查找相关的节点
        related_nodes = graph.find_similar_nodes(query.query, top_k=len(candidates))

        # 计算关联分数
        node_scores = {node[0]: distance for node in related_nodes}

        results = []
        query_terms = query.query.split()

        for item_id, item in candidates.items():
            if item_id in node_scores:
                distance = node_scores[item_id]

                # 距离转换为分数 (距离越小分数越高)
                base_score = 1.0 - distance

                # 包含查询词的奖励
                matches = [term for term in query_terms if term in item.content.lower()]
                match_bonus = len(matches) * 0.1

                score = min(base_score + match_bonus, 1.0)

                results.append(
                    SearchResult(
                        context_id=item_id,
                        content=item.content,
                        score=score,
                        matches=matches,
                        metadata=item.metadata,
                    )
                )

        # 添加未在图谱中但包含关键词的项
        for item_id, item in candidates.items():
            if item_id not in node_scores:
                content_parts = set(item.content.lower().split())
                query_parts = set(query_terms)

                # Jaccard 相似度
                intersection = len(content_parts & query_parts)
                union = len(content_parts | query_parts)

                if intersection > 0:
                    score = intersection / union

                    matches = list(content_parts & query_parts)

                    results.append(
                        SearchResult(
                            context_id=item_id,
                            content=item.content,
                            score=score,
                            matches=matches,
                            metadata=item.metadata,
                        )
                    )

        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _filter_by_scope(
        self, results: List[SearchResult], scope: SearchScope, history: List[AggregatedContext]
    ) -> List[SearchResult]:
        """按范围过滤

        Args:
            results: 搜索结果
            scope: 搜索范围
            history: 上下文历史

        Returns:
            过滤后的结果
        """
        if scope == SearchScope.ALL:
            return results

        # 构建索引
        recent_items = {}
        high_confidence_items = {}
        by_source_items = defaultdict(list)

        # 收集最近 10 项
        for ctx in history[-10:]:
            for item in ctx.items:
                recent_items[item.id] = item

                # 按置信度分类
                if item.score >= 0.7:
                    high_confidence_items[item.id] = item

                # 按源分类
                source = item.source
                by_source_items[source].append(item.id)

        # 应用过滤
        if scope == SearchScope.RECENT:
            filtered = [r for r in results if r.context_id in recent_items]

        elif scope == SearchScope.HIGH_CONFIDENCE:
            filtered = [r for r in results if r.context_id in high_confidence_items]

        elif scope == SearchScope.BY_SOURCE:
            # 使用默认的源过滤（可扩展）
            target_sources = query.filters.get("sources", [])
            if target_sources:
                filtered = []
                for r in results:
                    for source_val in by_source_items.values():
                        if r.context_id in source_val:
                            # 检查是否匹配目标源
                            item_id = r.context_id
                            item = recent_items.get(item_id)
                            if item and item.source in target_sources:
                                filtered.append(r)
                                break
                results = filtered
            else:
                filtered = results

        else:
            filtered = results

        return filtered

    def _calculate_tfidf_score(self, query_terms: List[str], content: str) -> float:
        """计算 TF-IDF 风格的相似度

        Args:
            query_terms: 查询词
            content: 内容

        Returns:
            相似度分数
        """
        if not query_terms:
            return 0.0

        content_parts = content.split()
        content_length = len(content_parts)

        if content_length == 0:
            return 0.0

        score = 0.0

        for term in query_terms:
            # TF (词频)
            term_count = content_parts.count(term)
            tf = term_count / content_length

            # 简单的 IDF (假设所有词权重相同)
            idf = 1.0

            score += tf * idf

        # 归一化
        score = score / len(query_terms)

        return min(score, 1.0)

    def suggest(self, partial_query: str, limit: int = 5) -> List[str]:
        """建议查询词（基于历史查询）

        Args:
            partial_query: 部分查询
            limit: 返回数量

        Returns:
            建议的查询词列表
        """
        # 从上下文内容中提取关键词
        history = self.aggregator.get_history(limit=50)

        # 收集所有单词
        all_words = set()
        for ctx in history:
            for item in ctx.items:
                words = set(item.content.lower().split())
                all_words.update(words)

        # 过滤包含部分查询的词
        suggestions = [
            word for word in all_words if len(word) > 3 and partial_query.lower() in word
        ]

        # 按词频排序（需要额外的统计）
        return suggestions[:limit]

    def get_search_history(self) -> List[SearchStats]:
        """获取搜索历史统计

        Returns:
            搜索统计列表
        """
        return list(self._search_stats)

    def clear_history(self) -> None:
        """清空搜索历史"""
        self._search_stats.clear()
