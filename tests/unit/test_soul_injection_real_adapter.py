"""
SoulInjectionEngine external service call hardening tests.
Tests for timeout, retry, fallback, and error code handling.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from ai_collab.engines.soul_injection_engine import (
    SoulInjectionEngine,
    SoulServiceError,
    SoulServiceErrorCode,
)


class TestExternalServiceTimeout:
    """Tests for request timeout handling"""

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Timeout should raise SoulServiceError with TIMEOUT code"""
        engine = SoulInjectionEngine()

        # Mock environment to enable external service
        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            # Mock aiohttp to raise TimeoutError
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_post.side_effect = asyncio.TimeoutError()

                with pytest.raises(SoulServiceError) as exc_info:
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=0.1, max_retries=1
                    )

                assert exc_info.value.error_code == SoulServiceErrorCode.TIMEOUT

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """Timeout should trigger retry logic"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            # Create a proper async context manager mock
            class MockPost:
                def __init__(self):
                    self.call_count = 0

                async def __aenter__(self):
                    self.call_count += 1
                    raise asyncio.TimeoutError()

                async def __aexit__(self, *args):
                    pass

            mock_post_instance = MockPost()

            with patch("aiohttp.ClientSession.post", return_value=mock_post_instance):
                with pytest.raises(SoulServiceError):
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=0.1, max_retries=3
                    )

                # Should have retried 3 times
                assert mock_post_instance.call_count == 3


class TestExternalServiceConnectionError:
    """Tests for connection error handling"""

    @pytest.mark.asyncio
    async def test_connection_error_raises_error(self):
        """Connection error should raise SoulServiceError with CONNECTION_ERROR code"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_post.side_effect = aiohttp.ClientError("Connection failed")

                with pytest.raises(SoulServiceError) as exc_info:
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=1
                    )

                assert exc_info.value.error_code == SoulServiceErrorCode.CONNECTION_ERROR


class TestExternalServiceHTTPStatus:
    """Tests for HTTP status code handling"""

    @pytest.mark.asyncio
    async def test_rate_limit_429(self):
        """HTTP 429 should raise RATE_LIMIT error"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            mock_response = AsyncMock()
            mock_response.status = 429

            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.post", return_value=mock_post):
                with pytest.raises(SoulServiceError) as exc_info:
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=1
                    )

                assert exc_info.value.error_code == SoulServiceErrorCode.RATE_LIMIT

    @pytest.mark.asyncio
    async def test_service_unavailable_500(self):
        """HTTP 500 should raise SERVICE_UNAVAILABLE error"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            mock_response = AsyncMock()
            mock_response.status = 500

            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.post", return_value=mock_post):
                with pytest.raises(SoulServiceError) as exc_info:
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=1
                    )

                assert exc_info.value.error_code == SoulServiceErrorCode.SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_invalid_response_format(self):
        """Missing personalized_content should raise INVALID_RESPONSE error"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"invalid_key": "invalid_value"})

            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.post", return_value=mock_post):
                with pytest.raises(SoulServiceError) as exc_info:
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=1
                    )

                assert exc_info.value.error_code == SoulServiceErrorCode.INVALID_RESPONSE


class TestFallbackBehavior:
    """Tests for fallback to strategy chain"""

    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_strategy_chain(self):
        """Timeout should fall back to strategy chain in REAL mode"""
        engine = SoulInjectionEngine()

        with patch.dict(
            "os.environ",
            {"SOUL_AI_SERVICE_URL": "http://test-service", "SOUL_ENGINE_AVAILABLE": "true"},
        ):
            with patch.object(engine, "_call_external_ai_service") as mock_call:
                # Simulate timeout
                mock_call.side_effect = SoulServiceError("Timeout", SoulServiceErrorCode.TIMEOUT)

                result = await engine.inject_soul_real(
                    "test content", "luoyonghao", timeout=1.0, max_retries=1
                )

                # Should have fallen back to strategy chain
                assert result["success"] is True
                assert result.get("fallback_used") is True
                assert result.get("error_code") == "TIMEOUT"
                assert result["strategies_applied"] > 0

    @pytest.mark.asyncio
    async def test_service_unavailable_falls_back_to_strategy_chain(self):
        """Service unavailable should fall back to strategy chain in REAL mode"""
        engine = SoulInjectionEngine()

        with patch.dict(
            "os.environ",
            {"SOUL_AI_SERVICE_URL": "http://test-service", "SOUL_ENGINE_AVAILABLE": "true"},
        ):
            with patch.object(engine, "_call_external_ai_service") as mock_call:
                # Simulate service unavailable
                mock_call.side_effect = SoulServiceError(
                    "Service unavailable", SoulServiceErrorCode.SERVICE_UNAVAILABLE
                )

                result = await engine.inject_soul_real(
                    "test content", "luoyonghao", timeout=1.0, max_retries=1
                )

                # Should have fallen back to strategy chain
                assert result["success"] is True
                assert result.get("fallback_used") is True
                assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_connection_error_does_not_fall_back(self):
        """Connection error should NOT fall back (raises exception)"""
        engine = SoulInjectionEngine()

        with patch.dict(
            "os.environ",
            {"SOUL_AI_SERVICE_URL": "http://test-service", "SOUL_ENGINE_AVAILABLE": "true"},
        ):
            with patch.object(engine, "_call_external_ai_service") as mock_call:
                # Simulate connection error
                mock_call.side_effect = SoulServiceError(
                    "Connection error", SoulServiceErrorCode.CONNECTION_ERROR
                )

                with pytest.raises(SoulServiceError):
                    await engine.inject_soul_real(
                        "test content", "luoyonghao", timeout=1.0, max_retries=1
                    )


class TestRetryLogic:
    """Tests for retry logic"""

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Rate limit should trigger retry with exponential backoff"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            # Create a proper async context manager mock
            class MockPost:
                def __init__(self):
                    self.call_count = 0

                async def __aenter__(self):
                    self.call_count += 1
                    mock_response = AsyncMock()
                    mock_response.status = 429
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            mock_post_instance = MockPost()

            with patch("aiohttp.ClientSession.post", return_value=mock_post_instance):
                with pytest.raises(SoulServiceError):
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=3
                    )

                # Should have retried 3 times
                assert mock_post_instance.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_service_unavailable(self):
        """Service unavailable should trigger retry with exponential backoff"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            # Create a proper async context manager mock
            class MockPost:
                def __init__(self):
                    self.call_count = 0

                async def __aenter__(self):
                    self.call_count += 1
                    mock_response = AsyncMock()
                    mock_response.status = 503
                    return mock_response

                async def __aexit__(self, *args):
                    pass

            mock_post_instance = MockPost()

            with patch("aiohttp.ClientSession.post", return_value=mock_post_instance):
                with pytest.raises(SoulServiceError):
                    await engine._call_external_ai_service(
                        "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=3
                    )

                # Should have retried 3 times
                assert mock_post_instance.call_count == 3


class TestSuccessfulServiceCall:
    """Tests for successful service calls"""

    @pytest.mark.asyncio
    async def test_successful_call_returns_content(self):
        """Successful call should return personalized content"""
        engine = SoulInjectionEngine()

        with patch.dict("os.environ", {"SOUL_AI_SERVICE_URL": "http://test-service"}):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(
                return_value={"personalized_content": "Personalized test content"}
            )

            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession.post", return_value=mock_post):
                result = await engine._call_external_ai_service(
                    "test content", engine.profiles["luoyonghao"], timeout=1.0, max_retries=1
                )

                assert result == "Personalized test content"
