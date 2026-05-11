"""Focused tests for CLI ACK persistence."""

import json
from pathlib import Path
from types import SimpleNamespace

from ai_collab import cli
from ai_collab.missing_ack_monitor import run_missing_ack_monitor


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_cmd_ack_persists_explicit_cli_ack(capsys, tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "collaboration_state.json",
        {
            "version": "2.0.0",
            "workspace": str(workspace),
            "last_updated": "2026-03-18T11:00:00+08:00",
            "tasks": {
                "TASK-CLI-ACK-PERSIST-001": {
                    "task_id": "TASK-CLI-ACK-PERSIST-001",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "status": "completed",
                    "created_at": "2026-03-18T10:50:00+08:00",
                    "updated_at": "2026-03-18T10:59:00+08:00",
                    "completed_at": "2026-03-18T10:59:30+08:00",
                    "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-PERSIST-001.md",
                }
            },
            "patches": {},
            "active_tasks": [],
            "completed_tasks": ["TASK-CLI-ACK-PERSIST-001"],
            "conflicts": [],
            "file_status": {},
        },
    )

    args = SimpleNamespace(
        workspace=str(workspace),
        task_id="TASK-CLI-ACK-PERSIST-001",
        ai=None,
        status=None,
        result_file=None,
    )

    result = cli.cmd_ack(args)
    assert result == 0

    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "C.ACK|task=TASK-CLI-ACK-PERSIST-001|status=ok|result=collaboration/results/RESULT_TASK-CLI-ACK-PERSIST-001.md"
    )

    ack_state = json.loads((workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    item = ack_state["items"]["TASK-CLI-ACK-PERSIST-001"]
    assert item["source"] == "cli-ack"
    assert item["ack_line"] == captured.out.strip()


def test_cmd_ack_clears_remediation_flag_after_explicit_ack(capsys, tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "collaboration_state.json",
        {
            "version": "2.0.0",
            "workspace": str(workspace),
            "last_updated": "2026-03-19T09:00:00+08:00",
            "tasks": {
                "TASK-CLI-ACK-RESOLVE-001": {
                    "task_id": "TASK-CLI-ACK-RESOLVE-001",
                    "ai_type": "claude_code",
                    "assignee": "claude_code",
                    "status": "completed",
                    "created_at": "2026-03-19T08:40:00+08:00",
                    "updated_at": "2026-03-19T08:58:00+08:00",
                    "completed_at": "2026-03-19T08:58:30+08:00",
                    "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-001.md",
                }
            },
            "patches": {},
            "active_tasks": [],
            "completed_tasks": ["TASK-CLI-ACK-RESOLVE-001"],
            "conflicts": [],
            "file_status": {},
        },
    )
    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-CLI-ACK-RESOLVE-001": {
                    "task_id": "TASK-CLI-ACK-RESOLVE-001",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-001.md",
                    "ack_line": "C.ACK|task=TASK-CLI-ACK-RESOLVE-001|status=ok|result=collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-001.md",
                    "receipt_completed_at": "2026-03-19T08:58:30+08:00",
                    "bridged_at": "2026-03-19T08:59:00+08:00",
                    "bridge_count": 1,
                    "source": "missing_ack_monitor:completed_state_fallback",
                    "closeout_eligible": False,
                    "remediation_status": "needs_explicit_ack",
                    "remediation_reason": "explicit ACK required for claude_code closeout",
                    "remediation_updated_at": "2026-03-19T09:00:00+08:00",
                    "remediation_source": "ack_remediation",
                }
            },
        },
    )

    args = SimpleNamespace(
        workspace=str(workspace),
        task_id="TASK-CLI-ACK-RESOLVE-001",
        ai=None,
        status=None,
        result_file=None,
    )

    result = cli.cmd_ack(args)
    assert result == 0
    captured = capsys.readouterr()
    assert "C.ACK|task=TASK-CLI-ACK-RESOLVE-001|status=ok" in captured.out

    ack_state = json.loads((workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    item = ack_state["items"]["TASK-CLI-ACK-RESOLVE-001"]
    assert item["source"] == "cli-ack"
    assert item["closeout_eligible"] is True
    assert "remediation_status" not in item
    assert item["remediation_cleared_source"] == "cli-ack"
    assert item["remediation_previous_source"] == "missing_ack_monitor:completed_state_fallback"
    assert item["remediation_previous_status"] == "needs_explicit_ack"

    report = run_missing_ack_monitor(workspace=workspace)
    assert report["stale_explicit_ack_count"] == 0
    assert report["already_bridged_count"] == 1


def test_cmd_ack_persists_explicit_ack_for_missing_task_with_legacy_bridge(capsys, tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "collaboration_state.json",
        {
            "version": "2.0.0",
            "workspace": str(workspace),
            "last_updated": "2026-03-19T09:10:00+08:00",
            "tasks": {},
            "patches": {},
            "active_tasks": [],
            "completed_tasks": [],
            "conflicts": [],
            "file_status": {},
        },
    )
    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-CLI-ACK-RESOLVE-002": {
                    "task_id": "TASK-CLI-ACK-RESOLVE-002",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-002.md",
                    "ack_line": "C.ACK|task=TASK-CLI-ACK-RESOLVE-002|status=ok|result=collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-002.md",
                    "receipt_completed_at": "2026-03-18T20:00:00+08:00",
                    "bridged_at": "2026-03-18T20:00:10+08:00",
                    "bridge_count": 1,
                    "source": "missing_ack_monitor",
                    "closeout_eligible": False,
                    "remediation_status": "needs_explicit_ack",
                }
            },
        },
    )

    args = SimpleNamespace(
        workspace=str(workspace),
        task_id="TASK-CLI-ACK-RESOLVE-002",
        ai="claude_code",
        status="ok",
        result_file=None,
    )

    result = cli.cmd_ack(args)
    assert result == 0
    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "C.ACK|task=TASK-CLI-ACK-RESOLVE-002|status=ok|result=collaboration/results/RESULT_TASK-CLI-ACK-RESOLVE-002.md"
    )

    ack_state = json.loads((workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    item = ack_state["items"]["TASK-CLI-ACK-RESOLVE-002"]
    assert item["source"] == "cli-ack"
    assert item["receipt_completed_at"] == "2026-03-18T20:00:00+08:00"
    assert item["closeout_eligible"] is True
    assert "remediation_status" not in item
