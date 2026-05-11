import json
from pathlib import Path

from ai_collab.adapters.claude_adapter import get_claude_adapter_contract
from ai_collab.adapters.codearts_adapter import get_codearts_adapter_contract
from ai_collab.intervention_queue import enqueue_intervention


def _write_workspace_config(workspace: Path) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "claudeAdapter": {
                "enabled": True,
                "channel": "claude-main",
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/claude_adapter_report.json",
                "history": "logs/claude_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/claude_push_events",
            },
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            },
            "registryState": "logs/session_registry_state.json",
            "registryHistory": "logs/session_registry_history.jsonl",
            "registrySummary": "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md",
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
        },
    }
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_claude_adapter_contract_exposes_push_and_heartbeat(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    contract = get_claude_adapter_contract()
    contract.register_session(workspace=workspace, session_id="claude-main")
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact="collaboration/monitoring/session_interventions/claude.md",
        intervention_id="contract-claude-001",
    )

    heartbeat = contract.heartbeat(workspace=workspace)

    assert contract.capability == "push"
    assert contract.push_interventions is not None
    assert contract.pull_interventions is None
    assert heartbeat["session_registered"] is True
    assert heartbeat["session_id"] == "claude-main"
    assert heartbeat["open_intervention_count"] == 1


def test_codearts_adapter_contract_exposes_pull_and_heartbeat(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    contract = get_codearts_adapter_contract()
    contract.register_session(workspace=workspace, session_id="codearts-main")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="unregistered_session",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/codearts.md",
        intervention_id="contract-codearts-001",
    )

    heartbeat = contract.heartbeat(workspace=workspace)

    assert contract.capability == "pull"
    assert contract.push_interventions is None
    assert contract.pull_interventions is not None
    assert heartbeat["session_registered"] is True
    assert heartbeat["session_id"] == "codearts-main"
    assert heartbeat["open_intervention_count"] == 1
