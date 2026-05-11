import json
from pathlib import Path

from ai_collab.adapters.claude_adapter import run_claude_push_adapter
from ai_collab.intervention_queue import enqueue_intervention, inspect_interventions


def _write_workspace_config(workspace: Path, claude_adapter: dict | None = None) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "claudeAdapter": {
                "enabled": False,
                "channel": "",
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/claude_adapter_report.json",
                "history": "logs/claude_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/claude_push_events",
            }
        },
    }
    if claude_adapter:
        config["sessionOrchestration"]["claudeAdapter"].update(claude_adapter)

    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_intervention_artifact(workspace: Path, relpath: str, message: str) -> None:
    artifact = workspace / relpath
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "\n".join(
            [
                "# Session Intervention Artifact",
                "",
                "## Exact Forward Message",
                "",
                "```text",
                message,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_claude_adapter_generates_artifact_only_when_bridge_disabled(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace, {"enabled": False, "channel": "claude-main"})

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_claude_ack_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请补发 ACK。")
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-claude-001",
    )

    report = run_claude_push_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["artifact_only_count"] == 1
    assert report["queued_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "artifact_only"
    assert delivery["event_file"] == (
        "collaboration/monitoring/claude_push_events/"
        "CLAUDE_PUSH_EVENT_intervention-claude-001_latest.md"
    )
    event_text = (workspace / delivery["event_file"]).read_text(encoding="utf-8")
    assert "请补发 ACK。" in event_text

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "pending_operator_delivery"
    assert (workspace / report["report_file"]).exists()
    assert (workspace / report["summary_file"]).exists()
    assert (workspace / report["history_file"]).exists()


def test_claude_adapter_queues_delivery_when_bridge_command_succeeds(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "channel": "claude-main",
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/bridge_delivery.txt\"",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_claude_payload_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请读取最新 payload。")
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="stale_payload",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-claude-002",
    )

    report = run_claude_push_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["queued_count"] == 1
    assert report["artifact_only_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["delivery_status"] == "queued_for_delivery"
    assert (workspace / "bridge_delivery.txt").exists()

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "queued_for_delivery"
    assert queue["interventions"][0]["delivery_mode"] == "bridge"


def test_claude_adapter_marks_failed_when_bridge_command_fails(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "channel": "claude-main",
            "bridgeCommand": "exit 7",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_claude_result_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请修复结果文件状态头。")
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="terminal_status_mismatch",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-claude-003",
    )

    report = run_claude_push_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["failed_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "failed"
    assert delivery["delivery_status"] == "failed"
    assert delivery["error"] != ""

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "failed"
    assert queue["interventions"][0]["delivery_mode"] == "bridge"
