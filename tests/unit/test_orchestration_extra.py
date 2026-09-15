
"""
orchestration.py 补测 - 重点覆盖 enum 和数据类
目标: 27% -> 40%+ (单测可覆盖的部分)
"""

import pytest

from ai_collab.orchestration import (
    AgentProvider,
    BindingStatus,
    ProviderConnectionStatus,
    RoleStatus,
    StartupMode,
)


# ============================================================
# Enum 值校验
# ============================================================

def test_binding_status_enum_values():
    assert BindingStatus.UNINITIALIZED.value == "uninitialized"
    assert BindingStatus.MINIMAL.value == "minimal"
    assert BindingStatus.PARTIAL.value == "partial"
    assert BindingStatus.ACTIVE.value == "active"


def test_startup_mode_enum_values():
    assert StartupMode.SINGLE_AGENT.value == "single_agent"
    assert StartupMode.SUB_AGENT.value == "sub_agent"
    assert StartupMode.MULTI_AGENT.value == "multi_agent"


def test_role_status_enum_values():
    assert RoleStatus.ACTIVE.value == "active"
    assert RoleStatus.DORMANT.value == "dormant"
    assert RoleStatus.DISABLED.value == "disabled"


def test_provider_connection_status_enum_values():
    assert ProviderConnectionStatus.CONNECTED.value == "connected"
    assert ProviderConnectionStatus.DETECTED.value == "detected"
    assert ProviderConnectionStatus.UNAVAILABLE.value == "unavailable"


# ============================================================
# AgentProvider 构造与属性
# ============================================================

def test_agent_provider_default_construction():
    """空 config 时使用 defaults"""
    p = AgentProvider("unknown_id", {})
    assert p.provider_id == "unknown_id"
    assert p.name == "unknown_id"  # default to id
    assert p.connection_status == ProviderConnectionStatus.UNAVAILABLE
    assert p.supports_sub_agent is False
    assert p.model_variants == []
    assert p.capabilities == []
    assert p.last_check is None


def test_agent_provider_with_config():
    """带 config 时正确填充属性"""
    config = {
        "name": "Custom Provider",
        "supports_sub_agent": True,
        "model_variants": ["gpt-4", "gpt-3.5"],
        "capabilities": ["code", "test"],
    }
    p = AgentProvider("custom_id", config)
    assert p.name == "Custom Provider"
    assert p.supports_sub_agent is True
    assert p.model_variants == ["gpt-4", "gpt-3.5"]
    assert p.capabilities == ["code", "test"]


def test_agent_provider_claude_code_always_available():
    """claude_code 提供商始终可用 (CLI 集成)"""
    p = AgentProvider("claude_code", AgentProvider.PROVIDER_DETECTORS["claude_code"])
    assert p.check_availability() is True
    assert p.connection_status == ProviderConnectionStatus.CONNECTED
    assert p.last_check is not None


def test_agent_provider_partial_config():
    """config 缺失部分字段时使用 defaults"""
    config = {"name": "Minimal"}
    p = AgentProvider("min", config)
    assert p.name == "Minimal"
    assert p.supports_sub_agent is False  # default
    assert p.model_variants == []  # default
    assert p.capabilities == []  # default


def test_provider_detectors_contains_expected_keys():
    """PROVIDER_DETECTORS 字典含 4 个标准提供商"""
    expected = {"claude_code", "codex_cli", "gemini_cli", "codearts_agent"}
    actual = set(AgentProvider.PROVIDER_DETECTORS.keys())
    assert expected.issubset(actual)


def test_provider_detectors_have_required_fields():
    """每个 PROVIDER_DETECTORS 字典必须有 name 字段"""
    for provider_id, config in AgentProvider.PROVIDER_DETECTORS.items():
        assert "name" in config, f"{provider_id} missing name"
        assert isinstance(config.get("capabilities", []), list)
