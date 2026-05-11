"""Automatic session registration/refresh from real local anchors."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .session_registry import load_session_registry_state, refresh_session, register_session

SUPPORTED_AUTO_ASSIGNEES = {"claude_code", "codearts_agent", "codex"}
DEFAULT_CODEX_RUNTIME_PATH = ".cc-claude-codex/runtime.json"
DEFAULT_CODEX_MAX_AGE_MINUTES = 720

_AI_ALIAS_MAP = {
    "claude": "claude_code",
    "claude_code": "claude_code",
    "codearts": "codearts_agent",
    "codearts_agent": "codearts_agent",
    "copilot": "codearts_agent",
    "codex": "codex",
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_assignee(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return _AI_ALIAS_MAP.get(normalized, normalized)


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _relative_to_workspace(workspace: Path, candidate: object) -> str:
    raw = str(candidate or "").strip()
    if not raw:
        return ""
    path = Path(raw)
    if not path.is_absolute():
        path = workspace / path
    if not path.exists():
        return ""
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _default_handoff_artifact(workspace: Path, assignee: str) -> str:
    candidate = workspace / "collaboration" / "monitoring" / f"AGENT_TRIGGER_{assignee}_latest.md"
    return str(candidate.relative_to(workspace)) if candidate.exists() else ""


def _session_exists(workspace: Path, session_id: str) -> bool:
    _, _, _, _, sessions = load_session_registry_state(workspace)
    return isinstance(sessions.get(session_id), dict)


def _upsert_session(
    *,
    workspace: Path,
    session_id: str,
    assignee: str,
    transport_mode: str,
    session_status: str,
    last_handoff_artifact: str = "",
) -> dict[str, Any]:
    if _session_exists(workspace, session_id):
        record = refresh_session(
            workspace=workspace,
            session_id=session_id,
            assignee=assignee,
            transport_mode=transport_mode,
            session_status=session_status,
            last_handoff_artifact=last_handoff_artifact or None,
        )
        return {"action": "refreshed", "record": record}

    record = register_session(
        workspace=workspace,
        session_id=session_id,
        assignee=assignee,
        transport_mode=transport_mode,
        session_status=session_status,
        last_handoff_artifact=last_handoff_artifact,
    )
    return {"action": "registered", "record": record}


def register_codex_session_from_runtime(
    *,
    workspace: Path,
    runtime_path: str = DEFAULT_CODEX_RUNTIME_PATH,
    max_age_minutes: int = DEFAULT_CODEX_MAX_AGE_MINUTES,
) -> dict[str, Any]:
    runtime_file = workspace / runtime_path
    runtime = _load_json(runtime_file)
    if not runtime:
        return {
            "status": "skipped",
            "reason": "runtime_missing_or_invalid",
            "runtime_file": str(runtime_file),
        }

    anchor = (
        runtime.get("last_synced_at")
        or runtime.get("last_run_at")
        or runtime.get("last_plan_at")
    )
    anchor_time = _parse_iso(anchor)
    if anchor_time is None:
        return {
            "status": "skipped",
            "reason": "runtime_missing_anchor_timestamp",
            "runtime_file": str(runtime_file),
        }

    now = datetime.now(anchor_time.tzinfo) if anchor_time.tzinfo else datetime.now()
    age = now - anchor_time
    if age > timedelta(minutes=max(int(max_age_minutes), 1)):
        return {
            "status": "skipped",
            "reason": "runtime_stale",
            "runtime_file": str(runtime_file),
            "age_minutes": int(age.total_seconds() // 60),
        }

    session_id = str(runtime.get("session_id") or "codex-runtime").strip() or "codex-runtime"
    handoff_artifact = (
        _relative_to_workspace(workspace, runtime.get("output_file"))
        or _relative_to_workspace(workspace, runtime.get("progress_file"))
        or _relative_to_workspace(workspace, runtime.get("log_file"))
    )
    result = _upsert_session(
        workspace=workspace,
        session_id=session_id,
        assignee="codex",
        transport_mode="manual",
        session_status="active",
        last_handoff_artifact=handoff_artifact,
    )
    return {
        "status": "ok",
        "runtime_file": str(runtime_file.relative_to(workspace)),
        "age_minutes": int(age.total_seconds() // 60),
        **result,
    }


def register_claude_session_from_hook(
    *,
    workspace: Path,
    hook_input: dict[str, Any],
    event_name: str,
) -> dict[str, Any]:
    session_id = str(
        hook_input.get("session_id")
        or hook_input.get("sessionId")
        or ""
    ).strip()
    if not session_id:
        return {"status": "skipped", "reason": "missing_session_id"}

    event = str(event_name or "").strip().lower()
    session_status = "idle" if event in {"stop", "sessionend"} else "active"
    handoff_artifact = _default_handoff_artifact(workspace, "claude_code")
    result = _upsert_session(
        workspace=workspace,
        session_id=session_id,
        assignee="claude_code",
        transport_mode="manual",
        session_status=session_status,
        last_handoff_artifact=handoff_artifact,
    )
    return {"status": "ok", "event_name": event_name, **result}


def register_session_from_activation(
    *,
    workspace: Path,
    assignee: str,
    session_id: str,
) -> dict[str, Any]:
    normalized_assignee = _normalize_assignee(assignee)
    if normalized_assignee != "codex":
        return {
            "status": "skipped",
            "reason": "activation_registration_limited_to_codex",
            "assignee": normalized_assignee,
        }
    if not str(session_id or "").strip():
        return {"status": "skipped", "reason": "missing_session_id", "assignee": normalized_assignee}

    result = _upsert_session(
        workspace=workspace,
        session_id=str(session_id).strip(),
        assignee=normalized_assignee,
        transport_mode="manual",
        session_status="active",
        last_handoff_artifact=_relative_to_workspace(
            workspace, workspace / ".cc-claude-codex" / "runtime.json"
        ),
    )
    return {"status": "ok", **result}


def sync_auto_sessions(
    *,
    workspace: Path,
    runtime_path: str = DEFAULT_CODEX_RUNTIME_PATH,
    max_codex_runtime_age_minutes: int = DEFAULT_CODEX_MAX_AGE_MINUTES,
) -> dict[str, Any]:
    codex_result = register_codex_session_from_runtime(
        workspace=workspace,
        runtime_path=runtime_path,
        max_age_minutes=max_codex_runtime_age_minutes,
    )
    return {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "results": [codex_result],
        "registered_count": len([item for item in [codex_result] if item.get("status") == "ok"]),
        "skipped_count": len([item for item in [codex_result] if item.get("status") != "ok"]),
    }
