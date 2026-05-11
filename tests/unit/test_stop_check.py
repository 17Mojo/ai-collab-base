#!/usr/bin/env python3
# ruff: noqa: E402
"""
Unit tests for ai_collab.hooks.stop_check module
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add path
project_root = Path(__file__).parent.parent.parent
ai_collab_path = project_root / "ai_collab"
if str(ai_collab_path) not in sys.path:
    sys.path.insert(0, str(ai_collab_path))

from hooks.stop_check import (
    ACTIVE_STATUSES,
    PATCH_TERMINAL_STATUSES,
    _get_cwd,
    _load_json,
    _read_missing_explicit_ack,
    _read_state_active,
    _read_state_drift,
    _read_status_unfinished,
    _resolve_existing_path,
    main,
)


class TestGetCwd:
    """Tests for _get_cwd function."""

    def test_get_cwd_string(self):
        """Test getting cwd from string input."""
        hook_input = {"cwd": "/path/to/workspace"}
        result = _get_cwd(hook_input)
        assert str(result) == "/path/to/workspace"

    def test_get_cwd_bytes(self):
        """Test getting cwd from bytes input."""
        hook_input = {"cwd": b"/path/to/workspace"}
        result = _get_cwd(hook_input)
        assert str(result) == "/path/to/workspace"

    def test_get_cwd_missing(self):
        """Test getting cwd returns default when missing."""
        hook_input = {}
        result = _get_cwd(hook_input)
        assert str(result) == "."


class TestLoadJson:
    """Tests for _load_json function."""

    def test_load_json_existing_file(self, tmp_path):
        """Test loading JSON from existing file."""
        js_file = tmp_path / "test.json"
        js_file.write_text('{"key": "value"}')
        result = _load_json(js_file)
        assert result == {"key": "value"}

    def test_load_json_nonexistent_file(self, tmp_path):
        """Test loading JSON from non-existent file."""
        js_file = tmp_path / "nonexistent.json"
        result = _load_json(js_file)
        assert result == {}

    def test_load_json_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns empty dict."""
        js_file = tmp_path / "invalid.json"
        js_file.write_text("not valid json}")
        result = _load_json(js_file)
        assert result == {}


class TestReadStatusUnfinished:
    """Tests for _read_status_unfinished function."""

    def test_read_with_unfinished_items(self, tmp_path):
        """Test reading status with unfinished items."""
        status_file = tmp_path / "status.md"
        status_file.write_text("- [ ] Task 1\n- [ ] Task 2\n- [x] Completed\n")
        result = _read_status_unfinished(status_file)
        assert result == ["Task 1", "Task 2"]

    def test_read_with_stop_emoji(self, tmp_path):
        """Test reading status with stop emoji blocks exit."""
        status_file = tmp_path / "status.md"
        status_file.write_text("- [ ] Task 1\n🛑 Stop here\n- [ ] Task 2")
        result = _read_status_unfinished(status_file)
        assert result == []

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading non-existent status file."""
        status_file = tmp_path / "status.md"
        result = _read_status_unfinished(status_file)
        assert result == []

    def test_read_with_utf8_bom(self, tmp_path):
        """Test reading status file with UTF-8 BOM."""
        # UTF-8 BOM + content
        bom_content = b"\xef\xbb\xbf- [ ] Task 1"
        status_file = tmp_path / "status.md"
        status_file.write_bytes(bom_content)
        result = _read_status_unfinished(status_file)
        assert result == ["Task 1"]


class TestReadStateActive:
    """Tests for _read_state_active function."""

    def test_read_state_with_active_tasks(self, tmp_path):
        """Test reading state with active tasks."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-001": {"status": "in_progress"},
                "TASK-002": {"status": "pending"},
                "TASK-003": {"status": "completed"},
            }
        }
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file)
        assert len(result) == 2
        assert "TASK-001" in result
        assert "TASK-002" in result

    def test_read_state_no_active_tasks(self, tmp_path):
        """Test reading state with no active tasks."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {"TASK-001": {"status": "completed"}, "TASK-002": {"status": "failed"}}
        }
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file)
        assert result == []

    def test_read_state_with_active_status_name(self, tmp_path):
        """Test reading state respects ACTIVE_STATUSES constant."""
        state_file = tmp_path / "state.json"

        for status in ACTIVE_STATUSES:
            state_data = {"tasks": {f"TASK-{status}": {"status": status}}}
            state_file.write_text(json.dumps(state_data))
            result = _read_state_active(state_file)
            assert f"TASK-{status}" in result

    def test_read_state_case_insensitive(self, tmp_path):
        """Test reading status with case-insensitive matching."""
        state_file = tmp_path / "state.json"
        state_data = {"tasks": {"TASK-001": {"status": "In_Progress"}}}
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file)
        assert "TASK-001" in result  # lowercase comparison

    def test_read_state_invalid_dict(self, tmp_path):
        """Test reading state with invalid task entries."""
        state_file = tmp_path / "state.json"
        state_data = {"tasks": {"TASK-001": "not a dict", "TASK-002": None}}
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file)
        assert result == []

    def test_read_state_missing_status_field(self, tmp_path):
        """Test reading state with tasks missing status field."""
        state_file = tmp_path / "state.json"
        state_data = {"tasks": {"TASK-001": {}, "TASK-002": {"name": "Test"}}}
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file)
        assert result == []

    def test_read_state_filters_other_assignee_when_current_agent_known(self, tmp_path):
        """Test only current agent's active tasks are considered blocking."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-CODEX-001": {"status": "in_progress", "assignee": "codex"},
                "TASK-CODEARTS-001": {"status": "pending", "assignee": "codearts_agent"},
            }
        }
        state_file.write_text(json.dumps(state_data))
        result = _read_state_active(state_file, current_agent="codex")
        assert result == ["TASK-CODEX-001"]


