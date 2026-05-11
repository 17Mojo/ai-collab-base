"""
NotebookLM MCP strict/fallback mode tests.
Tests for strict MCP adapter behavior without environment variable fallback.
"""

from __future__ import annotations

import builtins

import pytest

from ai_collab.integrations.notebooklm import NotebookLMIntegration


class TestStrictMCPMode:
    """Tests for STRICT (REAL) mode behavior"""

    def test_strict_mode_raises_on_missing_mcp_health_tool(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP health tool is missing"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._check_mcp_health()

        assert "MCP get_health 工具不可用" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_raises_on_mcp_health_empty_result(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP health returns empty"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        def fake_health():
            return None

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False
        )

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._check_mcp_health()

        assert "MCP 健康检查返回空结果" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_raises_on_mcp_not_authenticated(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP is not authenticated"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        def fake_health():
            return {"authenticated": False, "error": "Not logged in"}

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False
        )

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._check_mcp_health()

        assert "MCP 未认证" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_raises_on_missing_mcp_ask_tool(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP ask tool is missing"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._query_mcp("test topic")

        assert "MCP ask_question 工具不可用" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_raises_on_mcp_query_empty_result(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP query returns empty"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        def fake_ask_question(*, question, notebook_id):
            return None

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
        )

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._query_mcp("test topic")

        assert "MCP 查询返回空结果" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_raises_on_mcp_query_invalid_format(self, monkeypatch):
        """REAL mode should raise ConnectionError when MCP response format is invalid"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        def fake_ask_question(*, question, notebook_id):
            return {"invalid_key": "invalid_value"}

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
        )

        integration = NotebookLMIntegration()

        with pytest.raises(ConnectionError) as exc_info:
            integration._query_mcp("test topic")

        assert "MCP 响应格式错误" in str(exc_info.value)
        assert "REAL 模式" in str(exc_info.value)

    def test_strict_mode_succeeds_with_valid_mcp(self, monkeypatch):
        """REAL mode should succeed when MCP is properly configured"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")

        def fake_health():
            return {"authenticated": True, "active_sessions": 1}

        def fake_ask_question(*, question, notebook_id):
            return {
                "answer": "real answer",
                "sources": ["doc-a", "doc-b"],
                "session_id": "sess-1",
            }

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False
        )
        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
        )

        integration = NotebookLMIntegration(notebook_id="test-notebook")

        # Health check should pass
        assert integration._check_mcp_health() is True

        # Query should succeed
        result = integration._query_mcp("test topic")
        assert result["response"] == "real answer"
        assert result["mcp_mode"] == "real"


class TestFallbackMCPMode:
    """Tests for FALLBACK mode behavior"""

    def test_fallback_mode_returns_false_on_missing_mcp_health_tool(self, monkeypatch):
        """FALLBACK mode should return False (not raise) when MCP health tool is missing"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)

        integration = NotebookLMIntegration()

        # Should return False, not raise
        assert integration._check_mcp_health() is False

    def test_fallback_mode_returns_false_on_mcp_not_authenticated(self, monkeypatch):
        """FALLBACK mode should return False when MCP is not authenticated"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")

        def fake_health():
            return {"authenticated": False}

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False
        )

        integration = NotebookLMIntegration()

        # Should return False, not raise
        assert integration._check_mcp_health() is False

    def test_fallback_mode_raises_on_missing_mcp_ask_tool(self, monkeypatch):
        """FALLBACK mode should raise ConnectionError when MCP ask tool is missing"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)

        integration = NotebookLMIntegration()

        # Should raise (not return False)
        with pytest.raises(ConnectionError) as exc_info:
            integration._query_mcp("test topic")

        assert "MCP ask_question 工具不可用" in str(exc_info.value)
        # Should NOT contain "REAL 模式"
        assert "REAL 模式" not in str(exc_info.value)

    def test_fallback_mode_raises_on_mcp_query_invalid_format(self, monkeypatch):
        """FALLBACK mode should raise ConnectionError when MCP response format is invalid"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")

        def fake_ask_question(*, question, notebook_id):
            return {"invalid_key": "invalid_value"}

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
        )

        integration = NotebookLMIntegration()

        # Should raise (not return False)
        with pytest.raises(ConnectionError) as exc_info:
            integration._query_mcp("test topic")

        assert "MCP 响应格式错误" in str(exc_info.value)
        # Should NOT contain "REAL 模式"
        assert "REAL 模式" not in str(exc_info.value)

    def test_fallback_mode_succeeds_with_valid_mcp(self, monkeypatch):
        """FALLBACK mode should succeed when MCP is properly configured"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")

        def fake_health():
            return {"authenticated": True, "active_sessions": 1}

        def fake_ask_question(*, question, notebook_id):
            return {
                "answer": "real answer",
                "sources": ["doc-a", "doc-b"],
                "session_id": "sess-1",
            }

        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False
        )
        monkeypatch.setattr(
            builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
        )

        integration = NotebookLMIntegration(notebook_id="test-notebook")

        # Health check should pass
        assert integration._check_mcp_health() is True

        # Query should succeed
        result = integration._query_mcp("test topic")
        assert result["response"] == "real answer"
        assert result["mcp_mode"] == "real"

    def test_fallback_mode_query_knowledge_falls_back_to_mock(self, monkeypatch):
        """FALLBACK mode should fall back to mock when MCP fails"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)

        integration = NotebookLMIntegration()
        integration.connect()  # Should succeed and set _mock = True

        # Query should use mock mode
        result = integration.query_knowledge("test topic")
        assert "mode" in result
        # Should be either "mock" or "fallback"
        assert result["mode"] in ["mock", "fallback"]


class TestNoEnvironmentVariableFallback:
    """Tests to ensure no environment variable fallback is used"""

    def test_no_env_var_used_in_health_check(self, monkeypatch):
        """Health check should not use NOTEBOOKLM_MCP_AVAILABLE env var"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.setenv("NOTEBOOKLM_MCP_AVAILABLE", "true")  # Should be ignored
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)

        integration = NotebookLMIntegration()

        # Should return False (not use env var)
        assert integration._check_mcp_health() is False

    def test_no_env_var_used_in_query(self, monkeypatch):
        """Query should not use NOTEBOOKLM_MCP_AVAILABLE env var"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.setenv("NOTEBOOKLM_MCP_AVAILABLE", "true")  # Should be ignored
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)

        integration = NotebookLMIntegration()

        # Should raise (not use env var)
        with pytest.raises(ConnectionError):
            integration._query_mcp("test topic")
