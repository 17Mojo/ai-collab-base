"""Focused tests for CLI monitoring report refresh with missing ACK bridge."""

import json
from pathlib import Path

from ai_collab import cli


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_result(workspace: Path, relative_path: str) -> None:
    result_file = workspace / relative_path
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# Result",
                "## 执行命令",
                "```bash",
                "echo test",
                "```",
                "## 测试结论",
                "- pass",
                "## 风险",
                "- none",
            ]
        ),
        encoding="utf-8",
    )


def test_generate_reports_and_summaries_marks_codearts_missing_ack_as_residual(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-16T11:50:00+08:00",
        "tasks": {
            "TASK-CLI-ACK-001": {
                "task_id": "TASK-CLI-ACK-001",
                "ai_type": "codearts_agent",
                "assignee": "codearts_agent",
                "status": "completed",
                "updated_at": "2026-03-16T11:48:50.639556",
                "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-001.md",
            }
        },
        "patches": {},
        "active_tasks": [],
        "completed_tasks": ["TASK-CLI-ACK-001"],
        "conflicts": [],
        "file_status": {},
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "task_receipt_report.json",
        {
            "completed_count": 1,
            "error_count": 0,
            "candidate_count": 1,
        },
    )
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-CLI-ACK-001": {
                    "task_id": "TASK-CLI-ACK-001",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-001.md",
                    "completed_at": "2026-03-16T11:48:50.639556",
                }
            },
        },
    )
    _write_result(workspace, "collaboration/results/RESULT_TASK-CLI-ACK-001.md")

    cli._generate_reports_and_summaries(workspace=str(workspace))

    missing_ack_report = json.loads((workspace / "logs" / "missing_ack_report.json").read_text(encoding="utf-8"))
    assert missing_ack_report["candidate_count"] == 0
    assert missing_ack_report["bridged_count"] == 0
    assert missing_ack_report["stale_explicit_ack_count"] == 1

    remediation_report = json.loads((workspace / "logs" / "ack_remediation_report.json").read_text(encoding="utf-8"))
    assert remediation_report["candidate_count"] == 0

    daily_report = json.loads((workspace / "logs" / "daily_report.json").read_text(encoding="utf-8"))
    assert daily_report["missing_ack_stats"]["bridged_count"] == 0
    assert daily_report["missing_ack_stats"]["stale_explicit_ack_count"] == 1
    assert daily_report["ack_stats"]["total_acks"] == 1
    assert daily_report["ack_stats"]["bridge_record_count"] == 0
    assert daily_report["ack_stats"]["explicit_ack_count"] == 0
    assert daily_report["ack_stats"]["closeout_eligible_ack_count"] == 0


def test_generate_reports_and_summaries_bridges_completed_task_without_receipt_state(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-16T16:20:00+08:00",
        "tasks": {
            "TASK-CLI-ACK-002": {
                "task_id": "TASK-CLI-ACK-002",
                "ai_type": "claude_code",
                "assignee": "claude_code",
                "status": "completed",
                "completed_at": "2026-03-16T16:22:50.438073",
                "updated_at": "2026-03-16T16:22:50.438073",
                "result_file": "collaboration/results/RESULT_TASK-CLI-ACK-002.md",
            }
        },
        "patches": {},
        "active_tasks": [],
        "completed_tasks": ["TASK-CLI-ACK-002"],
        "conflicts": [],
        "file_status": {},
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "task_receipt_report.json",
        {
            "completed_count": 0,
            "error_count": 0,
            "candidate_count": 0,
        },
    )
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {},
        },
    )
    _write_result(workspace, "collaboration/results/RESULT_TASK-CLI-ACK-002.md")

    cli._generate_reports_and_summaries(workspace=str(workspace))

    missing_ack_report = json.loads((workspace / "logs" / "missing_ack_report.json").read_text(encoding="utf-8"))
    assert missing_ack_report["candidate_count"] == 0
    assert missing_ack_report["bridged_count"] == 0
    assert missing_ack_report["stale_explicit_ack_count"] == 1
    assert missing_ack_report["other_skipped_count"] == 0
    assert missing_ack_report["skipped_count"] == 1
    assert "explicit ACK required" in missing_ack_report["skipped_tasks"][0]["reason"]

    remediation_report = json.loads((workspace / "logs" / "ack_remediation_report.json").read_text(encoding="utf-8"))
    assert remediation_report["candidate_count"] == 0
    assert remediation_report["flagged_count"] == 0

    daily_report = json.loads((workspace / "logs" / "daily_report.json").read_text(encoding="utf-8"))
    assert daily_report["missing_ack_stats"]["bridged_count"] == 0
    assert daily_report["missing_ack_stats"]["stale_explicit_ack_count"] == 1
    assert daily_report["missing_ack_stats"]["remediation_flagged_count"] == 0
    assert daily_report["ack_stats"]["bridge_record_count"] == 0
    assert daily_report["ack_stats"]["explicit_ack_count"] == 0
    assert daily_report["ack_stats"]["claude_legacy_fallback_count"] == 0
    assert daily_report["pending_tasks"] == []
