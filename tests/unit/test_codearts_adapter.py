import json
from pathlib import Path

from ai_collab.adapters.codearts_adapter import run_codearts_pull_adapter
from ai_collab.intervention_queue import enqueue_intervention, inspect_interventions


def _write_workspace_config(workspace: Path, codearts_adapter: dict | None = None) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            }
        },
    }
    if codearts_adapter:
        config["sessionOrchestration"]["codeartsAdapter"].update(codearts_adapter)

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


def test_codearts_adapter_generates_artifact_only_when_bridge_disabled(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace, {"enabled": False})

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_ack_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请先拉取并补发 ACK。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-001",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["artifact_only_count"] == 1
    assert report["queued_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "artifact_only"
    assert delivery["event_file"] == (
        "collaboration/monitoring/codearts_pull_events/"
        "CODEARTS_PULL_EVENT_intervention-codearts-001_latest.md"
    )
    event_text = (workspace / delivery["event_file"]).read_text(encoding="utf-8")
    assert "请先拉取并补发 ACK。" in event_text

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "pending_operator_delivery"
    assert (workspace / report["report_file"]).exists()
    assert (workspace / report["summary_file"]).exists()
    assert (workspace / report["history_file"]).exists()


def test_codearts_adapter_queues_delivery_when_bridge_command_succeeds(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/codearts_bridge_delivery.txt\"",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_payload_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请拉取最新 intervention。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="stale_payload",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-002",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["queued_count"] == 1
    assert report["artifact_only_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["delivery_status"] == "queued_for_delivery"
    assert (workspace / "codearts_bridge_delivery.txt").exists()

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "queued_for_delivery"
    assert queue["interventions"][0]["delivery_mode"] == "bridge"


def test_codearts_adapter_marks_failed_when_bridge_command_fails(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "exit 9",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_result_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请修复结果文件状态头。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="terminal_status_mismatch",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-003",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

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


def test_codearts_adapter_marks_failed_when_artifact_is_missing(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="missing_result_file",
        severity="high",
        message_artifact="collaboration/monitoring/session_interventions/DOES_NOT_EXIST.md",
        intervention_id="intervention-codearts-004",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["failed_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "failed"
    assert "unable to read artifact" in delivery["error"]

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "failed"
