"""Unit tests for session intervention queue primitives."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_collab.intervention_queue import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_MANUAL_DELIVERY_STATUS,
    DEFAULT_STATE_PATH,
    DEFAULT_SUMMARY_PATH,
    ack_intervention,
    enqueue_intervention,
    load_intervention_state,
    read_intervention_items,
    rearm_interventions,
    resolve_intervention,
    run_intervention_queue_summary,
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _item(intervention_id: str, assignee: str, delivery_status: str) -> dict:
    """构造一条 intervention 记录。"""
    return {
        "intervention_id": intervention_id,
        "session_id": "session-001",
        "assignee": assignee,
        "reason_code": "ack_silence_after_run",
        "severity": "medium",
        "message_artifact": "collaboration/monitoring/x.md",
        "delivery_mode": "bridge",
        "delivery_status": delivery_status,
        "created_at": "2026-03-17T08:00:00+08:00",
        "updated_at": "2026-03-17T08:00:00+08:00",
        "resolved_at": "",
        "source_signal": "ack_silence_after_run",
    }


def test_enqueue_intervention_defaults_to_manual_pending_operator_delivery(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    report = enqueue_intervention(
        workspace=workspace,
        session_id="claude-session-001",
        assignee="claude_code",
        reason_code="ack_timeout",
        severity="high",
        message_artifact="collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md",
    )

    intervention = report["intervention"]
    assert intervention["delivery_mode"] == "manual"
    assert intervention["delivery_status"] == DEFAULT_MANUAL_DELIVERY_STATUS
    assert report["pending_operator_delivery_count"] == 1
    assert report["open_count"] == 1

    state_file = workspace / DEFAULT_STATE_PATH
    history_file = workspace / DEFAULT_HISTORY_PATH
    summary_file = workspace / DEFAULT_SUMMARY_PATH

    assert state_file.exists()
    assert history_file.exists()
    assert summary_file.exists()

    state_payload = _read_json(state_file)
    assert intervention["intervention_id"] in state_payload["items"]

    history_lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(history_lines) == 1
    history_item = json.loads(history_lines[0])
    assert history_item["event"] == "queued"
    assert history_item["delivery_status"] == DEFAULT_MANUAL_DELIVERY_STATUS

    summary_text = summary_file.read_text(encoding="utf-8")
    assert "Session Intervention Summary" in summary_text
    assert "pending_operator_delivery" in summary_text


def test_ack_and_resolve_intervention_update_delivery_state(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    enqueue_report = enqueue_intervention(
        workspace=workspace,
        session_id="codearts-session-001",
        assignee="codearts_agent",
        reason_code="stale_payload",
        severity="medium",
        message_artifact="collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md",
        intervention_id="intervention-queue-001",
    )
    assert enqueue_report["open_count"] == 1

    ack_report = ack_intervention(
        workspace=workspace,
        intervention_id="intervention-queue-001",
    )
    ack_item = ack_report["intervention"]
    assert ack_item["delivery_status"] == "delivered"
    assert ack_item["resolved_at"]
    assert ack_report["delivered_count"] == 1
    assert ack_report["open_count"] == 0

    resolve_report = resolve_intervention(
        workspace=workspace,
        intervention_id="intervention-queue-001",
    )
    resolve_item = resolve_report["intervention"]
    assert resolve_item["delivery_status"] == "resolved"
    assert resolve_report["resolved_count"] == 1
    assert resolve_report["open_count"] == 0

    history_file = workspace / DEFAULT_HISTORY_PATH
    history_lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(history_lines) == 3
    assert json.loads(history_lines[1])["event"] == "delivery_status_updated"
    assert json.loads(history_lines[2])["delivery_status"] == "resolved"


def test_load_and_read_helpers_return_stable_records(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    enqueue_intervention(
        workspace=workspace,
        session_id="s-2",
        assignee="codex",
        reason_code="manual_recheck",
        severity="low",
        message_artifact="artifact-b.md",
        intervention_id="intervention-b",
        created_at="2026-03-28T20:00:01",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="s-1",
        assignee="claude_code",
        reason_code="ack_timeout",
        severity="high",
        message_artifact="artifact-a.md",
        intervention_id="intervention-a",
        created_at="2026-03-28T20:00:00",
    )

    _, payload, items = load_intervention_state(workspace)
    assert payload["version"] == "1.0.0"
    assert set(items.keys()) == {"intervention-a", "intervention-b"}

    records = read_intervention_items(workspace=workspace)
    assert [item["intervention_id"] for item in records] == [
        "intervention-a",
        "intervention-b",
    ]

    summary_report = run_intervention_queue_summary(workspace=workspace)
    assert summary_report["total_count"] == 2
    assert summary_report["pending_operator_delivery_count"] == 2


def test_enqueue_rejects_unsupported_assignee(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with pytest.raises(ValueError):
        enqueue_intervention(
            workspace=workspace,
            session_id="session-x",
            assignee="unknown_agent",
            reason_code="ack_timeout",
            severity="high",
            message_artifact="artifact.md",
        )


def test_intervention_queue_reads_paths_from_session_orchestration_config(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir()
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(
            {
                "sessionOrchestration": {
                    "interventionState": "logs/custom_intervention_state.json",
                    "interventionHistory": "logs/custom_intervention_history.jsonl",
                    "interventionSummary": "collaboration/monitoring/CUSTOM_SESSION_INTERVENTION_SUMMARY.md",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = enqueue_intervention(
        workspace=workspace,
        session_id="session-configured",
        assignee="codex",
        reason_code="manual_recheck",
        severity="low",
        message_artifact="artifact.md",
        intervention_id="intervention-configured",
    )

    state_file = workspace / "logs/custom_intervention_state.json"
    history_file = workspace / "logs/custom_intervention_history.jsonl"
    summary_file = workspace / "collaboration/monitoring/CUSTOM_SESSION_INTERVENTION_SUMMARY.md"

    assert state_file.exists()
    assert history_file.exists()
    assert summary_file.exists()
    assert report["state_file"] == "logs/custom_intervention_state.json"

    _, payload, items = load_intervention_state(workspace)
    assert payload["version"] == "1.0.0"
    assert "intervention-configured" in items

    summary_report = run_intervention_queue_summary(workspace=workspace)
    assert summary_report["summary_file"] == "collaboration/monitoring/CUSTOM_SESSION_INTERVENTION_SUMMARY.md"


def test_rearm_interventions_only_rearms_in_flight_items(tmp_path: Path):
    """重新武装只动在途项：终态不动，失败项不动，别家不动。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    workspace.joinpath(DEFAULT_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    workspace.joinpath(DEFAULT_STATE_PATH).write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "in-flight": _item("in-flight", "codearts_agent", "queued_for_delivery"),
                    "delivered": _item("delivered", "codearts_agent", "delivered"),
                    "failed": _item("failed", "codearts_agent", "failed"),
                    "other-agent": _item("other-agent", "claude_code", "queued_for_delivery"),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rearmed = rearm_interventions(workspace=workspace, assignee="codearts_agent")

    assert rearmed == ["in-flight"]
    _, _, items = load_intervention_state(workspace)
    assert items["in-flight"]["delivery_status"] == "pending_operator_delivery"
    assert items["in-flight"]["resolved_at"] == ""
    assert items["delivered"]["delivery_status"] == "delivered"
    assert items["failed"]["delivery_status"] == "failed"
    assert items["other-agent"]["delivery_status"] == "queued_for_delivery"


def test_rearm_interventions_is_a_noop_without_in_flight_items(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    workspace.joinpath(DEFAULT_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    workspace.joinpath(DEFAULT_STATE_PATH).write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "delivered": _item("delivered", "codearts_agent", "delivered"),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert rearm_interventions(workspace=workspace, assignee="codearts_agent") == []
