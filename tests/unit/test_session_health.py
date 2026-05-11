import json
from datetime import datetime, timedelta
from pathlib import Path

import ai_collab.state_manager as state_manager
from ai_collab.dispatch_trigger import build_handoff_payload
from ai_collab.intervention_queue import enqueue_intervention, inspect_interventions
from ai_collab.session_health import run_session_health_aggregation
from ai_collab.session_registry import inspect_sessions, register_session


def _patch_state_paths(monkeypatch, workspace: Path):
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "get_project_config",
        lambda: {"stateFile": "./logs/collaboration_state.json"},
    )
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "update_vscode_output",
        lambda message, channel="AI Collab": None,
    )
    monkeypatch.setattr(
        state_manager.VSCodeStateManager,
        "get_global_state_file",
        lambda: str(workspace / "global_collaboration_state.json"),
    )


def _write_workspace_config(workspace: Path):
    config = {
        "version": "1.0.0",
        "stateFile": "./logs/collaboration_state.json",
        "sessionOrchestration": {
            "registryState": "logs/session_registry_state.json",
            "registryHistory": "logs/session_registry_history.jsonl",
            "registrySummary": "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md",
            "healthReport": "logs/session_health_report.json",
            "healthHistory": "logs/session_health_history.jsonl",
            "healthSummary": "collaboration/monitoring/SESSION_HEALTH_SUMMARY_latest.md",
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
            "interventionArtifactDir": "collaboration/monitoring/session_interventions",
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            },
            "codexAdapter": {
                "runtimeFile": ".cc-claude-codex/runtime.json",
                "staleAfterMinutes": 180,
                "report": "logs/codex_adapter_report.json",
                "history": "logs/codex_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEX_ADAPTER_SUMMARY_latest.md",
            },
        },
    }
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_result_file(path: Path, status_line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Result",
                status_line,
                "## 执行命令",
                "pytest -q tests/unit/test_session_health.py",
                "## 测试结论",
                "all green",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )


