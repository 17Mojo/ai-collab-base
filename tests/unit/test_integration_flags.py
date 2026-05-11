"""Unit tests for AI integration mode configuration"""

import pytest

from ai_collab.config import IntegrationMode, get_mode, is_mock_mode, should_use_fallback


class TestIntegrationMode:
    """Test IntegrationMode enum"""

    def test_mode_values(self):
        """Test that enum values are correct"""
        assert IntegrationMode.MOCK.value == "mock"
        assert IntegrationMode.FALLBACK.value == "fallback"
        assert IntegrationMode.REAL.value == "real"

    def test_mode_comparison(self):
        """Test mode comparison"""
        assert IntegrationMode.MOCK == IntegrationMode.MOCK
        assert IntegrationMode.MOCK != IntegrationMode.FALLBACK
        assert IntegrationMode.FALLBACK == IntegrationMode.FALLBACK


class TestGetMode:
    """Test get_mode function"""

    def test_default_modes(self):
        """Test default mode configuration"""
        assert get_mode("notebooklm") == IntegrationMode.FALLBACK
        assert get_mode("consensus_engine") == IntegrationMode.FALLBACK
        assert get_mode("soul_injection") == IntegrationMode.FALLBACK
        assert get_mode("codex") == IntegrationMode.REAL

    def test_unknown_module(self):
        """Test error handling for unknown module"""
        with pytest.raises(ValueError, match="Unknown integration module"):
            get_mode("unknown_module")

    def test_env_global_override(self, monkeypatch):
        """Test global environment variable override"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "mock")
        assert get_mode("notebooklm") == IntegrationMode.MOCK
        assert get_mode("consensus_engine") == IntegrationMode.MOCK

        monkeypatch.setenv("AI_INTEGRATION_MODE", "real")
        assert get_mode("notebooklm") == IntegrationMode.REAL
        assert get_mode("consensus_engine") == IntegrationMode.REAL

    def test_env_per_module_override(self, monkeypatch):
        """Test per-module environment variable override"""
        # Override only notebooklm
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")

        assert get_mode("notebooklm") == IntegrationMode.MOCK
        assert get_mode("consensus_engine") == IntegrationMode.FALLBACK  # Uses default

        # Override another module
        monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "real")

        assert get_mode("notebooklm") == IntegrationMode.MOCK
        assert get_mode("consensus_engine") == IntegrationMode.REAL

    def test_env_per_module_overrides_global(self, monkeypatch):
        """Test that per-module override takes precedence over global"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "mock")
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        # Per-module override should take precedence
        assert get_mode("notebooklm") == IntegrationMode.REAL
        # Other modules use global override
        assert get_mode("consensus_engine") == IntegrationMode.MOCK

    def test_invalid_env_value(self, monkeypatch):
        """Test error handling for invalid environment variable value"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "invalid_mode")

        with pytest.raises(ValueError, match="Invalid AI_INTEGRATION_MODE value"):
            get_mode("notebooklm")

    def test_invalid_per_module_env_value(self, monkeypatch):
        """Test error handling for invalid per-module environment variable"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "invalid_mode")

        with pytest.raises(ValueError, match="Invalid AI_INTEGRATION_MODE_NOTEBOOKLM value"):
            get_mode("notebooklm")


class TestIsMockMode:
    """Test is_mock_mode function"""

    def test_mock_mode(self, monkeypatch):
        """Test returns True for MOCK mode"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "mock")
        assert is_mock_mode("notebooklm") is True
        assert is_mock_mode("consensus_engine") is True

    def test_fallback_mode(self):
        """Test returns False for FALLBACK mode"""
        assert is_mock_mode("notebooklm") is False
        assert is_mock_mode("consensus_engine") is False

    def test_real_mode(self, monkeypatch):
        """Test returns False for REAL mode"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "real")
        assert is_mock_mode("notebooklm") is False
        assert is_mock_mode("codex") is False


class TestShouldUseFallback:
    """Test should_use_fallback function"""

    def test_mock_mode_allows_fallback(self, monkeypatch):
        """Test returns True for MOCK mode"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "mock")
        assert should_use_fallback("notebooklm") is True
        assert should_use_fallback("consensus_engine") is True

    def test_fallback_mode_allows_fallback(self):
        """Test returns True for FALLBACK mode (default)"""
        assert should_use_fallback("notebooklm") is True
        assert should_use_fallback("consensus_engine") is True

    def test_real_mode_forbids_fallback(self):
        """Test returns False for REAL mode"""
        assert should_use_fallback("codex") is False

    def test_real_mode_forbids_fallback_with_override(self, monkeypatch):
        """Test returns False when REAL mode is set via env"""
        monkeypatch.setenv("AI_INTEGRATION_MODE", "real")
        assert should_use_fallback("notebooklm") is False
        assert should_use_fallback("consensus_engine") is False


class TestPriorityOrder:
    """Test priority order of configuration sources"""

    def test_per_module_highest_priority(self, monkeypatch):
        """Test per-module override has highest priority"""
        # Set global to mock, per-module to real
        monkeypatch.setenv("AI_INTEGRATION_MODE", "mock")
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        # Per-module should win
        assert get_mode("notebooklm") == IntegrationMode.REAL
        assert is_mock_mode("notebooklm") is False
        assert should_use_fallback("notebooklm") is False

    def test_global_over_default(self, monkeypatch):
        """Test global override has higher priority than default"""
        # Set global to real, no per-module override
        monkeypatch.setenv("AI_INTEGRATION_MODE", "real")

        # Global should override default fallback
        assert get_mode("notebooklm") == IntegrationMode.REAL
        assert get_mode("consensus_engine") == IntegrationMode.REAL

    def test_default_when_no_env(self):
        """Test default is used when no env variables are set"""
        # Clear env (monkeypatch fixture will restore original)
        assert get_mode("notebooklm") == IntegrationMode.FALLBACK
        assert get_mode("codex") == IntegrationMode.REAL
