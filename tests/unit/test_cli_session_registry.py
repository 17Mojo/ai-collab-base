import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_collab import cli


def test_cmd_sessions_register_and_inspect_json(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        register_args = SimpleNamespace(
            workspace=str(workspace),
            subcommand="register",
            session_id="claude-main",
            assignee="claude_code",
            transport_mode="manual",
            session_status="active",
            health_status="healthy",
            last_handoff_artifact="collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md",
            state=None,
            history=None,
            summary=None,
            json=False,
        )
        assert cli.cmd_sessions(register_args) == 0
        capsys.readouterr()

        inspect_args = SimpleNamespace(
            workspace=str(workspace),
            subcommand="inspect",
            session_id=None,
            assignee=None,
            transport_mode="manual",
            session_status=None,
            health_status=None,
            last_handoff_artifact=None,
            state=None,
            history=None,
            summary=None,
            json=True,
        )
        assert cli.cmd_sessions(inspect_args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["session_count"] == 1
        assert payload["sessions"][0]["session_id"] == "claude-main"


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "inspect", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_claude_push_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "claude-push", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_codearts_pull_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "codearts-pull", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_interventions_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "interventions", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_intervention_pack_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "intervention-pack", "--assignee", "claude_code", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_closeout_queue_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "closeout-queue", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_auto_sync_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "auto-sync", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_codex_adapter_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "codex-adapter", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.cli._cli_main.cmd_sessions")
def test_main_routes_sessions_handoff_command(mock_cmd_sessions):
    mock_cmd_sessions.return_value = 0
    with patch.object(
        sys,
        "argv",
        ["ai-collab", "sessions", "handoff", "--json"],
    ):
        assert cli.main() == 0
    mock_cmd_sessions.assert_called_once()


@patch("ai_collab.session_health.run_session_health_aggregation")
def test_cmd_sessions_health_json(mock_run_health, capsys):
    mock_run_health.return_value = {
        "session_count": 1,
        "healthy_count": 0,
        "unhealthy_count": 1,
        "unregistered_count": 0,
        "incident_count": 1,
        "intervention_count": 1,
        "report_file": "logs/session_health_report.json",
        "summary_file": "collaboration/monitoring/SESSION_HEALTH_SUMMARY_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="health",
        report=None,
        history=None,
        summary=None,
        artifact_dir=None,
        no_interventions=False,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["incident_count"] == 1
    mock_run_health.assert_called_once()


@patch("ai_collab.adapters.claude_adapter.run_claude_push_adapter")
def test_cmd_sessions_claude_push_json(mock_run_push, capsys):
    mock_run_push.return_value = {
        "mode": "apply",
        "candidate_count": 1,
        "queued_count": 1,
        "artifact_only_count": 0,
        "failed_count": 0,
        "report_file": "logs/claude_adapter_report.json",
        "summary_file": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="claude-push",
        dry_run=False,
        report=None,
        history=None,
        summary=None,
        event_dir=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["queued_count"] == 1
    mock_run_push.assert_called_once()


@patch("ai_collab.adapters.codearts_adapter.run_codearts_pull_adapter")
def test_cmd_sessions_codearts_pull_json(mock_run_pull, capsys):
    mock_run_pull.return_value = {
        "mode": "apply",
        "candidate_count": 1,
        "queued_count": 1,
        "artifact_only_count": 0,
        "failed_count": 0,
        "report_file": "logs/codearts_adapter_report.json",
        "summary_file": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="codearts-pull",
        dry_run=False,
        report=None,
        history=None,
        summary=None,
        event_dir=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["queued_count"] == 1
    mock_run_pull.assert_called_once()


@patch("ai_collab.intervention_queue.inspect_interventions")
def test_cmd_sessions_interventions_json(mock_inspect, capsys):
    mock_inspect.return_value = {
        "intervention_count": 1,
        "open_count": 1,
        "pending_operator_delivery_count": 1,
        "queued_for_delivery_count": 0,
        "interventions": [
            {
                "intervention_id": "intervention-001",
                "assignee": "claude_code",
                "session_id": "claude-main",
                "reason_code": "closeout_followup",
                "delivery_status": "pending_operator_delivery",
                "message_artifact": "collaboration/monitoring/session_interventions/example.md",
            }
        ],
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="interventions",
        session_id=None,
        assignee="claude_code",
        reason_code=None,
        delivery_status=None,
        only_open=True,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["intervention_count"] == 1
    mock_inspect.assert_called_once()


@patch("ai_collab.intervention_queue.render_intervention_pack")
def test_cmd_sessions_intervention_pack_json(mock_render_pack, capsys):
    mock_render_pack.return_value = {
        "assignee": "claude_code",
        "intervention_count": 1,
        "pack_file": "collaboration/monitoring/intervention_packs/SESSION_INTERVENTION_PACK_claude_code_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="intervention-pack",
        assignee="claude_code",
        include_closed=False,
        pack_dir=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["assignee"] == "claude_code"
    mock_render_pack.assert_called_once()


@patch("ai_collab.external_closeout_queue.render_external_closeout_queue")
def test_cmd_sessions_closeout_queue_json(mock_render_queue, capsys):
    mock_render_queue.return_value = {
        "active_task_count": 3,
        "open_intervention_count": 2,
        "blocking_intervention_count": 1,
        "ready_pack_count": 2,
        "output_file": "collaboration/monitoring/EXTERNAL_CLOSEOUT_QUEUE_2026-03-29_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="closeout-queue",
        report=None,
        history=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["blocking_intervention_count"] == 1
    mock_render_queue.assert_called_once()


@patch("ai_collab.session_auto_register.run_session_auto_sync")
def test_cmd_sessions_auto_sync_json(mock_run_auto_sync, capsys):
    mock_run_auto_sync.return_value = {
        "mode": "dry-run",
        "candidate_count": 2,
        "registered_count": 0,
        "refreshed_count": 1,
        "sources": {
            "activation_log_count": 1,
            "hook_observation_count": 1,
            "codex_runtime_count": 0,
        },
        "observation_file": "logs/session_observations.jsonl",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="auto-sync",
        dry_run=True,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidate_count"] == 2
    assert payload["observation_file"] == "logs/session_observations.jsonl"
    mock_run_auto_sync.assert_called_once()


@patch("ai_collab.adapters.codex_adapter.run_codex_native_adapter")
def test_cmd_sessions_codex_adapter_json(mock_run_codex, capsys):
    mock_run_codex.return_value = {
        "mode": "apply",
        "runtime_present": True,
        "runtime_fresh": False,
        "session_registered": False,
        "report_file": "logs/codex_adapter_report.json",
        "summary_file": "collaboration/monitoring/CODEX_ADAPTER_SUMMARY_latest.md",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="codex-adapter",
        dry_run=False,
        report=None,
        history=None,
        summary=None,
        runtime_path=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["runtime_present"] is True
    mock_run_codex.assert_called_once()


@patch("ai_collab.session_continuation_handoff.run_session_continuation_handoff")
def test_cmd_sessions_handoff_json(mock_run_handoff, capsys):
    mock_run_handoff.return_value = {
        "mode": "apply",
        "output_file": "collaboration/results/SESSION_CONTINUATION_HANDOFF_2026-03-29.md",
        "report_file": "logs/session_continuation_handoff_report.json",
        "summary_file": "collaboration/monitoring/SESSION_CONTINUATION_HANDOFF_SUMMARY_latest.md",
        "history_file": "logs/session_continuation_handoff_history.jsonl",
    }
    args = SimpleNamespace(
        workspace=tempfile.gettempdir(),
        subcommand="handoff",
        dry_run=False,
        objective=None,
        next_slice=None,
        completed_item=None,
        validation_command=None,
        related_file=None,
        report=None,
        history=None,
        summary=None,
        output_dir=None,
        json=True,
    )

    assert cli.cmd_sessions(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["output_file"].endswith(".md")
    mock_run_handoff.assert_called_once()
