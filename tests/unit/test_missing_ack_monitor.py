"""Unit tests for missing ACK bridge monitoring."""

import json
from pathlib import Path

import ai_collab.missing_ack_monitor as missing_ack_monitor
from ai_collab.missing_ack_monitor import run_missing_ack_monitor


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-16T11:40:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


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


def test_missing_ack_monitor_flags_completed_codearts_task_without_explicit_ack(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = _base_state(workspace)
    state["tasks"]["TASK-ACK-001"] = {
        "task_id": "TASK-ACK-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "completed",
        "updated_at": "2026-03-16T11:48:50.639556",
        "result_file": "collaboration/results/RESULT_TASK-ACK-001.md",
    }
    state["completed_tasks"] = ["TASK-ACK-001"]
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-001": {
                    "task_id": "TASK-ACK-001",
                    "assignee": "codearts_agent",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-001.md",
                    "completed_at": "2026-03-16T11:48:50.639556",
                }
            },
        },
    )
    _write_result(workspace, "collaboration/results/RESULT_TASK-ACK-001.md")

    report = run_missing_ack_monitor(workspace=workspace)

    assert report["candidate_count"] == 0
    assert report["bridged_count"] == 0
    assert report["already_bridged_count"] == 0
    assert report["stale_explicit_ack_count"] == 1
    assert report["skipped_count"] == 1
    assert report["error_count"] == 0
    assert report["stale_explicit_ack_tasks"][0]["task_id"] == "TASK-ACK-001"
    assert "explicit ACK required" in report["skipped_tasks"][0]["reason"]
    assert not (workspace / "logs" / "agent_ack_bridge_state.json").exists()

    summary_text = (workspace / "collaboration" / "monitoring" / "MISSING_ACK_SUMMARY_latest.md").read_text(
        encoding="utf-8"
    )
    assert "TASK-ACK-001" in summary_text
    assert "显式 ACK 残留" in summary_text


def test_missing_ack_monitor_skips_already_bridged(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = _base_state(workspace)
    state["tasks"]["TASK-ACK-002"] = {
        "task_id": "TASK-ACK-002",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "completed",
        "updated_at": "2026-03-16T12:00:00+08:00",
        "result_file": "collaboration/results/RESULT_TASK-ACK-002.md",
    }
    state["completed_tasks"] = ["TASK-ACK-002"]
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-002": {
                    "task_id": "TASK-ACK-002",
                    "assignee": "claude_code",
                    "result_file": "collaboration/results/RESULT_TASK-ACK-002.md",
                    "completed_at": "2026-03-16T12:00:00+08:00",
                }
            },
        },
    )
    _write_json(
        workspace / "logs" / "agent_ack_bridge_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ACK-002": {
                    "task_id": "TASK-ACK-002",
                    "ack_line": "C.ACK|task=TASK-ACK-002|status=ok|result=collaboration/results/RESULT_TASK-ACK-002.md",
                    "source": "chat-ack:explicit-retry",
                    "bridge_count": 1,
                }
            },
        },
    )
    _write_result(workspace, "collaboration/results/RESULT_TASK-ACK-002.md")

    report = run_missing_ack_monitor(workspace=workspace)

    assert report["candidate_count"] == 0
    assert report["bridged_count"] == 0
    assert report["stale_explicit_ack_count"] == 0
    assert report["other_skipped_count"] == 0
    assert report["already_bridged_count"] == 1
    assert report["already_bridged_tasks"] == ["TASK-ACK-002"]


def test_missing_ack_monitor_bridges_completed_task_without_receipt_state(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = _base_state(workspace)
    state["tasks"]["TASK-ACK-003"] = {
        "task_id": "TASK-ACK-003",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "completed",
        "completed_at": "2026-03-16T12:15:00+08:00",
        "updated_at": "2026-03-16T12:15:00+08:00",
        "result_file": "collaboration/results/RESULT_TASK-ACK-003.md",
    }
    state["completed_tasks"] = ["TASK-ACK-003"]
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {},
        },
    )
    _write_result(workspace, "collaboration/results/RESULT_TASK-ACK-003.md")

    report = run_missing_ack_monitor(workspace=workspace)

    assert report["candidate_count"] == 0
    assert report["bridged_count"] == 0
    assert report["stale_explicit_ack_count"] == 1
    assert report["other_skipped_count"] == 0
    assert report["skipped_count"] == 1
    assert report["stale_explicit_ack_tasks"][0]["task_id"] == "TASK-ACK-003"
    assert report["skipped_tasks"][0]["task_id"] == "TASK-ACK-003"
    assert "explicit ACK required" in report["skipped_tasks"][0]["reason"]
    assert not (workspace / "logs" / "agent_ack_bridge_state.json").exists()

    summary_text = (workspace / "collaboration" / "monitoring" / "MISSING_ACK_SUMMARY_latest.md").read_text(
        encoding="utf-8"
    )
    assert "显式 ACK 残留" in summary_text
    assert "TASK-ACK-003" in summary_text


def test_missing_ack_monitor_restores_result_from_mirror_workspace(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    mirror_root = tmp_path / "mirror-root"
    mirror_workspace = mirror_root / "playwright-wave-prep-20260314"
    mirror_workspace.mkdir(parents=True)

    monkeypatch.setattr(missing_ack_monitor, "MIRROR_SEARCH_ROOTS", (mirror_root,))

    state = _base_state(workspace)
    state["tasks"]["TASK-ACK-004"] = {
        "task_id": "TASK-ACK-004",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "completed",
        "completed_at": "2026-03-16T12:30:00+08:00",
        "updated_at": "2026-03-16T12:30:00+08:00",
        "result_file": "collaboration/results/RESULT_TASK-ACK-004.md",
    }
    state["completed_tasks"] = ["TASK-ACK-004"]
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_receipt_state.json",
        {
            "version": "1.0.0",
            "items": {},
        },
    )
    _write_result(mirror_workspace, "collaboration/results/RESULT_TASK-ACK-004.md")

    report = run_missing_ack_monitor(workspace=workspace)

    restored_file = workspace / "collaboration/results/RESULT_TASK-ACK-004.md"
    assert not restored_file.exists()
    assert report["bridged_count"] == 0
    assert report["stale_explicit_ack_count"] == 1
    assert report["stale_explicit_ack_tasks"][0]["task_id"] == "TASK-ACK-004"
