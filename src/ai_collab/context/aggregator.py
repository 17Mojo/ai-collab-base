"""
上下文聚合管理器

集成多源知识聚合到上下文管理系统中。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_collab.integrations.multi_source import (
    AggregatedKnowledge,
    KnowledgeAggregator,
    KnowledgeSource,
)


@dataclass
class AggregationContext:
    """聚合上下文"""

    context_id: str
    query: str
    sources: List[str]
    result: Optional[AggregatedKnowledge] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "context_id": self.context_id,
            "query": self.query,
            "sources": self.sources,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at.isoformat(),
        }


class ContextAggregator:
    """上下文聚合管理器"""

    def __init__(self):
        """初始化上下文聚合管理器"""
        self.aggregator = KnowledgeAggregator()
        self.contexts: Dict[str, AggregationContext] = {}

    def aggregate_from_sources(
        self, sources: List[str], context: Any, max_sources: int = 5
    ) -> AggregatedKnowledge:
        """
        从多个源聚合知识

        Args:
            sources: 源ID列表
            context: 上下文对象
            max_sources: 最大源数量

        Returns:
            聚合知识对象
        """
        # 1. 提取知识
        knowledge_sources = []
        for source_id in sources[:max_sources]:
            source = self.aggregator.get_source(source_id)
            if source:
                knowledge_sources.append(source)

        # 2. 去重
        deduplicated = self.aggregator.deduplicate(knowledge_sources)

        # 3. 交叉验证
        validation = self.aggregator.cross_validate(deduplicated)

        # 4. 合并
        merged_content = self.aggregator._merge_content(deduplicated)

        # 5. 计算置信度
        aggregated = AggregatedKnowledge(
            content=merged_content,
            sources=deduplicated,
            cross_validation=validation,
            overall_confidence=0.0,
        )
        confidence = self.aggregator.calculate_confidence(aggregated)
        aggregated.overall_confidence = confidence

        return aggregated

    def extract_knowledge(
        self,
        source_type: str,
        content: str,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeSource:
        """
        从源提取知识

        Args:
            source_type: 源类型 (notebooklm/file/api)
            content: 内容
            confidence: 置信度
            metadata: 元数据

        Returns:
            知识源对象
        """
        # 生成源ID
        source_id = self._generate_source_id(source_type, content)

        # 创建知识源
        source = KnowledgeSource(
            source_id=source_id,
            source_type=source_type,
            content=content,
            confidence=confidence,
            metadata=metadata or {},
        )

        # 添加到聚合器
        self.aggregator.add_source(source)

        return source

    def merge_knowledge(
        self, sources: List[KnowledgeSource], strategy: str = "weighted"
    ) -> AggregatedKnowledge:
        """
        合并知识

        Args:
            sources: 知识源列表
            strategy: 合并策略 (weighted/consensus/all)

        Returns:
            聚合知识对象
        """
        if not sources:
            return AggregatedKnowledge(
                content="", sources=[], cross_validation={}, overall_confidence=0.0
            )

        # 根据策略选择源
        if strategy == "weighted":
            # 按置信度加权
            selected = self._weighted_selection(sources)
        elif strategy == "consensus":
            # 选择一致的源
            selected = self._consensus_selection(sources)
        else:
            # 使用所有源
            selected = sources

        # 去重
        deduplicated = self.aggregator.deduplicate(selected)

        # 交叉验证
        validation = self.aggregator.cross_validate(deduplicated)

        # 合并内容
        merged_content = self.aggregator._merge_content(deduplicated)

        # 计算置信度
        aggregated = AggregatedKnowledge(
            content=merged_content,
            sources=deduplicated,
            cross_validation=validation,
            overall_confidence=0.0,
        )
        confidence = self.aggregator.calculate_confidence(aggregated)
        aggregated.overall_confidence = confidence

        return aggregated

    def create_context(self, query: str, sources: List[str]) -> str:
        """
        创建聚合上下文

        Args:
            query: 查询字符串
            sources: 源ID列表

        Returns:
            上下文ID
        """
        context_id = self._generate_context_id(query, sources)

        context = AggregationContext(context_id=context_id, query=query, sources=sources)

        self.contexts[context_id] = context

        return context_id

    def execute_aggregation(self, context_id: str, max_sources: int = 5) -> AggregatedKnowledge:
        """
        执行聚合

        Args:
            context_id: 上下文ID
            max_sources: 最大源数量

        Returns:
            聚合知识对象
        """
        context = self.contexts.get(context_id)
        if not context:
            raise ValueError(f"Context not found: {context_id}")

        # 执行聚合
        result = self.aggregate_from_sources(context.sources, context, max_sources)

        # 更新上下文
        context.result = result

        return result

    def get_context(self, context_id: str) -> Optional[AggregationContext]:
        """获取上下文"""
        return self.contexts.get(context_id)

    def list_contexts(self) -> List[AggregationContext]:
        """列出所有上下文"""
        return list(self.contexts.values())

    def get_history(self, limit: int = 10) -> List[Any]:
        """获取历史上下文（简化版本）
        返回最近创建的聚合上下文列表
        """
        contexts = list(self.contexts.values())
        contexts.sort(key=lambda x: x.created_at, reverse=True)
        return contexts[:limit]

    def _generate_source_id(self, source_type: str, content: str) -> str:
        """生成源ID"""
        import hashlib

        timestamp = datetime.now().isoformat()
        hash_input = f"{source_type}:{content[:100]}:{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{source_type}_{hash_value}"

    def _generate_context_id(self, query: str, sources: List[str]) -> str:
        """生成上下文ID"""
        import hashlib

        timestamp = datetime.now().isoformat()
        hash_input = f"{query}:{','.join(sources)}:{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"ctx_{hash_value}"

    def _weighted_selection(self, sources: List[KnowledgeSource]) -> List[KnowledgeSource]:
        """加权选择"""
        # 按置信度排序
        sorted_sources = sorted(sources, key=lambda s: s.confidence, reverse=True)
        # 选择置信度 > 0.5 的源
        return [s for s in sorted_sources if s.confidence > 0.5]

    def _consensus_selection(self, sources: List[KnowledgeSource]) -> List[KnowledgeSource]:
        """一致性选择"""
        # 交叉验证
        validation = self.aggregator.cross_validate(sources)
        # 选择通过验证的源
        return [s for s in sources if validation.get(s.source_id, False)]
