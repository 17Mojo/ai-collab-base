"""Session intervention queue primitives with state/history/summary outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ack_protocol import SUPPORTED_ASSIGNEES, load_json, write_json

DEFAULT_STATE_PATH = "logs/session_intervention_state.json"
DEFAULT_HISTORY_PATH = "logs/session_intervention_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md"
DEFAULT_PACK_DIR = "collaboration/monitoring/intervention_packs"

DEFAULT_DELIVERY_MODE = "manual"
DEFAULT_MANUAL_DELIVERY_STATUS = "pending_operator_delivery"
DEFAULT_BRIDGE_DELIVERY_STATUS = "queued_for_delivery"

SUPPORTED_DELIVERY_MODES = {"manual", "bridge"}
TERMINAL_DELIVERY_STATUSES = {"delivered", "resolved", "cancelled"}


@dataclass
class InterventionRecord:
    intervention_id: str
    session_id: str
    assignee: str
    reason_code: str
    severity: str
    message_artifact: str
    delivery_mode: str
    delivery_status: str
    created_at: str
    updated_at: str
    resolved_at: str
    source_signal: str


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_assignee(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_delivery_mode(value: object) -> str:
    mode = str(value or "").strip().lower()
    if not mode:
        mode = DEFAULT_DELIVERY_MODE
    if mode not in SUPPORTED_DELIVERY_MODES:
        raise ValueError(f"unsupported delivery_mode: {mode}")
    return mode


def _default_delivery_status_for_mode(delivery_mode: str) -> str:
    return (
        DEFAULT_MANUAL_DELIVERY_STATUS
        if delivery_mode == "manual"
        else DEFAULT_BRIDGE_DELIVERY_STATUS
    )


def _ensure_payload_shape(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if not isinstance(items, dict):
        payload["items"] = {}
    if not isinstance(payload.get("version"), str):
        payload["version"] = "1.0.0"
    return payload


def _load_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
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
    resolved_state = workspace / str(config.get("interventionState", state_path or DEFAULT_STATE_PATH))
    resolved_history = workspace / str(config.get("interventionHistory", history_path or DEFAULT_HISTORY_PATH))
    resolved_summary = workspace / str(config.get("interventionSummary", summary_path or DEFAULT_SUMMARY_PATH))
    return resolved_state, resolved_history, resolved_summary


def _resolve_pack_dir(*, workspace: Path, pack_dir: str | None = None) -> Path:
    config = _load_config(workspace)
    return workspace / str(config.get("interventionPackDir", pack_dir or DEFAULT_PACK_DIR))


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _sort_interventions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("intervention_id") or ""),
        ),
    )


def _slug(value: object) -> str:
    token = "".join(ch if str(ch).isalnum() or ch in {"-", "_", "."} else "-" for ch in str(value or "").strip())
    token = token.strip("-")
    return token or "unknown"


def _load_exact_forward_message(workspace: Path, artifact_relpath: str) -> str:
    artifact_file = workspace / artifact_relpath
    try:
        text = artifact_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    marker = "## Exact Forward Message"
    if marker not in text:
        return text.strip()
    _, tail = text.split(marker, 1)
    if "```text" not in tail:
        return tail.strip()
    _, block = tail.split("```text", 1)
    message, _, _ = block.partition("```")
    return message.strip()


def load_intervention_state(
    workspace: Path,
    *,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    state_file, _, _ = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    payload = load_json(state_file, {"version": "1.0.0", "items": {}})
    payload = _ensure_payload_shape(payload)
    items = payload.get("items", {})
    return state_file, payload, items


def read_intervention_items(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> list[dict[str, Any]]:
    """Read interventions from state and return a stable sorted list."""
    _, _, items = load_intervention_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    return _sort_interventions(
        [item for item in items.values() if isinstance(item, dict)]
    )


def inspect_interventions(
    *,
    workspace: Path,
    session_id: str | None = None,
    assignee: str | None = None,
    reason_code: str | None = None,
    delivery_status: str | None = None,
    only_open: bool = False,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    """Inspect interventions with stable filtering and summary counts."""
    records = read_intervention_items(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )

    normalized_session_id = str(session_id or "").strip()
    normalized_assignee = str(assignee or "").strip().lower()
    normalized_reason_code = str(reason_code or "").strip().lower()
    normalized_delivery_status = str(delivery_status or "").strip().lower()

    if normalized_session_id:
        records = [
            item
            for item in records
            if str(item.get("session_id") or "").strip() == normalized_session_id
        ]
    if normalized_assignee:
        records = [
            item
            for item in records
            if str(item.get("assignee") or "").strip().lower() == normalized_assignee
        ]
    if normalized_reason_code:
        records = [
            item
            for item in records
            if str(item.get("reason_code") or "").strip().lower() == normalized_reason_code
        ]
    if normalized_delivery_status:
        records = [
            item
            for item in records
            if str(item.get("delivery_status") or "").strip().lower() == normalized_delivery_status
        ]
    if only_open:
        records = [
            item
            for item in records
            if str(item.get("delivery_status") or "").strip().lower()
            not in TERMINAL_DELIVERY_STATUSES
        ]

    stats = summarize_intervention_items(
        {item["intervention_id"]: item for item in records if item.get("intervention_id")}
    )
    return {
        "generated_at": _now_iso(),
        "workspace": str(workspace),
        "intervention_count": len(records),
        **stats,
        "interventions": records,
    }


def summarize_intervention_items(items: dict[str, Any]) -> dict[str, int]:
    summary = {
        "total_count": 0,
        "manual_count": 0,
        "bridge_count": 0,
        "pending_operator_delivery_count": 0,
        "queued_for_delivery_count": 0,
        "delivered_count": 0,
        "failed_count": 0,
        "resolved_count": 0,
        "open_count": 0,
    }
    if not isinstance(items, dict):
        return summary

    for raw_item in items.values():
        if not isinstance(raw_item, dict):
            continue
        mode = str(raw_item.get("delivery_mode") or "").strip().lower()
        status = str(raw_item.get("delivery_status") or "").strip().lower()

        summary["total_count"] += 1
        if mode == "manual":
            summary["manual_count"] += 1
        elif mode == "bridge":
            summary["bridge_count"] += 1

        if status == DEFAULT_MANUAL_DELIVERY_STATUS:
            summary["pending_operator_delivery_count"] += 1
        elif status == DEFAULT_BRIDGE_DELIVERY_STATUS:
            summary["queued_for_delivery_count"] += 1
        elif status == "delivered":
            summary["delivered_count"] += 1
        elif status == "failed":
            summary["failed_count"] += 1
        elif status == "resolved":
            summary["resolved_count"] += 1

        if status not in TERMINAL_DELIVERY_STATUSES:
            summary["open_count"] += 1

    return summary


def build_summary_markdown(*, report: dict[str, Any], items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Session Intervention Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 工作区: `{report.get('workspace', '')}`")
    lines.append(f"- 模式: `{report.get('mode', '')}`")
    lines.append(f"- intervention 总数: `{report.get('total_count', 0)}`")
    lines.append(f"- open: `{report.get('open_count', 0)}`")
    lines.append(f"- manual: `{report.get('manual_count', 0)}`")
    lines.append(f"- bridge: `{report.get('bridge_count', 0)}`")
    lines.append(
        "- pending_operator_delivery: "
        f"`{report.get('pending_operator_delivery_count', 0)}`"
    )
    lines.append(
        f"- queued_for_delivery: `{report.get('queued_for_delivery_count', 0)}`"
    )
    lines.append(f"- delivered: `{report.get('delivered_count', 0)}`")
    lines.append(f"- failed: `{report.get('failed_count', 0)}`")
    lines.append(f"- resolved: `{report.get('resolved_count', 0)}`")
    lines.append("")

    lines.append("## Pending Operator Delivery")
    lines.append("")
    pending_items = [
        item
        for item in items
        if str(item.get("delivery_status") or "").strip().lower()
        == DEFAULT_MANUAL_DELIVERY_STATUS
    ]
    if not pending_items:
        lines.append("- 无")
    else:
        for item in pending_items:
            lines.append(
                f"- `{item.get('intervention_id', '')}` "
                f"assignee=`{item.get('assignee', '')}` "
                f"session=`{item.get('session_id', '')}` "
                f"reason=`{item.get('reason_code', '')}`"
            )
            lines.append(f"  artifact: `{item.get('message_artifact', '')}`")
    lines.append("")

    lines.append("## Recent Interventions")
    lines.append("")
    if not items:
        lines.append("- 无")
    else:
        recent_items = sorted(
            items,
            key=lambda item: (
                str(item.get("updated_at") or ""),
                str(item.get("intervention_id") or ""),
            ),
            reverse=True,
        )[:10]
        for item in recent_items:
            lines.append(
                f"- `{item.get('intervention_id', '')}` "
                f"status=`{item.get('delivery_status', '')}` "
                f"mode=`{item.get('delivery_mode', '')}` "
                f"assignee=`{item.get('assignee', '')}`"
            )
    lines.append("")
    return "\n".join(lines)


def _build_summary_payload(
    *,
    workspace: Path,
    payload: dict[str, Any],
    mode: str,
    summary_file: Path,
) -> dict[str, Any]:
    items_dict = payload.get("items", {})
    interventions = _sort_interventions(
        [
            item
            for item in items_dict.values()
            if isinstance(item, dict)
        ]
    )
    stats = summarize_intervention_items(items_dict)
    report = {
        "generated_at": _now_iso(),
        "workspace": str(workspace),
        "mode": mode,
        **stats,
        "interventions": interventions,
    }

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        build_summary_markdown(report=report, items=interventions),
        encoding="utf-8",
    )
    report["summary_file"] = str(summary_file.relative_to(workspace))
    return report


def enqueue_intervention(
    *,
    workspace: Path,
    session_id: str,
    assignee: str,
    reason_code: str,
    severity: str,
    message_artifact: str,
    delivery_mode: str = DEFAULT_DELIVERY_MODE,
    delivery_status: str | None = None,
    intervention_id: str | None = None,
    created_at: str | None = None,
    source_signal: str = "",
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    normalized_assignee = _normalize_assignee(assignee)
    if normalized_assignee not in SUPPORTED_ASSIGNEES:
        raise ValueError(f"unsupported assignee: {normalized_assignee or '<empty>'}")

    normalized_mode = _normalize_delivery_mode(delivery_mode)
    resolved_status = str(delivery_status or "").strip().lower()
    if not resolved_status:
        resolved_status = _default_delivery_status_for_mode(normalized_mode)

    timestamp = str(created_at or _now_iso())
    resolved_intervention_id = str(intervention_id or f"intervention-{uuid4().hex}")
    record = InterventionRecord(
        intervention_id=resolved_intervention_id,
        session_id=str(session_id).strip(),
        assignee=normalized_assignee,
        reason_code=str(reason_code).strip(),
        severity=str(severity).strip().lower(),
        message_artifact=str(message_artifact).strip(),
        delivery_mode=normalized_mode,
        delivery_status=resolved_status,
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=timestamp if resolved_status in TERMINAL_DELIVERY_STATUSES else "",
        source_signal=str(source_signal).strip(),
    )

    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    _, payload, items = load_intervention_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    items[resolved_intervention_id] = asdict(record)
    payload["generated_at"] = _now_iso()
    write_json(state_file, payload)

    history_entry = {
        "generated_at": _now_iso(),
        "event": "queued",
        "intervention_id": resolved_intervention_id,
        "assignee": normalized_assignee,
        "delivery_mode": normalized_mode,
        "delivery_status": resolved_status,
        "reason_code": record.reason_code,
        "session_id": record.session_id,
    }
    _append_history(history_file, history_entry)

    report = _build_summary_payload(
        workspace=workspace,
        payload=payload,
        mode="queue",
        summary_file=summary_file,
    )
    report["intervention"] = asdict(record)
    report["state_file"] = str(state_file.relative_to(workspace))
    return report


def ack_intervention(
    *,
    workspace: Path,
    intervention_id: str,
    delivery_status: str = "delivered",
    delivery_mode: str | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    target_id = str(intervention_id).strip()
    if not target_id:
        raise ValueError("intervention_id is required")
    next_status = str(delivery_status or "").strip().lower()
    if not next_status:
        raise ValueError("delivery_status is required")

    state_file, history_file, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    _, payload, items = load_intervention_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    existing = items.get(target_id)
    if not isinstance(existing, dict):
        raise KeyError(f"intervention not found: {target_id}")

    if delivery_mode is not None:
        existing["delivery_mode"] = _normalize_delivery_mode(delivery_mode)
    existing["delivery_status"] = next_status
    existing["updated_at"] = _now_iso()
    if next_status in TERMINAL_DELIVERY_STATUSES:
        existing["resolved_at"] = _now_iso()
    elif not str(existing.get("resolved_at") or "").strip():
        existing["resolved_at"] = ""

    payload["generated_at"] = _now_iso()
    write_json(state_file, payload)

    history_entry = {
        "generated_at": _now_iso(),
        "event": "delivery_status_updated",
        "intervention_id": target_id,
        "assignee": str(existing.get("assignee") or ""),
        "delivery_mode": str(existing.get("delivery_mode") or ""),
        "delivery_status": next_status,
    }
    _append_history(history_file, history_entry)

    report = _build_summary_payload(
        workspace=workspace,
        payload=payload,
        mode="ack",
        summary_file=summary_file,
    )
    report["intervention"] = existing
    report["state_file"] = str(state_file.relative_to(workspace))
    return report


def resolve_intervention(
    *,
    workspace: Path,
    intervention_id: str,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    """Mark an intervention as resolved and persist summary outputs."""
    return ack_intervention(
        workspace=workspace,
        intervention_id=intervention_id,
        delivery_status="resolved",
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )


def render_intervention_summary_markdown(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> str:
    """Render and persist summary markdown from current intervention state."""
    _, _, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    _, payload, _ = load_intervention_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    report = _build_summary_payload(
        workspace=workspace,
        payload=payload,
        mode="summary",
        summary_file=summary_file,
    )
    return (workspace / report["summary_file"]).read_text(encoding="utf-8")


def run_intervention_queue_summary(
    *,
    workspace: Path,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    _, _, summary_file = _resolve_paths(
        workspace=workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    _, payload, _ = load_intervention_state(
        workspace,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    return _build_summary_payload(
        workspace=workspace,
        payload=payload,
        mode="summary",
        summary_file=summary_file,
    )


def build_intervention_pack_markdown(
    *,
    workspace: Path,
    assignee: str,
    interventions: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Session Intervention Pack（自动生成）")
    lines.append("")
    lines.append(f"- generated_at: `{_now_iso()}`")
    lines.append(f"- assignee: `{assignee}`")
    lines.append(f"- intervention_count: `{len(interventions)}`")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append("复制下面每条 intervention 的 Exact Forward Message 到目标会话，完成后等待对方返回正式 ACK。")
    lines.append("")
    lines.append("## Items")
    lines.append("")
    if not interventions:
        lines.append("- 无 open interventions")
        lines.append("")
        return "\n".join(lines)

    for index, item in enumerate(interventions, start=1):
        artifact = str(item.get("message_artifact") or "")
        exact_message = _load_exact_forward_message(workspace, artifact)
        lines.append(f"### {index}. `{item.get('intervention_id', '')}`")
        lines.append("")
        lines.append(f"- session_id: `{item.get('session_id', '')}`")
        lines.append(f"- reason_code: `{item.get('reason_code', '')}`")
        lines.append(f"- delivery_status: `{item.get('delivery_status', '')}`")
        lines.append(f"- artifact: `{artifact}`")
        lines.append("")
        lines.append("#### Exact Forward Message")
        lines.append("")
        lines.append("```text")
        lines.append(exact_message)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def render_intervention_pack(
    *,
    workspace: Path,
    assignee: str,
    only_open: bool = True,
    pack_dir: str | None = None,
    state_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
) -> dict[str, Any]:
    normalized_assignee = _normalize_assignee(assignee)
    if normalized_assignee not in SUPPORTED_ASSIGNEES:
        raise ValueError(f"unsupported assignee: {normalized_assignee or '<empty>'}")

    report = inspect_interventions(
        workspace=workspace,
        assignee=normalized_assignee,
        only_open=only_open,
        state_path=state_path,
        history_path=history_path,
        summary_path=summary_path,
    )
    interventions = list(report.get("interventions", []) or [])
    pack_root = _resolve_pack_dir(workspace=workspace, pack_dir=pack_dir)
    pack_file = pack_root / f"SESSION_INTERVENTION_PACK_{_slug(normalized_assignee)}_latest.md"
    pack_file.parent.mkdir(parents=True, exist_ok=True)
    markdown = build_intervention_pack_markdown(
        workspace=workspace,
        assignee=normalized_assignee,
        interventions=interventions,
    )
    pack_file.write_text(markdown, encoding="utf-8")
    return {
        "generated_at": _now_iso(),
        "workspace": str(workspace),
        "assignee": normalized_assignee,
        "only_open": only_open,
        "intervention_count": len(interventions),
        "pack_file": str(pack_file.relative_to(workspace)),
    }


# Backward-compatible aliases while the rest of the codebase migrates.
queue_intervention = enqueue_intervention
update_intervention_delivery = ack_intervention
