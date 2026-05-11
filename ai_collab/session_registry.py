"""Session registry primitives for session-orchestration Slice 1."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import SUPPORTED_ASSIGNEES

DEFAULT_STATE_PATH = "logs/session_registry_state.json"
DEFAULT_HISTORY_PATH = "logs/session_registry_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md"
SUPPORTED_TRANSPORT_MODES = {"manual", "bridge"}


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default
    return payload if isinstance(payload, dict) else default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = _load_json(config_file, default={})
    raw = payload.get("sessionOrchestration")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> tuple[Path, Path, Path]:
    config = _load_config(workspace)
    resolved_state = workspace / (
        state_path or str(config.get("registryState", DEFAULT_STATE_PATH))
    )
    resolved_history = workspace / (
        history_path or str(config.get("registryHistory", DEFAULT_HISTORY_PATH))
    )
    resolved_summary = workspace / (
        summary_path or str(config.get("registrySummary", DEFAULT_SUMMARY_PATH))
    )
    return resolved_state, resolved_history, resolved_summary


def _relative_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _normalize_assignee(value: str) -> str:
    assignee = str(value or "").strip().lower()
    if assignee not in SUPPORTED_ASSIGNEES:
        raise ValueError(f"unsupported assignee: {value}")
    return assignee


def _normalize_transport_mode(value: str) -> str:
    transport_mode = str(value or "").strip().lower()
    if transport_mode not in SUPPORTED_TRANSPORT_MODES:
        raise ValueError(f"unsupported transport_mode: {value}")
    return transport_mode


def _normalize_text(value: str | None, *, fallback: str) -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def _load_state(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _load_json(path, default={"version": "1.0.0", "generated_at": "", "sessions": {}})
    sessions = payload.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
        payload["sessions"] = sessions
    return payload, sessions


def load_session_registry_state(
    workspace: Path,
    *,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
    """Load registry state and resolve configured output paths."""
    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    payload, sessions = _load_state(state_file)
    return state_file, history_file, summary_file, payload, sessions


def _build_summary_payload(
    *,
    workspace: Path,
    state_file: Path,
    summary_file: Path,
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    healthy_count = 0
    unhealthy_count = 0
    for item in sessions:
        if str(item.get("health_status", "")).strip().lower() == "healthy":
            healthy_count += 1
        else:
            unhealthy_count += 1

    return {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "session_count": len(sessions),
        "healthy_count": healthy_count,
        "unhealthy_count": unhealthy_count,
        "state_file": _relative_path(state_file, workspace),
        "summary_file": _relative_path(summary_file, workspace),
        "sessions": sessions,
    }


def build_summary_markdown(*, payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Session Registry Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{payload.get('generated_at', '')}`")
    lines.append(f"- 会话数: `{payload.get('session_count', 0)}`")
    lines.append(f"- healthy: `{payload.get('healthy_count', 0)}`")
    lines.append(f"- unhealthy: `{payload.get('unhealthy_count', 0)}`")
    lines.append(f"- state_file: `{payload.get('state_file', '')}`")
    lines.append("")
    lines.append("## Sessions")
    lines.append("")
    sessions = payload.get("sessions", [])
    if sessions:
        for item in sessions:
            lines.append(
                f"- `{item.get('session_id', '')}` assignee=`{item.get('assignee', '')}` transport=`{item.get('transport_mode', '')}` status=`{item.get('session_status', '')}` health=`{item.get('health_status', '')}`"
            )
    else:
        lines.append("- 无会话")
    lines.append("")
    return "\n".join(lines)


def _write_summary(
    *, workspace: Path, summary_file: Path, sessions: list[dict[str, Any]]
) -> dict[str, Any]:
    payload = _build_summary_payload(
        workspace=workspace,
        state_file=workspace / DEFAULT_STATE_PATH,
        summary_file=summary_file,
        sessions=sessions,
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(payload=payload), encoding="utf-8")
    return payload


def _sorted_sessions(sessions: dict[str, Any]) -> list[dict[str, Any]]:
    records = [value for value in sessions.values() if isinstance(value, dict)]
    records.sort(key=lambda item: (str(item.get("assignee", "")), str(item.get("session_id", ""))))
    return records


def read_session_registry(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return a stable, sorted view of the current session registry."""
    _, _, _, _, sessions = load_session_registry_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    return _sorted_sessions(sessions)


