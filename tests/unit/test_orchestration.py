"""
orchestration.py 的最小测试覆盖

目标：从 0% 到 70%+ 局部覆盖率
"""

import os

from ai_collab.orchestration import (
    AgentProvider,
    BindingStatus,
    OrchestrationConfig,
    OrchestrationRole,
    ProviderConnectionStatus,
    RoleStatus,
    StartupMode,
)


class TestEnums:
    def test_binding_status_values(self):
        assert BindingStatus.UNINITIALIZED.value == "uninitialized"
        assert BindingStatus.MINIMAL.value == "minimal"
        assert BindingStatus.PARTIAL.value == "partial"
        assert BindingStatus.ACTIVE.value == "active"

    def test_startup_mode_values(self):
        assert StartupMode.SINGLE_AGENT.value == "single_agent"
        assert StartupMode.SUB_AGENT.value == "sub_agent"
        assert StartupMode.MULTI_AGENT.value == "multi_agent"

    def test_provider_connection_values(self):
        assert ProviderConnectionStatus.CONNECTED.value == "connected"
        assert ProviderConnectionStatus.DETECTED.value == "detected"
        assert ProviderConnectionStatus.UNAVAILABLE.value == "unavailable"


class TestAgentProvider:
    def test_init_minimal(self):
        p = AgentProvider("codex", {"type": "cli"})
        assert p.provider_id == "codex"
        assert p.connection_status == ProviderConnectionStatus.UNAVAILABLE
        assert p.supports_sub_agent is False

    def test_init_with_supports_sub_agent(self):
        p = AgentProvider("claude_code", {"supports_sub_agent": True})
        assert p.supports_sub_agent is True

    def test_init_with_capabilities(self):
        p = AgentProvider("codex", {"capabilities": ["implementation", "testing"]})
        assert "implementation" in p.capabilities

    def test_init_with_model_variants(self):
        p = AgentProvider("claude_code", {"model_variants": ["opus", "sonnet"]})
        assert "opus" in p.model_variants


class TestAgentProviderDetectors:
    def test_detector_claude_code(self):
        d = AgentProvider.PROVIDER_DETECTORS["claude_code"]
        assert d["name"] == "Claude Code"
        assert d["supports_sub_agent"] is True

    def test_detector_codex_cli(self):
        d = AgentProvider.PROVIDER_DETECTORS["codex_cli"]
        assert d["check_command"] == "which codex"

    def test_detector_gemini_cli(self):
        d = AgentProvider.PROVIDER_DETECTORS["gemini_cli"]
        assert d["check_command"] == "which gemini"


class TestOrchestrationRole:
    def test_init_basic(self):
        role = OrchestrationRole(
            role_id="AGENT_ARCH",
            display_name="架构师",
            duties=["设计 API"],
            required_capabilities=["api-design"],
            raci_role="R",
        )
        assert role.role_id == "AGENT_ARCH"
        assert role.display_name == "架构师"

    def test_init_defaults_binding(self):
        role = OrchestrationRole(
            role_id="AGENT_TEST",
            display_name="测试",
            duties=["写测试"],
            required_capabilities=["pytest"],
            raci_role="R",
        )
        assert role.binding["status"] == RoleStatus.DORMANT.value
        assert role.activated_at is None

    def test_is_active_default_false(self):
        role = OrchestrationRole(
            role_id="R",
            display_name="d",
            duties=["d"],
            required_capabilities=["d"],
            raci_role="R",
        )
        assert role.is_active() is False

    def test_activate(self):
        role = OrchestrationRole(
            role_id="R",
            display_name="d",
            duties=["d"],
            required_capabilities=["d"],
            raci_role="R",
        )
        role.activate("claude_code", "opus")
        assert role.is_active() is True
        assert role.binding["provider"] == "claude_code"
        assert role.binding["model_variant"] == "opus"
        assert role.activated_at is not None

    def test_deactivate(self):
        role = OrchestrationRole(
            role_id="R",
            display_name="d",
            duties=["d"],
            required_capabilities=["d"],
            raci_role="R",
        )
        role.activate("claude_code")
        role.deactivate()
        assert role.is_active() is False

    def test_to_dict(self):
        role = OrchestrationRole(
            role_id="R",
            display_name="d",
            duties=["d"],
            required_capabilities=["d"],
            raci_role="R",
        )
        d = role.to_dict()
        assert d["role_id"] == "R"
        assert d["raci_role"] == "R"
        assert d["binding"] is not None


class TestOrchestrationConfig:
    def test_init_paths(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        assert cfg.workspace_path == str(tmp_path)
        assert cfg.config_dir.endswith("config")
        assert cfg.config_file.endswith("agent-orchestration.json")
        assert cfg.config == {}
        assert cfg.roles == {}

    def test_init_creates_config_dir(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        assert os.path.exists(cfg.config_dir)

    def test_default_roles_constant(self):
        roles = OrchestrationConfig.DEFAULT_ROLES
        assert "AGENT_EXEC" in roles
        assert "AGENT_ARCH" in roles
        assert "AGENT_TEST" in roles

    def test_command_prefixes_default(self):
        prefixes = OrchestrationConfig.DEFAULT_COMMAND_PREFIXES
        assert "A.RUN" in prefixes
        assert "X.RUN" in prefixes
        assert "C.RUN" in prefixes
