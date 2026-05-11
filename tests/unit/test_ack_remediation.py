"""Unit tests for ACK remediation of legacy non-explicit ACK bridges."""

import json
from pathlib import Path

from ai_collab.ack_remediation import REMEDIATION_STATUS_NEEDS_EXPLICIT_ACK, run_ack_remediation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_ack_remediation_flags_legacy_claude_bridge(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-REMED-001": {
                    "task_id": "TASK-ACK-REMED-001",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-REMED-001.md",
                    "ack_line": "C.ACK|task=TASK-ACK-REMED-001|status=ok|result=collaboration/results/RESULT_TASK-ACK-REMED-001.md",
                    "receipt_completed_at": "2026-03-18T14:00:00+08:00",
                    "bridged_at": "2026-03-18T14:00:00+08:00",
                    "bridge_count": 1,
                    "source": "missing_ack_monitor:completed_state_fallback",
                }
            },
        },
    )

    report = run_ack_remediation(workspace=workspace, dry_run=False)

    assert report["candidate_count"] == 1
    assert report["flagged_count"] == 1
    assert report["already_flagged_count"] == 0

    state = json.loads((workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    item = state["items"]["TASK-ACK-REMED-001"]
    assert item["remediation_status"] == REMEDIATION_STATUS_NEEDS_EXPLICIT_ACK
    assert item["closeout_eligible"] is False
    assert item["remediation_source"] == "ack_remediation"

    summary = (workspace / "collaboration" / "monitoring" / "ACK_REMEDIATION_SUMMARY_latest.md").read_text(
        encoding="utf-8"
    )
    assert "TASK-ACK-REMED-001" in summary
    assert "python3 -m ai_collab.cli ack --task-id TASK-ACK-REMED-001 --ai claude_code --status ok" in summary


def test_ack_remediation_flags_legacy_codearts_bridge(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-REMED-001A": {
                    "task_id": "TASK-ACK-REMED-001A",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-REMED-001A.md",
                    "ack_line": "A.ACK|task=TASK-ACK-REMED-001A|status=completed|result=collaboration/results/RESULT_TASK-ACK-REMED-001A.md",
                    "receipt_completed_at": "2026-03-18T14:00:00+08:00",
                    "bridged_at": "2026-03-18T14:00:00+08:00",
                    "bridge_count": 1,
                    "source": "missing_ack_monitor:completed_state_fallback",
                }
            },
        },
    )

    report = run_ack_remediation(workspace=workspace, dry_run=False)

    assert report["candidate_count"] == 1
    assert report["flagged_count"] == 1
    state = json.loads((workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    item = state["items"]["TASK-ACK-REMED-001A"]
    assert item["remediation_reason"] == "explicit ACK required for codearts_agent closeout"

    summary = (workspace / "collaboration" / "monitoring" / "ACK_REMEDIATION_SUMMARY_latest.md").read_text(
        encoding="utf-8"
    )
    assert "python3 -m ai_collab.cli ack --task-id TASK-ACK-REMED-001A --ai codearts_agent --status ok" in summary


def test_ack_remediation_dry_run_preserves_state(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state_file = workspace / "logs" / "agent_ack_bridge_state.json"
    _write_json(
        state_file,
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-REMED-002": {
                    "task_id": "TASK-ACK-REMED-002",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-REMED-002.md",
                    "ack_line": "C.ACK|task=TASK-ACK-REMED-002|status=ok|result=collaboration/results/RESULT_TASK-ACK-REMED-002.md",
                    "receipt_completed_at": "2026-03-18T14:05:00+08:00",
                    "bridged_at": "2026-03-18T14:05:00+08:00",
                    "bridge_count": 1,
                    "source": "missing_ack_monitor",
                }
            },
        },
    )

    report = run_ack_remediation(workspace=workspace, dry_run=True)

    assert report["candidate_count"] == 1
    assert report["flagged_count"] == 1
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "remediation_status" not in state["items"]["TASK-ACK-REMED-002"]


def test_ack_remediation_ignores_resolved_explicit_ack(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-REMED-003": {
                    "task_id": "TASK-ACK-REMED-003",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-REMED-003.md",
                    "ack_line": "C.ACK|task=TASK-ACK-REMED-003|status=ok|result=collaboration/results/RESULT_TASK-ACK-REMED-003.md",
                    "receipt_completed_at": "2026-03-18T14:05:00+08:00",
                    "bridged_at": "2026-03-18T14:05:00+08:00",
                    "bridge_count": 2,
                    "source": "cli-ack",
                    "closeout_eligible": True,
                    "remediation_cleared_at": "2026-03-19T09:20:00+08:00",
                    "remediation_cleared_source": "cli-ack",
                    "remediation_previous_source": "missing_ack_monitor",
                    "remediation_previous_status": "needs_explicit_ack",
                }
            },
        },
    )

    report = run_ack_remediation(workspace=workspace, dry_run=False)

    assert report["candidate_count"] == 0
    assert report["flagged_count"] == 0
    assert report["already_flagged_count"] == 0
