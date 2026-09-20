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



class TestNotebookLMConnect:
    def test_connect_mock_mode(self, monkeypatch):
        """MOCK 模式应该直接连接成功"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        assert integration.connect() is True
        assert integration.is_connected is True

    def test_connect_real_mode_mcp_unavailable(self, monkeypatch):
        """REAL 模式下 MCP 不可用应该失败"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        integration = NotebookLMIntegration()
        assert integration.connect() is False

    def test_connect_fallback_to_mock(self, monkeypatch):
        """FALLBACK 模式下 MCP 不可用应该回退到 MOCK"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        integration = NotebookLMIntegration()
        assert integration.connect() is True
        assert integration._mock is True
        assert integration.is_connected is True


class TestNotebookLMQueryKnowledge:
    def test_query_knowledge_mock_mode(self, monkeypatch):
        """MOCK 模式直接返回模拟数据"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        result = integration.query_knowledge("测试主题")
        assert result["mode"] == "mock"
        assert "response" in result
        assert "sources" in result

    def test_query_knowledge_with_context(self, monkeypatch):
        """带 context 的查询"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        result = integration.query_knowledge("测试主题", context="背景信息")
        assert "query" in result
        assert "背景信息" in result["query"]

    def test_query_knowledge_fallback_on_failure(self, monkeypatch):
        """FALLBACK 模式 MCP 失败时回退到 MOCK"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "fallback")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)
        integration = NotebookLMIntegration()
        integration.connect()  # trigger fallback to mock
        result = integration.query_knowledge("测试")
        # After fallback, integration is in mock mode
        assert result["mode"] in ("mock", "fallback")
        assert "response" in result

    def test_query_knowledge_real_mode_failure(self, monkeypatch):
        """REAL 模式 MCP 不可用时返回 error"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)
        integration = NotebookLMIntegration()
        result = integration.query_knowledge("测试")
        assert "error" in result


class TestNotebookLMEnhancePrompt:
    def test_enhance_prompt_success(self, monkeypatch):
        """成功增强 prompt"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        enhanced = integration.enhance_prompt("原始 prompt", "主题")
        assert "原始 prompt" in enhanced
        assert "参考知识" in enhanced
        assert "来源" in enhanced

    def test_enhance_prompt_returns_original_on_error(self, monkeypatch):
        """查询失败时返回原始 prompt"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__ask_question", raising=False)
        integration = NotebookLMIntegration()
        original = "原始 prompt"
        enhanced = integration.enhance_prompt(original, "主题")
        assert enhanced == original


class TestNotebookLMSaveResult:
    def test_save_result_success(self, monkeypatch, capsys):
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        assert integration.save_result("测试内容", {"topic": "测试主题", "pack_name": "TestPack", "tags": ["t1"]}) is True

    def test_save_result_even_when_not_connected(self, monkeypatch, capsys):
        """save_result 在未连接时调用 connect,REAL 模式下 connect 返回 False 但 save_result 仍 print"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "real")
        monkeypatch.delattr(builtins, "mcp__plugin_notebooklm__get_health", raising=False)
        integration = NotebookLMIntegration()
        result = integration.save_result("content", {"topic": "测试"})
        # save_result 总是返回 True(因为没有真实的保存实现,只是 print)
        assert result is True


class TestNotebookLMRecommendPacks:
    def test_get_recommended_packs(self, monkeypatch):
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        packs = integration.get_recommended_packs("帮我写文章")
        assert isinstance(packs, list)
        assert len(packs) > 0
        for p_obj in packs:
            assert "pack_name" in p_obj
            assert "relevance" in p_obj
            assert "reason" in p_obj


class TestNotebookLMCreateNotebook:
    def test_create_notebook_from_pack(self, monkeypatch, capsys):
        monkeypatch.setenv("AI_INTEGRATION_MODE_NOTEBOOKLM", "mock")
        integration = NotebookLMIntegration()
        pack = {
            "metadata": {
                "pack_name": "测试Pack",
                "description": "测试描述"
            },
            "workflow": {
                "steps": [
                    {"name": "步骤1", "type": "GENERATION"},
                    {"name": "步骤2", "type": "LOCAL"}
                ]
            }
        }
        notebook_id = integration.create_notebook_from_pack(pack)
        assert notebook_id.startswith("notebook-")


class TestNotebookLMStudioConverter:
    def test_convert_basic(self):
        from ai_collab.integrations.notebooklm import PackToStudioConverter
        converter = PackToStudioConverter()
        pack = {
            "metadata": {
                "pack_name": "TestPack",
                "description": "Test Desc",
                "tags": ["t1"]
            },
            "workflow": {
                "steps": [
                    {"name": "S1", "type": "GENERATION", "template": "Hello {name}", "params": {"max_tokens": 100}},
                    {"name": "S2", "type": "LOCAL", "inputs": [{"key": "name", "required": True, "default": "World"}]}
                ]
            }
        }
        result = converter.convert(pack)
        assert result["name"] == "TestPack"
        assert result["description"] == "Test Desc"
        assert "Hello" in result["prompt"]
        assert len(result["variables"]) == 1
        assert result["variables"][0]["name"] == "name"
        assert len(result["workflow"]) == 2
        assert result["workflow"][0]["config"]["template"] == "Hello {name}"
        assert result["workflow"][0]["config"]["params"]["max_tokens"] == 100

    def test_extract_prompt_with_no_generation(self):
        from ai_collab.integrations.notebooklm import PackToStudioConverter
        converter = PackToStudioConverter()
        pack = {"workflow": {"steps": [{"name": "S1", "type": "LOCAL"}]}}
        prompt = converter._extract_prompt(pack)
        assert prompt == ""

    def test_extract_variables_empty(self):
        from ai_collab.integrations.notebooklm import PackToStudioConverter
        converter = PackToStudioConverter()
        pack = {"workflow": {"steps": [{"name": "S1", "type": "GENERATION"}]}}
        variables = converter._extract_variables(pack)
        assert variables == []

    def test_convert_workflow_with_other_step_types(self):
        from ai_collab.integrations.notebooklm import PackToStudioConverter
        converter = PackToStudioConverter()
        workflow = {"steps": [{"name": "S1", "type": "VALIDATION"}]}
        result = converter._convert_workflow(workflow)
        assert len(result) == 1
        assert result[0]["type"] == "VALIDATION"
        assert result[0]["config"] == {}
