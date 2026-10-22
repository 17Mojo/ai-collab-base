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


def _write_in_flight_intervention(workspace: Path, assignee: str, intervention_id: str) -> None:
    """放一条在途（已投递、等 ACK）的 intervention。"""
    _write_json(
        workspace / "logs" / "session_intervention_state.json",
        {
            "version": "1.0.0",
            "generated_at": "2026-03-17T08:00:00+08:00",
            "items": {
                intervention_id: {
                    "intervention_id": intervention_id,
                    "session_id": "codearts-main",
                    "assignee": assignee,
                    "reason_code": "ack_silence_after_run",
                    "severity": "medium",
                    "message_artifact": "collaboration/monitoring/x.md",
                    "delivery_mode": "bridge",
                    "delivery_status": "queued_for_delivery",
                    "created_at": "2026-03-17T08:00:00+08:00",
                    "updated_at": "2026-03-17T08:00:00+08:00",
                    "resolved_at": "",
                    "source_signal": "ack_silence_after_run",
                }
            },
        },
    )


def test_ack_watchdog_redispatch_rearms_in_flight_intervention(tmp_path: Path):
    """重派是明确的再发一次决定，在途干预必须被重新武装。

    回归：在途干预默认被适配器跳过（否则每轮轮询都在对方那边新建会话）。
    但 watchdog 判定要重派时如果不重新武装，payload 刷新了却送不出去——
    派单链路在最后一步断掉。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    dispatched_at = (datetime.now() - timedelta(seconds=180)).isoformat()
    state = _base_state(workspace)
    state["tasks"]["TASK-REARM-001"] = {
        "task_id": "TASK-REARM-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "pending",
        "updated_at": dispatched_at,
        "result_file": "collaboration/results/RESULT_TASK-REARM-001.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_dispatch_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-REARM-001": {
                    "task_id": "TASK-REARM-001",
                    "assignee": "claude_code",
                    "status": "pending",
                    "result_file": "collaboration/results/RESULT_TASK-REARM-001.md",
                    "updated_at": dispatched_at,
                    "dispatched_at": dispatched_at,
                    "dispatch_count": 1,
                }
            },
        },
    )
    _write_json(workspace / "logs" / "agent_receipt_state.json", {"version": "1.0.0", "items": {}})
    _write_json(workspace / "logs" / "agent_ack_bridge_state.json", {"version": "1.0.0", "items": {}})
    _write_orders(workspace, "claude_code", "TASK-REARM-001")
    _write_in_flight_intervention(workspace, "claude_code", "intervention-rearm-001")

    report = run_ack_watchdog(workspace=workspace, threshold_seconds=120)

    assert report["redispatched_count"] == 1
    assert report["rearmed_count"] == 1
    assert report["rearmed_by_assignee"]["claude_code"] == ["intervention-rearm-001"]

    interventions = json.loads(
        (workspace / "logs" / "session_intervention_state.json").read_text(encoding="utf-8")
    )
    item = interventions["items"]["intervention-rearm-001"]
    assert item["delivery_status"] == "pending_operator_delivery"
    assert item["resolved_at"] == ""


def test_ack_watchdog_alert_does_not_rearm_intervention(tmp_path: Path):
    """只告警（不重派）时不能动在途干预 —— 那是运维决定要不要重投。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    dispatched_at = (datetime.now() - timedelta(seconds=180)).isoformat()
    state = _base_state(workspace)
    state["tasks"]["TASK-NOREARM-001"] = {
        "task_id": "TASK-NOREARM-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "updated_at": dispatched_at,
        "result_file": "collaboration/results/RESULT_TASK-NOREARM-001.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_dispatch_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-NOREARM-001": {
                    "task_id": "TASK-NOREARM-001",
                    "assignee": "claude_code",
                    "status": "testing",
                    "result_file": "collaboration/results/RESULT_TASK-NOREARM-001.md",
                    "updated_at": dispatched_at,
                    "dispatched_at": dispatched_at,
                    "dispatch_count": 1,
                }
            },
        },
    )
    _write_json(workspace / "logs" / "agent_receipt_state.json", {"version": "1.0.0", "items": {}})
    _write_json(workspace / "logs" / "agent_ack_bridge_state.json", {"version": "1.0.0", "items": {}})
    _write_orders(workspace, "claude_code", "TASK-NOREARM-001")
    _write_in_flight_intervention(workspace, "claude_code", "intervention-norearm-001")

    report = run_ack_watchdog(workspace=workspace, threshold_seconds=120)

    assert report["alerted_count"] == 1
    assert report["rearmed_count"] == 0

    interventions = json.loads(
        (workspace / "logs" / "session_intervention_state.json").read_text(encoding="utf-8")
    )
    item = interventions["items"]["intervention-norearm-001"]
    assert item["delivery_status"] == "queued_for_delivery"


def test_ack_watchdog_uses_role_scoped_run_hint(tmp_path: Path):
    """watchdog 重派提示必须跟着工单声明的角色走。

    claude_code 声明为 AGENT_ARCH 席位时，提示词应该是 `X.RUN`；
    provider 兜底表里的 `C.RUN`（claude_code → C）会与角色表冲突，
    接收方拿到 "用 C.RUN 触发、却要回 X.ACK" 这种自相矛盾的指令。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "agent-orchestration.json").write_text(
        (Path(__file__).resolve().parents[2] / "config" / "agent-orchestration.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    dispatched_at = (datetime.now() - timedelta(seconds=180)).isoformat()
    state = _base_state(workspace)
    state["tasks"]["TASK-ROLE-001"] = {
        "task_id": "TASK-ROLE-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "assignee_role": "AGENT_ARCH",
        "status": "pending",
        "updated_at": dispatched_at,
        "result_file": "collaboration/results/RESULT_TASK-ROLE-001.md",
    }
    _write_json(workspace / "logs" / "collaboration_state.json", state)
    _write_json(
        workspace / "logs" / "agent_dispatch_state.json",
        {
            "version": "1.0.0",
            "items": {
                "TASK-ROLE-001": {
                    "task_id": "TASK-ROLE-001",
                    "assignee": "claude_code",
                    "status": "pending",
                    "result_file": "collaboration/results/RESULT_TASK-ROLE-001.md",
                    "updated_at": dispatched_at,
                    "dispatched_at": dispatched_at,
                    "dispatch_count": 1,
                }
            },
        },
    )
    _write_json(workspace / "logs" / "agent_receipt_state.json", {"version": "1.0.0", "items": {}})
    _write_json(workspace / "logs" / "agent_ack_bridge_state.json", {"version": "1.0.0", "items": {}})
    _write_orders(workspace, "claude_code", "TASK-ROLE-001")

    report = run_ack_watchdog(workspace=workspace, threshold_seconds=120)

    assert report["redispatched_count"] == 1
    payload = (
        workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_claude_code_latest.md"
    ).read_text(encoding="utf-8")
    assert "X.RUN-RESET" in payload
    assert "X.RUN" in payload
    assert "C.RUN" not in payload


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
