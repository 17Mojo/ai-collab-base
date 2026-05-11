"""
NotebookLM 结果缓存模块

提供 NotebookLM 查询结果的智能缓存，支持：
- 相似问题匹配（避免重复查询）
- TTL 过期机制
- 统计监控
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedAnswer:
    """缓存的 NotebookLM 答案"""

    question: str
    answer: str
    sources: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    ttl: int = 3600  # 默认 1 小时
    query_count: int = 0
    similarity_hits: int = 0

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl

    def increment_hit(self) -> None:
        self.query_count += 1


@dataclass
class CacheStats:
    """缓存统计"""

    total_entries: int = 0
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    similarity_matches: int = 0
    expired_evictions: int = 0
    hit_rate: float = 0.0
    avg_query_time_saved_ms: float = 0.0

    def calculate_hit_rate(self) -> float:
        if self.total_queries > 0:
            self.hit_rate = (self.cache_hits / self.total_queries) * 100
        return self.hit_rate


class NotebookLMCache:
    """
    NotebookLM 查询缓存

    功能：
    1. 直接命中：完全相同的问题
    2. 相似命中：语义相似的问题（threshold > 0.85）
    3. TTL 过期自动清理
    4. 统计监控
    """

    def __init__(
        self,
        default_ttl: int = 3600,
        similarity_threshold: float = 0.85,
        max_entries: int = 100,
        avg_query_time_ms: float = 8000.0,
    ):
        """
        Args:
            default_ttl: 默认缓存时间（秒）
            similarity_threshold: 相似度阈值（0-1）
            max_entries: 最大缓存条目数
            avg_query_time_ms: 平均查询时间（毫秒，用于统计节省时间）
        """
        self._cache: Dict[str, CachedAnswer] = {}
        self._default_ttl = default_ttl
        self._similarity_threshold = similarity_threshold
        self._max_entries = max_entries
        self._avg_query_time_ms = avg_query_time_ms
        self._lock = threading.Lock()
        self._stats = CacheStats()

    def _normalize_question(self, question: str) -> str:
        """标准化问题文本"""
        # 移除多余空格
        question = re.sub(r"\s+", " ", question.strip())
        # 移除标点符号差异
        question = re.sub(r"[？?。.！!，,]", "", question)
        # 转换小写
        question = question.lower()
        return question

    def _hash_question(self, question: str) -> str:
        """生成问题的哈希键"""
        normalized = self._normalize_question(question)
        return hashlib.md5(normalized.encode()).hexdigest()

    def _find_similar_question(self, question: str) -> Optional[str]:
        """查找相似问题"""
        normalized = self._normalize_question(question)

        with self._lock:
            for cached_key, cached_answer in self._cache.items():
                cached_normalized = self._normalize_question(cached_answer.question)
                similarity = SequenceMatcher(None, normalized, cached_normalized).ratio()

                if similarity >= self._similarity_threshold:
                    logger.info(
                        f"找到相似问题: {similarity:.2f} - '{cached_answer.question[:50]}...'"
                    )
                    return cached_key

        return None

    def get_exact(self, question: str) -> Optional[CachedAnswer]:
        """
        精确匹配获取缓存

        Args:
            question: 用户问题

        Returns:
            缓存的答案，未命中返回 None
        """
        key = self._hash_question(question)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats.expired_evictions += 1
                return None

            entry.increment_hit()
            self._stats.cache_hits += 1
            return entry

    def get_similar(self, question: str) -> Optional[CachedAnswer]:
        """
        相似匹配获取缓存

        Args:
            question: 用户问题

        Returns:
            缓存的答案，未命中返回 None
        """
        # 先尝试精确匹配
        exact_result = self.get_exact(question)
        if exact_result is not None:
            return exact_result

        # 尝试相似匹配
        similar_key = self._find_similar_question(question)
        if similar_key is not None:
            with self._lock:
                entry = self._cache.get(similar_key)
                if entry and not entry.is_expired():
                    entry.similarity_hits += 1
                    self._stats.similarity_matches += 1
                    self._stats.cache_hits += 1
                    return entry

        return None

    def cache_answer(
        self,
        question: str,
        answer: str,
        sources: Optional[List[str]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        缓存答案

        Args:
            question: 用户问题
            answer: NotebookLM 答案
            sources: 来源文档列表
            ttl: 缓存时间（秒）

        Returns:
            缓存键
        """
        key = self._hash_question(question)

        with self._lock:
            # 检查容量
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()

            entry = CachedAnswer(
                question=question,
                answer=answer,
                sources=sources or [],
                ttl=ttl or self._default_ttl,
            )
            self._cache[key] = entry

            logger.info(f"缓存答案: '{question[:50]}...' -> {key}")
            return key

    def _evict_oldest(self) -> None:
        """清理最旧的条目"""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self._stats.expired_evictions += 1

    def cleanup_expired(self) -> int:
        """清理过期条目"""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
                self._stats.expired_evictions += 1
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            self._stats.total_entries = len(self._cache)
            self._stats.calculate_hit_rate()
            self._stats.avg_query_time_saved_ms = (
                self._stats.cache_hits * self._avg_query_time_ms
            )

            return {
                "backend": "notebooklm_cache",
                "total_entries": self._stats.total_entries,
                "max_entries": self._max_entries,
                "total_queries": self._stats.total_queries,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "similarity_matches": self._stats.similarity_matches,
                "expired_evictions": self._stats.expired_evictions,
                "hit_rate": f"{self._stats.hit_rate:.2f}%",
                "time_saved_ms": self._stats.avg_query_time_saved_ms,
                "similarity_threshold": self._similarity_threshold,
                "default_ttl": self._default_ttl,
            }

    def record_query(self, hit: bool) -> None:
        """记录查询统计"""
        with self._lock:
            self._stats.total_queries += 1
            if not hit:
                self._stats.cache_misses += 1

    def clear(self) -> int:
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count


