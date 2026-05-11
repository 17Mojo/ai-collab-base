import json
import tempfile
from pathlib import Path

from ai_collab.session_registry import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_STATE_PATH,
    DEFAULT_SUMMARY_PATH,
    inspect_sessions,
    load_session_registry_state,
    read_session_registry,
    refresh_session,
    register_session,
    render_session_registry_summary,
    run_session_registry,
    update_session_health,
)


def test_register_session_persists_state_and_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        record = register_session(
            workspace=workspace,
            session_id="claude-main",
            assignee="claude_code",
            transport_mode="manual",
            last_handoff_artifact="collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md",
        )

        state_payload = json.loads((workspace / DEFAULT_STATE_PATH).read_text(encoding="utf-8"))
        history_lines = (
            (workspace / DEFAULT_HISTORY_PATH).read_text(encoding="utf-8").strip().splitlines()
        )
        summary_text = (workspace / DEFAULT_SUMMARY_PATH).read_text(encoding="utf-8")

        assert record["session_id"] == "claude-main"
        assert record["assignee"] == "claude_code"
        assert state_payload["sessions"]["claude-main"]["transport_mode"] == "manual"
        assert len(history_lines) == 1
        assert "claude-main" in summary_text


def test_refresh_session_updates_existing_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        register_session(
            workspace=workspace,
            session_id="codearts-main",
            assignee="codearts_agent",
            transport_mode="manual",
        )

        updated = refresh_session(
            workspace=workspace,
            session_id="codearts-main",
            transport_mode="bridge",
            session_status="blocked",
            health_status="unhealthy",
            last_handoff_artifact="collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md",
        )

        state_payload = json.loads((workspace / DEFAULT_STATE_PATH).read_text(encoding="utf-8"))
        history_lines = (
            (workspace / DEFAULT_HISTORY_PATH).read_text(encoding="utf-8").strip().splitlines()
        )

        assert updated["transport_mode"] == "bridge"
        assert updated["session_status"] == "blocked"
        assert updated["health_status"] == "unhealthy"
        assert state_payload["sessions"]["codearts-main"]["last_handoff_artifact"].endswith(
            "codearts_agent_latest.md"
        )
        assert len(history_lines) == 2


def test_inspect_sessions_filters_and_writes_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        register_session(
            workspace=workspace, session_id="x-1", assignee="codex", transport_mode="bridge"
        )
        register_session(
            workspace=workspace, session_id="c-1", assignee="claude_code", transport_mode="manual"
        )

        payload = inspect_sessions(workspace=workspace, assignee="codex")
        summary_text = (workspace / DEFAULT_SUMMARY_PATH).read_text(encoding="utf-8")

        assert payload["session_count"] == 1
        assert payload["sessions"][0]["session_id"] == "x-1"
        assert "x-1" in summary_text
        assert "c-1" not in summary_text


def test_registry_helpers_load_render_and_run_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        register_session(
            workspace=workspace,
            session_id="claude-main",
            assignee="claude_code",
            transport_mode="manual",
            health_status="healthy",
        )
        register_session(
            workspace=workspace,
            session_id="codearts-main",
            assignee="codearts_agent",
            transport_mode="bridge",
            health_status="unhealthy",
        )

        state_file, history_file, summary_file, payload, sessions = load_session_registry_state(
            workspace
        )
        assert state_file == workspace / DEFAULT_STATE_PATH
        assert history_file == workspace / DEFAULT_HISTORY_PATH
        assert summary_file == workspace / DEFAULT_SUMMARY_PATH
        assert payload["version"] == "1.0.0"
        assert set(sessions.keys()) == {"claude-main", "codearts-main"}

        records = read_session_registry(workspace=workspace)
        assert [item["session_id"] for item in records] == ["claude-main", "codearts-main"]

        markdown = render_session_registry_summary(workspace=workspace)
        assert "Session Registry Summary" in markdown
        assert "claude-main" in markdown
        assert "codearts-main" in markdown

        report = run_session_registry(workspace=workspace)
        assert report["session_count"] == 2
        assert report["healthy_count"] == 1
        assert report["unhealthy_count"] == 1


def test_update_session_health_preserves_last_seen_timestamp():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        record = register_session(
            workspace=workspace,
            session_id="claude-main",
            assignee="claude_code",
            transport_mode="manual",
        )

        updated = update_session_health(
            workspace=workspace,
            session_id="claude-main",
            health_status="unhealthy",
            reason_codes=["stale_payload", "ack_timeout"],
            incident_count=2,
        )

        assert updated["health_status"] == "unhealthy"
        assert updated["health_reason_codes"] == ["ack_timeout", "stale_payload"]
        assert updated["health_incident_count"] == 2
        assert updated["last_seen_at"] == record["last_seen_at"]
