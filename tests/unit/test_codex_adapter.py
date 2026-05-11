import json
from datetime import datetime, timedelta
from pathlib import Path

from ai_collab.adapters.codex_adapter import (
    get_codex_adapter_contract,
    run_codex_native_adapter,
)


def _write_workspace_config(workspace: Path, codex_adapter: dict | None = None) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "codexAdapter": {
                "runtimeFile": ".cc-claude-codex/runtime.json",
                "staleAfterMinutes": 180,
                "report": "logs/codex_adapter_report.json",
                "history": "logs/codex_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEX_ADAPTER_SUMMARY_latest.md",
            },
            "registryState": "logs/session_registry_state.json",
            "registryHistory": "logs/session_registry_history.jsonl",
            "registrySummary": "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md",
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
        },
    }
    if codex_adapter:
        config["sessionOrchestration"]["codexAdapter"].update(codex_adapter)

    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_runtime(workspace: Path, last_synced_at: str) -> None:
    runtime_file = workspace / ".cc-claude-codex" / "runtime.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(
        json.dumps(
            {
                "task_id": "TASK-CODEX-001",
                "last_synced_at": last_synced_at,
                "last_run_at": last_synced_at,
                "exit_reason": "done",
                "return_code": 0,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_codex_adapter_reports_stale_runtime_without_registration(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    stale_time = (datetime.now() - timedelta(days=3)).isoformat()
    _write_runtime(workspace, stale_time)

    report = run_codex_native_adapter(workspace=workspace)

    assert report["runtime_present"] is True
    assert report["runtime_fresh"] is False
    assert report["session_registered"] is False
    assert (workspace / report["report_file"]).exists()
    assert (workspace / report["summary_file"]).exists()
    assert (workspace / report["history_file"]).exists()


def test_codex_adapter_registers_fresh_runtime_when_allowed(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    fresh_time = datetime.now().isoformat()
    _write_runtime(workspace, fresh_time)

    report = run_codex_native_adapter(workspace=workspace)

    assert report["runtime_present"] is True
    assert report["runtime_fresh"] is True
    assert report["session_registered"] is True
    assert report["session_id"] == "codex-runtime"


def test_codex_adapter_contract_exposes_native_heartbeat(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    fresh_time = datetime.now().isoformat()
    _write_runtime(workspace, fresh_time)

    contract = get_codex_adapter_contract()
    heartbeat = contract.heartbeat(workspace=workspace)

    assert contract.capability == "native"
    assert contract.push_interventions is None
    assert contract.pull_interventions is None
    assert heartbeat["runtime_present"] is True
