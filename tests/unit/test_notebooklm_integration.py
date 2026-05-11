"""
NotebookLM integration tests for MCP adapter behavior.
"""

from __future__ import annotations

import builtins

import pytest

from ai_collab.integrations.notebooklm import NotebookLMIntegration


def test_check_mcp_health_uses_builtin_tool(monkeypatch):
    """When MCP health tool exists, adapter should use it."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")

    def fake_health():
        return {"authenticated": True, "active_sessions": 1}

    monkeypatch.setattr(builtins, "mcp__plugin_notebooklm__get_health", fake_health, raising=False)

    integration = NotebookLMIntegration()
    assert integration._check_mcp_health() is True


def test_check_mcp_health_falls_back_to_env(monkeypatch):
    """When MCP health tool is missing, adapter should return False (no env fallback)."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
    monkeypatch.setenv("NOTEBOOKLM_MCP_AVAILABLE", "true")  # Should be ignored
    monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)

    integration = NotebookLMIntegration()
    # Should return False (not use env var)
    assert integration._check_mcp_health() is False


def test_query_mcp_uses_builtin_ask_question(monkeypatch):
    """When MCP ask tool exists, adapter should map its response."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")

    def fake_ask_question(*, question, notebook_id):
        assert "关于测试主题的详细信息" in question
        assert notebook_id == "test-notebook"
        return {
            "answer": "real answer",
            "sources": ["doc-a", "doc-b"],
            "session_id": "sess-1",
        }

    monkeypatch.setattr(
        builtins, "mcp__plugin_notebooklm__ask_question", fake_ask_question, raising=False
    )

    integration = NotebookLMIntegration(notebook_id="test-notebook")
    result = integration._query_mcp("测试主题")

    assert result["response"] == "real answer"
    assert result["sources"] == ["doc-a", "doc-b"]
    assert result["session_id"] == "sess-1"
    assert result["mcp_mode"] == "real"


def test_query_mcp_falls_back_to_simulated(monkeypatch):
    """When MCP ask tool is missing, adapter should raise (no env fallback)."""
    monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
    monkeypatch.setenv("NOTEBOOKLM_MCP_AVAILABLE", "true")  # Should be ignored
    monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)

    integration = NotebookLMIntegration()

    # Should raise ConnectionError (not use env var)
    with pytest.raises(ConnectionError) as exc_info:
        integration._query_mcp("测试主题")

    assert "MCP ask_question 工具不可用" in str(exc_info.value)
