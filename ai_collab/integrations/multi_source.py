"""
多源知识聚合引擎

支持从多个知识源抽取、去重、合并和验证知识。
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeSource:
    """知识源"""

    source_id: str
    source_type: str  # notebooklm/file/api
    content: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """验证参数"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        if self.source_type not in ["notebooklm", "file", "api"]:
            raise ValueError(f"Invalid source type: {self.source_type}")

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeSource":
        """从字典反序列化"""
        return cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            content=data["content"],
            confidence=data["confidence"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class AggregatedKnowledge:
    """聚合知识"""

    content: str
    sources: List[KnowledgeSource]
    cross_validation: Dict[str, bool]
    overall_confidence: float
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "content": self.content,
            "sources": [s.to_dict() for s in self.sources],
            "cross_validation": self.cross_validation,
            "overall_confidence": self.overall_confidence,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AggregatedKnowledge":
        """从字典反序列化"""
        return cls(
            content=data["content"],
            sources=[KnowledgeSource.from_dict(s) for s in data["sources"]],
            cross_validation=data["cross_validation"],
            overall_confidence=data["overall_confidence"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class KnowledgeAggregator:
    """知识聚合引擎"""

    def __init__(self):
        """初始化聚合引擎"""
        self.sources: Dict[str, KnowledgeSource] = {}
        self.aggregation_cache: Dict[str, AggregatedKnowledge] = {}

    def add_source(self, source: KnowledgeSource) -> str:
        """
        添加知识源

        Args:
            source: 知识源对象

        Returns:
            源ID
        """
        self.sources[source.source_id] = source
        return source.source_id

    def aggregate(self, query: str, max_sources: int = 5) -> AggregatedKnowledge:
        """
        聚合知识

        Args:
            query: 查询字符串
            max_sources: 最大源数量

        Returns:
            聚合知识对象
        """
        # 1. 选择相关源
        relevant_sources = self._select_relevant_sources(query, max_sources)

        # 2. 去重
        deduplicated = self.deduplicate(relevant_sources)

        # 3. 交叉验证
        validation = self.cross_validate(deduplicated)

        # 4. 合并内容
        merged_content = self._merge_content(deduplicated)

        # 5. 计算置信度
        confidence = self.calculate_confidence(
            AggregatedKnowledge(
                content=merged_content,
                sources=deduplicated,
                cross_validation=validation,
                overall_confidence=0.0,
            )
        )

        # 6. 创建聚合知识
        aggregated = AggregatedKnowledge(
            content=merged_content,
            sources=deduplicated,
            cross_validation=validation,
            overall_confidence=confidence,
        )

        # 缓存结果
        cache_key = self._get_cache_key(query, max_sources)
        self.aggregation_cache[cache_key] = aggregated

        return aggregated

    def deduplicate(self, sources: List[KnowledgeSource]) -> List[KnowledgeSource]:
        """
        去重知识源

        Args:
            sources: 知识源列表

        Returns:
            去重后的列表
        """
        seen_hashes = set()
        unique_sources = []

        for source in sources:
            # 计算内容哈希
            content_hash = self._hash_content(source.content)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_sources.append(source)

        return unique_sources

    def cross_validate(self, sources: List[KnowledgeSource]) -> Dict[str, bool]:
        """
        交叉验证知识源

        Args:
            sources: 知识源列表

        Returns:
            验证结果字典 {source_id: is_valid}
        """
        if len(sources) < 2:
            return {s.source_id: True for s in sources}

        validation = {}

        # 提取所有内容的关键信息
        key_info = [self._extract_key_info(s.content) for s in sources]

        for i, source in enumerate(sources):
            # 检查与其他源的一致性
            is_consistent = self._check_consistency(key_info[i], key_info, i)
            validation[source.source_id] = is_consistent

        return validation

    def calculate_confidence(self, knowledge: AggregatedKnowledge) -> float:
        """
        计算置信度

        Args:
            knowledge: 聚合知识对象

        Returns:
            置信度分数 (0-1)
        """
        if not knowledge.sources:
            return 0.0

        # 1. 基础置信度: 源的平均置信度
        base_confidence = sum(s.confidence for s in knowledge.sources) / len(knowledge.sources)

        # 2. 源数量加成: 更多源提供更高置信度
        source_bonus = min(len(knowledge.sources) * 0.1, 0.3)

        # 3. 验证加成: 通过验证的源比例
        if knowledge.cross_validation:
            validation_rate = sum(knowledge.cross_validation.values()) / len(
                knowledge.cross_validation
            )
            validation_bonus = validation_rate * 0.2
        else:
            validation_bonus = 0.0

        # 4. 源类型多样性加成
        source_types = set(s.source_type for s in knowledge.sources)
        diversity_bonus = min(len(source_types) * 0.05, 0.15)

        # 综合置信度
        overall = base_confidence + source_bonus + validation_bonus + diversity_bonus

        return min(overall, 1.0)

    def _select_relevant_sources(self, query: str, max_sources: int) -> List[KnowledgeSource]:
        """选择相关源"""
        # 简单实现: 按置信度排序
        sorted_sources = sorted(self.sources.values(), key=lambda s: s.confidence, reverse=True)
        return sorted_sources[:max_sources]

    def _merge_content(self, sources: List[KnowledgeSource]) -> str:
        """合并内容"""
        if not sources:
            return ""

        if len(sources) == 1:
            return sources[0].content

        # 合并多个源的内容
        merged_parts = []
        for i, source in enumerate(sources):
            merged_parts.append(f"[Source {i+1}: {source.source_type}]\n{source.content}")

        return "\n\n".join(merged_parts)

    def _hash_content(self, content: str) -> str:
        """计算内容哈希"""
        # 标准化内容
        normalized = re.sub(r"\s+", " ", content.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()

    def _extract_key_info(self, content: str) -> set:
        """提取关键信息"""
        # 简单实现: 提取关键词
        words = re.findall(r"\b\w{3,}\b", content.lower())
        return set(words)

    def _check_consistency(self, info: set, all_info: List[set], index: int) -> bool:
        """检查一致性"""
        if len(all_info) < 2:
            return True

        # 计算与其他源的重叠度
        overlaps = []
        for i, other_info in enumerate(all_info):
            if i != index:
                if not info or not other_info:
                    continue
                overlap = len(info & other_info) / max(len(info), len(other_info))
                overlaps.append(overlap)

        if not overlaps:
            return True

        # 平均重叠度 > 0.3 认为一致
        avg_overlap = sum(overlaps) / len(overlaps)
        return avg_overlap > 0.3

    def _get_cache_key(self, query: str, max_sources: int) -> str:
        """获取缓存键"""
        return f"{query}:{max_sources}"

    def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """获取知识源"""
        return self.sources.get(source_id)

    def list_sources(self) -> List[KnowledgeSource]:
        """列出所有知识源"""
        return list(self.sources.values())

    def clear_cache(self):
        """清空缓存"""
        self.aggregation_cache.clear()
