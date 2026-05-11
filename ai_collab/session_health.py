"""Session health aggregation and intervention artifact generation."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import SUPPORTED_ASSIGNEES, load_json, write_json
from .ack_watchdog import run_ack_watchdog
from .adapters.claude_adapter import run_claude_push_adapter
from .adapters.codearts_adapter import run_codearts_pull_adapter
from .adapters.codex_adapter import run_codex_native_adapter
from .dispatch_trigger import RUN_HINT, build_payload_refresh_command, check_payload_freshness
from .intervention_queue import (
    TERMINAL_DELIVERY_STATUSES,
    enqueue_intervention,
    inspect_interventions,
    resolve_intervention,
)
from .missing_ack_monitor import run_missing_ack_monitor
from .result_consistency_audit import run_terminal_result_consistency_audit
from .session_auto_register import run_session_auto_sync
from .session_registry import inspect_sessions, refresh_session

DEFAULT_REPORT_PATH = "logs/session_health_report.json"
DEFAULT_HISTORY_PATH = "logs/session_health_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/SESSION_HEALTH_SUMMARY_latest.md"
DEFAULT_ARTIFACT_DIR = "collaboration/monitoring/session_interventions"
DEFAULT_TASK_STATE_PATH = "logs/collaboration_state.json"
DEFAULT_DISPATCH_REPORT_PATH = "logs/task_dispatch_report.json"

GENERATED_AT_PATTERN = re.compile(r"^- GeneratedAt:\s*`(?P<generated_at>[^`]+)`\s*$")
TERMINAL_TASK_STATUSES = {"completed", "failed", "blocked", "cancelled"}

REASON_SEVERITY = {
    "stale_payload": "high",
    "ack_silence_after_run": "high",
    "missing_explicit_ack": "high",
    "missing_result_file": "high",
    "unparseable_result_header": "medium",
    "terminal_status_mismatch": "high",
    "unregistered_session": "medium",
}

HEALTH_MANAGED_SOURCE_SIGNALS = {
    "payload_freshness",
    "ack_watchdog",
    "missing_ack_monitor",
    "result_consistency_audit",
    "session_registry",
}


def _load_session_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    raw = payload.get("sessionOrchestration")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    artifact_dir: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    config = _load_session_config(workspace)
    resolved_report = workspace / str(
        config.get("healthReport", report_path or DEFAULT_REPORT_PATH)
    )
    resolved_history = workspace / str(
        config.get("healthHistory", history_path or DEFAULT_HISTORY_PATH)
    )
    resolved_summary = workspace / str(
        config.get("healthSummary", summary_path or DEFAULT_SUMMARY_PATH)
    )
    resolved_artifact_dir = workspace / str(
        config.get("interventionArtifactDir", artifact_dir or DEFAULT_ARTIFACT_DIR)
    )
    return resolved_report, resolved_history, resolved_summary, resolved_artifact_dir


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "session_count": payload.get("session_count", 0),
        "healthy_count": payload.get("healthy_count", 0),
        "unhealthy_count": payload.get("unhealthy_count", 0),
        "incident_count": payload.get("incident_count", 0),
        "intervention_count": payload.get("intervention_count", 0),
        "open_intervention_count": payload.get("open_intervention_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _load_project_state(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    config = load_json(config_file, default={})
    state_path = str(config.get("stateFile") or DEFAULT_TASK_STATE_PATH)
    return load_json(workspace / state_path, default={"tasks": {}})


def _slug(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip())
    return token.strip("-") or "unknown"


def _read_payload_generated_at(payload_file: Path) -> str:
    try:
        content = payload_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw_line in content.splitlines():
        match = GENERATED_AT_PATTERN.match(raw_line.strip())
        if match:
            return str(match.group("generated_at")).strip()
    return ""


def _parse_iso(value: object) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        return datetime.fromtimestamp(0)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.fromtimestamp(0)


def _select_latest_session(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in records:
        assignee = str(item.get("assignee") or "").strip().lower()
        if assignee not in SUPPORTED_ASSIGNEES:
            continue
        current = selected.get(assignee)
        if current is None or _parse_iso(
            item.get("updated_at") or item.get("last_seen_at")
        ) >= _parse_iso(current.get("updated_at") or current.get("last_seen_at")):
            selected[assignee] = item
    return selected


def _run_reset_hint(assignee: str) -> str:
    run_hint = RUN_HINT.get(assignee, "RUN")
    return run_hint.replace(".RUN", ".RUN-RESET") if ".RUN" in run_hint else f"{run_hint}-RESET"


def _session_context(
    *,
    assignee: str,
    sessions_by_assignee: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    record = sessions_by_assignee.get(assignee)
    if isinstance(record, dict):
        return {
            "session_id": str(record.get("session_id") or ""),
            "session_status": str(record.get("session_status") or "active"),
            "transport_mode": str(record.get("transport_mode") or "manual"),
            "registered": True,
        }
    return {
        "session_id": f"unregistered:{assignee}",
        "session_status": "unregistered",
        "transport_mode": "manual",
        "registered": False,
    }


def _merge_incident(
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
    *,
    assignee: str,
    reason_code: str,
    source_signal: str,
    summary: str,
    recommended_action: str,
    sessions_by_assignee: dict[str, dict[str, Any]],
    task_ids: list[str] | None = None,
    details: list[dict[str, Any]] | None = None,
) -> None:
    session = _session_context(assignee=assignee, sessions_by_assignee=sessions_by_assignee)
    key = (
        assignee,
        str(session.get("session_id") or ""),
        reason_code,
        source_signal,
    )
    incident = incidents.get(key)
    if incident is None:
        incident = {
            "assignee": assignee,
            "session_id": str(session.get("session_id") or ""),
            "session_status": str(session.get("session_status") or ""),
            "transport_mode": str(session.get("transport_mode") or "manual"),
            "health_status": "unhealthy" if session.get("registered") else "unregistered",
            "reason_code": reason_code,
            "severity": REASON_SEVERITY.get(reason_code, "medium"),
            "source_signal": source_signal,
            "summary": summary,
            "recommended_action": recommended_action,
            "task_ids": [],
            "details": [],
            "requires_operator_delivery": True,
        }
        incidents[key] = incident

    for task_id in task_ids or []:
        normalized = str(task_id or "").strip()
        if normalized and normalized not in incident["task_ids"]:
            incident["task_ids"].append(normalized)
    for detail in details or []:
        if detail not in incident["details"]:
            incident["details"].append(detail)


def _build_exact_message(incident: dict[str, Any]) -> str:
    assignee = str(incident.get("assignee") or "")
    reason_code = str(incident.get("reason_code") or "")
    task_ids = [str(item) for item in incident.get("task_ids", []) if str(item).strip()]
    details = list(incident.get("details", []) or [])

    if reason_code == "stale_payload":
        detail = details[0] if details else {}
        fix_command = str(detail.get("fix_command") or build_payload_refresh_command(assignee))
        handoff_artifact = str(detail.get("last_handoff_artifact") or "")
        lines = [
            f"检测到当前 payload 已过期或无法通过新鲜度校验（assignee={assignee}）。",
            f"请立即停止继续执行当前 payload，并执行以下修复命令重新生成最新 payload：{fix_command}",
            "重新生成后，请完整读取新 payload，再继续执行任务。",
        ]
        if handoff_artifact:
            lines.append(f"当前失效 payload: {handoff_artifact}")
        return "\n".join(lines)

    if reason_code == "ack_silence_after_run":
        lines = [
            f"检测到 `{assignee}` 在 RUN 后未按预期返回 ACK 或 receipt。",
            f"请先执行 `{_run_reset_hint(assignee)}`，再重新执行 `{RUN_HINT.get(assignee, 'RUN')}`。",
            "完成后不要手写 ACK，请使用任务块中的 `python3 -m ai_collab.cli ack ...` 生成并原样回复。",
        ]
        if task_ids:
            lines.append(f"涉及任务: {', '.join(task_ids)}")
        return "\n".join(lines)

    if reason_code == "missing_explicit_ack":
        lines = [
            f"检测到 `{assignee}` 已完成任务但缺失显式 ACK。",
            "请对以下任务逐个执行 ack 命令，并原样回复输出的单行 ACK：",
        ]
        for task_id in task_ids:
            lines.append(
                f"python3 -m ai_collab.cli ack --task-id {task_id} --ai {assignee} --status ok"
            )
        return "\n".join(lines)

    if reason_code == "missing_result_file":
        return f"检测到 `{assignee}` 的终态任务缺少结果文件。\n" "请先补齐 `result_file` 指向的结果产物，再继续收口。"

    if reason_code == "unparseable_result_header":
        return (
            f"检测到 `{assignee}` 的结果文件缺少可解析状态头。\n"
            "请在结果文件前 40 行内补齐类似 `**状态**: completed|blocked|failed|cancelled` 的状态行。"
        )

    if reason_code == "terminal_status_mismatch":
        return f"检测到 `{assignee}` 的控制面终态与结果文件状态头不一致。\n" "请修正结果文件中的顶层状态头，使其与控制面终态一致后再继续收口。"

    if reason_code == "unregistered_session":
        return f"控制面尚未登记 `{assignee}` 的活跃会话。\n" "请先注册或确认目标会话，再继续执行派发/纠偏动作；在此之前系统不会宣称可自动投递。"

    return str(incident.get("recommended_action") or "请根据控制面摘要执行纠偏。")


def _build_intervention_artifact_markdown(*, incident: dict[str, Any], artifact_path: Path) -> str:
    exact_message = _build_exact_message(incident)
    lines = [
        "# Session Intervention Artifact（自动生成）",
        "",
        f"- generated_at: `{datetime.now().isoformat()}`",
        f"- assignee: `{incident.get('assignee', '')}`",
        f"- session_id: `{incident.get('session_id', '')}`",
        f"- session_status: `{incident.get('session_status', '')}`",
        f"- reason_code: `{incident.get('reason_code', '')}`",
        f"- severity: `{incident.get('severity', '')}`",
        f"- source_signal: `{incident.get('source_signal', '')}`",
        f"- recommended_action: `{incident.get('recommended_action', '')}`",
        f"- requires_operator_delivery: `{incident.get('requires_operator_delivery', False)}`",
        f"- artifact_file: `{artifact_path}`",
        "",
        "## Summary",
        "",
        str(incident.get("summary") or ""),
        "",
        "## Exact Forward Message",
        "",
        "```text",
        exact_message,
        "```",
        "",
    ]
    if incident.get("task_ids"):
        lines.extend(["## Tasks", ""])
        for task_id in incident["task_ids"]:
            lines.append(f"- `{task_id}`")
        lines.append("")
    return "\n".join(lines)


def _artifact_path(artifact_dir: Path, incident: dict[str, Any]) -> Path:
    session_token = _slug(str(incident.get("session_id") or incident.get("assignee") or "session"))
    reason_token = _slug(str(incident.get("reason_code") or "incident"))
    return artifact_dir / f"SESSION_INTERVENTION_{session_token}_{reason_token}_latest.md"


def _upsert_intervention_for_incident(
    *,
    workspace: Path,
    incident: dict[str, Any],
    artifact_dir: Path,
    dry_run: bool,
    emit_interventions: bool,
) -> dict[str, Any]:
    artifact_file = _artifact_path(artifact_dir, incident)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_text(
        _build_intervention_artifact_markdown(incident=incident, artifact_path=artifact_file),
        encoding="utf-8",
    )
    artifact_relpath = str(artifact_file.relative_to(workspace))
    incident["message_artifact"] = artifact_relpath

    existing = inspect_interventions(
        workspace=workspace,
        session_id=str(incident.get("session_id") or ""),
        assignee=str(incident.get("assignee") or ""),
        reason_code=str(incident.get("reason_code") or ""),
        only_open=True,
    )
    if existing.get("interventions"):
        current = existing["interventions"][0]
        incident["intervention_id"] = str(current.get("intervention_id") or "")
        incident["delivery_mode"] = str(current.get("delivery_mode") or "manual")
        incident["delivery_status"] = str(
            current.get("delivery_status") or "pending_operator_delivery"
        )
        incident["intervention_action"] = "reused_open"
        return incident

    if dry_run or not emit_interventions:
        incident["delivery_mode"] = "manual"
        incident["delivery_status"] = "pending_operator_delivery"
        incident["intervention_action"] = "dry_run" if dry_run else "artifact_only"
        return incident

    record = enqueue_intervention(
        workspace=workspace,
        session_id=str(incident.get("session_id") or ""),
        assignee=str(incident.get("assignee") or ""),
        reason_code=str(incident.get("reason_code") or ""),
        severity=str(incident.get("severity") or "medium"),
        message_artifact=artifact_relpath,
        delivery_mode="manual",
        source_signal=str(incident.get("source_signal") or ""),
    )
    queued = record.get("intervention", {})
    incident["intervention_id"] = str(queued.get("intervention_id") or "")
    incident["delivery_mode"] = str(queued.get("delivery_mode") or "manual")
    incident["delivery_status"] = str(queued.get("delivery_status") or "pending_operator_delivery")
    incident["intervention_action"] = "queued"
    return incident


def _incident_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(item.get("session_id") or "").strip(),
        str(item.get("assignee") or "").strip().lower(),
        str(item.get("reason_code") or "").strip().lower(),
        str(item.get("source_signal") or "").strip().lower(),
    )


def _resolve_obsolete_health_interventions(
    *,
    workspace: Path,
    incidents: list[dict[str, Any]],
    dry_run: bool,
    emit_interventions: bool,
) -> list[dict[str, Any]]:
    if dry_run or not emit_interventions:
        return []

    active_keys = {_incident_key(item) for item in incidents}
    queue = inspect_interventions(workspace=workspace, only_open=True)
    resolved: list[dict[str, Any]] = []

    for item in list(queue.get("interventions", []) or []):
        source_signal = str(item.get("source_signal") or "").strip().lower()
        intervention_id = str(item.get("intervention_id") or "").strip()
        if not intervention_id or source_signal not in HEALTH_MANAGED_SOURCE_SIGNALS:
            continue
        if _incident_key(item) in active_keys:
            continue

        update = resolve_intervention(
            workspace=workspace,
            intervention_id=intervention_id,
        )
        resolved_item = dict(update.get("intervention") or {})
        resolved.append(
            {
                "intervention_id": intervention_id,
                "session_id": str(resolved_item.get("session_id") or item.get("session_id") or ""),
                "assignee": str(resolved_item.get("assignee") or item.get("assignee") or ""),
                "reason_code": str(
                    resolved_item.get("reason_code") or item.get("reason_code") or ""
                ),
                "source_signal": str(resolved_item.get("source_signal") or source_signal),
                "previous_delivery_status": str(item.get("delivery_status") or ""),
                "next_delivery_status": str(resolved_item.get("delivery_status") or "resolved"),
            }
        )

    return resolved


def _collect_payload_freshness_incidents(
    *,
    workspace: Path,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
) -> None:
    dispatch_report_file = workspace / DEFAULT_DISPATCH_REPORT_PATH
    for assignee, session in sessions_by_assignee.items():
        artifact_relpath = str(session.get("last_handoff_artifact") or "").strip()
        if not artifact_relpath:
            continue
        artifact_file = workspace / artifact_relpath
        payload_generated_at = _read_payload_generated_at(artifact_file)
        if not payload_generated_at:
            _merge_incident(
                incidents,
                assignee=assignee,
                reason_code="stale_payload",
                source_signal="payload_freshness",
                summary="最近一次 handoff artifact 缺少可解析的 GeneratedAt，无法证明 payload 仍然新鲜。",
                recommended_action=build_payload_refresh_command(assignee),
                sessions_by_assignee=sessions_by_assignee,
                details=[
                    {
                        "last_handoff_artifact": artifact_relpath,
                        "payload_generated_at": "",
                        "fix_command": build_payload_refresh_command(assignee),
                    }
                ],
            )
            continue

        freshness = check_payload_freshness(
            payload_generated_at=payload_generated_at,
            dispatch_report_path=dispatch_report_file,
            assignee=assignee,
            record_stats=False,
        )
        if freshness.get("is_fresh") is True:
            continue
        _merge_incident(
            incidents,
            assignee=assignee,
            reason_code="stale_payload",
            source_signal="payload_freshness",
            summary=str(freshness.get("warning") or "payload freshness 校验失败"),
            recommended_action=str(
                freshness.get("fix_command") or build_payload_refresh_command(assignee)
            ),
            sessions_by_assignee=sessions_by_assignee,
            details=[{**freshness, "last_handoff_artifact": artifact_relpath}],
        )


def _collect_ack_silence_incidents(
    *,
    workspace: Path,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    report = run_ack_watchdog(workspace=workspace, dry_run=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in report.get("candidate_tasks", []):
        assignee = str(item.get("assignee") or "").strip().lower()
        if assignee in SUPPORTED_ASSIGNEES:
            grouped[assignee].append(item)

    for assignee, entries in grouped.items():
        task_ids = [
            str(item.get("task_id") or "")
            for item in entries
            if str(item.get("task_id") or "").strip()
        ]
        threshold = entries[0].get("threshold_seconds", 0) if entries else 0
        _merge_incident(
            incidents,
            assignee=assignee,
            reason_code="ack_silence_after_run",
            source_signal="ack_watchdog",
            summary=f"检测到 {len(entries)} 个任务在 RUN 后超过 {threshold}s 仍无 ACK/receipt。",
            recommended_action=f"{_run_reset_hint(assignee)} -> {RUN_HINT.get(assignee, 'RUN')}",
            sessions_by_assignee=sessions_by_assignee,
            task_ids=task_ids,
            details=entries,
        )
    return report


def _collect_missing_ack_incidents(
    *,
    workspace: Path,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
    tasks_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    report = run_missing_ack_monitor(workspace=workspace, dry_run=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in report.get("stale_explicit_ack_tasks", []):
        task = tasks_by_id.get(str(item.get("task_id") or ""))
        if not isinstance(task, dict):
            continue
        assignee = str(task.get("assignee") or task.get("ai_type") or "").strip().lower()
        if assignee in SUPPORTED_ASSIGNEES:
            grouped[assignee].append(item)

    for assignee, entries in grouped.items():
        task_ids = [
            str(item.get("task_id") or "")
            for item in entries
            if str(item.get("task_id") or "").strip()
        ]
        _merge_incident(
            incidents,
            assignee=assignee,
            reason_code="missing_explicit_ack",
            source_signal="missing_ack_monitor",
            summary=f"检测到 {len(entries)} 个已完成任务仍缺失显式 ACK。",
            recommended_action="逐个执行 ai_collab.cli ack 并原样回复 ACK 行",
            sessions_by_assignee=sessions_by_assignee,
            task_ids=task_ids,
            details=entries,
        )
    return report


def _collect_result_consistency_incidents(
    *,
    workspace: Path,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    report = run_terminal_result_consistency_audit(workspace=workspace)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in report.get("issues", []):
        assignee = str(item.get("assignee") or item.get("ai_type") or "").strip().lower()
        reason_code = str(item.get("issue_type") or "").strip().lower()
        if assignee in SUPPORTED_ASSIGNEES and reason_code:
            grouped[(assignee, reason_code)].append(item)

    for (assignee, reason_code), entries in grouped.items():
        task_ids = [
            str(item.get("task_id") or "")
            for item in entries
            if str(item.get("task_id") or "").strip()
        ]
        _merge_incident(
            incidents,
            assignee=assignee,
            reason_code=reason_code,
            source_signal="result_consistency_audit",
            summary=f"检测到 {len(entries)} 个终态结果一致性问题（{reason_code}）。",
            recommended_action="修复结果文件和控制面终态的一致性后再收口",
            sessions_by_assignee=sessions_by_assignee,
            task_ids=task_ids,
            details=entries,
        )
    return report


def _collect_unregistered_session_incidents(
    *,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: dict[tuple[str, str, str, str], dict[str, Any]],
    tasks_by_id: dict[str, dict[str, Any]],
) -> None:
    active_assignees: set[str] = set()
    for task in tasks_by_id.values():
        if not isinstance(task, dict):
            continue
        assignee = str(task.get("assignee") or task.get("ai_type") or "").strip().lower()
        status = str(task.get("status") or "").strip().lower()
        if assignee in SUPPORTED_ASSIGNEES and status and status not in TERMINAL_TASK_STATUSES:
            active_assignees.add(assignee)

    for assignee in sorted(active_assignees):
        if assignee in sessions_by_assignee:
            continue
        _merge_incident(
            incidents,
            assignee=assignee,
            reason_code="unregistered_session",
            source_signal="session_registry",
            summary=f"检测到 `{assignee}` 仍有活跃任务，但控制面没有登记到对应会话。",
            recommended_action="先注册会话，再执行派发或纠偏动作",
            sessions_by_assignee=sessions_by_assignee,
        )


def _sync_registered_session_health(
    *,
    workspace: Path,
    sessions_by_assignee: dict[str, dict[str, Any]],
    incidents: list[dict[str, Any]],
    dry_run: bool,
) -> list[dict[str, str]]:
    unhealthy_sessions = {
        str(item.get("session_id") or "")
        for item in incidents
        if str(item.get("session_status") or "") != "unregistered"
    }
    updates: list[dict[str, str]] = []
    for assignee, session in sessions_by_assignee.items():
        session_id = str(session.get("session_id") or "")
        next_health = "unhealthy" if session_id in unhealthy_sessions else "healthy"
        if str(session.get("health_status") or "").strip().lower() == next_health:
            continue
        updates.append(
            {
                "session_id": session_id,
                "assignee": assignee,
                "previous_health_status": str(session.get("health_status") or ""),
                "next_health_status": next_health,
            }
        )
        if dry_run:
            continue
        refresh_session(
            workspace=workspace,
            session_id=session_id,
            health_status=next_health,
            touch_last_seen=False,
        )
    return updates


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Session Health Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 模式: `{report.get('mode', '')}`")
    lines.append(f"- session_count: `{report.get('session_count', 0)}`")
    lines.append(f"- healthy: `{report.get('healthy_count', 0)}`")
    lines.append(f"- unhealthy: `{report.get('unhealthy_count', 0)}`")
    lines.append(f"- unregistered: `{report.get('unregistered_count', 0)}`")
    lines.append(f"- incidents: `{report.get('incident_count', 0)}`")
    lines.append(f"- interventions: `{report.get('intervention_count', 0)}`")
    lines.append(f"- open_interventions: `{report.get('open_intervention_count', 0)}`")
    if report.get("adapter_reports", {}).get("claude_push_report"):
        lines.append(
            f"- claude_push_report: `{report.get('adapter_reports', {}).get('claude_push_report', '')}`"
        )
    if report.get("adapter_reports", {}).get("codearts_pull_report"):
        lines.append(
            f"- codearts_pull_report: `{report.get('adapter_reports', {}).get('codearts_pull_report', '')}`"
        )
    if report.get("adapter_reports", {}).get("codex_native_report"):
        lines.append(
            f"- codex_native_report: `{report.get('adapter_reports', {}).get('codex_native_report', '')}`"
        )
    lines.append("")

    lines.append("## Sessions")
    lines.append("")
    sessions: list[dict[str, Any]] = list(report.get("sessions", []) or [])
    if sessions:
        for item in sessions:
            lines.append(
                f"- `{item.get('session_id', '')}` assignee=`{item.get('assignee', '')}` "
                f"health=`{item.get('health_status', '')}` reasons=`{','.join(item.get('reason_codes', []))}`"
            )
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## Incidents")
    lines.append("")
    incidents: list[dict[str, Any]] = list(report.get("incidents", []) or [])
    if incidents:
        for item in incidents:
            lines.append(
                f"- assignee=`{item.get('assignee', '')}` session=`{item.get('session_id', '')}` "
                f"reason=`{item.get('reason_code', '')}` severity=`{item.get('severity', '')}`"
            )
            if item.get("message_artifact"):
                lines.append(f"  artifact: `{item.get('message_artifact', '')}`")
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_session_health_aggregation(
    *,
    workspace: Path,
    dry_run: bool = False,
    emit_interventions: bool = True,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    artifact_dir: str | None = None,
) -> dict[str, Any]:
    report_file, history_file, summary_file, artifact_root = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        summary_path=summary_path,
        artifact_dir=artifact_dir,
    )
    auto_sync_raw = run_session_auto_sync(workspace=workspace, dry_run=dry_run)
    auto_sync_report = {
        **auto_sync_raw,
        "results": list(auto_sync_raw.get("synced_sessions", []) or []),
        "skipped_count": max(
            int(auto_sync_raw.get("candidate_count", 0) or 0)
            - int(auto_sync_raw.get("registered_count", 0) or 0)
            - int(auto_sync_raw.get("refreshed_count", 0) or 0),
            0,
        ),
    }
    registry = inspect_sessions(workspace=workspace)
    session_records = list(registry.get("sessions", []) or [])
    sessions_by_assignee = _select_latest_session(session_records)
    project_state = _load_project_state(workspace)
    tasks_by_id = (
        project_state.get("tasks", {}) if isinstance(project_state.get("tasks"), dict) else {}
    )

    incidents: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    _collect_payload_freshness_incidents(
        workspace=workspace,
        sessions_by_assignee=sessions_by_assignee,
        incidents=incidents,
    )
    _collect_ack_silence_incidents(
        workspace=workspace,
        sessions_by_assignee=sessions_by_assignee,
        incidents=incidents,
    )
    _collect_missing_ack_incidents(
        workspace=workspace,
        sessions_by_assignee=sessions_by_assignee,
        incidents=incidents,
        tasks_by_id=tasks_by_id,
    )
    result_report = _collect_result_consistency_incidents(
        workspace=workspace,
        sessions_by_assignee=sessions_by_assignee,
        incidents=incidents,
    )
    _collect_unregistered_session_incidents(
        sessions_by_assignee=sessions_by_assignee,
        incidents=incidents,
        tasks_by_id=tasks_by_id,
    )

    incident_list = sorted(
        incidents.values(),
        key=lambda item: (
            str(item.get("assignee") or ""),
            str(item.get("session_id") or ""),
            str(item.get("reason_code") or ""),
        ),
    )
    for incident in incident_list:
        _upsert_intervention_for_incident(
            workspace=workspace,
            incident=incident,
            artifact_dir=artifact_root,
            dry_run=dry_run,
            emit_interventions=emit_interventions,
        )
    resolved_interventions = _resolve_obsolete_health_interventions(
        workspace=workspace,
        incidents=incident_list,
        dry_run=dry_run,
        emit_interventions=emit_interventions,
    )

    claude_adapter_report: dict[str, Any] = {}
    codearts_adapter_report: dict[str, Any] = {}
    codex_adapter_report: dict[str, Any] = {}
    if emit_interventions:
        claude_adapter_report = run_claude_push_adapter(
            workspace=workspace,
            dry_run=dry_run,
            allow_delivery=emit_interventions,
        )
        codearts_adapter_report = run_codearts_pull_adapter(
            workspace=workspace,
            dry_run=dry_run,
            allow_delivery=emit_interventions,
        )
    codex_adapter_report = run_codex_native_adapter(
        workspace=workspace,
        dry_run=dry_run,
        allow_registration=emit_interventions,
    )

    health_updates = _sync_registered_session_health(
        workspace=workspace,
        sessions_by_assignee=sessions_by_assignee,
        incidents=incident_list,
        dry_run=dry_run,
    )

    open_intervention_count = len(
        [
            item
            for item in incident_list
            if str(item.get("delivery_status") or "").strip().lower()
            not in TERMINAL_DELIVERY_STATUSES
        ]
    )
    healthy_count = len(
        [
            item
            for item in session_records
            if str(item.get("session_id") or "")
            not in {
                str(incident.get("session_id") or "")
                for incident in incident_list
                if str(incident.get("session_status") or "") != "unregistered"
            }
        ]
    )
    unhealthy_count = len(session_records) - healthy_count

    sessions_summary: list[dict[str, Any]] = []
    reasons_by_session: dict[str, list[str]] = defaultdict(list)
    for incident in incident_list:
        session_id = str(incident.get("session_id") or "")
        reason_code = str(incident.get("reason_code") or "")
        if reason_code and reason_code not in reasons_by_session[session_id]:
            reasons_by_session[session_id].append(reason_code)

    for session in session_records:
        session_id = str(session.get("session_id") or "")
        health_status = "unhealthy" if session_id in reasons_by_session else "healthy"
        sessions_summary.append(
            {
                "session_id": session_id,
                "assignee": str(session.get("assignee") or ""),
                "session_status": str(session.get("session_status") or ""),
                "transport_mode": str(session.get("transport_mode") or ""),
                "health_status": health_status,
                "reason_codes": sorted(reasons_by_session.get(session_id, [])),
            }
        )

    for incident in incident_list:
        if str(incident.get("session_status") or "") != "unregistered":
            continue
        sessions_summary.append(
            {
                "session_id": str(incident.get("session_id") or ""),
                "assignee": str(incident.get("assignee") or ""),
                "session_status": "unregistered",
                "transport_mode": "manual",
                "health_status": "unregistered",
                "reason_codes": [str(incident.get("reason_code") or "")],
            }
        )

    unregistered_count = len(
        [
            item
            for item in sessions_summary
            if str(item.get("session_status") or "") == "unregistered"
        ]
    )
    report = {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "session_count": len(sessions_summary),
        "healthy_count": healthy_count,
        "unhealthy_count": unhealthy_count,
        "unregistered_count": unregistered_count,
        "incident_count": len(incident_list),
        "intervention_count": len(incident_list),
        "open_intervention_count": open_intervention_count,
        "sessions": sessions_summary,
        "incidents": incident_list,
        "resolved_interventions": resolved_interventions,
        "health_updates": health_updates,
        "auto_sync": auto_sync_report,
        "adapter_reports": {
            "claude_push_report": str(claude_adapter_report.get("report_file") or ""),
            "codearts_pull_report": str(codearts_adapter_report.get("report_file") or ""),
            "codex_native_report": str(codex_adapter_report.get("report_file") or ""),
        },
        "signal_reports": {
            "ack_watchdog_report": "logs/ack_watchdog_report.json",
            "missing_ack_report": "logs/missing_ack_report.json",
            "result_consistency_report": str(result_report.get("report_file") or ""),
        },
    }

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = str(summary_file.relative_to(workspace))
    report["report_file"] = str(report_file.relative_to(workspace))
    write_json(report_file, report)
    _append_history(history_file, report)
    return report
