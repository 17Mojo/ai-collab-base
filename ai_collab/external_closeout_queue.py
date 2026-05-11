"""External closeout queue generation for operator-facing session control."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import load_json, write_json
from .intervention_queue import DEFAULT_PACK_DIR, inspect_interventions

DEFAULT_REPORT_PATH = "logs/external_closeout_queue_report.json"
DEFAULT_HISTORY_PATH = "logs/external_closeout_queue_history.jsonl"
DEFAULT_OUTPUT_TEMPLATE = "collaboration/monitoring/EXTERNAL_CLOSEOUT_QUEUE_{date}_latest.md"
DEFAULT_TASK_STATE_PATH = "logs/collaboration_state.json"
EXTERNAL_ASSIGNEES = ("claude_code", "codearts_agent")

_NOTE_PREFIX_PATTERN = re.compile(r"^\[[^\]]+\]\s*")


def _load_session_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    raw = payload.get("sessionOrchestration")
    return raw if isinstance(raw, dict) else {}


def _load_project_state(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    config = load_json(config_file, default={})
    state_path = str(config.get("stateFile") or DEFAULT_TASK_STATE_PATH)
    return load_json(workspace / state_path, default={"tasks": {}, "active_tasks": []})


def _relative_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    output_path: str | None = None,
) -> tuple[Path, Path, Path]:
    config = _load_session_config(workspace)
    generated_at = datetime.now()
    default_output = DEFAULT_OUTPUT_TEMPLATE.format(date=generated_at.date().isoformat())
    resolved_report = workspace / str(config.get("externalCloseoutQueueReport", report_path or DEFAULT_REPORT_PATH))
    resolved_history = workspace / str(config.get("externalCloseoutQueueHistory", history_path or DEFAULT_HISTORY_PATH))
    resolved_output = workspace / str(config.get("externalCloseoutQueueOutput", output_path or default_output))
    return resolved_report, resolved_history, resolved_output


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at", ""),
        "output_file": payload.get("output_file", ""),
        "active_task_count": payload.get("active_task_count", 0),
        "open_intervention_count": payload.get("open_intervention_count", 0),
        "blocking_intervention_count": payload.get("blocking_intervention_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _pack_file_for_assignee(*, workspace: Path, assignee: str) -> str:
    config = _load_session_config(workspace)
    pack_dir = workspace / str(config.get("interventionPackDir", DEFAULT_PACK_DIR))
    pack_file = pack_dir / f"SESSION_INTERVENTION_PACK_{assignee}_latest.md"
    return _relative_path(pack_file, workspace) if pack_file.exists() else ""


def _strip_note_prefix(note: object) -> str:
    normalized = str(note or "").strip()
    if not normalized:
        return ""
    return _NOTE_PREFIX_PATTERN.sub("", normalized).strip()


def _latest_note(task: dict[str, Any]) -> str:
    notes = task.get("notes")
    if not isinstance(notes, list) or not notes:
        return ""
    for item in reversed(notes):
        normalized = _strip_note_prefix(item)
        if normalized:
            return normalized
    return ""


def _action_hint(
    *,
    task: dict[str, Any],
    pack_by_assignee: dict[str, str],
    blockers_by_assignee: dict[str, list[str]],
) -> str:
    note = _latest_note(task)
    if note:
        return note

    assignee = str(task.get("assignee") or task.get("ai_type") or "").strip().lower()
    blocker_reasons = blockers_by_assignee.get(assignee, [])
    if "unregistered_session" in blocker_reasons:
        return "先注册当前活跃会话，再按对应 intervention pack 推进 closeout"
    if pack_by_assignee.get(assignee):
        return "按对应 intervention pack 推进 closeout，并在完成后补 fresh ACK"
    return "复核 result_file 与 acceptance commands 后推进 closeout"


def _collect_active_external_tasks(
    *,
    workspace: Path,
    project_state: dict[str, Any],
    pack_by_assignee: dict[str, str],
    blockers_by_assignee: dict[str, list[str]],
) -> list[dict[str, Any]]:
    tasks = project_state.get("tasks", {})
    active_ids = project_state.get("active_tasks", [])
    if not isinstance(tasks, dict) or not isinstance(active_ids, list):
        return []

    records: list[dict[str, Any]] = []
    for task_id in active_ids:
        task = tasks.get(task_id)
        if not isinstance(task, dict):
            continue
        assignee = str(task.get("assignee") or task.get("ai_type") or "").strip().lower()
        if assignee not in EXTERNAL_ASSIGNEES:
            continue
        task_file = workspace / "collaboration" / "tasks" / f"{task_id}.md"
        records.append(
            {
                "task_id": str(task_id),
                "assignee": assignee,
                "status": str(task.get("status") or ""),
                "description": str(task.get("description") or ""),
                "result_file": str(task.get("result_file") or ""),
                "task_file": _relative_path(task_file, workspace) if task_file.exists() else "",
                "updated_at": str(task.get("updated_at") or ""),
                "latest_note": _latest_note(task),
                "pack_file": pack_by_assignee.get(assignee, ""),
                "action_hint": _action_hint(
                    task=task,
                    pack_by_assignee=pack_by_assignee,
                    blockers_by_assignee=blockers_by_assignee,
                ),
            }
        )

    return sorted(records, key=lambda item: (item["assignee"], item["task_id"]))


def _collect_interventions(workspace: Path) -> list[dict[str, Any]]:
    report = inspect_interventions(workspace=workspace, only_open=True)
    items: list[dict[str, Any]] = []
    for item in report.get("interventions", []) or []:
        if not isinstance(item, dict):
            continue
        assignee = str(item.get("assignee") or "").strip().lower()
        if assignee not in EXTERNAL_ASSIGNEES:
            continue
        items.append(
            {
                "intervention_id": str(item.get("intervention_id") or ""),
                "session_id": str(item.get("session_id") or ""),
                "assignee": assignee,
                "reason_code": str(item.get("reason_code") or ""),
                "severity": str(item.get("severity") or ""),
                "delivery_status": str(item.get("delivery_status") or ""),
                "message_artifact": str(item.get("message_artifact") or ""),
                "created_at": str(item.get("created_at") or ""),
                "updated_at": str(item.get("updated_at") or ""),
                "source_signal": str(item.get("source_signal") or ""),
            }
        )
    return sorted(items, key=lambda item: (item["assignee"], item["reason_code"], item["intervention_id"]))


def _build_blockers(interventions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = [item for item in interventions if item.get("reason_code") == "unregistered_session"]
    return sorted(blockers, key=lambda item: (item["assignee"], item["intervention_id"]))


def _recommended_order(
    *,
    tasks: list[dict[str, Any]],
    interventions: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    pack_by_assignee: dict[str, str],
) -> list[str]:
    lines: list[str] = []
    blocker_assignees = {str(item.get("assignee") or "") for item in blockers}
    tasks_by_assignee = {
        assignee: [item for item in tasks if item.get("assignee") == assignee]
        for assignee in EXTERNAL_ASSIGNEES
    }

    if "codearts_agent" in blocker_assignees:
        lines.append("1. 先处理 CodeArts，会话注册完成后再继续收口其待办任务。")
    elif tasks_by_assignee.get("codearts_agent"):
        lines.append("1. 先处理 CodeArts 当前待办，避免 unregistered-session 风险扩大。")

    if tasks_by_assignee.get("claude_code"):
        index = len(lines) + 1
        pack = pack_by_assignee.get("claude_code", "")
        if pack:
            lines.append(f"{index}. 再处理 Claude，优先按 `{pack}` 推进当前待办 closeout。")
        else:
            lines.append(f"{index}. 再处理 Claude 的 active tasks，并补 fresh ACK 证据。")

    if not lines and interventions:
        interventions_by_assignee = {
            assignee: [item for item in interventions if item.get("assignee") == assignee]
            for assignee in EXTERNAL_ASSIGNEES
        }
        for assignee in EXTERNAL_ASSIGNEES:
            pending = interventions_by_assignee.get(assignee) or []
            if not pending:
                continue
            needs_registration = any(
                str(item.get("session_id") or "").strip().lower().startswith("unregistered:")
                for item in pending
            )
            index = len(lines) + 1
            pack = pack_by_assignee.get(assignee, "")
            label = "Claude" if assignee == "claude_code" else "CodeArts"
            if pack:
                if needs_registration:
                    lines.append(
                        f"{index}. `{label}` 当前无 health blocker，但会话仍未注册；"
                        f"先注册当前活跃会话，再按 `{pack}` 人工投递并等待外部回执。"
                    )
                else:
                    lines.append(
                        f"{index}. `{label}` 当前无 health blocker，但仍有待转发的 manual intervention pack；"
                        f"按 `{pack}` 人工投递并等待外部回执。"
                    )
            else:
                if needs_registration:
                    lines.append(
                        f"{index}. `{label}` 当前无 health blocker，但会话仍未注册；"
                        "先注册当前活跃会话，再人工转发现有 artifact 并等待外部回执。"
                    )
                else:
                    lines.append(
                        f"{index}. `{label}` 当前无 health blocker，但仍有待转发的 manual intervention；"
                        "请人工转发现有 artifact 并等待外部回执。"
                    )

    if not lines:
        lines.append("1. 当前没有 external closeout backlog。")
    return lines


def build_external_closeout_queue_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# External Closeout Queue（自动生成）",
        "",
        "## 当前目标",
        "",
        "完成 session-orchestration 主线后的外部 closeout 收口，不假装控制外部 GUI，只输出可审计、可转发、可复跑的正式队列。",
        "",
        "## 控制面快照",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- active_external_tasks: `{report.get('active_task_count', 0)}`",
        f"- open_interventions: `{report.get('open_intervention_count', 0)}`",
        f"- blocking_interventions: `{report.get('blocking_intervention_count', 0)}`",
        f"- ready_packs: `{report.get('ready_pack_count', 0)}`",
        "",
        "## 当前 active tasks",
        "",
    ]

    active_tasks = list(report.get("active_tasks", []) or [])
    if active_tasks:
        for item in active_tasks:
            lines.append(f"- `{item.get('task_id', '')}`")
            lines.append(f"  - assignee: `{item.get('assignee', '')}`")
            lines.append(f"  - status: `{item.get('status', '')}`")
            if item.get("result_file"):
                lines.append(f"  - result_file: `{item.get('result_file', '')}`")
            if item.get("pack_file"):
                lines.append(f"  - pack_file: `{item.get('pack_file', '')}`")
            if item.get("action_hint"):
                lines.append(f"  - action: {item.get('action_hint', '')}")
    else:
        lines.append("- 无 external active tasks")
    lines.append("")

    lines.extend(["## 当前 open interventions", ""])
    interventions = list(report.get("open_interventions", []) or [])
    if interventions:
        for item in interventions:
            lines.append(
                f"- `{item.get('intervention_id', '')}` assignee=`{item.get('assignee', '')}` reason=`{item.get('reason_code', '')}` delivery=`{item.get('delivery_status', '')}`"
            )
            if item.get("message_artifact"):
                lines.append(f"  - artifact: `{item.get('message_artifact', '')}`")
    else:
        lines.append("- 无 open interventions")
    lines.append("")

    lines.extend(["## Ready-to-Send Packs", ""])
    ready_packs = list(report.get("ready_packs", []) or [])
    if ready_packs:
        for item in ready_packs:
            lines.append(f"- `{item.get('assignee', '')}`: `{item.get('pack_file', '')}`")
    else:
        lines.append("- 无 ready pack")
    lines.append("")

    lines.extend(["## 当前系统阻塞", ""])
    blockers = list(report.get("blocking_interventions", []) or [])
    if blockers:
        for item in blockers:
            lines.append(
                f"- `{item.get('assignee', '')}` reason=`{item.get('reason_code', '')}` session=`{item.get('session_id', '')}`"
            )
            if item.get("message_artifact"):
                lines.append(f"  - artifact: `{item.get('message_artifact', '')}`")
    else:
        lines.append("- 无 session blocker")
    lines.append("")

    lines.extend(["## 推荐使用顺序", ""])
    lines.extend(list(report.get("recommended_order", []) or ["1. 当前没有待推进的 external closeout。"]))
    lines.append("")
    return "\n".join(lines)


def render_external_closeout_queue(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    resolved_report, resolved_history, resolved_output = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        output_path=output_path,
    )
    generated_at = datetime.now().isoformat()
    project_state = _load_project_state(workspace)
    open_interventions = _collect_interventions(workspace)
    blockers = _build_blockers(open_interventions)

    relevant_assignees = {
        str(item.get("assignee") or "")
        for item in open_interventions
        if str(item.get("assignee") or "")
    }
    tasks = project_state.get("tasks", {})
    active_ids = project_state.get("active_tasks", [])
    if isinstance(tasks, dict) and isinstance(active_ids, list):
        for task_id in active_ids:
            task = tasks.get(task_id)
            if not isinstance(task, dict):
                continue
            assignee = str(task.get("assignee") or task.get("ai_type") or "").strip().lower()
            if assignee in EXTERNAL_ASSIGNEES:
                relevant_assignees.add(assignee)

    pack_by_assignee = {
        assignee: _pack_file_for_assignee(workspace=workspace, assignee=assignee)
        for assignee in sorted(relevant_assignees)
    }
    pack_by_assignee = {key: value for key, value in pack_by_assignee.items() if value}

    blockers_by_assignee: dict[str, list[str]] = {}
    for item in blockers:
        assignee = str(item.get("assignee") or "")
        reason_code = str(item.get("reason_code") or "")
        blockers_by_assignee.setdefault(assignee, [])
        if reason_code and reason_code not in blockers_by_assignee[assignee]:
            blockers_by_assignee[assignee].append(reason_code)

    active_tasks = _collect_active_external_tasks(
        workspace=workspace,
        project_state=project_state,
        pack_by_assignee=pack_by_assignee,
        blockers_by_assignee=blockers_by_assignee,
    )
    ready_packs = [
        {"assignee": assignee, "pack_file": pack_file}
        for assignee, pack_file in sorted(pack_by_assignee.items())
    ]

    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "mode": "apply",
        "active_task_count": len(active_tasks),
        "open_intervention_count": len(open_interventions),
        "blocking_intervention_count": len(blockers),
        "ready_pack_count": len(ready_packs),
        "active_tasks": active_tasks,
        "open_interventions": open_interventions,
        "blocking_interventions": blockers,
        "ready_packs": ready_packs,
    }
    report["recommended_order"] = _recommended_order(
        tasks=active_tasks,
        interventions=open_interventions,
        blockers=blockers,
        pack_by_assignee=pack_by_assignee,
    )

    markdown = build_external_closeout_queue_markdown(report=report)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(markdown, encoding="utf-8")

    report["output_file"] = _relative_path(resolved_output, workspace)
    report["report_file"] = _relative_path(resolved_report, workspace)
    report["history_file"] = _relative_path(resolved_history, workspace)

    write_json(resolved_report, report)
    _append_history(resolved_history, report)
    return report
