"""Detect and bridge completed tasks that never emitted a chat-layer ACK."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import (
    SUPPORTED_ASSIGNEES,
    build_ack_line,
    has_ack_evidence,
    normalize_assignee,
    normalize_result_file,
    record_ack_bridge,
    requires_explicit_ack,
)

MIRROR_SEARCH_ROOTS = (Path("/private/tmp"),)


@dataclass
class MissingAckCandidate:
    """A completed task that needs an ACK bridge record."""

    task_id: str
    assignee: str
    result_file: str
    updated_at: str
    receipt_completed_at: str
    bridge_source: str
    result_synced_from: str
    ack_line: str


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    return payload if isinstance(payload, dict) else default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_result_file(workspace: Path, result_file: str) -> tuple[Path | None, str]:
    resolved_result = workspace / result_file
    if resolved_result.exists():
        return resolved_result, ""

    mirror_matches: list[Path] = []
    for search_root in MIRROR_SEARCH_ROOTS:
        if not search_root.exists() or not search_root.is_dir():
            continue
        try:
            children = list(search_root.iterdir())
        except OSError:
            continue

        for child in children:
            if not child.is_dir():
                continue
            candidate = child / result_file
            if candidate.exists():
                mirror_matches.append(candidate)

    if len(mirror_matches) > 1:
        return None, f"multiple mirrored result files found: {result_file}"
    if not mirror_matches:
        return None, f"result file not found: {result_file}"

    resolved_result.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mirror_matches[0], resolved_result)
    return resolved_result, str(mirror_matches[0])


def collect_missing_ack_candidates(
    *,
    workspace: Path,
    state: dict[str, Any],
    receipt_state: dict[str, Any],
    ack_bridge_state: dict[str, Any],
    rebridge: bool = False,
) -> tuple[list[MissingAckCandidate], list[str], list[dict[str, str]], list[dict[str, str]]]:
    """Collect completed tasks that still lack an ACK bridge record."""
    tasks = state.get("tasks", {})
    receipt_items = receipt_state.get("items", {})
    bridged_items = ack_bridge_state.get("items", {})

    if not isinstance(tasks, dict):
        return [], [], [], []
    if not isinstance(receipt_items, dict):
        receipt_items = {}
    if not isinstance(bridged_items, dict):
        bridged_items = {}

    candidates: list[MissingAckCandidate] = []
    already_bridged: list[str] = []
    stale_explicit_ack: list[dict[str, str]] = []
    other_skipped: list[dict[str, str]] = []

    for task_id, task in tasks.items():
        if not isinstance(task, dict):
            continue

        if str(task.get("status") or "").strip().lower() != "completed":
            continue

        assignee = normalize_assignee(task)
        if assignee not in SUPPORTED_ASSIGNEES:
            other_skipped.append(
                {
                    "task_id": str(task_id),
                    "reason": f"unsupported assignee: {assignee or '<empty>'}",
                }
            )
            continue

        existing_bridge = (
            bridged_items.get(task_id) if isinstance(bridged_items.get(task_id), dict) else {}
        )
        if requires_explicit_ack(assignee):
            if has_ack_evidence(
                bridged_items, task_id=str(task_id), assignee=assignee, require_explicit=True
            ):
                already_bridged.append(str(task_id))
            else:
                source = str(existing_bridge.get("source") or "").strip()
                remediation_status = str(existing_bridge.get("remediation_status") or "").strip()
                source_suffix = f" (current_source={source})" if source else ""
                remediation_suffix = (
                    f" remediation_status={remediation_status}" if remediation_status else ""
                )
                stale_explicit_ack.append(
                    {
                        "task_id": str(task_id),
                        "reason": (
                            "explicit ACK required; auto-bridge disabled "
                            f"for {assignee}{source_suffix}{remediation_suffix}"
                        ),
                        "source": source,
                        "remediation_status": remediation_status,
                    }
                )
            continue

        if task_id in bridged_items and not rebridge:
            already_bridged.append(str(task_id))
            continue

        receipt_item = receipt_items.get(task_id)
        receipt_completed_at = ""
        bridge_source = "missing_ack_monitor:receipt_state"
        if isinstance(receipt_item, dict):
            receipt_completed_at = str(
                receipt_item.get("completed_at")
                or task.get("completed_at")
                or task.get("updated_at")
                or task.get("created_at")
                or ""
            )
        else:
            receipt_completed_at = str(
                task.get("completed_at") or task.get("updated_at") or task.get("created_at") or ""
            )
            bridge_source = "missing_ack_monitor:completed_state_fallback"

        if not receipt_completed_at:
            other_skipped.append(
                {
                    "task_id": str(task_id),
                    "reason": "missing completion timestamp for ACK bridge",
                }
            )
            continue

        result_file = normalize_result_file(str(task_id), task)
        resolved_result, result_synced_from = _ensure_result_file(workspace, result_file)
        if resolved_result is None:
            other_skipped.append(
                {
                    "task_id": str(task_id),
                    "reason": result_synced_from,
                }
            )
            continue

        candidates.append(
            MissingAckCandidate(
                task_id=str(task_id),
                assignee=assignee,
                result_file=result_file,
                updated_at=str(task.get("updated_at") or task.get("created_at") or ""),
                receipt_completed_at=receipt_completed_at,
                bridge_source=bridge_source,
                result_synced_from=result_synced_from,
                ack_line=build_ack_line(
                    assignee=assignee,
                    task_id=str(task_id),
                    result_file=result_file,
                ),
            )
        )

    candidates.sort(key=lambda item: item.task_id)
    already_bridged.sort()
    stale_explicit_ack.sort(key=lambda item: item.get("task_id", ""))
    other_skipped.sort(key=lambda item: item.get("task_id", ""))
    return candidates, already_bridged, stale_explicit_ack, other_skipped


def build_summary_markdown(
    *,
    report: dict[str, Any],
    bridged_tasks: list[dict[str, Any]],
    stale_explicit_ack_tasks: list[dict[str, Any]],
    other_skipped_tasks: list[dict[str, Any]],
) -> str:
    """Render the missing ACK bridge summary."""
    lines: list[str] = []
    lines.append("# Missing ACK Bridge Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 模式: `{report.get('mode', '')}`")
    lines.append(f"- 候选任务: `{report.get('candidate_count', 0)}`")
    lines.append(f"- 新补桥: `{report.get('bridged_count', 0)}`")
    lines.append(f"- 已补桥跳过: `{report.get('already_bridged_count', 0)}`")
    lines.append(f"- 显式 ACK 残留: `{report.get('stale_explicit_ack_count', 0)}`")
    lines.append(f"- 其他规则跳过: `{report.get('other_skipped_count', 0)}`")
    lines.append(f"- 规则跳过总计: `{report.get('skipped_count', 0)}`")
    lines.append(f"- 错误: `{report.get('error_count', 0)}`")
    lines.append("")

    lines.append("## 已补桥任务")
    lines.append("")
    if bridged_tasks:
        for item in bridged_tasks:
            lines.append(f"- `{item.get('task_id', '')}` -> `{item.get('ack_line', '')}`")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 可直接复制的 ACK 行")
    lines.append("")
    if bridged_tasks:
        lines.append("```text")
        for item in bridged_tasks:
            lines.append(str(item.get("ack_line", "")))
        lines.append("```")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 显式 ACK 残留")
    lines.append("")
    if stale_explicit_ack_tasks:
        for item in stale_explicit_ack_tasks:
            lines.append(f"- `{item.get('task_id', '')}`: {item.get('reason', '')}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 其他跳过项")
    lines.append("")
    if other_skipped_tasks:
        for item in other_skipped_tasks:
            lines.append(f"- `{item.get('task_id', '')}`: {item.get('reason', '')}")
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_missing_ack_monitor(
    *,
    workspace: Path,
    dry_run: bool = False,
    rebridge: bool = False,
    report_path: str = "logs/missing_ack_report.json",
    state_path: str = "logs/agent_ack_bridge_state.json",
    receipt_state_path: str = "logs/agent_receipt_state.json",
    summary_path: str = "collaboration/monitoring/MISSING_ACK_SUMMARY_latest.md",
) -> dict[str, Any]:
    """Detect and bridge completed tasks that lack an ACK bridge record."""
    state_file = workspace / "logs" / "collaboration_state.json"
    project_state = _load_json(state_file, default={"tasks": {}})
    receipt_state_file = workspace / receipt_state_path
    receipt_state = _load_json(receipt_state_file, default={"version": "1.0.0", "items": {}})
    ack_bridge_state_file = workspace / state_path
    ack_bridge_state = _load_json(ack_bridge_state_file, default={"version": "1.0.0", "items": {}})

    items = ack_bridge_state.get("items")
    if not isinstance(items, dict):
        items = {}
        ack_bridge_state["items"] = items

    candidates, already_bridged, stale_explicit_ack, other_skipped = collect_missing_ack_candidates(
        workspace=workspace,
        state=project_state,
        receipt_state=receipt_state,
        ack_bridge_state=ack_bridge_state,
        rebridge=rebridge,
    )

    generated_at = datetime.now().isoformat()
    bridged_tasks: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            record = record_ack_bridge(
                workspace=workspace,
                task_id=candidate.task_id,
                assignee=candidate.assignee,
                result_file=candidate.result_file,
                completed_at=candidate.receipt_completed_at,
                source=candidate.bridge_source,
                bridged_at=generated_at,
                state_path=state_path,
                result_synced_from=candidate.result_synced_from,
                increment_count=True,
                dry_run=dry_run,
            )
            bridged_tasks.append(record)
        except Exception as exc:  # noqa: BLE001
            errors.append({"task_id": candidate.task_id, "error": str(exc)})

    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "rebridge": rebridge,
        "candidate_count": len(candidates),
        "bridged_count": len(bridged_tasks),
        "already_bridged_count": len(already_bridged),
        "stale_explicit_ack_count": len(stale_explicit_ack),
        "other_skipped_count": len(other_skipped),
        "skipped_count": len(stale_explicit_ack) + len(other_skipped),
        "error_count": len(errors),
        "candidate_tasks": [asdict(item) for item in candidates],
        "bridged_tasks": bridged_tasks,
        "already_bridged_tasks": already_bridged,
        "stale_explicit_ack_tasks": stale_explicit_ack,
        "other_skipped_tasks": other_skipped,
        "skipped_tasks": stale_explicit_ack + other_skipped,
        "errors": errors,
        "state_updated": not dry_run,
        "ack_bridge_state_file": str(ack_bridge_state_file.relative_to(workspace)),
        "receipt_state_file": str(receipt_state_file.relative_to(workspace)),
    }

    summary_file = workspace / summary_path
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        build_summary_markdown(
            report=report,
            bridged_tasks=bridged_tasks,
            stale_explicit_ack_tasks=stale_explicit_ack,
            other_skipped_tasks=other_skipped,
        ),
        encoding="utf-8",
    )
    report["summary_file"] = str(summary_file.relative_to(workspace))

    report_file = workspace / report_path
    _write_json(report_file, report)
    return report
