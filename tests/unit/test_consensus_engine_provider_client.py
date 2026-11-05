"""
Consensus Engine Provider Client Tests

Tests for:
- Async provider client calls
- Sync provider client calls
- Provider client failure handling
- Response normalization
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from ai_collab.engines.consensus_engine import AIProvider, ConsensusEngine


class TestAsyncProviderClient:
    """Test async provider client calls"""

    @pytest.mark.asyncio
    async def test_async_provider_client_call(self):
        """Test calling async provider client"""
        # Create async mock client
        async_client = AsyncMock()
        async_client.query = AsyncMock(
            return_value={"ai": "test_async", "response": "Async response", "confidence": 0.95}
        )

        # Create engine and register provider
        engine = ConsensusEngine()
        engine.register_provider("test_async", async_client, timeout=30.0)

        # Generate consensus
        result = await engine.generate_consensus("test topic")

        # Verify result (check for 'topic' field instead of 'success')
        assert "topic" in result
        assert "test_async" in [s["ai"] for s in result["sources"]]

    @pytest.mark.asyncio
    async def test_async_provider_client_string_response(self):
        """Test async provider client returning string"""
        async_client = AsyncMock()
        async_client.query = AsyncMock(return_value="String response")

        engine = ConsensusEngine()
        engine.register_provider("test_async_str", async_client)

        result = await engine.generate_consensus("test")

        assert "topic" in result
        # Should normalize string to dict
        sources = result["sources"]
        async_source = next(s for s in sources if s["ai"] == "test_async_str")
        assert async_source["response"] == "String response"


class TestSyncProviderClient:
    """Test sync provider client calls"""

    @pytest.mark.asyncio
    async def test_sync_provider_client_call(self):
        """Test calling sync provider client"""
        # Create sync mock client
        sync_client = Mock()
        sync_client.query = Mock(
            return_value={"ai": "test_sync", "response": "Sync response", "confidence": 0.9}
        )

        # Create engine and register provider
        engine = ConsensusEngine()
        engine.register_provider("test_sync", sync_client, timeout=30.0)

        # Generate consensus
        result = await engine.generate_consensus("test topic")

        # Verify result
        assert "topic" in result
        assert "test_sync" in [s["ai"] for s in result["sources"]]

    @pytest.mark.asyncio
    async def test_sync_provider_client_string_response(self):
        """Test sync provider client returning string"""
        sync_client = Mock()
        sync_client.query = Mock(return_value="Sync string response")

        engine = ConsensusEngine()
        engine.register_provider("test_sync_str", sync_client)

        result = await engine.generate_consensus("test")

        assert "topic" in result
        sources = result["sources"]
        sync_source = next(s for s in sources if s["ai"] == "test_sync_str")
        assert sync_source["response"] == "Sync string response"


class TestProviderClientFailure:
    """Test provider client failure handling

    2026-11-05 诚实化收口：client=None / 缺 query / 调用失败不再返回
    "[X REAL] …真实观点" 假填充冒充成功（误导性遥测）——失败如实上抛，
    全部失败时 FALLBACK 模式整体降级为标注 Mock 的三件套。
    """

    @pytest.mark.asyncio
    async def test_provider_client_not_found(self):
        """client=None 是配置缺口：如实失败降级，不给 test_none 配假填充"""
        engine = ConsensusEngine()
        engine.providers["test_none"] = AIProvider(
            name="test_none", client=None, timeout=30.0, enabled=True
        )

        result = await engine.generate_consensus("test")

        # 全部 provider 配置缺口 → FALLBACK 整体降级（默认 fallback 模式）
        assert result["mode"] == "fallback"
        # 假填充禁止复活锚：失败 provider 不得出现在 sources 里冒充成功
        assert "test_none" not in [s["ai"] for s in result["sources"]]
        for s in result["sources"]:
            assert "真实观点" not in s["response"]
            assert " REAL]" not in s["response"]

    @pytest.mark.asyncio
    async def test_provider_client_no_query_method(self):
        """client 缺 query 方法：如实失败降级，不造假填充"""
        client_without_query = Mock(spec=[])  # No query method

        engine = ConsensusEngine()
        engine.register_provider("no_query", client_without_query)

        result = await engine.generate_consensus("test")

        assert result["mode"] == "fallback"
        assert "no_query" not in [s["ai"] for s in result["sources"]]
        for s in result["sources"]:
            assert "真实观点" not in s["response"]

    @pytest.mark.asyncio
    async def test_provider_client_exception(self):
        """sync client 调用抛异常：如实失败降级，吞异常换假填充禁止复活"""
        failing_client = Mock()
        failing_client.query = Mock(side_effect=Exception("API failure"))

        engine = ConsensusEngine()
        engine.register_provider("failing", failing_client)

        result = await engine.generate_consensus("test")

        assert result["mode"] == "fallback"
        assert "failing" not in [s["ai"] for s in result["sources"]]
        for s in result["sources"]:
            assert "真实观点" not in s["response"]

    @pytest.mark.asyncio
    async def test_async_provider_client_exception(self):
        """async client 调用抛异常：同上，如实失败降级"""
        failing_async_client = AsyncMock()
        failing_async_client.query = AsyncMock(side_effect=Exception("Async API failure"))

        engine = ConsensusEngine()
        engine.register_provider("failing_async", failing_async_client)

        result = await engine.generate_consensus("test")

        assert result["mode"] == "fallback"
        assert "failing_async" not in [s["ai"] for s in result["sources"]]
        for s in result["sources"]:
            assert "真实观点" not in s["response"]


class TestResponseNormalization:
    """Test response normalization"""

    @pytest.mark.asyncio
    async def test_dict_response_normalization(self):
        """Test dict response normalization"""
        client = Mock()
        client.query = Mock(
            return_value={"ai": "custom_ai", "response": "Custom response", "confidence": 0.85}
        )

        engine = ConsensusEngine()
        engine.register_provider("dict_provider", client)

        result = await engine.generate_consensus("test")

        sources = result["sources"]
        dict_source = next(s for s in sources if s["ai"] == "custom_ai")
        assert dict_source["response"] == "Custom response"
        assert dict_source["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_string_response_normalization(self):
        """Test string response normalization"""
        client = Mock()
        client.query = Mock(return_value="Plain string response")

        engine = ConsensusEngine()
        engine.register_provider("string_provider", client)

        result = await engine.generate_consensus("test")

        sources = result["sources"]
        string_source = next(s for s in sources if s["ai"] == "string_provider")
        assert string_source["response"] == "Plain string response"
        assert string_source["confidence"] == 0.9  # Default confidence

    @pytest.mark.asyncio
    async def test_other_response_normalization(self):
        """Test other type response normalization"""
        client = Mock()
        client.query = Mock(return_value=12345)  # Integer response

        engine = ConsensusEngine()
        engine.register_provider("int_provider", client)

        result = await engine.generate_consensus("test")

        sources = result["sources"]
        int_source = next(s for s in sources if s["ai"] == "int_provider")
        assert int_source["response"] == "12345"  # Converted to string
        assert int_source["confidence"] == 0.9


class TestTimeoutAndRetry:
    """Test timeout and retry mechanisms"""

    @pytest.mark.asyncio
    async def test_provider_timeout(self):
        """Test provider timeout"""
        slow_client = AsyncMock()

        async def slow_query(topic):
            await asyncio.sleep(5)  # Simulate slow response
            return {"response": "slow response"}

        slow_client.query = slow_query

        engine = ConsensusEngine()
        engine.register_provider("slow", slow_client, timeout=0.1)  # Very short timeout

        # 超时如实失败：其余默认 provider 也全缺口 → 整体降级 fallback
        result = await engine.generate_consensus("test")
        assert result["mode"] == "fallback"
        assert "slow" not in [s["ai"] for s in result["sources"]]

    @pytest.mark.asyncio
    async def test_provider_retry_on_failure(self):
        """Test provider retry on failure"""
        fail_count = 0

        def failing_query(topic):
            nonlocal fail_count
            fail_count += 1
            if fail_count < 3:
                raise Exception(f"Failure {fail_count}")
            return {"response": "success after retries"}

        client = Mock()
        client.query = failing_query

        engine = ConsensusEngine()
        provider = AIProvider(
            name="retry_provider", client=client, timeout=30.0, max_retries=3, enabled=True
        )
        engine.providers["retry_provider"] = provider

        result = await engine.generate_consensus("test")

        # 第 3 次真成功——sources 是真产出，不是假填充
        assert any(s["response"] == "success after retries" for s in result["sources"])
        assert result["mode"] == "real"
        # 其余默认 provider（client=None 配置缺口）如实进 failed_providers
        assert set(result["failed_providers"]) == {"chatgpt", "claude", "kimi", "qianwen"}
        assert fail_count >= 3  # 重试机制真跑了
