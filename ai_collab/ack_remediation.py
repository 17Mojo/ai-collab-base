"""Audit and flag legacy non-explicit ACK bridge records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import (
    is_explicit_ack_source,
    load_ack_bridge_state,
    requires_explicit_ack,
    write_json,
)

DEFAULT_REPORT_PATH = "logs/ack_remediation_report.json"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/ACK_REMEDIATION_SUMMARY_latest.md"
DEFAULT_STATE_PATH = "logs/agent_ack_bridge_state.json"
REMEDIATION_STATUS_NEEDS_EXPLICIT_ACK = "needs_explicit_ack"


@dataclass
class AckRemediationCandidate:
    task_id: str
    assignee: str
    source: str
    ack_line: str
    result_file: str
    remediation_status: str
    reason: str


def _is_legacy_nonexplicit_required_ack(item: dict[str, Any]) -> bool:
    assignee = str(item.get("assignee") or "").strip().lower()
    source = str(item.get("source") or "").strip()
    return requires_explicit_ack(assignee) and not is_explicit_ack_source(source)


def collect_ack_remediation_candidates(
    *,
    ack_bridge_state: dict[str, Any],
    task_id: str | None = None,
) -> tuple[list[AckRemediationCandidate], list[AckRemediationCandidate]]:
    items = ack_bridge_state.get("items")
    if not isinstance(items, dict):
        return [], []

    candidates: list[AckRemediationCandidate] = []
    already_flagged: list[AckRemediationCandidate] = []
    selected_task_id = str(task_id or "").strip()

    for raw_task_id, raw_item in items.items():
        if not isinstance(raw_item, dict):
            continue
        if selected_task_id and str(raw_task_id) != selected_task_id:
            continue
        if not _is_legacy_nonexplicit_required_ack(raw_item):
            continue

        status = str(raw_item.get("remediation_status") or "").strip()
        candidate = AckRemediationCandidate(
            task_id=str(raw_task_id),
            assignee=str(raw_item.get("assignee") or "").strip().lower(),
            source=str(raw_item.get("source") or "").strip(),
            ack_line=str(raw_item.get("ack_line") or "").strip(),
            result_file=str(raw_item.get("result_file") or "").strip(),
            remediation_status=status,
            reason="legacy non-explicit ACK bridge cannot be used for closeout",
        )
        if status == REMEDIATION_STATUS_NEEDS_EXPLICIT_ACK:
            already_flagged.append(candidate)
        else:
            candidates.append(candidate)

    candidates.sort(key=lambda item: item.task_id)
    already_flagged.sort(key=lambda item: item.task_id)
    return candidates, already_flagged


def _flag_candidate(
    *,
    item: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    assignee = str(item.get("assignee") or "").strip().lower()
    item["closeout_eligible"] = False
    item["remediation_status"] = REMEDIATION_STATUS_NEEDS_EXPLICIT_ACK
    item["remediation_reason"] = f"explicit ACK required for {assignee or 'assignee'} closeout"
    item["remediation_updated_at"] = generated_at
    item["remediation_source"] = "ack_remediation"
    return item


def build_summary_markdown(
    *,
    report: dict[str, Any],
    flagged_tasks: list[dict[str, Any]],
    already_flagged_tasks: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# ACK Remediation Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 模式: `{report.get('mode', '')}`")
    lines.append(f"- 候选残留: `{report.get('candidate_count', 0)}`")
    lines.append(f"- 新标记: `{report.get('flagged_count', 0)}`")
    lines.append(f"- 已标记: `{report.get('already_flagged_count', 0)}`")
    lines.append(f"- 错误: `{report.get('error_count', 0)}`")
    lines.append("")

    lines.append("## 新标记的历史 fallback bridge")
    lines.append("")
    if flagged_tasks:
        for item in flagged_tasks:
            lines.append(
                f"- `{item.get('task_id', '')}` "
                f"source=`{item.get('source', '')}` status=`{item.get('remediation_status', '')}`"
            )
            lines.append(
                "  remediation: "
                f"`python3 -m ai_collab.cli ack --task-id {item.get('task_id', '')} --ai {item.get('assignee', '')} --status ok`"
            )
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 已标记残留")
    lines.append("")
    if already_flagged_tasks:
        for item in already_flagged_tasks:
            lines.append(
                f"- `{item.get('task_id', '')}` "
                f"source=`{item.get('source', '')}` status=`{item.get('remediation_status', '')}`"
            )
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_ack_remediation(
    *,
    workspace: Path,
    dry_run: bool = False,
    task_id: str | None = None,
    report_path: str = DEFAULT_REPORT_PATH,
    summary_path: str = DEFAULT_SUMMARY_PATH,
    state_path: str = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    state_file, payload, items = load_ack_bridge_state(workspace, state_path=state_path)
    candidates, already_flagged = collect_ack_remediation_candidates(
        ack_bridge_state=payload,
        task_id=task_id,
    )

    generated_at = datetime.now().isoformat()
    flagged_tasks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for candidate in candidates:
        raw_item = items.get(candidate.task_id)
        if not isinstance(raw_item, dict):
            errors.append({"task_id": candidate.task_id, "error": "ack bridge item missing during remediation"})
            continue
        updated = dict(raw_item)
        _flag_candidate(item=updated, generated_at=generated_at)
        if not dry_run:
            items[candidate.task_id] = updated
        flagged_tasks.append(updated)

    if not dry_run:
        write_json(state_file, payload)

    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "task_id": str(task_id or ""),
        "candidate_count": len(candidates),
        "flagged_count": len(flagged_tasks),
        "already_flagged_count": len(already_flagged),
        "error_count": len(errors),
        "candidate_tasks": [asdict(item) for item in candidates],
        "flagged_tasks": flagged_tasks,
        "already_flagged_tasks": [asdict(item) for item in already_flagged],
        "errors": errors,
        "state_updated": not dry_run,
        "ack_bridge_state_file": str(state_file.relative_to(workspace)),
    }

    summary_file = workspace / summary_path
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        build_summary_markdown(
            report=report,
            flagged_tasks=flagged_tasks,
            already_flagged_tasks=report["already_flagged_tasks"],
        ),
        encoding="utf-8",
    )
    report["summary_file"] = str(summary_file.relative_to(workspace))

    report_file = workspace / report_path
    report["report_file"] = str(report_file.relative_to(workspace))
    write_json(report_file, report)
    return report
