#!/usr/bin/env python3
"""
Tests for ai_collab/integrations/vscode.py
"""

import json
import os
from unittest.mock import patch

import pytest

from ai_collab.integrations.vscode import VSCodeIntegration


class TestVSCodeIntegration:
    """Tests for VSCodeIntegration class"""

    def test_is_valid_workspace_with_valid_path(self, tmp_path):
        """Test _is_valid_workspace with valid directory"""
        valid_dir = str(tmp_path)
        assert VSCodeIntegration._is_valid_workspace(valid_dir) is True

    def test_is_valid_workspace_with_invalid_path(self):
        """Test _is_valid_workspace with non-existent path"""
        assert VSCodeIntegration._is_valid_workspace("/nonexistent/path") is False

    def test_is_valid_workspace_with_empty_string(self):
        """Test _is_valid_workspace with empty string"""
        assert VSCodeIntegration._is_valid_workspace("") is False

    def test_is_valid_workspace_with_none(self):
        """Test _is_valid_workspace with None"""
        assert VSCodeIntegration._is_valid_workspace(None) is False

    def test_is_valid_workspace_with_root_path(self):
        """Test _is_valid_workspace with root path (should be invalid)"""
        # Root path should be invalid
        assert VSCodeIntegration._is_valid_workspace(os.sep) is False

    def test_get_workspace_path_from_env(self, tmp_path, monkeypatch):
        """Test get_workspace_path from environment variable"""
        # Set VSCODE_CWD environment variable
        monkeypatch.setenv("VSCODE_CWD", str(tmp_path))

        result = VSCodeIntegration.get_workspace_path()
        assert result == str(tmp_path.absolute())

    def test_get_workspace_path_from_vscode_dir(self, tmp_path, monkeypatch):
        """Test get_workspace_path by finding .vscode directory"""
        # Create .vscode directory
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()

        # Change to subdirectory
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        monkeypatch.chdir(sub_dir)

        # Remove VSCODE_CWD from environment if exists
        monkeypatch.delenv("VSCODE_CWD", raising=False)

        result = VSCodeIntegration.get_workspace_path()
        assert result == str(tmp_path.absolute())

    def test_get_workspace_path_from_package_json(self, tmp_path, monkeypatch):
        """Test get_workspace_path by finding package.json"""
        # Create package.json
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test-project"}')

        # Change to subdirectory
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        monkeypatch.chdir(sub_dir)

        # Remove VSCODE_CWD from environment if exists
        monkeypatch.delenv("VSCODE_CWD", raising=False)

        result = VSCodeIntegration.get_workspace_path()
        assert result == str(tmp_path.absolute())

    def test_get_workspace_path_returns_cwd(self, tmp_path, monkeypatch):
        """Test get_workspace_path returns cwd when no workspace found"""
        monkeypatch.chdir(tmp_path)

        # Remove VSCODE_CWD from environment if exists
        monkeypatch.delenv("VSCODE_CWD", raising=False)

        result = VSCodeIntegration.get_workspace_path()
        assert result == str(tmp_path.absolute())

    def test_get_project_config_with_valid_file(self, tmp_path, monkeypatch):
        """Test get_project_config with valid config file"""
        # Create .vscode directory and config file
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        config_file = vscode_dir / "ai-collab.json"
        config_data = {"version": "1.0", "enabled": True}
        config_file.write_text(json.dumps(config_data))

        # Mock get_workspace_path
        with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)):
            result = VSCodeIntegration.get_project_config()
            assert result == config_data

    def test_get_project_config_with_invalid_json(self, tmp_path, monkeypatch):
        """Test get_project_config with invalid JSON"""
        # Create .vscode directory and invalid config file
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        config_file = vscode_dir / "ai-collab.json"
        config_file.write_text("invalid json")

        # Mock get_workspace_path
        with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)):
            result = VSCodeIntegration.get_project_config()
            assert result == {}

    def test_get_project_config_without_file(self, tmp_path, monkeypatch):
        """Test get_project_config when config file doesn't exist"""
        # Mock get_workspace_path
        with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)):
            result = VSCodeIntegration.get_project_config()
            assert result == {}

    def test_get_project_config_without_workspace(self, monkeypatch):
        """Test get_project_config when workspace is None"""
        # Mock get_workspace_path to return None
        with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None):
            result = VSCodeIntegration.get_project_config()
            assert result == {}

    def test_get_global_config_with_valid_file(self, tmp_path, monkeypatch):
        """Test get_global_config with valid config file"""
        # Create global config directory and file
        vscode_dir = tmp_path / ".vscode" / "ai-collab"
        vscode_dir.mkdir(parents=True)
        config_file = vscode_dir / "config.json"
        config_data = {"global_setting": "value"}
        config_file.write_text(json.dumps(config_data))

        # Mock expanduser to return the vscode directory
        with patch("os.path.expanduser", return_value=str(vscode_dir)):
            result = VSCodeIntegration.get_global_config()
            assert result == config_data

    def test_get_global_config_with_invalid_json(self, tmp_path, monkeypatch):
        """Test get_global_config with invalid JSON"""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        vscode_dir = home_dir / ".vscode" / "ai-collab"
        vscode_dir.mkdir(parents=True)
        config_file = vscode_dir / "config.json"
        config_file.write_text("invalid json")

        # Mock expanduser
        with patch("os.path.expanduser", return_value=str(vscode_dir.parent)):
            result = VSCodeIntegration.get_global_config()
            assert result == {}

    def test_get_global_config_without_file(self, tmp_path, monkeypatch):
        """Test get_global_config when config file doesn't exist"""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        vscode_dir = home_dir / ".vscode" / "ai-collab"
        vscode_dir.mkdir(parents=True)

        # Mock expanduser
        with patch("os.path.expanduser", return_value=str(vscode_dir.parent)):
            result = VSCodeIntegration.get_global_config()
            assert result == {}

    def test_get_global_config_handles_io_error(self, tmp_path, monkeypatch):
        """Test get_global_config handles IOError"""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        vscode_dir = home_dir / ".vscode" / "ai-collab"
        vscode_dir.mkdir(parents=True)
        config_file = vscode_dir / "config.json"
        config_file.write_text('{"test": "data"}')

        # Mock expanduser and make file unreadable
        with patch("os.path.expanduser", return_value=str(vscode_dir.parent)):
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                result = VSCodeIntegration.get_global_config()
                assert result == {}

    def test_get_rule_files_for_claude(self, tmp_path):
        """Test get_rule_files includes governance quickstart for claude."""
        with patch.object(
            VSCodeIntegration, "get_project_config", return_value={"rulesDir": "./rules"}
        ):
            files = VSCodeIntegration.get_rule_files("claude_code")
        assert any("claude_code_memory.md" in path for path in files)
        assert any("agent_governance_quickstart.md" in path for path in files)

    def test_get_rule_files_for_codearts(self, tmp_path):
        """Test get_rule_files returns codearts rule chain."""
        with patch.object(
            VSCodeIntegration, "get_project_config", return_value={"rulesDir": "./rules"}
        ):
            files = VSCodeIntegration.get_rule_files("codearts_agent")
        assert any("codearts_agent_rules.md" in path for path in files)
        assert any("agent_governance_quickstart.md" in path for path in files)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