def register_session(
    *,
    workspace: Path,
    session_id: str,
    assignee: str,
    transport_mode: str,
    session_status: str = "active",
    last_handoff_artifact: str = "",
    health_status: str = "healthy",
    observed_at: str | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    normalized_session_id = _normalize_text(session_id, fallback="")
    if not normalized_session_id:
        raise ValueError("session_id is required")

    normalized_assignee = _normalize_assignee(assignee)
    normalized_transport = _normalize_transport_mode(transport_mode)
    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )

    payload, sessions = _load_state(state_file)
    existing = (
        sessions.get(normalized_session_id)
        if isinstance(sessions.get(normalized_session_id), dict)
        else {}
    )
    now = datetime.now().isoformat()
    seen_at = _normalize_text(observed_at, fallback=now)
    record = {
        "session_id": normalized_session_id,
        "assignee": normalized_assignee,
        "transport_mode": normalized_transport,
        "session_status": _normalize_text(session_status, fallback="active").lower(),
        "last_seen_at": seen_at,
        "last_handoff_artifact": str(
            last_handoff_artifact or existing.get("last_handoff_artifact") or ""
        ).strip(),
        "health_status": _normalize_text(health_status, fallback="healthy").lower(),
        "created_at": str(existing.get("created_at") or seen_at),
        "updated_at": now,
    }
    sessions[normalized_session_id] = record
    payload["generated_at"] = now
    payload["sessions"] = sessions
    _write_json(state_file, payload)
    _append_jsonl(
        history_file,
        {
            "generated_at": now,
            "action": "register" if not existing else "register_update",
            **record,
        },
    )
    summary_payload = _build_summary_payload(
        workspace=workspace,
        state_file=state_file,
        summary_file=summary_file,
        sessions=_sorted_sessions(sessions),
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(payload=summary_payload), encoding="utf-8")
    return record


def refresh_session(
    *,
    workspace: Path,
    session_id: str,
    assignee: str | None = None,
    transport_mode: str | None = None,
    session_status: str | None = None,
    last_handoff_artifact: str | None = None,
    health_status: str | None = None,
    observed_at: str | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    touch_last_seen: bool = True,
) -> dict[str, Any]:
    normalized_session_id = _normalize_text(session_id, fallback="")
    if not normalized_session_id:
        raise ValueError("session_id is required")

    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    payload, sessions = _load_state(state_file)
    existing = sessions.get(normalized_session_id)
    if not isinstance(existing, dict):
        raise ValueError(f"session not found: {normalized_session_id}")

    now = datetime.now().isoformat()
    record = dict(existing)
    if assignee is not None:
        record["assignee"] = _normalize_assignee(assignee)
    if transport_mode is not None:
        record["transport_mode"] = _normalize_transport_mode(transport_mode)
    if session_status is not None:
        record["session_status"] = _normalize_text(
            session_status, fallback=record.get("session_status", "active")
        ).lower()
    if last_handoff_artifact is not None:
        record["last_handoff_artifact"] = str(last_handoff_artifact).strip()
    if health_status is not None:
        record["health_status"] = _normalize_text(
            health_status, fallback=record.get("health_status", "healthy")
        ).lower()
    record["updated_at"] = now
    if touch_last_seen:
        record["last_seen_at"] = _normalize_text(observed_at, fallback=now)

    sessions[normalized_session_id] = record
    payload["generated_at"] = now
    payload["sessions"] = sessions
    _write_json(state_file, payload)
    _append_jsonl(
        history_file,
        {
            "generated_at": now,
            "action": "refresh",
            **record,
        },
    )
    summary_payload = _build_summary_payload(
        workspace=workspace,
        state_file=state_file,
        summary_file=summary_file,
        sessions=_sorted_sessions(sessions),
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(payload=summary_payload), encoding="utf-8")
    return record