def test_session_health_detects_stale_payload_and_preserves_last_seen(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)

    payload_relpath = "collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md"
    payload_file = workspace / payload_relpath
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(
        build_handoff_payload(
            assignee="claude_code",
            trigger_phrase="TEST",
            orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
            section_markdown="## 发送给 `Claude` (`claude_code`)\n\n测试任务",
            generated_at="2026-03-28T20:00:00",
        ),
        encoding="utf-8",
    )
    dispatch_report_file = workspace / "logs/task_dispatch_report.json"
    dispatch_report_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_report_file.write_text(
        json.dumps({"generated_at": "2026-03-28T20:10:00"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    register_session(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        transport_mode="manual",
        last_handoff_artifact=payload_relpath,
    )
    before_last_seen = inspect_sessions(workspace=workspace)["sessions"][0]["last_seen_at"]

    report = run_session_health_aggregation(workspace=workspace)

    assert report["incident_count"] == 1
    assert report["intervention_count"] == 1
    incident = report["incidents"][0]
    assert incident["reason_code"] == "stale_payload"
    assert incident["delivery_status"] == "pending_operator_delivery"
    assert (workspace / incident["message_artifact"]).exists()

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1

    session = inspect_sessions(workspace=workspace)["sessions"][0]
    assert session["health_status"] == "unhealthy"
    assert session["last_seen_at"] == before_last_seen


def test_session_health_detects_ack_silence_and_missing_explicit_ack(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)
    manager = state_manager.StateManager(workspace_path=str(workspace))

    register_session(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        transport_mode="manual",
    )
    register_session(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        transport_mode="manual",
    )

    manager.register_task(
        task_id="TASK-SILENCE-001",
        ai_type="codearts_agent",
        description="silent task",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-SILENCE-001.md",
        contract_required=False,
    )

    ack_result = workspace / "collaboration" / "results" / "RESULT_TASK-ACK-001.md"
    _write_result_file(ack_result, "**状态**: completed")
    manager.register_task(
        task_id="TASK-ACK-001",
        ai_type="claude_code",
        description="completed without explicit ack",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-ACK-001.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-ACK-001",
        status=state_manager.TaskStatus.COMPLETED,
        note="done",
    )

    dispatch_state_file = workspace / "logs/agent_dispatch_state.json"
    dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-SILENCE-001": {
                        "assignee": "codearts_agent",
                        "dispatched_at": "2026-03-28T19:50:00",
                        "dispatch_count": 1,
                        "result_file": "collaboration/results/RESULT_TASK-SILENCE-001.md",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = run_session_health_aggregation(workspace=workspace)

    reason_codes = {item["reason_code"] for item in report["incidents"]}
    assert "ack_silence_after_run" in reason_codes
    assert "missing_explicit_ack" in reason_codes

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 2

    missing_ack_incident = next(
        item for item in report["incidents"] if item["reason_code"] == "missing_explicit_ack"
    )
    artifact_text = (workspace / missing_ack_incident["message_artifact"]).read_text(encoding="utf-8")
    assert "python3 -m ai_collab.cli ack --task-id TASK-ACK-001 --ai claude_code --status ok" in artifact_text


def test_session_health_surfaces_unregistered_sessions(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)
    manager = state_manager.StateManager(workspace_path=str(workspace))

    mismatch_result = workspace / "collaboration" / "results" / "RESULT_TASK-MISMATCH-001.md"
    _write_result_file(mismatch_result, "**状态**: testing")
    manager.register_task(
        task_id="TASK-MISMATCH-001",
        ai_type="codearts_agent",
        description="mismatch without session registration",
        files=["ai_collab/result_consistency_audit.py"],
        result_file="collaboration/results/RESULT_TASK-MISMATCH-001.md",
        contract_required=False,
    )
    manager.register_task(
        task_id="TASK-UNREGISTERED-PENDING-001",
        ai_type="codearts_agent",
        description="active task without session registration",
        files=["ai_collab/session_health.py"],
        result_file="collaboration/results/RESULT_TASK-UNREGISTERED-PENDING-001.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-MISMATCH-001",
        status=state_manager.TaskStatus.FAILED,
        note="failed state",
    )

    report = run_session_health_aggregation(workspace=workspace, emit_interventions=False)

    reason_codes = {item["reason_code"] for item in report["incidents"]}
    assert "unregistered_session" in reason_codes
    assert "terminal_status_mismatch" in reason_codes
    assert report["unregistered_count"] >= 1
    unregistered_sessions = [
        item for item in report["sessions"] if item["session_status"] == "unregistered"
    ]
    assert any(item["assignee"] == "codearts_agent" for item in unregistered_sessions)

    unregistered_incident = next(
        item for item in report["incidents"] if item["reason_code"] == "unregistered_session"
    )
    artifact_text = (workspace / unregistered_incident["message_artifact"]).read_text(encoding="utf-8")
    assert "不会宣称可自动投递" in artifact_text


def test_session_health_includes_codearts_adapter_report(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)

    register_session(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        transport_mode="manual",
    )

    report = run_session_health_aggregation(workspace=workspace, emit_interventions=True)

    assert report["adapter_reports"]["codearts_pull_report"] == "logs/codearts_adapter_report.json"
    assert (workspace / "logs" / "codearts_adapter_report.json").exists()


def test_session_health_includes_codex_adapter_report(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)

    runtime_file = workspace / ".cc-claude-codex" / "runtime.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps(
            {
                "task_id": "TASK-CODEX-HEARTBEAT-001",
                "last_synced_at": "2026-03-29T08:00:00",
                "last_run_at": "2026-03-29T08:00:00",
                "exit_reason": "done",
                "return_code": 0,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = run_session_health_aggregation(workspace=workspace, emit_interventions=True)

    assert report["adapter_reports"]["codex_native_report"] == "logs/codex_adapter_report.json"
    assert (workspace / "logs" / "codex_adapter_report.json").exists()


def test_session_health_auto_registers_codearts_from_recent_activation(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)
    manager = state_manager.StateManager(workspace_path=str(workspace))

    manager.register_task(
        task_id="TASK-CODEARTS-ACTIVE-001",
        ai_type="codearts_agent",
        description="active CodeArts task with recent activation evidence",
        files=["ai_collab/session_health.py"],
        result_file="collaboration/results/RESULT_TASK-CODEARTS-ACTIVE-001.md",
        contract_required=False,
    )

    activation_file = workspace / "logs" / "activations" / "2026-03-29.jsonl"
    activation_file.parent.mkdir(parents=True, exist_ok=True)
    recent_activation = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    activation_file.write_text(
        json.dumps(
            {
                "session_id": "codearts-live-001",
                "ai_type": "codearts_agent",
                "activation_time": recent_activation,
                "mode": "command",
                "rules_loaded": ["codearts_agent_rules.md"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_session_health_aggregation(workspace=workspace, emit_interventions=False)

    reason_codes = {item["reason_code"] for item in report["incidents"]}
    assert "unregistered_session" not in reason_codes
    assert report["auto_sync"]["registered_count"] == 1
    assert report["auto_sync"]["sources"]["activation_log_count"] == 1

    sessions = inspect_sessions(workspace=workspace)["sessions"]
    codearts_session = next(item for item in sessions if item["assignee"] == "codearts_agent")
    assert codearts_session["session_id"] == "codearts-live-001"


def test_session_health_resolves_obsolete_health_managed_interventions(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _patch_state_paths(monkeypatch, workspace)
    _write_workspace_config(workspace)

    artifact_relpath = (
        "collaboration/monitoring/session_interventions/"
        "SESSION_INTERVENTION_claude-main_terminal_status_mismatch_latest.md"
    )
    artifact = workspace / artifact_relpath
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# Intervention\n", encoding="utf-8")

    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="terminal_status_mismatch",
        severity="high",
        message_artifact=artifact_relpath,
        source_signal="result_consistency_audit",
        intervention_id="intervention-claude-terminal-mismatch",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="closeout_followup",
        severity="medium",
        message_artifact=artifact_relpath,
        source_signal="operator_followup",
        intervention_id="intervention-claude-followup",
    )

    before_queue = inspect_interventions(workspace=workspace, only_open=True)
    assert before_queue["intervention_count"] == 2

    report = run_session_health_aggregation(workspace=workspace)

    assert report["incident_count"] == 0
    assert report["open_intervention_count"] == 0
    assert report["resolved_interventions"] == [
        {
            "intervention_id": "intervention-claude-terminal-mismatch",
            "session_id": "claude-main",
            "assignee": "claude_code",
            "reason_code": "terminal_status_mismatch",
            "source_signal": "result_consistency_audit",
            "previous_delivery_status": "pending_operator_delivery",
            "next_delivery_status": "resolved",
        }
    ]

    open_queue = inspect_interventions(workspace=workspace, only_open=True)
    assert open_queue["intervention_count"] == 1
    assert open_queue["interventions"][0]["intervention_id"] == "intervention-claude-followup"

    full_queue = inspect_interventions(workspace=workspace, only_open=False)
    terminal_item = next(
        item
        for item in full_queue["interventions"]
        if item["intervention_id"] == "intervention-claude-terminal-mismatch"
    )
    assert terminal_item["delivery_status"] == "resolved"
