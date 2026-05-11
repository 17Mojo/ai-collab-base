"""
缓存管理模块

提供 Redis + 内存缓存能力，支持故障自动降级。
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    from redis import Redis
except Exception:  # pragma: no cover - redis 是可选依赖
    Redis = None


class CacheEntry:
    """缓存条目"""

    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl


class MemoryCache:
    """内存缓存"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            self._cache[key] = CacheEntry(value=value, ttl=ttl or self.default_ttl)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys:
                del self._cache[key]
            return len(keys)

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup(self) -> int:
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            return {
                "backend": "memory",
                "total_entries": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate": f"{hit_rate:.2f}%",
            }

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]


class RedisCache:
    """Redis 缓存后端"""

    def __init__(
        self,
        redis_url: str,
        default_ttl: int = 300,
        key_prefix: str = "prompt_pack:",
        socket_timeout: float = 0.2,
        connect_timeout: float = 0.2,
    ):
        if Redis is None:
            raise RuntimeError("redis package is not installed")

        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._hits = 0
        self._misses = 0
        self._client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=connect_timeout,
            health_check_interval=30,
        )
        self._client.ping()

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        payload = self._client.get(self._key(key))
        if payload is None:
            self._misses += 1
            return None
        self._hits += 1
        return json.loads(payload)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        ttl_seconds = ttl or self.default_ttl
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return bool(self._client.setex(self._key(key), ttl_seconds, payload))

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(self._key(key)))

    def delete_prefix(self, prefix: str) -> int:
        pattern = self._key(f"{prefix}*")
        removed = 0
        for key in self._client.scan_iter(match=pattern, count=200):
            removed += int(self._client.delete(key))
        return removed

    def clear(self) -> int:
        return self.delete_prefix("")

    def cleanup(self) -> int:
        return 0

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        return {
            "backend": "redis",
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.2f}%",
            "key_prefix": self.key_prefix,
        }


class CacheManager:
    """统一缓存管理（Redis 优先，失败自动降级）"""

    def __init__(self):
        self._default_ttl = int(os.getenv("CACHE_TTL_SECONDS", "300"))
        self._max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))
        self._configured_backend = os.getenv("CACHE_BACKEND", "memory").strip().lower()
        if self._configured_backend not in {"memory", "redis", "auto"}:
            self._configured_backend = "memory"

        self._memory = MemoryCache(default_ttl=self._default_ttl, max_size=self._max_size)
        self._redis: Optional[RedisCache] = None
        self._active_backend = "memory"
        self._fallback_count = 0
        self._last_error: Optional[str] = None

        if self._configured_backend in {"redis", "auto"}:
            self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        redis_key_prefix = os.getenv("REDIS_KEY_PREFIX", "prompt_pack:")
        socket_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", "0.2"))
        connect_timeout = float(os.getenv("REDIS_CONNECT_TIMEOUT", "0.2"))
        try:
            self._redis = RedisCache(
                redis_url=redis_url,
                default_ttl=self._default_ttl,
                key_prefix=redis_key_prefix,
                socket_timeout=socket_timeout,
                connect_timeout=connect_timeout,
            )
            self._active_backend = "redis"
        except Exception as exc:
            self._last_error = f"redis init failed: {exc}"
            self._active_backend = "memory"

    def _record_fallback(self, action: str, exc: Exception):
        self._fallback_count += 1
        self._last_error = f"redis {action} failed: {exc}"
        self._active_backend = "memory"

    def _redis_enabled(self) -> bool:
        return self._active_backend == "redis" and self._redis is not None

    def get(self, key: str) -> Optional[Any]:
        if self._redis_enabled():
            try:
                value = self._redis.get(key)
                if value is not None:
                    return value
            except Exception as exc:
                self._record_fallback("get", exc)
        return self._memory.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        memory_ok = self._memory.set(key, value, ttl)
        if self._redis_enabled():
            try:
                redis_ok = self._redis.set(key, value, ttl)
                return bool(memory_ok or redis_ok)
            except Exception as exc:
                self._record_fallback("set", exc)
        return memory_ok

    def delete(self, key: str) -> bool:
        removed = self._memory.delete(key)
        if self._redis is not None:
            try:
                removed = bool(self._redis.delete(key) or removed)
            except Exception as exc:
                self._record_fallback("delete", exc)
        return removed

    def delete_prefix(self, prefix: str) -> int:
        removed = self._memory.delete_prefix(prefix)
        if self._redis is not None:
            try:
                removed += self._redis.delete_prefix(prefix)
            except Exception as exc:
                self._record_fallback("delete_prefix", exc)
        return removed

    def clear(self) -> int:
        removed = self._memory.clear()
        if self._redis is not None:
            try:
                removed += self._redis.clear()
            except Exception as exc:
                self._record_fallback("clear", exc)
        return removed

    def cleanup(self) -> int:
        cleaned = self._memory.cleanup()
        if self._redis is not None:
            try:
                cleaned += self._redis.cleanup()
            except Exception as exc:
                self._record_fallback("cleanup", exc)
        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        memory_stats = self._memory.get_stats()
        redis_stats = self._redis.get_stats() if self._redis is not None else None
        active_stats = redis_stats if self._active_backend == "redis" and redis_stats else memory_stats
        return {
            "enabled": True,
            "configured_backend": self._configured_backend,
            "active_backend": self._active_backend,
            "fallback_count": self._fallback_count,
            "last_error": self._last_error,
            "hits": active_stats.get("hits", 0),
            "misses": active_stats.get("misses", 0),
            "total_requests": active_stats.get("total_requests", 0),
            "hit_rate": active_stats.get("hit_rate", "0.00%"),
            "memory": memory_stats,
            "redis": redis_stats,
        }


_global_cache_manager: Optional[CacheManager] = None


def get_global_cache(force_reload: bool = False) -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None or force_reload:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def get_cache_manager(force_reload: bool = False) -> CacheManager:
    """兼容别名"""
    return get_global_cache(force_reload=force_reload)


def cached(ttl: int = 300, key_func: Optional[Callable] = None):
    """函数缓存装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()

            cache = get_global_cache()
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        wrapper.cache_clear = lambda: get_global_cache().clear()
        wrapper.cache_stats = lambda: get_global_cache().get_stats()
        return wrapper

    return decorator
