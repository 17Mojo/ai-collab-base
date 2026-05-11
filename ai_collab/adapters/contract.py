"""Shared adapter contract helpers for session orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

AdapterCapability = Literal["push", "pull", "native"]
HeartbeatFn = Callable[..., dict[str, Any]]
RegisterSessionFn = Callable[..., dict[str, Any]]
DeliveryFn = Callable[..., dict[str, Any]]
AckDeliveryFn = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class SessionAdapterContract:
    """Minimal shared contract for external session adapters."""

    name: str
    assignee: str
    capability: AdapterCapability
    register_session: RegisterSessionFn
    ack_delivery: AckDeliveryFn
    heartbeat: HeartbeatFn
    push_interventions: DeliveryFn | None = None
    pull_interventions: DeliveryFn | None = None


def build_adapter_heartbeat(
    *,
    workspace: Path,
    name: str,
    assignee: str,
    capability: AdapterCapability,
    adapter_enabled: bool,
    bridge_configured: bool,
    open_intervention_count: int,
    session_id: str = "",
    session_status: str = "",
    transport_mode: str = "",
    report_file: Path | None = None,
    history_file: Path | None = None,
    summary_file: Path | None = None,
    event_dir: Path | None = None,
) -> dict[str, Any]:
    def _rel(path: Path | None) -> str:
        if path is None:
            return ""
        try:
            return str(path.relative_to(workspace))
        except ValueError:
            return str(path)

    return {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "adapter_name": name,
        "assignee": assignee,
        "capability": capability,
        "adapter_enabled": adapter_enabled,
        "bridge_configured": bridge_configured,
        "session_registered": bool(session_id),
        "session_id": session_id,
        "session_status": session_status,
        "transport_mode": transport_mode,
        "open_intervention_count": open_intervention_count,
        "report_file": _rel(report_file),
        "history_file": _rel(history_file),
        "summary_file": _rel(summary_file),
        "event_dir": _rel(event_dir),
    }
