import json
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path

from ai_collab import cli
from ai_collab.ack_watchdog import run_ack_watchdog


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-17T08:00:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def _write_orders(workspace: Path, assignee: str, task_id: str) -> None:
    role = "Claude" if assignee == "claude_code" else "CodeArts"
    content = "\n".join(
        [
            "# Agent Dispatch Orders（自动生成）",
            "",
            f"## 发送给 `{role}` (`{assignee}`)",
            "",
            f"### {task_id}",
            "",
            "```text",
            f"【执行指令 | {task_id}】",
            "python3 -m ai_collab.cli tasks update --task-id test --status implementing",
            "```",
            "",
        ]
    )
    orders_file = workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_latest.md"
    orders_file.parent.mkdir(parents=True, exist_ok=True)
    orders_file.write_text(content, encoding="utf-8")


def test_cmd_ack_emits_tool_output_from_task_state(tmp_path: Path, capsys):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    state = _base_state(workspace)
    state["tasks"]["TASK-ACK-EMIT-001"] = {
        "task_id": "TASK-ACK-EMIT-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "result_file": "collaboration/results/RESULT_TASK-ACK-EMIT-001.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)

    args = Namespace(
        workspace=str(workspace),
        task_id="TASK-ACK-EMIT-001",
        ai=None,
        status=None,
        result_file=None,
    )
    assert cli.cmd_ack(args) == 0
    output = capsys.readouterr().out.strip()
    assert output == (
        "C.ACK|task=TASK-ACK-EMIT-001|status=ok|result="
        "collaboration/results/RESULT_TASK-ACK-EMIT-001.md"
    )


def test_ack_watchdog_redispatches_silent_pending_task_once(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    dispatched_at = (datetime.now() - timedelta(seconds=180)).isoformat()
    state = _base_state(workspace)
    state["tasks"]["TASK-WATCH-001"] = {
        "task_id": "TASK-WATCH-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "pending",
        "updated_at": dispatched_at,
        "result_file": "collaboration/results/RESULT_TASK-WATCH-001.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_dispatch_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-WATCH-001": {
                    "task_id": "TASK-WATCH-001",
                    "assignee": "claude_code",
                    "status": "pending",
                    "result_file": "collaboration/results/RESULT_TASK-WATCH-001.md",
                    "updated_at": dispatched_at,
                    "dispatched_at": dispatched_at,
                    "dispatch_count": 1,
                }
            },
        },
    )
    _write_json(workspace / "logs" / "agent_receipt_state.json", {"version": "1.0.0", "items": {}})
    _write_json(workspace / "logs" / "agent_ack_bridge_state.json", {"version": "1.0.0", "items": {}})
    _write_orders(workspace, "claude_code", "TASK-WATCH-001")

    report = run_ack_watchdog(workspace=workspace, threshold_seconds=120)

    assert report["candidate_count"] == 1
    assert report["redispatched_count"] == 1
    assert report["alerted_count"] == 0

    dispatch_state = json.loads((workspace / "logs" / "agent_dispatch_state.json").read_text(encoding="utf-8"))
    item = dispatch_state["items"]["TASK-WATCH-001"]
    assert item["dispatch_count"] == 2
    assert item["watchdog_redispatch_count"] == 1

    payload = (workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_claude_code_latest.md").read_text(
        encoding="utf-8"
    )
    assert "ACK Watchdog（自动重派）" in payload
    assert "C.RUN-RESET" in payload
    assert "TASK-WATCH-001" in payload
    assert "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH Claude' --target claude_code" in payload


def test_ack_watchdog_alerts_when_max_redispatch_reached(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    dispatched_at = (datetime.now() - timedelta(seconds=240)).isoformat()
    state = _base_state(workspace)
    state["tasks"]["TASK-WATCH-002"] = {
        "task_id": "TASK-WATCH-002",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "pending",
        "updated_at": dispatched_at,
        "result_file": "collaboration/results/RESULT_TASK-WATCH-002.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_dispatch_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-WATCH-002": {
                    "task_id": "TASK-WATCH-002",
                    "assignee": "codearts_agent",
                    "status": "pending",
                    "result_file": "collaboration/results/RESULT_TASK-WATCH-002.md",
                    "updated_at": dispatched_at,
                    "dispatched_at": dispatched_at,
                    "dispatch_count": 2,
                    "watchdog_redispatch_count": 1,
                }
            },
        },
    )
    _write_json(workspace / "logs" / "agent_receipt_state.json", {"version": "1.0.0", "items": {}})
    _write_json(workspace / "logs" / "agent_ack_bridge_state.json", {"version": "1.0.0", "items": {}})

    report = run_ack_watchdog(workspace=workspace, threshold_seconds=120, max_redispatch_count=1)

    assert report["candidate_count"] == 1
    assert report["redispatched_count"] == 0
    assert report["alerted_count"] == 1

    dispatch_state = json.loads((workspace / "logs" / "agent_dispatch_state.json").read_text(encoding="utf-8"))
    item = dispatch_state["items"]["TASK-WATCH-002"]
    assert item["dispatch_count"] == 2
    assert item["watchdog_alert_count"] == 1

    summary = (workspace / "collaboration" / "monitoring" / "ACK_WATCHDOG_SUMMARY_latest.md").read_text(
        encoding="utf-8"
    )
    assert "TASK-WATCH-002" in summary
    assert "action=`alert`" in summary