def update_session_health(
    *,
    workspace: Path,
    session_id: str,
    health_status: str,
    reason_codes: list[str] | None = None,
    incident_count: int | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    """Persist health metadata without mutating session last_seen_at."""
    normalized_session_id = _normalize_text(session_id, fallback="")
    if not normalized_session_id:
        raise ValueError("session_id is required")

    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    payload, sessions = _load_state(state_file)
    existing = sessions.get(normalized_session_id)
    if not isinstance(existing, dict):
        raise ValueError(f"session not found: {normalized_session_id}")

    now = datetime.now().isoformat()
    record = dict(existing)
    normalized_reason_codes = sorted(
        {
            str(item or "").strip().lower()
            for item in list(reason_codes or [])
            if str(item or "").strip()
        }
    )
    record["health_status"] = _normalize_text(
        health_status, fallback=record.get("health_status", "healthy")
    ).lower()
    record["health_reason_codes"] = normalized_reason_codes
    record["health_incident_count"] = max(int(incident_count or 0), 0)
    record["health_updated_at"] = now
    record["updated_at"] = now

    sessions[normalized_session_id] = record
    payload["generated_at"] = now
    payload["sessions"] = sessions
    _write_json(state_file, payload)
    _append_jsonl(
        history_file,
        {
            "generated_at": now,
            "action": "health_update",
            **record,
        },
    )
    summary_payload = _build_summary_payload(
        workspace=workspace,
        state_file=state_file,
        summary_file=summary_file,
        sessions=_sorted_sessions(sessions),
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(payload=summary_payload), encoding="utf-8")
    return record


def inspect_sessions(
    *,
    workspace: Path,
    session_id: str | None = None,
    assignee: str | None = None,
    transport_mode: str | None = None,
    session_status: str | None = None,
    health_status: str | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    state_file, _, summary_file, payload, sessions = load_session_registry_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    records = _sorted_sessions(sessions)

    normalized_session_id = str(session_id or "").strip()
    normalized_assignee = str(assignee or "").strip().lower()
    normalized_transport_mode = str(transport_mode or "").strip().lower()
    normalized_session_status = str(session_status or "").strip().lower()
    normalized_health_status = str(health_status or "").strip().lower()
    if normalized_session_id:
        records = [
            item for item in records if str(item.get("session_id", "")) == normalized_session_id
        ]
    if normalized_assignee:
        records = [
            item
            for item in records
            if str(item.get("assignee", "")).strip().lower() == normalized_assignee
        ]
    if normalized_transport_mode:
        records = [
            item
            for item in records
            if str(item.get("transport_mode", "")).strip().lower() == normalized_transport_mode
        ]
    if normalized_session_status:
        records = [
            item
            for item in records
            if str(item.get("session_status", "")).strip().lower() == normalized_session_status
        ]
    if normalized_health_status:
        records = [
            item
            for item in records
            if str(item.get("health_status", "")).strip().lower() == normalized_health_status
        ]

    summary_payload = _build_summary_payload(
        workspace=workspace,
        state_file=state_file,
        summary_file=summary_file,
        sessions=records,
    )
    summary_payload["generated_at"] = payload.get("generated_at") or summary_payload["generated_at"]
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(payload=summary_payload), encoding="utf-8")
    return summary_payload


def render_session_registry_summary(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> str:
    """Render and persist the latest session registry summary markdown."""
    _, _, summary_file, _, sessions = load_session_registry_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    _write_summary(
        workspace=workspace,
        summary_file=summary_file,
        sessions=_sorted_sessions(sessions),
    )
    return summary_file.read_text(encoding="utf-8")


def run_session_registry(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible summary entry point for registry reporting."""
    return inspect_sessions(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
