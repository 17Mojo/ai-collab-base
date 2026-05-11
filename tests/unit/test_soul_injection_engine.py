"""
Unit tests for SoulInjectionEngine real/fallback/mock routing.
"""

from __future__ import annotations

import pytest

from ai_collab.engines.soul_injection_engine import SoulInjectionEngine


def test_soul_engine_default_fallback_mode(monkeypatch):
    """Soul engine defaults to fallback mode (_mock=False)."""
    monkeypatch.delenv("AI_INTEGRATION_MODE", raising=False)
    monkeypatch.delenv("AI_INTEGRATION_MODE_SOUL_INJECTION", raising=False)
    engine = SoulInjectionEngine()
    assert engine._mock is False
    assert "fallback" in engine._mock_reason.lower()


@pytest.mark.asyncio
async def test_inject_soul_mock_mode():
    """Mock mode should route to mock and return content."""
    engine = SoulInjectionEngine()
    engine._mock = True
    engine._mock_reason = "test mock"
    result = await engine.inject_soul("测试内容")
    assert result["success"] is True
    assert result["mode"] == "mock"
    assert result["personalized_content"]


@pytest.mark.asyncio
async def test_inject_soul_fallback_when_real_unavailable(monkeypatch):
    """Fallback mode should switch to mock when real engine is unavailable."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_SOUL_INJECTION", "fallback")
    monkeypatch.setenv("SOUL_ENGINE_AVAILABLE", "false")
    engine = SoulInjectionEngine()

    result = await engine.inject_soul("测试内容")
    assert result["success"] is True
    assert result["mode"] == "fallback"
    assert engine._mock is True


@pytest.mark.asyncio
async def test_inject_soul_real_when_available(monkeypatch):
    """Real mode should use real path when engine is available."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_SOUL_INJECTION", "real")
    monkeypatch.setenv("SOUL_ENGINE_AVAILABLE", "true")
    engine = SoulInjectionEngine()

    result = await engine.inject_soul("测试内容")
    assert result["success"] is True
    assert result["mode"] == "real"


@pytest.mark.asyncio
async def test_inject_soul_real_returns_error_when_unavailable(monkeypatch):
    """Real mode should return explicit error when real engine is unavailable."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_SOUL_INJECTION", "real")
    monkeypatch.setenv("SOUL_ENGINE_AVAILABLE", "false")
    engine = SoulInjectionEngine()

    result = await engine.inject_soul("测试内容")
    assert result["success"] is False
    assert result["mode"] == "real"
    assert "unavailable" in result["error"].lower()