class TestResolveExistingPath:
    """Tests for _resolve_existing_path function."""

    def test_resolve_existing_absolute_path(self, tmp_path):
        """Test resolving existing absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = _resolve_existing_path(tmp_path, str(test_file))
        assert result == test_file

    def test_resolve_existing_relative_path(self, tmp_path):
        """Test resolving existing relative path."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("test")

        result = _resolve_existing_path(tmp_path, "subdir/test.txt")
        assert result == test_file

    def test_resolve_nonexistent_path(self, tmp_path):
        """Test resolving non-existent path returns None."""
        result = _resolve_existing_path(tmp_path, "nonexistent.txt")
        assert result is None

    def test_resolve_empty_string(self, tmp_path):
        """Test resolving empty string returns None."""
        result = _resolve_existing_path(tmp_path, "")
        assert result is None

    def test_resolve_whitespace_only(self, tmp_path):
        """Test resolving whitespace-only string returns None."""
        result = _resolve_existing_path(tmp_path, "   ")
        assert result is None

    def test_resolve_non_string_input(self, tmp_path):
        """Test resolving non-string input returns None."""
        result = _resolve_existing_path(tmp_path, None)
        assert result is None
        result = _resolve_existing_path(tmp_path, 123)
        assert result is None


class TestReadStateDrift:
    """Tests for _read_state_drift function."""

    def test_detect_task_drift_with_result_file(self, tmp_path):
        """Test detecting task drift when result file exists."""
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        result_file = result_dir / "RESULT_TASK-001.md"
        result_file.write_text("# Result")

        state_data = {
            "tasks": {"TASK-001": {"status": "in_progress"}, "TASK-002": {"status": "completed"}}
        }
        state_file.write_text(json.dumps(state_data))

        drifts = _read_state_drift(state_file, tmp_path)
        assert len(drifts) == 1
        assert "TASK-001" in drifts[0]

    def test_ignore_implied_task_completed(self, tmp_path):
        """Test ignoring tasks in terminal statuses."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-001": {"status": "completed"},
                "TASK-002": {"status": "failed"},
                "TASK-003": {"status": "cancelled"},
            }
        }
        state_file.write_text(json.dumps(state_data))
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-001.md").write_text("# Result")

        drifts = _read_state_drift(state_file, tmp_path)
        assert drifts == []


class TestReadMissingExplicitAck:
    """Tests for explicit ACK guard."""

    def test_detect_claude_completed_without_explicit_ack(self, tmp_path):
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-CLAUDE-001.md").write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CLAUDE-001": {
                    "status": "completed",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-CLAUDE-001.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data))

        missing = _read_missing_explicit_ack(state_file, tmp_path)
        assert len(missing) == 1
        assert missing[0]["task_id"] == "TASK-CLAUDE-001"
        assert "python3 -m ai_collab.cli ack" in missing[0]["command"]

    def test_detect_codearts_completed_without_explicit_ack_for_current_agent(self, tmp_path):
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-CODEARTS-001.md").write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CODEARTS-001": {
                    "status": "completed",
                    "ai_type": "codearts_agent",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CODEARTS-001.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data))

        missing = _read_missing_explicit_ack(
            state_file,
            tmp_path,
            current_agent="codearts_agent",
        )
        assert len(missing) == 1
        assert missing[0]["task_id"] == "TASK-CODEARTS-001"

    def test_ignore_other_agent_missing_explicit_ack(self, tmp_path):
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-CODEARTS-002.md").write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CODEARTS-002": {
                    "status": "completed",
                    "ai_type": "codearts_agent",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CODEARTS-002.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data))

        missing = _read_missing_explicit_ack(
            state_file,
            tmp_path,
            current_agent="codex",
        )
        assert missing == []

    def test_detect_patch_drift(self, tmp_path):
        """Test detecting patch drift."""
        state_file = tmp_path / "state.json"
        result_file = tmp_path / "custom" / "RESULT_PATCH-001.md"
        result_file.parent.mkdir(parents=True)
        result_file.write_text("# Result")

        state_data = {
            "patches": {"PATCH-001": {"status": "blocked", "result_file": str(result_file)}}
        }
        state_file.write_text(json.dumps(state_data))

        drifts = _read_state_drift(state_file, tmp_path)
        assert len(drifts) == 1
        assert "PATCH-001" in drifts[0]

    def test_patch_drift_with_task_result(self, tmp_path):
        """Test detecting patch drift using task result file."""
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        result_file = result_dir / "RESULT_TASK-001.md"
        result_file.write_text("# Result")

        state_data = {"patches": {"PATCH-001": {"status": "blocked", "task_id": "TASK-001"}}}
        state_file.write_text(json.dumps(state_data))

        drifts = _read_state_drift(state_file, tmp_path)
        assert len(drifts) == 1

    def test_patch_ignore_terminal_statuses(self, tmp_path):
        """Test ignoring patches in terminal statuses."""
        state_file = tmp_path / "state.json"
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        result_file = result_dir / "RESULT_PATCH-001.md"
        result_file.write_text("# Result")

        for status in PATCH_TERMINAL_STATUSES:
            state_data = {"patches": {"PATCH-001": {"status": status, "task_id": "TASK-001"}}}
            state_file.write_text(json.dumps(state_data))
            drifts = _read_state_drift(state_file, tmp_path)
            assert len(drifts) == 0

    def test_handle_invalid_task_patch_entries(self, tmp_path):
        """Test handling invalid task/patch entries gracefully."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {"TASK-001": None, "TASK-002": "not a dict"},
            "patches": {"PATCH-001": None, "PATCH-002": []},
        }
        state_file.write_text(json.dumps(state_data))
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)

        drifts = _read_state_drift(state_file, tmp_path)
        assert drifts == []


