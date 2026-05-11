"""Guardrails for Codex internal spawn_agent delegation."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .state_manager import TaskStatus

DEFAULT_SPAWN_AGENT_GUARD = {
    "enabled": True,
    "allowedLeadAgents": ["codex"],
    "requireParentTask": True,
    "requireWriteSet": True,
    "allowReadOnly": True,
    "protectedPaths": [
        ".vscode/ai-collab.json",
        "logs/collaboration_state.json",
        "logs/agent_dispatch_state.json",
        "logs/agent_receipt_state.json",
    ],
    "protectedPrefixes": [
        "collaboration/tasks/",
        "collaboration/monitoring/AGENT_TRIGGER_",
    ],
    "report": "logs/workspace_forensics/spawn_agent_guard_latest.json",
    "history": "logs/workspace_forensics/spawn_agent_guard_history.jsonl",
}

CONFLICT_STATUSES = {
    TaskStatus.PLANNING.value,
    TaskStatus.IMPLEMENTING.value,
    TaskStatus.TESTING.value,
}

INTERNAL_READ_ONLY_PARENT_PREFIXES = ("INTERNAL-CODEX-",)


def _normalize_actor(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_workspace_path(workspace: Path, raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""

    candidate = Path(text)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(workspace.resolve())
        except ValueError:
            return candidate.as_posix()
    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _normalize_prefix(workspace: Path, raw: Any) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return ""

    keep_trailing_slash = text.endswith("/")
    normalized = _normalize_workspace_path(workspace, text)
    if keep_trailing_slash and normalized and not normalized.endswith("/"):
        normalized += "/"
    return normalized


def _normalize_files(workspace: Path, files: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in files or []:
        path = _normalize_workspace_path(workspace, item)
        if not path or path in seen:
            continue
        seen.add(path)
        normalized.append(path)
    return normalized


def _is_internal_read_only_parent(*, actor: str, parent_task: str, read_only: bool) -> bool:
    if not read_only:
        return False
    if actor != "codex":
        return False
    normalized_parent = str(parent_task or "").strip().upper()
    return any(
        normalized_parent.startswith(prefix) for prefix in INTERNAL_READ_ONLY_PARENT_PREFIXES
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _load_state(workspace: Path, state_rel: str) -> tuple[dict[str, Any], str | None]:
    state_path = workspace / state_rel
    if not state_path.exists():
        return {}, None

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"failed to parse collaboration state: {exc}"

    return payload if isinstance(payload, dict) else {}, None


def resolve_spawn_agent_guard_config(
    config: dict[str, Any] | None, *, workspace: Path
) -> dict[str, Any]:
    resolved = deepcopy(DEFAULT_SPAWN_AGENT_GUARD)
    raw = {}
    if isinstance(config, dict) and isinstance(config.get("spawnAgentGuard"), dict):
        raw = dict(config["spawnAgentGuard"])

    for key in ("enabled", "requireParentTask", "requireWriteSet", "allowReadOnly"):
        if key in raw:
            resolved[key] = bool(raw[key])

    for key in ("report", "history"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            resolved[key] = value.strip()

    for key in ("allowedLeadAgents", "protectedPaths", "protectedPrefixes"):
        value = raw.get(key)
        if isinstance(value, list):
            resolved[key] = [str(item) for item in value if str(item).strip()]

    resolved["allowedLeadAgents"] = [
        _normalize_actor(item) for item in resolved["allowedLeadAgents"] if _normalize_actor(item)
    ]
    resolved["protectedPaths"] = [
        _normalize_workspace_path(workspace, item)
        for item in resolved["protectedPaths"]
        if _normalize_workspace_path(workspace, item)
    ]
    resolved["protectedPrefixes"] = [
        _normalize_prefix(workspace, item)
        for item in resolved["protectedPrefixes"]
        if _normalize_prefix(workspace, item)
    ]
    return resolved


def run_spawn_agent_guard(
    *,
    workspace: Path,
    actor: str,
    parent_task_id: str | None,
    files: list[str] | None,
    read_only: bool,
    metadata: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    guard_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    effective_config = dict(config or {})
    if isinstance(guard_config, dict):
        effective_config["spawnAgentGuard"] = dict(guard_config)
    resolved = resolve_spawn_agent_guard_config(effective_config, workspace=workspace)

    actor_normalized = _normalize_actor(actor)
    parent_task = str(parent_task_id or "").strip()
    declared_files = _normalize_files(workspace, files)
    mode = "read-only" if read_only else "write"
    internal_read_only_parent = _is_internal_read_only_parent(
        actor=actor_normalized,
        parent_task=parent_task,
        read_only=read_only,
    )

    violations: list[str] = []
    warnings: list[str] = []
    protected_hits: list[str] = []
    protected_prefix_hits: list[str] = []
    active_conflicts: list[dict[str, Any]] = []

    if not resolved["enabled"]:
        warnings.append("spawn agent guard disabled by config")
    else:
        if actor_normalized not in set(resolved["allowedLeadAgents"]):
            violations.append(
                f"actor '{actor_normalized or 'unknown'}' is not allowed for spawn_agent delegation"
            )

        if resolved["requireParentTask"] and not parent_task:
            violations.append("parent_task_id is required for spawn_agent delegation")

        if read_only:
            if not resolved["allowReadOnly"]:
                violations.append("read-only spawn_agent delegation is disabled by policy")
        else:
            if resolved["requireWriteSet"] and not declared_files:
                violations.append("write delegation requires a non-empty declared file set")

            for path in declared_files:
                if path in set(resolved["protectedPaths"]):
                    protected_hits.append(path)
                if any(
                    prefix and path.startswith(prefix) for prefix in resolved["protectedPrefixes"]
                ):
                    protected_prefix_hits.append(path)

            if protected_hits:
                violations.append(
                    "declared files include protected paths: "
                    + ", ".join(sorted(set(protected_hits)))
                )
            if protected_prefix_hits:
                violations.append(
                    "declared files include protected path prefixes: "
                    + ", ".join(sorted(set(protected_prefix_hits)))
                )

        state_rel = str(effective_config.get("stateFile", "./logs/collaboration_state.json"))
        state_payload, state_error = _load_state(workspace, state_rel)
        if state_error:
            violations.append(state_error)
        else:
            tasks = state_payload.get("tasks", {})
            if isinstance(tasks, dict):
                if parent_task and parent_task not in tasks and not internal_read_only_parent:
                    warnings.append(
                        f"parent_task_id '{parent_task}' not found in collaboration state"
                    )

                if not read_only and declared_files:
                    declared_set = set(declared_files)
                    for task_id, raw_task in tasks.items():
                        if str(task_id) == parent_task:
                            continue
                        task = raw_task if isinstance(raw_task, dict) else {}
                        status = str(task.get("status", "")).strip().lower()
                        if status not in CONFLICT_STATUSES:
                            continue

                        task_files = _normalize_files(workspace, task.get("files"))
                        overlapping = sorted(declared_set & set(task_files))
                        if not overlapping:
                            continue

                        active_conflicts.append(
                            {
                                "task_id": str(task_id),
                                "ai_type": str(task.get("ai_type", "unknown")),
                                "status": status,
                                "overlapping_files": overlapping,
                            }
                        )

                    if active_conflicts:
                        summaries = [
                            f"{item['task_id']} ({', '.join(item['overlapping_files'])})"
                            for item in active_conflicts
                        ]
                        violations.append(
                            "declared files overlap active task write sets: " + "; ".join(summaries)
                        )

    allowed = not violations
    timestamp = datetime.now().isoformat()
    report_rel = str(resolved["report"])
    history_rel = str(resolved["history"])

    report = {
        "timestamp": timestamp,
        "actor": actor_normalized,
        "mode": mode,
        "parent_task_id": parent_task or None,
        "parent_task_source": "internal-read-only" if internal_read_only_parent else "state-or-cli",
        "files": declared_files,
        "allowed": allowed,
        "violations": violations,
        "warnings": warnings,
        "protected_hits": sorted(set(protected_hits + protected_prefix_hits)),
        "active_conflicts": active_conflicts,
        "report_file": report_rel,
        "history_file": history_rel,
    }
    if isinstance(metadata, dict) and metadata:
        report["metadata"] = deepcopy(metadata)

    _write_json(workspace / report_rel, report)
    _append_jsonl(workspace / history_rel, report)
    return report
