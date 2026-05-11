"""Automatic session registration/refresh from workspace-local anchors."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .ack_protocol import SUPPORTED_ASSIGNEES, load_json
from .session_registry import inspect_sessions, refresh_session, register_session

DEFAULT_OBSERVATION_PATH = "logs/session_observations.jsonl"
DEFAULT_SYNC_MAX_AGE_HOURS = 24
DEFAULT_CODEX_SESSION_ID = "codex-runtime"


def _now() -> datetime:
    return datetime.now()


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    raw = payload.get("sessionOrchestration")
    return raw if isinstance(raw, dict) else {}


def _observation_file(workspace: Path) -> Path:
    config = _load_config(workspace)
    return workspace / str(config.get("observationHistory", DEFAULT_OBSERVATION_PATH))


def _max_age_hours(workspace: Path) -> int:
    config = _load_config(workspace)
    try:
        return max(int(config.get("autoRegisterMaxAgeHours", DEFAULT_SYNC_MAX_AGE_HOURS)), 1)
    except (TypeError, ValueError):
        return DEFAULT_SYNC_MAX_AGE_HOURS


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _latest_handoff_artifact(workspace: Path, assignee: str) -> str:
    candidate = workspace / "collaboration" / "monitoring" / f"AGENT_TRIGGER_{assignee}_latest.md"
    if candidate.exists():
        return str(candidate.relative_to(workspace))
    return ""


def _candidate_key(candidate: dict[str, Any]) -> tuple[str, str]:
    return (
        str(candidate.get("assignee") or "").strip().lower(),
        str(candidate.get("session_id") or "").strip(),
    )


def _select_latest(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = _candidate_key(candidate)
        if not key[0] or not key[1]:
            continue
        current = latest.get(key)
        current_seen = _parse_iso(current.get("observed_at")) if isinstance(current, dict) else None
        next_seen = _parse_iso(candidate.get("observed_at"))
        if current is None or (next_seen and (current_seen is None or next_seen >= current_seen)):
            latest[key] = candidate
    return sorted(
        latest.values(),
        key=lambda item: (
            str(item.get("assignee") or ""),
            str(item.get("observed_at") or ""),
            str(item.get("session_id") or ""),
        ),
    )


def record_hook_session_observation(
    *,
    workspace: Path,
    assignee: str,
    hook_input: dict[str, Any],
    source: str,
    transport_mode: str = "manual",
) -> dict[str, Any]:
    """Persist a hook observation and register/refresh immediately when session_id is present."""
    normalized_assignee = str(assignee or "").strip().lower()
    if normalized_assignee not in SUPPORTED_ASSIGNEES:
        return {}

    observed_at = _now().isoformat()
    session_id = str(
        hook_input.get("session_id")
        or hook_input.get("sessionId")
        or hook_input.get("conversation_id")
        or hook_input.get("conversationId")
        or ""
    ).strip()
    observation = {
        "observed_at": observed_at,
        "source": source,
        "assignee": normalized_assignee,
        "session_id": session_id,
        "cwd": str(hook_input.get("cwd") or ""),
        "model": str(hook_input.get("model") or ""),
        "transport_mode": transport_mode,
        "hook_keys": sorted(str(key) for key in hook_input.keys()),
    }
    observation_file = _observation_file(workspace)
    _append_jsonl(observation_file, observation)

    if not session_id:
        return observation

    registry = inspect_sessions(workspace=workspace, session_id=session_id)
    if registry.get("session_count", 0) > 0:
        refresh_session(
            workspace=workspace,
            session_id=session_id,
            assignee=normalized_assignee,
            transport_mode=transport_mode,
            session_status="active",
            last_handoff_artifact=_latest_handoff_artifact(workspace, normalized_assignee) or None,
            observed_at=observed_at,
        )
    else:
        register_session(
            workspace=workspace,
            session_id=session_id,
            assignee=normalized_assignee,
            transport_mode=transport_mode,
            session_status="active",
            last_handoff_artifact=_latest_handoff_artifact(workspace, normalized_assignee),
            observed_at=observed_at,
        )
    return observation


def _collect_activation_candidates(workspace: Path, *, max_age: timedelta) -> list[dict[str, Any]]:
    activation_dir = workspace / "logs" / "activations"
    if not activation_dir.exists():
        return []

    candidates: list[dict[str, Any]] = []
    cutoff = _now() - max_age
    for path in sorted(activation_dir.glob("*.jsonl")):
        for item in _load_jsonl(path):
            assignee = str(item.get("ai_type") or "").strip().lower()
            observed_at = str(item.get("activation_time") or "").strip()
            seen_at = _parse_iso(observed_at)
            if assignee not in SUPPORTED_ASSIGNEES or seen_at is None or seen_at < cutoff:
                continue
            candidates.append(
                {
                    "assignee": assignee,
                    "session_id": str(item.get("session_id") or "").strip(),
                    "observed_at": observed_at,
                    "transport_mode": "manual",
                    "session_status": "active",
                    "last_handoff_artifact": _latest_handoff_artifact(workspace, assignee),
                    "source": "activation_log",
                }
            )
    return _select_latest(candidates)


def _collect_hook_observation_candidates(
    workspace: Path, *, max_age: timedelta
) -> list[dict[str, Any]]:
    observation_file = _observation_file(workspace)
    if not observation_file.exists():
        return []

    candidates: list[dict[str, Any]] = []
    cutoff = _now() - max_age
    for item in _load_jsonl(observation_file):
        assignee = str(item.get("assignee") or "").strip().lower()
        session_id = str(item.get("session_id") or "").strip()
        observed_at = str(item.get("observed_at") or "").strip()
        seen_at = _parse_iso(observed_at)
        if (
            assignee not in SUPPORTED_ASSIGNEES
            or not session_id
            or seen_at is None
            or seen_at < cutoff
        ):
            continue
        candidates.append(
            {
                "assignee": assignee,
                "session_id": session_id,
                "observed_at": observed_at,
                "transport_mode": str(item.get("transport_mode") or "manual"),
                "session_status": "active",
                "last_handoff_artifact": _latest_handoff_artifact(workspace, assignee),
                "source": str(item.get("source") or "hook_observation"),
            }
        )
    return _select_latest(candidates)


def _collect_codex_runtime_candidates(
    workspace: Path, *, max_age: timedelta
) -> list[dict[str, Any]]:
    runtime_file = workspace / ".cc-claude-codex" / "runtime.json"
    runtime = load_json(runtime_file, default={})
    observed_at = ""
    for key in ("last_run_at", "last_synced_at", "last_plan_at"):
        candidate = str(runtime.get(key) or "").strip()
        if _parse_iso(candidate):
            if not observed_at or _parse_iso(candidate) >= _parse_iso(observed_at):
                observed_at = candidate

    seen_at = _parse_iso(observed_at)
    if seen_at is None or seen_at < (_now() - max_age):
        return []

    return [
        {
            "assignee": "codex",
            "session_id": DEFAULT_CODEX_SESSION_ID,
            "observed_at": observed_at,
            "transport_mode": "bridge",
            "session_status": "active",
            "last_handoff_artifact": "",
            "source": "codex_runtime",
        }
    ]


def run_session_auto_sync(
    *,
    workspace: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Register or refresh sessions from local observations and runtime anchors."""
    max_age = timedelta(hours=_max_age_hours(workspace))
    activation = _collect_activation_candidates(workspace, max_age=max_age)
    hook_observations = _collect_hook_observation_candidates(workspace, max_age=max_age)
    codex_runtime = _collect_codex_runtime_candidates(workspace, max_age=max_age)

    latest_by_assignee: dict[str, dict[str, Any]] = {}
    for candidate in activation + hook_observations + codex_runtime:
        assignee = str(candidate.get("assignee") or "").strip().lower()
        current = latest_by_assignee.get(assignee)
        current_seen = _parse_iso(current.get("observed_at")) if isinstance(current, dict) else None
        next_seen = _parse_iso(candidate.get("observed_at"))
        if current is None or (next_seen and (current_seen is None or next_seen >= current_seen)):
            latest_by_assignee[assignee] = candidate

    existing_sessions = inspect_sessions(workspace=workspace).get("sessions", [])
    existing_by_session_id = {
        str(item.get("session_id") or ""): item
        for item in existing_sessions
        if isinstance(item, dict) and str(item.get("session_id") or "").strip()
    }

    synced: list[dict[str, Any]] = []
    registered_count = 0
    refreshed_count = 0
    for candidate in sorted(
        latest_by_assignee.values(), key=lambda item: str(item.get("assignee") or "")
    ):
        session_id = str(candidate.get("session_id") or "").strip()
        if not session_id:
            continue
        assignee = str(candidate.get("assignee") or "").strip().lower()
        action = "register"
        if session_id in existing_by_session_id:
            action = "refresh"

        record = {
            "action": action,
            **candidate,
        }
        if not dry_run:
            if action == "refresh":
                refresh_session(
                    workspace=workspace,
                    session_id=session_id,
                    assignee=assignee,
                    transport_mode=str(candidate.get("transport_mode") or "manual"),
                    session_status=str(candidate.get("session_status") or "active"),
                    last_handoff_artifact=str(candidate.get("last_handoff_artifact") or "") or None,
                    observed_at=str(candidate.get("observed_at") or ""),
                )
                refreshed_count += 1
            else:
                register_session(
                    workspace=workspace,
                    session_id=session_id,
                    assignee=assignee,
                    transport_mode=str(candidate.get("transport_mode") or "manual"),
                    session_status=str(candidate.get("session_status") or "active"),
                    last_handoff_artifact=str(candidate.get("last_handoff_artifact") or ""),
                    observed_at=str(candidate.get("observed_at") or ""),
                )
                registered_count += 1
        synced.append(record)

    return {
        "generated_at": _now().isoformat(),
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "candidate_count": len(latest_by_assignee),
        "registered_count": registered_count,
        "refreshed_count": refreshed_count,
        "synced_sessions": synced,
        "sources": {
            "activation_log_count": len(activation),
            "hook_observation_count": len(hook_observations),
            "codex_runtime_count": len(codex_runtime),
        },
        "observation_file": str(_observation_file(workspace).relative_to(workspace)),
    }