class TestMain:
    """Tests for main function."""

    def test_main_allow_exit_no_blocks(self, tmp_path, capsys):
        """Test main allows exit when no blocking items exist."""
        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "检测到未完成事项" not in captured.err

    def test_main_block_on_unfinished_items(self, tmp_path, capsys):
        """Test main blocks on unfinished status.md tasks."""
        status_file = tmp_path / ".cc-claude-codex" / "status.md"
        status_file.parent.mkdir(parents=True)
        status_file.write_text("- [ ] Task 1")

        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "检测到未完成事项" in captured.err
        assert "Task 1" in captured.err

    def test_main_block_on_active_tasks(self, tmp_path, capsys):
        """Test main blocks on active collaboration tasks."""
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        state_data = {"tasks": {"TASK-001": {"status": "in_progress"}}}
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "检测到未完成事项" in captured.err
        assert "活跃协作任务" in captured.err

    def test_main_block_on_state_drift(self, tmp_path, capsys):
        """Test main blocks on state drift."""
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        result_file = result_dir / "RESULT_TASK-001.md"
        result_file.write_text("# Result")

        state_data = {"tasks": {"TASK-001": {"status": "pending"}}}
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "状态漂移" in captured.err
        assert "reconcile_state_drift" in captured.err

    def test_main_block_on_missing_claude_ack(self, tmp_path, capsys):
        """Test main blocks when Claude explicit ACK evidence is missing."""
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        result_file = result_dir / "RESULT_TASK-CLAUDE-ACK-001.md"
        result_file.write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CLAUDE-ACK-001": {
                    "status": "completed",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-CLAUDE-ACK-001.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path), "agent": "claude_code"})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "当前会话显式 ACK 缺失" in captured.err
        assert (
            "python3 -m ai_collab.cli ack --task-id TASK-CLAUDE-ACK-001 --ai claude_code --status ok"
            in captured.err
        )

    def test_main_does_not_block_on_other_assignee_tasks(self, tmp_path, capsys):
        """Test current session only blocks on its own tasks."""
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-CODEARTS-ACK-001.md").write_text("# Result")
        (result_dir / "RESULT_TASK-CODEARTS-PENDING-001.md").write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CODEARTS-PENDING-001": {
                    "status": "pending",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CODEARTS-PENDING-001.md",
                },
                "TASK-CODEARTS-ACK-001": {
                    "status": "completed",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CODEARTS-ACK-001.md",
                },
            }
        }
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path), "agent": "codex"})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "检测到未完成事项" not in captured.err

    def test_main_blocks_codearts_missing_ack_for_current_agent(self, tmp_path, capsys):
        """Test codearts session is blocked until explicit A.ACK exists."""
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        result_dir = tmp_path / "collaboration" / "results"
        result_dir.mkdir(parents=True)
        (result_dir / "RESULT_TASK-CODEARTS-ACK-003.md").write_text("# Result")

        state_data = {
            "tasks": {
                "TASK-CODEARTS-ACK-003": {
                    "status": "completed",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CODEARTS-ACK-003.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path), "agent": "codearts_agent"})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert (
            "python3 -m ai_collab.cli ack --task-id TASK-CODEARTS-ACK-003 --ai codearts_agent --status ok"
            in captured.err
        )

    def test_main_multiple_block_types(self, tmp_path, capsys):
        """Test main message includes all block types."""
        # Create unfinished status item
        status_file = tmp_path / ".cc-claude-codex" / "status.md"
        status_file.parent.mkdir(parents=True)
        status_file.write_text("- [ ] Status Task")

        # Create active task
        state_file = tmp_path / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True)
        state_data = {"tasks": {"TASK-ACTIVE": {"status": "in_progress"}}}
        state_file.write_text(json.dumps(state_data))

        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "未完成 status.md 任务" in captured.err
        assert "活跃协作任务" in captured.err

    def test_main_truncates_long_lists(self, tmp_path, capsys):
        """Test main truncates lists longer than 10 items."""
        status_file = tmp_path / ".cc-claude-codex" / "status.md"
        status_file.parent.mkdir(parents=True)
        # Create 12 tasks
        tasks = [f"- [ ] Task {i}" for i in range(12)]
        status_file.write_text("\n".join(tasks))

        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        # Only 10 tasks should be shown
        lines = [line.strip() for line in captured.err.split("\n") if line.strip().startswith("-")]
        assert len(lines) <= 10

    def test_main_with_invalid_input(self, tmp_path, capsys):
        """Test main handles invalid JSON input gracefully."""
        mock_stdin = Mock(read=Mock(side_effect=EOFError()))

        with patch("sys.stdin", mock_stdin):
            with pytest.raises(SystemExit):
                main()

        # Should exit 0 with default cwd and no files
        # 注意：此测试在隔离环境中运行，避免命中真实工作区活跃任务
        hook_input = json.dumps({"cwd": str(tmp_path)})
        mock_stdin_read = Mock(read=Mock(return_value=hook_input))

        with patch("sys.stdin", mock_stdin_read):
            with pytest.raises(SystemExit) as exc_info_isolated:
                main()

        assert exc_info_isolated.value.code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
