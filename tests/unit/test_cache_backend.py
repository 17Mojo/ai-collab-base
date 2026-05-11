"""
缓存后端单元测试
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "local-backend"))

from app.core.cache import get_cache_manager


def test_cache_manager_memory_backend(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "memory")
    manager = get_cache_manager(force_reload=True)

    manager.clear()
    assert manager.set("k1", {"v": 1}, ttl=30)
    assert manager.get("k1") == {"v": 1}

    stats = manager.get_stats()
    assert stats["configured_backend"] == "memory"
    assert stats["active_backend"] == "memory"
    assert stats["hits"] >= 1


def test_cache_manager_redis_unavailable_auto_fallback(monkeypatch):
    monkeypatch.setenv("CACHE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    manager = get_cache_manager(force_reload=True)

    # redis 初始化失败后应自动降级到 memory
    stats = manager.get_stats()
    assert stats["configured_backend"] == "redis"
    assert stats["active_backend"] == "memory"

    assert manager.set("fallback-key", {"ok": True}, ttl=30)
    assert manager.get("fallback-key") == {"ok": True}