# 全局缓存实例
_global_cache: Optional[NotebookLMCache] = None


def get_notebooklm_cache(
    force_reload: bool = False,
    ttl: int = 3600,
    similarity_threshold: float = 0.85,
) -> NotebookLMCache:
    """
    获取全局 NotebookLM 缓存实例

    Args:
        force_reload: 强制重新创建
        ttl: 缓存时间（秒）
        similarity_threshold: 相似度阈值

    Returns:
        NotebookLMCache 实例
    """
    global _global_cache
    if _global_cache is None or force_reload:
        _global_cache = NotebookLMCache(
            default_ttl=ttl,
            similarity_threshold=similarity_threshold,
        )
    return _global_cache


def cached_notebooklm_query(
    question: str,
    query_func: Callable,
    ttl: int = 3600,
) -> Dict[str, Any]:
    """
    NotebookLM 查询缓存包装函数

    Args:
        question: 用户问题
        query_func: 实际查询函数（当缓存未命中时调用）
        ttl: 缓存时间

    Returns:
        查询结果（包含 cache_hit 标记）
    """
    cache = get_notebooklm_cache()

    # 尝试获取缓存
    cached = cache.get_similar(question)
    if cached is not None:
        cache.record_query(hit=True)
        return {
            "question": question,
            "answer": cached.answer,
            "sources": cached.sources,
            "cache_hit": True,
            "similarity_match": cached.similarity_hits > 0,
            "cached_at": cached.created_at,
        }

    # 缓存未命中，执行查询
    cache.record_query(hit=False)
    result = query_func(question)

    # 缓存结果
    if "answer" in result and "error" not in result:
        cache.cache_answer(
            question=question,
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            ttl=ttl,
        )

    result["cache_hit"] = False
    result["similarity_match"] = False
    return result


# 使用示例
if __name__ == "__main__":
    print("=== NotebookLM 缓存示例 ===\n")

    cache = NotebookLMCache(similarity_threshold=0.85)

    # 模拟查询
    def mock_query(question: str) -> Dict[str, Any]:
        print(f"[查询] NotebookLM: '{question}'")
        return {
            "answer": f"关于 {question} 的详细回答...",
            "sources": ["doc1.pdf", "doc2.md"],
        }

    # 第一次查询（未命中）
    print("1. 首次查询:")
    result1 = cached_notebooklm_query("什么是 AI 协作系统?", mock_query)
    print(f"   结果: {result1['answer'][:50]}...")
    print(f"   缓存命中: {result1['cache_hit']}")

    # 第二次相同查询（命中）
    print("\n2. 相同问题:")
    result2 = cached_notebooklm_query("什么是 AI 协作系统?", mock_query)
    print(f"   结果: {result2['answer'][:50]}...")
    print(f"   缓存命中: {result2['cache_hit']}")

    # 相似问题查询（命中）
    print("\n3. 相似问题:")
    result3 = cached_notebooklm_query("AI 协作系统是什么?", mock_query)
    print(f"   结果: {result3['answer'][:50]}...")
    print(f"   缓存命中: {result3['cache_hit']}")
    print(f"   相似匹配: {result3['similarity_match']}")

    # 统计
    print("\n4. 缓存统计:")
    stats = cache.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")
