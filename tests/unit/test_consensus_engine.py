"""
Unit tests for ConsensusEngine real/fallback/mock orchestration.
"""

from __future__ import annotations

import pytest

from ai_collab.engines.consensus_engine import ConsensusEngine


def test_consensus_engine_default_fallback_mode(monkeypatch):
    """Consensus engine defaults to fallback mode (_mock=False)."""
    monkeypatch.delenv("AI_INTEGRATION_MODE", raising=False)
    monkeypatch.delenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", raising=False)
    engine = ConsensusEngine()
    assert engine._mock is False
    assert "fallback" in engine._mock_reason.lower()


@pytest.mark.asyncio
async def test_generate_consensus_mock_mode():
    """Mock mode should return mock response and keep mode=mock."""
    engine = ConsensusEngine()
    engine._mock = True
    engine._mock_reason = "test mock mode"
    result = await engine.generate_consensus("测试主题")
    assert result["mode"] == "mock"
    assert result["sources"]


@pytest.mark.asyncio
async def test_generate_consensus_fallback_when_real_unavailable(monkeypatch):
    """Fallback mode should switch to mock when real clients are unavailable."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "fallback")
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "false")

    engine = ConsensusEngine()
    result = await engine.generate_consensus("测试主题")

    assert result["mode"] == "fallback"
    assert engine._mock is True


@pytest.mark.asyncio
async def test_generate_consensus_real_when_available(monkeypatch):
    """Real mode should use real path when clients are available."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "true")

    engine = ConsensusEngine()
    result = await engine.generate_consensus("测试主题")

    assert result["mode"] == "real"
    assert result["sources"]


@pytest.mark.asyncio
async def test_generate_consensus_real_raises_when_unavailable(monkeypatch):
    """Real mode should raise when real clients are unavailable."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "false")

    engine = ConsensusEngine()
    with pytest.raises(ConnectionError):
        await engine.generate_consensus("测试主题")


@pytest.mark.asyncio
async def test_generate_consensus_uses_cache():
    """Repeated same topic should hit cache."""
    engine = ConsensusEngine()
    engine._mock = True
    first = await engine.generate_consensus("缓存主题")
    second = await engine.generate_consensus("缓存主题")
    assert first is second

