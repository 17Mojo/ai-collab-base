#!/usr/bin/env python3
"""Tests for ai_collab.dev_logger."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_collab.dev_logger import DevLogger, VSCodeIntegration, VSCodeOutputLogger


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(VSCodeIntegration, "get_workspace_path", lambda: str(tmp_path))
    monkeypatch.setattr(VSCodeIntegration, "get_project_config", lambda: {})
    return tmp_path


@pytest.fixture
def default_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Force deterministic template source for assertions in this test module.
    monkeypatch.setattr(DevLogger, "TEMPLATE_FILE", str(tmp_path / "missing-template.md"))


class TestVSCodeIntegration:
    def test_get_workspace_path_prefers_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VSCODE_CWD", "/tmp/ws")
        assert VSCodeIntegration.get_workspace_path() == "/tmp/ws"

    def test_get_project_config_without_workspace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(VSCodeIntegration, "get_workspace_path", lambda: None)
        assert VSCodeIntegration.get_project_config() == {}

    def test_get_project_config_reads_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg_file = tmp_path / ".vscode" / "ai-collab.json"
        cfg_file.parent.mkdir(parents=True)
        cfg_file.write_text(json.dumps({"logsDir": "custom_logs"}), encoding="utf-8")
        monkeypatch.setattr(VSCodeIntegration, "get_workspace_path", lambda: str(tmp_path))

        config = VSCodeIntegration.get_project_config()
        assert config["logsDir"] == "custom_logs"

    def test_get_project_config_invalid_json_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg_file = tmp_path / ".vscode" / "ai-collab.json"
        cfg_file.parent.mkdir(parents=True)
        cfg_file.write_text("{invalid", encoding="utf-8")
        monkeypatch.setattr(VSCodeIntegration, "get_workspace_path", lambda: str(tmp_path))

        assert VSCodeIntegration.get_project_config() == {}

    def test_update_vscode_output_writes_line(self, tmp_path: Path) -> None:
        with patch("os.path.expanduser", return_value=str(tmp_path)):
            VSCodeIntegration.update_vscode_output("hello", "test-channel")

        logs = list(tmp_path.glob("output_*.log"))
        assert len(logs) == 1
        content = logs[0].read_text(encoding="utf-8")
        assert "hello" in content
        assert "[test-channel]" in content

    def test_update_vscode_output_handles_exception(self) -> None:
        with patch("os.makedirs", side_effect=PermissionError("denied")):
            VSCodeIntegration.update_vscode_output("no-crash")


class TestVSCodeOutputLogger:
    def test_log_delegates(self) -> None:
        with patch.object(VSCodeIntegration, "update_vscode_output") as mock_update:
            VSCodeOutputLogger.log("message", "channel")
        mock_update.assert_called_once_with("message", "channel")

    def test_specialized_log_messages(self) -> None:
        with patch.object(VSCodeOutputLogger, "log") as mock_log:
            VSCodeOutputLogger.log_activation("claude", "S1", ["r1", "r2"])
            msg, channel = mock_log.call_args.args
            assert "Session=S1" in msg
            assert "Rules=r1, r2" in msg
            assert channel == "AI Collab Activation"

        with patch.object(VSCodeOutputLogger, "log") as mock_log:
            VSCodeOutputLogger.log_conflict(
                {"task_id_1": "A", "task_id_2": "B", "overlapping_files": ["x.py"]}
            )
            msg, channel = mock_log.call_args.args
            assert "A vs B" in msg
            assert channel == "AI Collab Conflicts"

        with patch.object(VSCodeOutputLogger, "log") as mock_log:
            VSCodeOutputLogger.log_task(
                {
                    "task_id": "TASK-1",
                    "ai_type": "codex",
                    "status": "in_progress",
                    "description": "desc",
                }
            )
            msg, channel = mock_log.call_args.args
            assert "TASK-1" in msg
            assert "Status=in_progress" in msg
            assert channel == "AI Collab Tasks"

        with patch.object(VSCodeOutputLogger, "log") as mock_log:
            VSCodeOutputLogger.log_progress("TASK-2", "Build", "running")
            msg, channel = mock_log.call_args.args
            assert "TASK: TASK-2" in msg
            assert "Stage: Build" in msg
            assert "running" in msg
            assert channel == "AI Collab Progress"


class TestDevLogger:
    def test_init_uses_workspace_defaults(self, workspace: Path, default_template: None) -> None:
        logger = DevLogger("claude-code", enable_git_log=False, enable_vsc_log=False)
        assert Path(logger.log_dir) == workspace / "logs" / "claude-code"
        assert (workspace / "logs" / "claude-code").exists()

    def test_init_applies_project_config(
        self, workspace: Path, default_template: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            VSCodeIntegration,
            "get_project_config",
            lambda: {"logsDir": "custom_logs", "autoLogToGit": False},
        )

        logger = DevLogger("copilot", enable_git_log=True, enable_vsc_log=False)
        assert Path(logger.log_dir) == workspace / "custom_logs" / "copilot"
        assert logger.enable_git_log is False
        assert not (workspace / ".git" / "ai-collab" / "copilot").exists()

    def test_create_log_writes_local_and_git_copy(
        self, workspace: Path, default_template: None
    ) -> None:
        logger = DevLogger("claude-code", enable_git_log=True, enable_vsc_log=False)
        path = Path(
            logger.create_log(
                task_name="feature/login api",
                task_id="TASK-001",
                description="implement login",
                goal="ship auth",
                steps="1. impl",
                risks="none",
            )
        )
        assert path.exists()
        assert path.parent.name == datetime.now().strftime("%Y-%m")
        content = path.read_text(encoding="utf-8")
        assert "TASK-001" in content
        assert "implement login" in content
        assert "进行中..." in content

        git_copy = workspace / ".git" / "ai-collab" / "claude-code" / path.name
        assert git_copy.exists()
        assert git_copy.read_text(encoding="utf-8") == content

    def test_append_update_and_finalize_sync(self, workspace: Path, default_template: None) -> None:
        logger = DevLogger("claude-code", enable_git_log=True, enable_vsc_log=False)
        path = Path(logger.create_log(task_name="task-append"))

        logger.append_to_log(str(path), "执行过程", "新增过程记录")
        logger.update_section(str(path), "总结", "最终总结内容")
        assert "最终总结内容" in path.read_text(encoding="utf-8")
        logger.finalize_log(str(path), summary="上线完成", coverage="88%")

        content = path.read_text(encoding="utf-8")
        assert "新增过程记录" in content
        assert "最终总结内容" not in content
        assert "上线完成" in content
        assert "覆盖率: 88%" in content
        assert "进行中..." not in content

        git_copy = workspace / ".git" / "ai-collab" / "claude-code" / path.name
        git_content = git_copy.read_text(encoding="utf-8")
        assert "最终总结内容" not in git_content
        assert "上线完成" in git_content

    def test_missing_file_raises(self, workspace: Path, default_template: None) -> None:
        logger = DevLogger("claude-code", enable_git_log=False, enable_vsc_log=False)
        missing = str(workspace / "not-exists.md")
        with pytest.raises(FileNotFoundError):
            logger.append_to_log(missing, "执行过程", "x")
        with pytest.raises(FileNotFoundError):
            logger.update_section(missing, "总结", "x")

    def test_list_logs_and_rotate(self, workspace: Path, default_template: None) -> None:
        logger = DevLogger("claude-code", enable_git_log=False, enable_vsc_log=False)
        created: list[Path] = []
        for idx in range(3):
            path = Path(logger.create_log(task_name=f"task-{idx}"))
            ts = 1_700_000_000 + idx
            os.utime(path, (ts, ts))
            created.append(path)

        assert len(logger.list_logs()) == 3
        month = datetime.now().strftime("%Y-%m")
        assert len(logger.list_logs(month=month)) == 3

        logger.rotate_logs(max_files=2)
        remaining = {Path(item).name for item in logger.list_logs()}
        assert len(remaining) == 2
        assert created[0].name not in remaining

    def test_vscode_notifications_when_enabled(
        self, workspace: Path, default_template: None
    ) -> None:
        with patch.object(VSCodeOutputLogger, "log") as mock_log:
            logger = DevLogger("claude-code", enable_git_log=False, enable_vsc_log=True)
            path = logger.create_log(task_name="task-vsc")
            logger.append_to_log(path, "执行过程", "新增")
            logger.finalize_log(path)

        messages = [call.args[0] for call in mock_log.call_args_list]
        assert any("DevLogger initialized" in msg for msg in messages)
        assert any("日志已创建" in msg for msg in messages)
        assert any("日志已更新" in msg for msg in messages)
        assert any("日志已完成" in msg for msg in messages)
