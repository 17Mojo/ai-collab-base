"""Codex native adapter with runtime-backed heartbeat semantics."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..ack_protocol import load_json, write_json
from ..adapters.contract import SessionAdapterContract, build_adapter_heartbeat
from ..intervention_queue import ack_intervention, inspect_interventions
from ..session_registry import inspect_sessions, refresh_session, register_session

DEFAULT_RUNTIME_PATH = ".cc-claude-codex/runtime.json"
DEFAULT_REPORT_PATH = "logs/codex_adapter_report.json"
DEFAULT_HISTORY_PATH = "logs/codex_adapter_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/CODEX_ADAPTER_SUMMARY_latest.md"
DEFAULT_SESSION_ID = "codex-runtime"
DEFAULT_STALE_AFTER_MINUTES = 180


def _load_codex_adapter_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    session_config = payload.get("sessionOrchestration")
    if not isinstance(session_config, dict):
        return {}
    raw = session_config.get("codexAdapter")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    runtime_path: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    config = _load_codex_adapter_config(workspace)
    resolved_report = workspace / str(report_path or config.get("report", DEFAULT_REPORT_PATH))
    resolved_history = workspace / str(history_path or config.get("history", DEFAULT_HISTORY_PATH))
    resolved_summary = workspace / str(summary_path or config.get("summary", DEFAULT_SUMMARY_PATH))
    resolved_runtime = workspace / str(
        runtime_path or config.get("runtimeFile", DEFAULT_RUNTIME_PATH)
    )
    return resolved_report, resolved_history, resolved_summary, resolved_runtime


def _stale_after_minutes(workspace: Path) -> int:
    config = _load_codex_adapter_config(workspace)
    raw = config.get("staleAfterMinutes", DEFAULT_STALE_AFTER_MINUTES)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_STALE_AFTER_MINUTES


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "runtime_present": payload.get("runtime_present", False),
        "runtime_fresh": payload.get("runtime_fresh", False),
        "session_registered": payload.get("session_registered", False),
        "open_intervention_count": payload.get("open_intervention_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _load_runtime_payload(runtime_file: Path) -> dict[str, Any]:
    return load_json(runtime_file, default={}) if runtime_file.exists() else {}


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _runtime_freshness(runtime: dict[str, Any], stale_after_minutes: int) -> tuple[bool, str]:
    if not runtime:
        return False, "missing"
    last_synced_at = _parse_iso(runtime.get("last_synced_at"))
    last_run_at = _parse_iso(runtime.get("last_run_at"))
    reference = last_synced_at or last_run_at
    if reference is None:
        return False, "missing_timestamp"
    age_minutes = (datetime.now(reference.tzinfo) - reference).total_seconds() / 60
    return age_minutes <= stale_after_minutes, f"{int(age_minutes)}"


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# Codex Adapter Summary（自动生成）",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- mode: `{report.get('mode', '')}`",
        f"- runtime_present: `{report.get('runtime_present', False)}`",
        f"- runtime_fresh: `{report.get('runtime_fresh', False)}`",
        f"- runtime_age_minutes: `{report.get('runtime_age_minutes', '')}`",
        f"- session_registered: `{report.get('session_registered', False)}`",
        f"- session_id: `{report.get('session_id', '')}`",
        f"- open_intervention_count: `{report.get('open_intervention_count', 0)}`",
        "",
        "## Runtime",
        "",
        f"- task_id: `{report.get('task_id', '')}`",
        f"- exit_reason: `{report.get('exit_reason', '')}`",
        f"- return_code: `{report.get('return_code', '')}`",
        f"- last_synced_at: `{report.get('last_synced_at', '')}`",
        "",
    ]
    return "\n".join(lines)


def run_codex_native_adapter(
    *,
    workspace: Path,
    dry_run: bool = False,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    runtime_path: str | None = None,
    allow_registration: bool = True,
) -> dict[str, Any]:
    report_file, history_file, summary_file, runtime_file = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        summary_path=summary_path,
        runtime_path=runtime_path,
    )
    runtime = _load_runtime_payload(runtime_file)
    runtime_present = bool(runtime)
    stale_after_minutes = _stale_after_minutes(workspace)
    runtime_fresh, runtime_age = _runtime_freshness(runtime, stale_after_minutes)
    queue = inspect_interventions(workspace=workspace, assignee="codex", only_open=True)
    registry = inspect_sessions(workspace=workspace, assignee="codex")
    sessions = list(registry.get("sessions", []) or [])
    latest = sessions[-1] if sessions else {}

    session_id = str(latest.get("session_id") or "")
    if runtime_present and runtime_fresh and allow_registration and not dry_run:
        if session_id:
            updated = refresh_session(
                workspace=workspace,
                session_id=session_id,
                session_status="active",
                health_status="healthy",
                touch_last_seen=True,
            )
            session_id = str(updated.get("session_id") or session_id)
        else:
            created = register_session(
                workspace=workspace,
                session_id=DEFAULT_SESSION_ID,
                assignee="codex",
                transport_mode="manual",
                session_status="active",
                health_status="healthy",
            )
            session_id = str(created.get("session_id") or DEFAULT_SESSION_ID)
        latest = {"session_id": session_id, "session_status": "active", "transport_mode": "manual"}

    report = build_adapter_heartbeat(
        workspace=workspace,
        name="codex",
        assignee="codex",
        capability="native",
        adapter_enabled=runtime_present,
        bridge_configured=False,
        open_intervention_count=int(queue.get("intervention_count", 0)),
        session_id=session_id,
        session_status=str(latest.get("session_status") or ("active" if session_id else "")),
        transport_mode=str(latest.get("transport_mode") or ("manual" if session_id else "")),
        report_file=report_file,
        history_file=history_file,
        summary_file=summary_file,
        event_dir=runtime_file.parent,
    )
    report.update(
        {
            "mode": "dry-run" if dry_run else "apply",
            "runtime_file": str(runtime_file.relative_to(workspace)),
            "runtime_present": runtime_present,
            "runtime_fresh": runtime_fresh,
            "runtime_age_minutes": runtime_age,
            "stale_after_minutes": stale_after_minutes,
            "task_id": str(runtime.get("task_id") or ""),
            "exit_reason": str(runtime.get("exit_reason") or ""),
            "return_code": runtime.get("return_code"),
            "last_synced_at": str(runtime.get("last_synced_at") or ""),
            "last_run_at": str(runtime.get("last_run_at") or ""),
        }
    )

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    write_json(report_file, report)
    _append_history(history_file, report)
    return report


def register_codex_session(
    *,
    workspace: Path,
    session_id: str,
    transport_mode: str = "manual",
    session_status: str = "active",
    last_handoff_artifact: str = "",
    health_status: str = "healthy",
) -> dict[str, Any]:
    return register_session(
        workspace=workspace,
        session_id=session_id,
        assignee="codex",
        transport_mode=transport_mode,
        session_status=session_status,
        last_handoff_artifact=last_handoff_artifact,
        health_status=health_status,
    )


def ack_codex_delivery(
    *,
    workspace: Path,
    intervention_id: str,
    delivery_status: str = "delivered",
    delivery_mode: str | None = None,
) -> dict[str, Any]:
    return ack_intervention(
        workspace=workspace,
        intervention_id=intervention_id,
        delivery_status=delivery_status,
        delivery_mode=delivery_mode,
    )


def heartbeat_codex_adapter(*, workspace: Path) -> dict[str, Any]:
    return run_codex_native_adapter(workspace=workspace, dry_run=True, allow_registration=False)


def get_codex_adapter_contract() -> SessionAdapterContract:
    return SessionAdapterContract(
        name="codex",
        assignee="codex",
        capability="native",
        register_session=register_codex_session,
        ack_delivery=ack_codex_delivery,
        heartbeat=heartbeat_codex_adapter,
    )
