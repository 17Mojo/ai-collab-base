"""CodeArts-oriented pull adapter with auditable fallback semantics."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..ack_protocol import load_json, write_json
from ..adapters.contract import SessionAdapterContract, build_adapter_heartbeat
from ..intervention_queue import (
    DEFAULT_BRIDGE_DELIVERY_STATUS,
    ack_intervention,
    inspect_interventions,
)
from ..session_registry import inspect_sessions, register_session

DEFAULT_REPORT_PATH = "logs/codearts_adapter_report.json"
DEFAULT_HISTORY_PATH = "logs/codearts_adapter_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md"
DEFAULT_EVENT_DIR = "collaboration/monitoring/codearts_pull_events"
EXACT_MESSAGE_PATTERN = re.compile(
    r"## Exact Forward Message\s+```text\s*(?P<message>.*?)\s*```",
    flags=re.DOTALL,
)


def _load_codearts_adapter_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    session_config = payload.get("sessionOrchestration")
    if not isinstance(session_config, dict):
        return {}
    raw = session_config.get("codeartsAdapter")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    event_dir: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    config = _load_codearts_adapter_config(workspace)
    resolved_report = workspace / str(report_path or config.get("report", DEFAULT_REPORT_PATH))
    resolved_history = workspace / str(history_path or config.get("history", DEFAULT_HISTORY_PATH))
    resolved_summary = workspace / str(summary_path or config.get("summary", DEFAULT_SUMMARY_PATH))
    resolved_event_dir = workspace / str(event_dir or config.get("eventDir", DEFAULT_EVENT_DIR))
    return resolved_report, resolved_history, resolved_summary, resolved_event_dir


def _adapter_mode(workspace: Path) -> tuple[bool, str, str]:
    config = _load_codearts_adapter_config(workspace)
    enabled = bool(config.get("enabled", False))
    bridge_command = str(config.get("bridgeCommand") or "").strip()
    delivery_status = (
        str(config.get("deliveryStatusOnSuccess") or DEFAULT_BRIDGE_DELIVERY_STATUS).strip().lower()
    )
    return enabled, bridge_command, delivery_status


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "candidate_count": payload.get("candidate_count", 0),
        "queued_count": payload.get("queued_count", 0),
        "artifact_only_count": payload.get("artifact_only_count", 0),
        "failed_count": payload.get("failed_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _load_artifact_message(path: Path) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "", f"unable to read artifact: {exc}"
    match = EXACT_MESSAGE_PATTERN.search(text)
    if match:
        return str(match.group("message")).strip(), ""
    return text.strip(), ""


def build_codearts_pull_event_markdown(
    *,
    intervention: dict[str, Any],
    exact_message: str,
    bridge_enabled: bool,
    artifact_file: Path,
) -> str:
    lines = [
        "# CodeArts Pull Event（自动生成）",
        "",
        f"- generated_at: `{datetime.now().isoformat()}`",
        f"- intervention_id: `{intervention.get('intervention_id', '')}`",
        f"- assignee: `{intervention.get('assignee', '')}`",
        f"- session_id: `{intervention.get('session_id', '')}`",
        f"- reason_code: `{intervention.get('reason_code', '')}`",
        f"- delivery_status: `{intervention.get('delivery_status', '')}`",
        f"- bridge_enabled: `{bridge_enabled}`",
        f"- source_artifact: `{artifact_file}`",
        "",
        "## Pull Snapshot",
        "",
        "```text",
        exact_message,
        "```",
        "",
    ]
    return "\n".join(lines)


def _event_file(event_dir: Path, intervention_id: str) -> Path:
    return event_dir / f"CODEARTS_PULL_EVENT_{intervention_id}_latest.md"


def _run_bridge_command(
    *,
    workspace: Path,
    command: str,
    event_file: Path,
    artifact_file: Path,
    intervention: dict[str, Any],
) -> subprocess.CompletedProcess[str]:
    rendered = command.format(
        workspace=str(workspace),
        event_file=str(event_file),
        artifact_file=str(artifact_file),
        intervention_id=str(intervention.get("intervention_id") or ""),
        session_id=str(intervention.get("session_id") or ""),
        assignee=str(intervention.get("assignee") or ""),
        reason_code=str(intervention.get("reason_code") or ""),
    )
    if platform.system() == "Windows":
        cmd = ["cmd", "/C", rendered]
    else:
        cmd = ["/bin/sh", "-lc", rendered]
    return subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# CodeArts Adapter Summary（自动生成）",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- mode: `{report.get('mode', '')}`",
        f"- candidate_count: `{report.get('candidate_count', 0)}`",
        f"- queued_count: `{report.get('queued_count', 0)}`",
        f"- artifact_only_count: `{report.get('artifact_only_count', 0)}`",
        f"- failed_count: `{report.get('failed_count', 0)}`",
        "",
        "## Deliveries",
        "",
    ]
    deliveries = list(report.get("deliveries", []) or [])
    if deliveries:
        for item in deliveries:
            lines.append(
                f"- `{item.get('intervention_id', '')}` action=`{item.get('action', '')}` "
                f"status=`{item.get('delivery_status', '')}`"
            )
            if item.get("event_file"):
                lines.append(f"  event_file: `{item.get('event_file', '')}`")
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_codearts_pull_adapter(
    *,
    workspace: Path,
    dry_run: bool = False,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    event_dir: str | None = None,
    allow_delivery: bool = True,
) -> dict[str, Any]:
    report_file, history_file, summary_file, event_root = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        summary_path=summary_path,
        event_dir=event_dir,
    )
    enabled, bridge_command, delivery_status_on_success = _adapter_mode(workspace)
    payload = inspect_interventions(workspace=workspace, assignee="codearts_agent", only_open=True)
    candidates = list(payload.get("interventions", []) or [])

    deliveries: list[dict[str, Any]] = []
    queued_count = 0
    artifact_only_count = 0
    failed_count = 0

    for intervention in candidates:
        intervention_id = str(intervention.get("intervention_id") or "").strip()
        artifact_relpath = str(intervention.get("message_artifact") or "").strip()
        artifact_file = workspace / artifact_relpath if artifact_relpath else workspace
        exact_message, error = _load_artifact_message(artifact_file)
        delivery = {
            "intervention_id": intervention_id,
            "session_id": str(intervention.get("session_id") or ""),
            "delivery_status": str(intervention.get("delivery_status") or ""),
            "event_file": "",
            "action": "",
            "error": "",
        }

        if error:
            if not dry_run:
                ack_report = ack_intervention(
                    workspace=workspace,
                    intervention_id=intervention_id,
                    delivery_status="failed",
                    delivery_mode="bridge"
                    if enabled and bridge_command and allow_delivery
                    else None,
                )
                updated = ack_report.get("intervention", {})
                delivery["delivery_status"] = str(updated.get("delivery_status") or "failed")
            delivery["action"] = "failed"
            delivery["error"] = error
            failed_count += 1
            deliveries.append(delivery)
            continue

        event_file = _event_file(event_root, intervention_id)
        event_file.parent.mkdir(parents=True, exist_ok=True)
        event_file.write_text(
            build_codearts_pull_event_markdown(
                intervention=intervention,
                exact_message=exact_message,
                bridge_enabled=enabled and bool(bridge_command) and allow_delivery and not dry_run,
                artifact_file=artifact_file,
            ),
            encoding="utf-8",
        )
        delivery["event_file"] = str(event_file.relative_to(workspace))

        if dry_run or not allow_delivery or not enabled or not bridge_command:
            delivery["action"] = "artifact_only"
            artifact_only_count += 1
            deliveries.append(delivery)
            continue

        result = _run_bridge_command(
            workspace=workspace,
            command=bridge_command,
            event_file=event_file,
            artifact_file=artifact_file,
            intervention=intervention,
        )
        if result.returncode == 0:
            ack_report = ack_intervention(
                workspace=workspace,
                intervention_id=intervention_id,
                delivery_status=delivery_status_on_success,
                delivery_mode="bridge",
            )
            updated = ack_report.get("intervention", {})
            delivery["action"] = "queued"
            delivery["delivery_status"] = str(
                updated.get("delivery_status") or delivery_status_on_success
            )
            queued_count += 1
        else:
            ack_report = ack_intervention(
                workspace=workspace,
                intervention_id=intervention_id,
                delivery_status="failed",
                delivery_mode="bridge",
            )
            updated = ack_report.get("intervention", {})
            delivery["action"] = "failed"
            delivery["delivery_status"] = str(updated.get("delivery_status") or "failed")
            delivery["error"] = (result.stderr or result.stdout or "").strip() or (
                f"bridge command exited with code {result.returncode}"
            )
            failed_count += 1
        deliveries.append(delivery)

    report = {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "adapter_enabled": enabled,
        "allow_delivery": allow_delivery,
        "candidate_count": len(candidates),
        "queued_count": queued_count,
        "artifact_only_count": artifact_only_count,
        "failed_count": failed_count,
        "deliveries": deliveries,
    }

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = str(summary_file.relative_to(workspace))
    report["report_file"] = str(report_file.relative_to(workspace))
    report["history_file"] = str(history_file.relative_to(workspace))
    write_json(report_file, report)
    _append_history(history_file, report)
    return report


def register_codearts_session(
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
        assignee="codearts_agent",
        transport_mode=transport_mode,
        session_status=session_status,
        last_handoff_artifact=last_handoff_artifact,
        health_status=health_status,
    )


def ack_codearts_delivery(
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


def heartbeat_codearts_adapter(*, workspace: Path) -> dict[str, Any]:
    report_file, history_file, summary_file, event_root = _resolve_paths(workspace=workspace)
    enabled, bridge_command, _ = _adapter_mode(workspace)
    queue = inspect_interventions(workspace=workspace, assignee="codearts_agent", only_open=True)
    registry = inspect_sessions(workspace=workspace, assignee="codearts_agent")
    sessions = list(registry.get("sessions", []) or [])
    latest = sessions[-1] if sessions else {}
    return build_adapter_heartbeat(
        workspace=workspace,
        name="codearts",
        assignee="codearts_agent",
        capability="pull",
        adapter_enabled=enabled,
        bridge_configured=bool(bridge_command),
        open_intervention_count=int(queue.get("intervention_count", 0)),
        session_id=str(latest.get("session_id") or ""),
        session_status=str(latest.get("session_status") or ""),
        transport_mode=str(latest.get("transport_mode") or ""),
        report_file=report_file,
        history_file=history_file,
        summary_file=summary_file,
        event_dir=event_root,
    )


def get_codearts_adapter_contract() -> SessionAdapterContract:
    return SessionAdapterContract(
        name="codearts",
        assignee="codearts_agent",
        capability="pull",
        register_session=register_codearts_session,
        pull_interventions=run_codearts_pull_adapter,
        ack_delivery=ack_codearts_delivery,
        heartbeat=heartbeat_codearts_adapter,
    )
