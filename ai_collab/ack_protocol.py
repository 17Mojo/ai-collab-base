"""Shared ACK protocol helpers for agent collaboration workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_ASSIGNEES = {"claude_code", "codearts_agent", "codex"}
DEFAULT_ACK_BRIDGE_STATE_PATH = "logs/agent_ack_bridge_state.json"
# 所有正式 assignee 都必须先给出显式 ACK，结果文件和 fallback bridge 不能代替。
EXPLICIT_ACK_REQUIRED_ASSIGNEES = set(SUPPORTED_ASSIGNEES)
EXPLICIT_ACK_SOURCE_PREFIXES = ("cli-ack", "chat-ack")

_ACK_PREFIX = {
    "claude_code": "C",
    "codearts_agent": "A",
    "codex": "X",
}

# Preserve existing bridge compatibility while allowing CLI emit to override.
_DEFAULT_ACK_STATUS = {
    "claude_code": "ok",
    "codearts_agent": "completed",
    "codex": "ok",
}


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    return payload if isinstance(payload, dict) else default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_assignee(task: dict[str, Any]) -> str:
    return str(task.get("assignee") or task.get("ai_type") or "").strip().lower()


def normalize_result_file(task_id: str, task: dict[str, Any]) -> str:
    raw = str(task.get("result_file") or "").strip()
    if raw:
        return raw
    return f"collaboration/results/RESULT_{task_id}.md"


def requires_explicit_ack(assignee: str) -> bool:
    normalized = str(assignee or "").strip().lower()
    return normalized in EXPLICIT_ACK_REQUIRED_ASSIGNEES


def is_explicit_ack_source(source: object) -> bool:
    normalized = str(source or "").strip().lower()
    return any(normalized.startswith(prefix) for prefix in EXPLICIT_ACK_SOURCE_PREFIXES)


def ack_prefix_for_assignee(assignee: str) -> str:
    normalized = str(assignee or "").strip().lower()
    return _ACK_PREFIX.get(normalized, "X")


def ack_status_for_assignee(assignee: str) -> str:
    normalized = str(assignee or "").strip().lower()
    return _DEFAULT_ACK_STATUS.get(normalized, "ok")


def build_ack_line(*, assignee: str, task_id: str, result_file: str, status: str | None = None) -> str:
    prefix = ack_prefix_for_assignee(assignee)
    resolved_status = str(status or ack_status_for_assignee(assignee)).strip()
    return f"{prefix}.ACK|task={task_id}|status={resolved_status}|result={result_file}"


def load_ack_bridge_state(
    workspace: Path,
    *,
    state_path: str = DEFAULT_ACK_BRIDGE_STATE_PATH,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    state_file = workspace / state_path
    payload = load_json(state_file, default={"version": "1.0.0", "items": {}})
    items = payload.get("items")
    if not isinstance(items, dict):
        items = {}
        payload["items"] = items
    return state_file, payload, items


def get_ack_bridge_item(items: dict[str, Any], task_id: str) -> dict[str, Any]:
    existing = items.get(task_id)
    return existing if isinstance(existing, dict) else {}


def _resolve_existing_bridge_audit(
    existing: dict[str, Any],
    *,
    source: str,
    bridged_at: str,
    preserve_existing_result_synced_from: bool,
) -> dict[str, Any]:
    """Carry forward or clear remediation metadata when explicit ACK arrives."""
    audit: dict[str, Any] = {}

    existing_result_synced_from = str(existing.get("result_synced_from") or "").strip()
    if preserve_existing_result_synced_from and existing_result_synced_from:
        audit["result_synced_from"] = existing_result_synced_from

    existing_source = str(existing.get("source") or "").strip()
    existing_remediation_status = str(existing.get("remediation_status") or "").strip()
    has_active_remediation = existing_remediation_status or existing.get("closeout_eligible") is False

    if is_explicit_ack_source(source):
        if has_active_remediation:
            audit["closeout_eligible"] = True
            audit["remediation_cleared_at"] = bridged_at
            audit["remediation_cleared_source"] = source
            if existing_source and existing_source != source:
                audit["remediation_previous_source"] = existing_source
            if existing_remediation_status:
                audit["remediation_previous_status"] = existing_remediation_status
        else:
            for field_name in (
                "closeout_eligible",
                "remediation_cleared_at",
                "remediation_cleared_source",
                "remediation_previous_source",
                "remediation_previous_status",
            ):
                if field_name in existing:
                    audit[field_name] = existing[field_name]

    return audit


def summarize_ack_bridge_items(items: dict[str, Any]) -> dict[str, int]:
    """Summarize ACK bridge records for observability/reporting."""
    summary = {
        "bridge_record_count": 0,
        "explicit_ack_count": 0,
        "non_explicit_ack_count": 0,
        "closeout_eligible_ack_count": 0,
        "claude_ack_count": 0,
        "claude_explicit_ack_count": 0,
        "claude_legacy_fallback_count": 0,
    }
    if not isinstance(items, dict):
        return summary

    for raw_item in items.values():
        if not isinstance(raw_item, dict):
            continue
        assignee = str(raw_item.get("assignee") or "").strip().lower()
        explicit = is_explicit_ack_source(raw_item.get("source"))

        summary["bridge_record_count"] += 1
        if explicit:
            summary["explicit_ack_count"] += 1
        else:
            summary["non_explicit_ack_count"] += 1

        if explicit or not requires_explicit_ack(assignee):
            summary["closeout_eligible_ack_count"] += 1

        if assignee == "claude_code":
            summary["claude_ack_count"] += 1
            if explicit:
                summary["claude_explicit_ack_count"] += 1
            else:
                summary["claude_legacy_fallback_count"] += 1

    return summary


def summarize_ack_bridge_state(
    workspace: Path,
    *,
    state_path: str = DEFAULT_ACK_BRIDGE_STATE_PATH,
) -> dict[str, int]:
    """Load and summarize ACK bridge state."""
    _, _, items = load_ack_bridge_state(workspace, state_path=state_path)
    return summarize_ack_bridge_items(items)


def has_ack_evidence(
    items: dict[str, Any],
    *,
    task_id: str,
    assignee: str,
    require_explicit: bool | None = None,
) -> bool:
    existing = get_ack_bridge_item(items, task_id)
    if not existing:
        return False

    if require_explicit is None:
        require_explicit = requires_explicit_ack(assignee)

    if not require_explicit:
        return True
    return is_explicit_ack_source(existing.get("source"))


def upsert_ack_bridge_item(
    items: dict[str, Any],
    *,
    task_id: str,
    assignee: str,
    result_file: str,
    completed_at: str,
    source: str,
    bridged_at: str,
    status: str | None = None,
    result_synced_from: str = "",
    increment_count: bool = True,
) -> dict[str, Any]:
    existing = get_ack_bridge_item(items, task_id)
    count = int(existing.get("bridge_count", 0)) + (1 if increment_count else 0)
    ack_line = build_ack_line(
        assignee=assignee,
        task_id=task_id,
        result_file=result_file,
        status=status,
    )
    existing_source = str(existing.get("source") or "").strip()
    resolved_source = source
    if is_explicit_ack_source(existing_source) and not is_explicit_ack_source(source):
        resolved_source = existing_source
    record = {
        "task_id": task_id,
        "assignee": assignee,
        "result_file": result_file,
        "ack_line": ack_line,
        "receipt_completed_at": completed_at,
        "bridged_at": bridged_at,
        "bridge_count": max(count, 1),
        "source": resolved_source,
    }
    if result_synced_from:
        record["result_synced_from"] = result_synced_from

    record.update(
        _resolve_existing_bridge_audit(
            existing,
            source=resolved_source,
            bridged_at=bridged_at,
            preserve_existing_result_synced_from=not bool(result_synced_from),
        )
    )
    items[task_id] = record
    return record


def record_ack_bridge(
    *,
    workspace: Path,
    task_id: str,
    assignee: str,
    result_file: str,
    completed_at: str,
    source: str,
    bridged_at: str,
    state_path: str = DEFAULT_ACK_BRIDGE_STATE_PATH,
    status: str | None = None,
    result_synced_from: str = "",
    increment_count: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    state_file, payload, items = load_ack_bridge_state(workspace, state_path=state_path)
    record = upsert_ack_bridge_item(
        items,
        task_id=task_id,
        assignee=assignee,
        result_file=result_file,
        completed_at=completed_at,
        source=source,
        bridged_at=bridged_at,
        status=status,
        result_synced_from=result_synced_from,
        increment_count=increment_count,
    )
    if not dry_run:
        write_json(state_file, payload)
    return record
