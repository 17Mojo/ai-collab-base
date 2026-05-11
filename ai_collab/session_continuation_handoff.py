"""Standard session continuation handoff generation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import load_json, write_json
from .adapters.claude_adapter import run_claude_push_adapter
from .adapters.codearts_adapter import run_codearts_pull_adapter
from .external_closeout_queue import render_external_closeout_queue
from .session_health import run_session_health_aggregation

DEFAULT_REPORT_PATH = "logs/session_continuation_handoff_report.json"
DEFAULT_HISTORY_PATH = "logs/session_continuation_handoff_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/SESSION_CONTINUATION_HANDOFF_SUMMARY_latest.md"
DEFAULT_OUTPUT_DIR = "collaboration/results"
DEFAULT_FILENAME_PREFIX = "SESSION_CONTINUATION_HANDOFF"
DEFAULT_OBJECTIVE = (
    "Continue building the session-orchestration control plane that reduces "
    'the user\'s manual "glue person" burden while preserving an honest automation boundary.'
)
DEFAULT_NEXT_SLICE = (
    "Close out Claude task 146 accurately, formalize the CodeArts pull adapter "
    "work in governance artifacts, and register the active CodeArts/Codex sessions."
)


def _load_handoff_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    session_config = payload.get("sessionOrchestration")
    if not isinstance(session_config, dict):
        return {}
    raw = session_config.get("continuationHandoff")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    output_dir: str | None = None,
) -> tuple[Path, Path, Path, Path, str]:
    config = _load_handoff_config(workspace)
    resolved_report = workspace / str(report_path or config.get("report", DEFAULT_REPORT_PATH))
    resolved_history = workspace / str(history_path or config.get("history", DEFAULT_HISTORY_PATH))
    resolved_summary = workspace / str(summary_path or config.get("summary", DEFAULT_SUMMARY_PATH))
    resolved_output_dir = workspace / str(output_dir or config.get("outputDir", DEFAULT_OUTPUT_DIR))
    filename_prefix = (
        str(config.get("filenamePrefix") or DEFAULT_FILENAME_PREFIX).strip()
        or DEFAULT_FILENAME_PREFIX
    )
    return resolved_report, resolved_history, resolved_summary, resolved_output_dir, filename_prefix


def _relative_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "output_file": payload.get("output_file", ""),
        "session_count": payload.get("health_snapshot", {}).get("session_count", 0),
        "incident_count": payload.get("health_snapshot", {}).get("incident_count", 0),
        "active_change_count": len(payload.get("active_changes", []) or []),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _collect_active_changes(workspace: Path) -> list[str]:
    changes_dir = workspace / "openspec" / "changes"
    if not changes_dir.exists():
        return []
    pending: list[str] = []
    complete_or_unknown: list[str] = []
    for child in sorted(changes_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == "archive":
            continue
        tasks_file = child / "tasks.md"
        if not tasks_file.exists():
            complete_or_unknown.append(child.name)
            continue
        try:
            content = tasks_file.read_text(encoding="utf-8")
        except OSError:
            complete_or_unknown.append(child.name)
            continue
        if "- [ ]" in content:
            pending.append(child.name)
        else:
            complete_or_unknown.append(child.name)
    return pending or complete_or_unknown


def _unique_output_file(*, output_dir: Path, filename_prefix: str, generated_at: datetime) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{filename_prefix}_{generated_at.date().isoformat()}.md"
    candidate = output_dir / base_name
    if not candidate.exists():
        return candidate

    for index in range(1, 100):
        suffixed = (
            output_dir / f"{filename_prefix}_{generated_at.date().isoformat()}_{index:02d}.md"
        )
        if not suffixed.exists():
            return suffixed
    raise RuntimeError("unable to allocate a unique continuation handoff output file")


def _normalize_lines(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for item in values or []:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _incident_lines(health_report: dict[str, Any], limit: int = 5) -> list[str]:
    incidents = list(health_report.get("incidents", []) or [])[:limit]
    lines: list[str] = []
    for item in incidents:
        assignee = str(item.get("assignee") or "")
        reason_code = str(item.get("reason_code") or "")
        summary = str(item.get("summary") or "")
        lines.append(f"- `{assignee}` reason=`{reason_code}` {summary}")
    return lines


def build_next_conversation_prompt(*, report: dict[str, Any]) -> str:
    handoff_file = str(report.get("output_file") or "")
    closeout_queue_file = str(
        report.get("closeout_queue_snapshot", {}).get("output_file") or ""
    ).strip()
    lines = [
        "继续 ai-collab-system 的 session-orchestration 控制面工作。",
        "",
        "先读：",
        f"1. {handoff_file}",
        "2. openspec/changes/add-session-orchestration-control-plane/proposal.md",
        "3. openspec/changes/add-session-orchestration-control-plane/tasks.md",
    ]
    if closeout_queue_file:
        lines.extend(
            [
                f"4. {closeout_queue_file}",
                "",
                "如果存在外部收口待办，优先以 closeout queue 为操作面板。",
            ]
        )
    lines.extend(
        [
            "",
            "当前要求：",
            "- 不要假装控制外部 GUI",
            "- 保持 honest automation boundary",
            "- 你直接做决策，不要把低层选择抛回给我",
            "",
            "下一步：",
            f"- {report.get('next_slice', DEFAULT_NEXT_SLICE)}",
            "- 补测试、跑验证、给出下一段切入点",
        ]
    )
    return "\n".join(lines)


def build_handoff_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# Session Continuation Handoff",
        "",
        "## Current Objective",
        "",
        str(report.get("objective") or DEFAULT_OBJECTIVE),
        "",
        "## Control Plane Snapshot",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- mode: `{report.get('mode', '')}`",
        f"- active_changes: `{len(report.get('active_changes', []) or [])}`",
        f"- sessions: `{report.get('health_snapshot', {}).get('session_count', 0)}`",
        f"- incidents: `{report.get('health_snapshot', {}).get('incident_count', 0)}`",
        f"- open_interventions: `{report.get('health_snapshot', {}).get('open_intervention_count', 0)}`",
        f"- unregistered: `{report.get('health_snapshot', {}).get('unregistered_count', 0)}`",
        f"- claude_adapter_candidates: `{report.get('claude_push_snapshot', {}).get('candidate_count', 0)}`",
        f"- claude_adapter_artifact_only: `{report.get('claude_push_snapshot', {}).get('artifact_only_count', 0)}`",
        f"- claude_adapter_failed: `{report.get('claude_push_snapshot', {}).get('failed_count', 0)}`",
        f"- codearts_adapter_candidates: `{report.get('codearts_pull_snapshot', {}).get('candidate_count', 0)}`",
        f"- codearts_adapter_artifact_only: `{report.get('codearts_pull_snapshot', {}).get('artifact_only_count', 0)}`",
        f"- codearts_adapter_failed: `{report.get('codearts_pull_snapshot', {}).get('failed_count', 0)}`",
        f"- external_closeout_tasks: `{report.get('closeout_queue_snapshot', {}).get('active_task_count', 0)}`",
        f"- external_open_interventions: `{report.get('closeout_queue_snapshot', {}).get('open_intervention_count', 0)}`",
        f"- external_blocking_interventions: `{report.get('closeout_queue_snapshot', {}).get('blocking_intervention_count', 0)}`",
        f"- external_ready_packs: `{report.get('closeout_queue_snapshot', {}).get('ready_pack_count', 0)}`",
        "",
    ]

    active_changes = list(report.get("active_changes", []) or [])
    lines.extend(["## Active Changes", ""])
    if active_changes:
        for change_id in active_changes:
            lines.append(f"- `{change_id}`")
    else:
        lines.append("- none detected")
    lines.append("")

    lines.extend(["## Notable Incidents", ""])
    incident_lines = _incident_lines(
        report.get("health_report", {}) if isinstance(report.get("health_report"), dict) else {}
    )
    if incident_lines:
        lines.extend(incident_lines)
    else:
        lines.append("- none")
    lines.append("")

    completed_items = _normalize_lines(report.get("completed_items"))
    lines.extend(["## Completed Items", ""])
    if completed_items:
        for item in completed_items:
            lines.append(f"- {item}")
    else:
        lines.append("- generated from current control-plane reports")
    lines.append("")

    validation_commands = _normalize_lines(report.get("validation_commands"))
    lines.extend(["## Validation Commands", ""])
    if validation_commands:
        for command in validation_commands:
            lines.append(f"- `{command}`")
    else:
        lines.append("- none recorded")
    lines.append("")

    related_files = _normalize_lines(report.get("related_files"))
    lines.extend(["## Relevant Files", ""])
    if related_files:
        for path in related_files:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none recorded")
    lines.append("")

    lines.extend(["## Recommended Next Slice", ""])
    lines.append(str(report.get("next_slice") or DEFAULT_NEXT_SLICE))
    lines.append("")

    lines.extend(["## Paste This Into The Next Conversation", "", "```text"])
    lines.append(str(report.get("next_conversation_prompt") or "").rstrip())
    lines.extend(["```", ""])
    return "\n".join(lines)


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# Session Continuation Handoff Summary（自动生成）",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- mode: `{report.get('mode', '')}`",
        f"- output_file: `{report.get('output_file', '')}`",
        f"- active_changes: `{len(report.get('active_changes', []) or [])}`",
        f"- sessions: `{report.get('health_snapshot', {}).get('session_count', 0)}`",
        f"- incidents: `{report.get('health_snapshot', {}).get('incident_count', 0)}`",
        f"- external_closeout_tasks: `{report.get('closeout_queue_snapshot', {}).get('active_task_count', 0)}`",
        f"- next_slice: `{report.get('next_slice', '')}`",
        "",
    ]
    return "\n".join(lines)


def run_session_continuation_handoff(
    *,
    workspace: Path,
    objective: str | None = None,
    next_slice: str | None = None,
    completed_items: list[str] | None = None,
    validation_commands: list[str] | None = None,
    related_files: list[str] | None = None,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    output_dir: str | None = None,
    dry_run: bool = False,
    refresh_state: bool = True,
) -> dict[str, Any]:
    report_file, history_file, summary_file, output_root, filename_prefix = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        summary_path=summary_path,
        output_dir=output_dir,
    )
    generated_at = datetime.now()

    if refresh_state:
        health_report = run_session_health_aggregation(
            workspace=workspace,
            dry_run=True,
            emit_interventions=False,
        )
        claude_push_report = run_claude_push_adapter(
            workspace=workspace,
            dry_run=True,
            allow_delivery=False,
        )
        codearts_pull_report = run_codearts_pull_adapter(
            workspace=workspace,
            dry_run=True,
            allow_delivery=False,
        )
        closeout_queue_report = render_external_closeout_queue(workspace=workspace)
    else:
        health_report = {}
        claude_push_report = {}
        codearts_pull_report = {}
        closeout_queue_report = {}

    output_file = Path()
    output_relpath = ""
    markdown = ""
    auto_related_files = list(related_files or [])
    closeout_queue_file = str(closeout_queue_report.get("output_file") or "").strip()
    if closeout_queue_file:
        auto_related_files.append(closeout_queue_file)
    report: dict[str, Any] = {
        "generated_at": generated_at.isoformat(),
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "objective": str(objective or DEFAULT_OBJECTIVE).strip() or DEFAULT_OBJECTIVE,
        "next_slice": str(next_slice or DEFAULT_NEXT_SLICE).strip() or DEFAULT_NEXT_SLICE,
        "completed_items": _normalize_lines(completed_items),
        "validation_commands": _normalize_lines(validation_commands),
        "related_files": _normalize_lines(auto_related_files),
        "active_changes": _collect_active_changes(workspace),
        "health_snapshot": {
            "session_count": int(health_report.get("session_count", 0) or 0),
            "incident_count": int(health_report.get("incident_count", 0) or 0),
            "open_intervention_count": int(health_report.get("open_intervention_count", 0) or 0),
            "unregistered_count": int(health_report.get("unregistered_count", 0) or 0),
        },
        "claude_push_snapshot": {
            "candidate_count": int(claude_push_report.get("candidate_count", 0) or 0),
            "artifact_only_count": int(claude_push_report.get("artifact_only_count", 0) or 0),
            "failed_count": int(claude_push_report.get("failed_count", 0) or 0),
        },
        "codearts_pull_snapshot": {
            "candidate_count": int(codearts_pull_report.get("candidate_count", 0) or 0),
            "artifact_only_count": int(codearts_pull_report.get("artifact_only_count", 0) or 0),
            "failed_count": int(codearts_pull_report.get("failed_count", 0) or 0),
        },
        "closeout_queue_snapshot": {
            "active_task_count": int(closeout_queue_report.get("active_task_count", 0) or 0),
            "open_intervention_count": int(
                closeout_queue_report.get("open_intervention_count", 0) or 0
            ),
            "blocking_intervention_count": int(
                closeout_queue_report.get("blocking_intervention_count", 0) or 0
            ),
            "ready_pack_count": int(closeout_queue_report.get("ready_pack_count", 0) or 0),
            "output_file": closeout_queue_file,
        },
        "health_report": {
            "report_file": str(health_report.get("report_file") or ""),
            "summary_file": str(health_report.get("summary_file") or ""),
            "incidents": list(health_report.get("incidents", []) or []),
        },
        "claude_push_report": {
            "report_file": str(claude_push_report.get("report_file") or ""),
            "summary_file": str(claude_push_report.get("summary_file") or ""),
        },
        "codearts_pull_report": {
            "report_file": str(codearts_pull_report.get("report_file") or ""),
            "summary_file": str(codearts_pull_report.get("summary_file") or ""),
        },
        "closeout_queue_report": {
            "report_file": str(closeout_queue_report.get("report_file") or ""),
            "history_file": str(closeout_queue_report.get("history_file") or ""),
            "output_file": closeout_queue_file,
        },
    }

    if not dry_run:
        output_file = _unique_output_file(
            output_dir=output_root,
            filename_prefix=filename_prefix,
            generated_at=generated_at,
        )
        output_relpath = _relative_path(output_file, workspace)
        report["output_file"] = output_relpath
    else:
        report["output_file"] = ""

    report["next_conversation_prompt"] = build_next_conversation_prompt(report=report)
    markdown = build_handoff_markdown(report=report)
    report["markdown_preview"] = markdown

    if not dry_run:
        output_file.write_text(markdown, encoding="utf-8")

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = _relative_path(summary_file, workspace)
    report["report_file"] = _relative_path(report_file, workspace)
    report["history_file"] = _relative_path(history_file, workspace)
    write_json(report_file, report)
    _append_history(history_file, report)
    return report
