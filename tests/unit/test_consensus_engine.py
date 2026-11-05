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
async def test_generate_consensus_real_with_registered_client(monkeypatch):
    """Real mode：注册真实 client 后走真链路，mode=real 且无失败 provider。

    （2026-11-05 重写：旧版用默认 client=None 的 provider 走假填充冒充
    mode="real"，是误导性遥测的锚——已随假填充一并收口。）
    """
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")

    class _Client:
        async def query(self, topic: str) -> str:
            return f"关于{topic}的真实回答"

    engine = ConsensusEngine()
    engine.providers = {}  # 全部换掉默认空 client provider
    engine.register_provider("only", _Client())

    result = await engine.generate_consensus("测试主题")

    assert result["mode"] == "real"
    assert result["sources"]
    assert result["failed_providers"] == []
    assert result["sources"][0]["response"] == "关于测试主题的真实回答"


@pytest.mark.asyncio
async def test_real_mode_config_gap_raises(monkeypatch):
    """Real mode + 无真实 client（仅 client=None 配置缺口）→ 如实抛错。

    旧版此处返回 4 条 "[X REAL] …真实观点" 假填充并报 mode="real"——
    误导性遥测回归锚，禁止复活。
    """
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "true")

    engine = ConsensusEngine()  # 默认 4 provider 均 client=None
    with pytest.raises(ConnectionError):
        await engine.generate_consensus("测试主题")


@pytest.mark.asyncio
async def test_partial_failure_reports_failed_providers(monkeypatch):
    """REAL 混部：真 client 成功 + 配置缺口失败 → mode=real 但 failed_providers 显式列出。"""
    monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")

    class _Client:
        async def query(self, topic: str) -> str:
            return f"关于{topic}的真实回答"

    engine = ConsensusEngine()
    engine.register_provider("chatgpt", _Client())  # 替换为真 client
    # claude/kimi/qianwen 保持 client=None → 配置缺口失败

    result = await engine.generate_consensus("混部主题")

    assert result["mode"] == "real"
    assert len(result["sources"]) == 1
    assert set(result["failed_providers"]) == {"claude", "kimi", "qianwen"}
    # 诚实性：sources 中不得出现假「REAL」占位文本
    for source in result["sources"]:
        assert "真实观点" not in source["response"]
        assert " REAL]" not in source["response"]


@pytest.mark.asyncio
async def test_call_provider_api_config_gap_raises():
    """client=None 是配置缺口，抛 ConnectionError 而非假填充。"""
    from ai_collab.engines.consensus_engine import AIProvider

    engine = ConsensusEngine()
    provider = AIProvider(name="ghost", client=None)
    with pytest.raises(ConnectionError):
        await engine._call_provider_api("主题", provider)


@pytest.mark.asyncio
async def test_call_provider_api_missing_query_method_raises():
    """client 缺 query 方法 → 抛 ConnectionError 而非假填充。"""
    from ai_collab.engines.consensus_engine import AIProvider

    engine = ConsensusEngine()
    provider = AIProvider(name="bad", client=object())
    with pytest.raises(ConnectionError):
        await engine._call_provider_api("主题", provider)


@pytest.mark.asyncio
async def test_call_provider_api_client_error_reraises():
    """client 调用抛异常 → 如实上抛，禁止吞掉换假填充。"""
    from ai_collab.engines.consensus_engine import AIProvider

    class _Boom:
        async def query(self, topic: str):
            raise RuntimeError("api down")

    engine = ConsensusEngine()
    provider = AIProvider(name="boom", client=_Boom())
    with pytest.raises(RuntimeError):
        await engine._call_provider_api("主题", provider)


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

