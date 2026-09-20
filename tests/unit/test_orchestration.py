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



class TestAgentProviderCheckAvailability:
    def test_claude_code_always_available(self):
        p_obj = AgentProvider("claude_code", {})
        assert p_obj.check_availability() is True
        assert p_obj.connection_status.value == "connected"
        assert p_obj.last_check is not None

    def test_codearts_agent_available_when_vscode(self, monkeypatch):
        monkeypatch.setenv("VSCODE_PID", "12345")
        p_obj = AgentProvider("codearts_agent", {})
        assert p_obj.check_availability() is True

    def test_codearts_agent_unavailable_without_vscode(self, monkeypatch):
        monkeypatch.delenv("VSCODE_PID", raising=False)
        monkeypatch.delenv("CODEARTS_SESSION", raising=False)
        p_obj = AgentProvider("codearts_agent", {})
        assert p_obj.check_availability() is False
        assert p_obj.connection_status.value == "unavailable"

    def test_cli_provider_detected_via_which(self, monkeypatch):
        class FakeResult:
            returncode = 0
            stdout = b"/usr/bin/codex"
            stderr = b""
        monkeypatch.setattr(
            "ai_collab.orchestration.subprocess.run",
            lambda *a, **kw: FakeResult()
        )
        p_obj = AgentProvider("codex_cli", {})
        assert p_obj.check_availability() is True
        assert p_obj.connection_status.value == "detected"

    def test_cli_provider_unavailable_when_which_fails(self, monkeypatch):
        class FakeResult:
            returncode = 1
            stdout = b""
            stderr = b"not found"
        monkeypatch.setattr(
            "ai_collab.orchestration.subprocess.run",
            lambda *a, **kw: FakeResult()
        )
        p_obj = AgentProvider("codex_cli", {})
        assert p_obj.check_availability() is False

    def test_cli_provider_handles_timeout(self, monkeypatch):
        import subprocess as sp_mod
        def fake_run(*a, **kw):
            raise sp_mod.TimeoutExpired(cmd="x", timeout=5)
        monkeypatch.setattr("ai_collab.orchestration.subprocess.run", fake_run)
        p_obj = AgentProvider("codex_cli", {})
        assert p_obj.check_availability() is False

    def test_unknown_provider_unavailable(self):
        p_obj = AgentProvider("totally_unknown_xyz", {})
        assert p_obj.check_availability() is False


class TestOrchestrationConfigLifecycle:
    def test_create_default_config_and_load(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        assert cfg.load() is True
        assert os.path.exists(cfg.config_file)

    def test_save_and_reload(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.roles["AGENT_EXEC"] = OrchestrationRole(
            role_id="AGENT_EXEC",
            display_name="执行",
            duties=["实现"],
            required_capabilities=["code"],
            raci_role="R",
        )
        cfg.roles["AGENT_EXEC"].activate("claude_code", "sonnet")
        assert cfg.save() is True
        assert os.path.exists(cfg.config_file)
        cfg2 = OrchestrationConfig(workspace_path=str(tmp_path))
        assert cfg2.load() is True
        assert "AGENT_EXEC" in cfg2.roles

    def test_save_creates_file(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.config["custom_field"] = "value"
        assert cfg.save() is True

    def test_load_handles_invalid_json(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg_file = cfg.config_file
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        result = cfg.load()
        assert result is False


class TestOrchestrationConfigStatus:
    def test_get_binding_status_initially_uninitialized(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        assert cfg.get_binding_status() == BindingStatus.UNINITIALIZED

    def test_update_binding_status_minimal(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.roles["R1"] = OrchestrationRole(
            role_id="R1", display_name="d", duties=["d"],
            required_capabilities=["d"], raci_role="R",
        )
        cfg.roles["R1"].activate("claude_code")
        cfg.update_binding_status()
        assert cfg.config["binding_status"] == BindingStatus.MINIMAL.value

    def test_update_binding_status_partial(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        for i in range(3):
            rid = f"R{i}"
            cfg.roles[rid] = OrchestrationRole(
                role_id=rid, display_name="d", duties=["d"],
                required_capabilities=["d"], raci_role="R",
            )
        cfg.roles["R0"].activate("claude_code")
        cfg.roles["R1"].activate("claude_code")
        cfg.update_binding_status()
        assert cfg.config["binding_status"] == BindingStatus.PARTIAL.value

    def test_update_binding_status_active(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        for rid in ["R1", "R2"]:
            cfg.roles[rid] = OrchestrationRole(
                role_id=rid, display_name="d", duties=["d"],
                required_capabilities=["d"], raci_role="R",
            )
            cfg.roles[rid].activate("claude_code")
        cfg.update_binding_status()
        assert cfg.config["binding_status"] == BindingStatus.ACTIVE.value

    def test_is_cold_start_needed_initial(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        assert cfg.is_cold_start_needed() is True

    def test_is_cold_start_not_needed_after_wizard(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.config["binding_status"] = BindingStatus.ACTIVE.value
        cfg.config["cold_start_config"] = {"wizard_completed": True}
        assert cfg.is_cold_start_needed() is False


class TestOrchestrationConfigProviders:
    def test_detect_providers(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        providers = cfg.detect_providers()
        assert "claude_code" in providers

    def test_get_available_providers_filters(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.providers["p1"] = AgentProvider("p1", {})
        cfg.providers["p1"].connection_status = ProviderConnectionStatus.CONNECTED
        cfg.providers["p2"] = AgentProvider("p2", {})
        cfg.providers["p2"].connection_status = ProviderConnectionStatus.UNAVAILABLE
        available = cfg.get_available_providers()
        assert len(available) == 1
        assert available[0].provider_id == "p1"


class TestOrchestrationConfigHistory:
    def test_add_history_event(self, tmp_path):
        cfg = OrchestrationConfig(workspace_path=str(tmp_path))
        cfg.config["history"] = []
        cfg.add_history_event("test_event", {"key": "value"})
        assert len(cfg.config["history"]) == 1
        assert cfg.config["history"][0]["event"] == "test_event"


class TestOrchestrationRoleActivate:
    def test_activate_sets_timestamp(self):
        role = OrchestrationRole(
            role_id="R", display_name="d", duties=["d"],
            required_capabilities=["d"], raci_role="R",
        )
        assert role.activated_at is None
        role.activate("claude_code")
        assert role.activated_at is not None

    def test_to_dict_with_none_timestamps(self):
        role = OrchestrationRole(
            role_id="R", display_name="d", duties=["d"],
            required_capabilities=["d"], raci_role="R",
        )
        d = role.to_dict()
        assert d["created_at"] is None
        assert d["activated_at"] is None
