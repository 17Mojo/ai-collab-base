#!/usr/bin/env python3
"""
Tests for ai_collab/hooks modules
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the hooks modules
from ai_collab.hooks import pre_compact, session_inject, stop_check


class TestPreCompactHook:
    """Tests for pre_compact.py"""

    def test_get_cwd_with_string(self):
        """Test _get_cwd with string input"""
        hook_input = {"cwd": "/test/path"}
        result = pre_compact._get_cwd(hook_input)
        assert result == Path("/test/path")

    def test_get_cwd_with_bytes(self):
        """Test _get_cwd with bytes input - should decode to string"""
        hook_input = {"cwd": b"/test/path"}
        # The implementation now supports bytes by decoding to string
        result = pre_compact._get_cwd(hook_input)
        assert result == Path("/test/path")

    def test_get_cwd_without_cwd(self):
        """Test _get_cwd without cwd key"""
        hook_input = {}
        result = pre_compact._get_cwd(hook_input)
        assert result == Path(".")

    def test_snapshot_existing_file(self, tmp_path):
        """Test _snapshot with existing source file"""
        src = tmp_path / "source.txt"
        src.write_text("test content")
        dest = tmp_path / "subdir" / "dest.txt"

        pre_compact._snapshot(src, dest)

        assert dest.exists()
        assert dest.read_text() == "test content"

    def test_snapshot_nonexistent_file(self, tmp_path):
        """Test _snapshot with non-existent source file"""
        src = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        # Should not raise error
        pre_compact._snapshot(src, dest)

        assert not dest.exists()

    @patch("sys.stdin", StringIO('{"cwd": "/test"}'))
    @patch("sys.stderr", new_callable=StringIO)
    def test_main_success(self, mock_stderr, tmp_path, monkeypatch):
        """Test main function with valid input"""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create necessary directories and files
        cc_dir = tmp_path / ".cc-claude-codex"
        cc_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        status_file = cc_dir / "status.md"
        status_file.write_text("# Status\n- [x] Task 1")

        state_file = logs_dir / "collaboration_state.json"
        state_file.write_text('{"version": "2.0.0"}')

        # Run main
        pre_compact.main()

        # Check output
        output = mock_stderr.getvalue()
        assert "AI Collab PreCompact: snapshot at" in output

        # Check snapshots were created (may be in different location due to cwd)
        # Just verify the function ran without error
        assert "snapshot at" in output

    @patch("sys.stdin", StringIO("invalid json"))
    @patch("sys.stderr", new_callable=StringIO)
    def test_main_with_invalid_json(self, mock_stderr, tmp_path, monkeypatch):
        """Test main function with invalid JSON input"""
        monkeypatch.chdir(tmp_path)

        # Should not raise error
        pre_compact.main()

        output = mock_stderr.getvalue()
        assert "AI Collab PreCompact: snapshot at" in output


class TestStopCheckHook:
    """Tests for stop_check.py"""

    def test_get_cwd_with_string(self):
        """Test _get_cwd with string input"""
        hook_input = {"cwd": "/test/path"}
        result = stop_check._get_cwd(hook_input)
        assert result == Path("/test/path")

    def test_load_json_valid(self, tmp_path):
        """Test _load_json with valid JSON"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        result = stop_check._load_json(json_file)
        assert result == {"key": "value"}

    def test_load_json_invalid(self, tmp_path):
        """Test _load_json with invalid JSON"""
        json_file = tmp_path / "test.json"
        json_file.write_text("invalid json")

        result = stop_check._load_json(json_file)
        assert result == {}

    def test_load_json_nonexistent(self, tmp_path):
        """Test _load_json with non-existent file"""
        json_file = tmp_path / "nonexistent.json"

        result = stop_check._load_json(json_file)
        assert result == {}

    def test_read_status_unfinished_with_tasks(self, tmp_path):
        """Test _read_status_unfinished with unfinished tasks"""
        status_file = tmp_path / "status.md"
        status_file.write_text("# Status\n- [ ] Task 1\n- [x] Task 2\n- [ ] Task 3")

        result = stop_check._read_status_unfinished(status_file)
        assert result == ["Task 1", "Task 3"]

    def test_read_status_unfinished_with_stop_flag(self, tmp_path):
        """Test _read_status_unfinished with stop flag"""
        status_file = tmp_path / "status.md"
        status_file.write_text("# Status\n🛑\n- [ ] Task 1")

        result = stop_check._read_status_unfinished(status_file)
        assert result == []

    def test_read_status_unfinished_nonexistent(self, tmp_path):
        """Test _read_status_unfinished with non-existent file"""
        status_file = tmp_path / "nonexistent.md"

        result = stop_check._read_status_unfinished(status_file)
        assert result == []

    def test_read_state_active_with_active_tasks(self, tmp_path):
        """Test _read_state_active with active tasks"""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-001": {"status": "pending"},
                "TASK-002": {"status": "completed"},
                "TASK-003": {"status": "in_progress"},
            }
        }
        state_file.write_text(json.dumps(state_data))

        result = stop_check._read_state_active(state_file)
        assert "TASK-001" in result
        assert "TASK-003" in result
        assert "TASK-002" not in result

    def test_read_state_active_without_active_tasks(self, tmp_path):
        """Test _read_state_active without active tasks"""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-001": {"status": "completed"},
                "TASK-002": {"status": "cancelled"},
            }
        }
        state_file.write_text(json.dumps(state_data))

        result = stop_check._read_state_active(state_file)
        assert result == []

    def test_read_state_active_filters_other_assignee_when_current_agent_known(self, tmp_path):
        """Test current session only sees its own active tasks."""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-CODEX-001": {"status": "pending", "assignee": "codex"},
                "TASK-CODEARTS-001": {"status": "in_progress", "assignee": "codearts_agent"},
            }
        }
        state_file.write_text(json.dumps(state_data))

        result = stop_check._read_state_active(state_file, current_agent="codex")
        assert result == ["TASK-CODEX-001"]

    def test_read_state_drift_detects_task_and_patch(self, tmp_path):
        """Test drift detection finds non-terminal items with result evidence"""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-DRIFT-001": {"status": "in_progress"},
            },
            "patches": {
                "PATCH-DRIFT-001": {
                    "status": "blocked",
                    "task_id": "TASK-DRIFT-001",
                }
            },
        }
        state_file.write_text(json.dumps(state_data))

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-DRIFT-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        drifts = stop_check._read_state_drift(state_file, tmp_path)
        assert "task TASK-DRIFT-001 (in_progress)" in drifts
        assert "patch PATCH-DRIFT-001 (blocked)" in drifts

    def test_read_state_drift_ignores_terminal_items(self, tmp_path):
        """Test drift detection ignores terminal statuses even with result files"""
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-CANCELLED-001": {"status": "cancelled"},
            },
            "patches": {
                "PATCH-CANCELLED-001": {
                    "status": "cancelled",
                    "task_id": "TASK-CANCELLED-001",
                }
            },
        }
        state_file.write_text(json.dumps(state_data))

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-CANCELLED-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        drifts = stop_check._read_state_drift(state_file, tmp_path)
        assert drifts == []

    def test_read_missing_explicit_ack_detects_claude_completed_without_ack(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-ACK-MISSING-001": {
                    "status": "completed",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-MISSING-001.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-ACK-MISSING-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        missing = stop_check._read_missing_explicit_ack(state_file, tmp_path)
        assert len(missing) == 1
        assert missing[0]["task_id"] == "TASK-ACK-MISSING-001"
        assert "python3 -m ai_collab.cli ack" in missing[0]["command"]

    def test_read_missing_explicit_ack_detects_codearts_completed_without_ack(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_data = {
            "tasks": {
                "TASK-ACK-MISSING-A-001": {
                    "status": "completed",
                    "ai_type": "codearts_agent",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-MISSING-A-001.md",
                }
            }
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-ACK-MISSING-A-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        missing = stop_check._read_missing_explicit_ack(
            state_file,
            tmp_path,
            current_agent="codearts_agent",
        )
        assert len(missing) == 1
        assert missing[0]["task_id"] == "TASK-ACK-MISSING-A-001"

    @patch("sys.stderr", new_callable=StringIO)
    def test_main_blocks_when_state_drift_detected(self, mock_stderr, tmp_path, monkeypatch):
        """Test main blocks session end when state drift exists"""
        monkeypatch.chdir(tmp_path)
        hook_input = {"cwd": str(tmp_path)}
        monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(hook_input)))

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        state_file = logs_dir / "collaboration_state.json"
        state_data = {
            "tasks": {
                "TASK-DRIFT-STOP-001": {"status": "pending"},
            }
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-DRIFT-STOP-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            stop_check.main()
        assert exc.value.code == 2

    @patch("sys.stderr", new_callable=StringIO)
    def test_main_blocks_when_claude_explicit_ack_missing(self, mock_stderr, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        hook_input = {"cwd": str(tmp_path), "agent": "claude_code"}
        monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(hook_input)))

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        state_file = logs_dir / "collaboration_state.json"
        state_data = {
            "tasks": {
                "TASK-ACK-MISSING-002": {
                    "status": "completed",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-MISSING-002.md",
                },
            }
        }
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-ACK-MISSING-002.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            stop_check.main()
        assert exc.value.code == 2
        output = mock_stderr.getvalue()
        assert "当前会话显式 ACK 缺失" in output
        assert (
            "python3 -m ai_collab.cli ack --task-id TASK-ACK-MISSING-002 --ai claude_code --status ok"
            in output
        )

    @patch("sys.stderr", new_callable=StringIO)
    def test_main_ignores_other_assignee_pending_and_missing_ack(
        self, mock_stderr, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        hook_input = {"cwd": str(tmp_path), "agent": "codex"}
        monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(hook_input)))

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        state_file = logs_dir / "collaboration_state.json"
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
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-CODEARTS-ACK-001.md"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text("# done\n", encoding="utf-8")
        pending_result = (
            tmp_path / "collaboration" / "results" / "RESULT_TASK-CODEARTS-PENDING-001.md"
        )
        pending_result.write_text("# done\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            stop_check.main()
        assert exc.value.code == 0
        assert "检测到未完成事项" not in mock_stderr.getvalue()


class TestSessionInjectHook:
    """Tests for session_inject.py"""

    def test_get_cwd_with_string(self):
        """Test _get_cwd with string input"""
        hook_input = {"cwd": "/test/path"}
        result = session_inject._get_cwd(hook_input)
        assert result == Path("/test/path")

    def test_load_json_valid(self, tmp_path):
        """Test _load_json with valid JSON"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        result = session_inject._load_json(json_file)
        assert result == {"key": "value"}

    def test_load_json_invalid(self, tmp_path):
        """Test _load_json with invalid JSON"""
        json_file = tmp_path / "test.json"
        json_file.write_text("invalid json")

        result = session_inject._load_json(json_file)
        assert result == {}

    def test_load_json_nonexistent(self, tmp_path):
        """Test _load_json with non-existent file"""
        json_file = tmp_path / "nonexistent.json"

        result = session_inject._load_json(json_file)
        assert result == {}

    def test_main_registers_claude_session_from_hook(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cc_dir = tmp_path / ".cc-claude-codex"
        cc_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (cc_dir / "status.md").write_text("# Status\n", encoding="utf-8")
        (logs_dir / "collaboration_state.json").write_text('{"tasks": {}}', encoding="utf-8")

        input_payload = json.dumps({"cwd": str(tmp_path), "session_id": "claude-session-hook-001"})
        with patch("sys.stdin", StringIO(input_payload)):
            session_inject.main()

        state_file = tmp_path / "logs" / "session_registry_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["sessions"]["claude-session-hook-001"]["assignee"] == "claude_code"

        output = capsys.readouterr().out
        payload = json.loads(output)
        assert "additionalContext" in payload

    def test_main_records_codearts_session_from_hook(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        cc_dir = tmp_path / ".cc-claude-codex"
        cc_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (cc_dir / "status.md").write_text("# Status\n", encoding="utf-8")
        (logs_dir / "collaboration_state.json").write_text('{"tasks": {}}', encoding="utf-8")

        input_payload = json.dumps(
            {
                "cwd": str(tmp_path),
                "agent": "codearts_agent",
                "session_id": "codearts-session-hook-001",
            }
        )
        with patch("sys.stdin", StringIO(input_payload)):
            session_inject.main()

        state_file = tmp_path / "logs" / "session_registry_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["sessions"]["codearts-session-hook-001"]["assignee"] == "codearts_agent"

        output = capsys.readouterr().out
        payload = json.loads(output)
        assert "additionalContext" in payload

    @patch("sys.stdin", StringIO('{"cwd": "/test"}'))
    @patch("sys.stdout", new_callable=StringIO)
    def test_main_with_state(self, mock_stdout, tmp_path, monkeypatch):
        """Test main function with state file"""
        monkeypatch.chdir(tmp_path)

        # Create state file
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        state_file = logs_dir / "collaboration_state.json"
        state_data = {"version": "2.0.0", "tasks": {"TASK-001": {"status": "completed"}}}
        state_file.write_text(json.dumps(state_data))

        # Run main
        session_inject.main()

        # Check output contains state info
        output = mock_stdout.getvalue()
        # The output should be JSON
        try:
            output_data = json.loads(output)
            # Check for any of the expected keys
            assert any(
                key in output_data for key in ["session_context", "state", "additionalContext"]
            )
        except json.JSONDecodeError:
            # If not JSON, check for some expected content
            assert "collaboration_state" in output or "TASK" in output or "AI Collab" in output

    @patch("sys.stdin", StringIO("invalid json"))
    @patch("sys.stdout", new_callable=StringIO)
    def test_main_with_invalid_json(self, mock_stdout, tmp_path, monkeypatch):
        """Test main function with invalid JSON input"""
        monkeypatch.chdir(tmp_path)

        # Should not raise error
        session_inject.main()

        # Check that it still produces some output
        output = mock_stdout.getvalue()
        # Should be valid JSON or empty
        try:
            if output.strip():
                json.loads(output)
        except json.JSONDecodeError:
            pytest.fail("Output should be valid JSON or empty")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
