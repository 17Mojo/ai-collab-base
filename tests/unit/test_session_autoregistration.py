import json
from datetime import datetime

from ai_collab.session_autoregistration import (
    register_claude_session_from_hook,
    register_codex_session_from_runtime,
    sync_auto_sessions,
)
from ai_collab.session_registry import inspect_sessions


def test_register_claude_session_from_hook_registers_and_closes_session(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    trigger_file = workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_claude_code_latest.md"
    trigger_file.parent.mkdir(parents=True, exist_ok=True)
    trigger_file.write_text("payload", encoding="utf-8")

    first = register_claude_session_from_hook(
        workspace=workspace,
        hook_input={"session_id": "claude-session-001"},
        event_name="SessionStart",
    )
    assert first["status"] == "ok"
    assert first["action"] == "registered"

    second = register_claude_session_from_hook(
        workspace=workspace,
        hook_input={"session_id": "claude-session-001"},
        event_name="Stop",
    )
    assert second["status"] == "ok"
    assert second["action"] == "refreshed"

    payload = inspect_sessions(workspace=workspace)
    assert payload["session_count"] == 1
    session = payload["sessions"][0]
    assert session["session_id"] == "claude-session-001"
    assert session["assignee"] == "claude_code"
    assert session["session_status"] == "idle"
    assert session["last_handoff_artifact"] == "collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md"


def test_register_codex_session_from_runtime_skips_stale_runtime(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    runtime_file = workspace / ".cc-claude-codex" / "runtime.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps({"last_synced_at": "2026-01-01T00:00:00"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = register_codex_session_from_runtime(workspace=workspace, max_age_minutes=60)
    assert report["status"] == "skipped"
    assert report["reason"] == "runtime_stale"
    assert inspect_sessions(workspace=workspace)["session_count"] == 0


def test_register_codex_session_from_runtime_registers_fresh_runtime(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    runtime_file = workspace / ".cc-claude-codex" / "runtime.json"
    output_file = workspace / ".cc-claude-codex" / "logs" / "codex-output.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("done", encoding="utf-8")
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps(
            {
                "last_synced_at": datetime.now().isoformat(),
                "output_file": str(output_file),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = register_codex_session_from_runtime(workspace=workspace, max_age_minutes=60)
    assert report["status"] == "ok"
    assert report["action"] == "registered"

    payload = inspect_sessions(workspace=workspace)
    assert payload["session_count"] == 1
    session = payload["sessions"][0]
    assert session["session_id"] == "codex-runtime"
    assert session["assignee"] == "codex"
    assert session["last_handoff_artifact"] == ".cc-claude-codex/logs/codex-output.md"


def test_sync_auto_sessions_reports_codex_result(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    report = sync_auto_sessions(workspace=workspace)
    assert report["registered_count"] == 0
    assert report["skipped_count"] == 1
    assert report["results"][0]["status"] == "skipped"
