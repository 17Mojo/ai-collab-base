"""Detect silent dispatched tasks that never emitted an ACK and escalate automatically."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import SUPPORTED_ASSIGNEES, load_json, write_json
from .dispatch_trigger import DISPLAY_NAME, RUN_HINT, build_handoff_payload, split_orders_by_assignee

DEFAULT_THRESHOLD_SECONDS = 120
DEFAULT_MAX_REDISPATCH = 1
DEFAULT_REPORT_PATH = "logs/ack_watchdog_report.json"
DEFAULT_HISTORY_PATH = "logs/ack_watchdog_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/ACK_WATCHDOG_SUMMARY_latest.md"
DEFAULT_DISPATCH_STATE_PATH = "logs/agent_dispatch_state.json"
DEFAULT_DISPATCH_REPORT_PATH = "logs/task_dispatch_report.json"
DEFAULT_TASK_STATE_PATH = "logs/collaboration_state.json"
DEFAULT_RECEIPT_STATE_PATH = "logs/agent_receipt_state.json"
DEFAULT_ACK_STATE_PATH = "logs/agent_ack_bridge_state.json"
DEFAULT_ORDERS_PATH = "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md"
DEFAULT_TRIGGER_OUTPUT_DIR = "collaboration/monitoring"
DEFAULT_TRIGGER_PREFIX = "AGENT_TRIGGER"

PENDING_LIKE_STATUSES = {"pending", "planning"}
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class AckWatchdogCandidate:
    task_id: str
    assignee: str
    current_status: str
    age_seconds: int
    threshold_seconds: int
    dispatched_at: str
    dispatch_count: int
    watchdog_redispatch_count: int
    result_file: str
    action: str
    reason: str
    handled_key: str


def _to_epoch(ts: Any) -> float:
    if not ts:
        return -1.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return -1.0


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "candidate_count": payload.get("candidate_count", 0),
        "redispatched_count": payload.get("redispatched_count", 0),
        "alerted_count": payload.get("alerted_count", 0),
        "error_count": payload.get("error_count", 0),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _watchdog_handled_key(*, task: dict[str, Any], dispatch_item: dict[str, Any]) -> str:
    return "|".join(
        [
            str(task.get("status") or "").strip().lower(),
            str(task.get("updated_at") or task.get("created_at") or ""),
            str(dispatch_item.get("dispatched_at") or ""),
            str(dispatch_item.get("dispatch_count") or 0),
        ]
    )


def collect_ack_watchdog_candidates(
    *,
    state: dict[str, Any],
    dispatch_state: dict[str, Any],
    receipt_state: dict[str, Any],
    ack_bridge_state: dict[str, Any],
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
    max_redispatch_count: int = DEFAULT_MAX_REDISPATCH,
    now_epoch: float | None = None,
) -> tuple[list[AckWatchdogCandidate], list[dict[str, str]]]:
    now_epoch = now_epoch if now_epoch is not None else datetime.now().timestamp()

    tasks = state.get("tasks", {}) if isinstance(state.get("tasks"), dict) else {}
    dispatch_items = dispatch_state.get("items", {}) if isinstance(dispatch_state.get("items"), dict) else {}
    receipt_items = receipt_state.get("items", {}) if isinstance(receipt_state.get("items"), dict) else {}
    ack_items = ack_bridge_state.get("items", {}) if isinstance(ack_bridge_state.get("items"), dict) else {}

    candidates: list[AckWatchdogCandidate] = []
    skipped: list[dict[str, str]] = []
    for task_id, dispatch_item in dispatch_items.items():
        if not isinstance(dispatch_item, dict):
            continue

        task = tasks.get(task_id)
        if not isinstance(task, dict):
            skipped.append({"task_id": str(task_id), "reason": "task missing from collaboration state"})
            continue

        assignee = str(dispatch_item.get("assignee") or task.get("assignee") or task.get("ai_type") or "").strip().lower()
        if assignee not in SUPPORTED_ASSIGNEES:
            skipped.append({"task_id": str(task_id), "reason": f"unsupported assignee: {assignee or '<empty>'}"})
            continue

        if task_id in receipt_items or task_id in ack_items:
            continue

        current_status = str(task.get("status") or "").strip().lower()
        if current_status in TERMINAL_STATUSES:
            continue

        dispatched_at = str(dispatch_item.get("dispatched_at") or "")
        dispatched_epoch = _to_epoch(dispatched_at)
        if dispatched_epoch < 0:
            skipped.append({"task_id": str(task_id), "reason": "missing dispatched_at timestamp"})
            continue

        age_seconds = max(0, int(now_epoch - dispatched_epoch))
        if age_seconds <= int(threshold_seconds):
            continue

        handled_key = _watchdog_handled_key(task=task, dispatch_item=dispatch_item)
        if str(dispatch_item.get("watchdog_last_handled_key") or "") == handled_key:
            continue

        watchdog_redispatch_count = int(dispatch_item.get("watchdog_redispatch_count", 0) or 0)
        action = "alert"
        if current_status in PENDING_LIKE_STATUSES and watchdog_redispatch_count < int(max_redispatch_count):
            action = "redispatch"

        reason = (
            f"dispatched {age_seconds}s ago without receipt/ACK; "
            f"status={current_status or '<empty>'}; dispatch_count={dispatch_item.get('dispatch_count', 0)}"
        )
        candidates.append(
            AckWatchdogCandidate(
                task_id=str(task_id),
                assignee=assignee,
                current_status=current_status,
                age_seconds=age_seconds,
                threshold_seconds=int(threshold_seconds),
                dispatched_at=dispatched_at,
                dispatch_count=int(dispatch_item.get("dispatch_count", 0) or 0),
                watchdog_redispatch_count=watchdog_redispatch_count,
                result_file=str(task.get("result_file") or dispatch_item.get("result_file") or ""),
                action=action,
                reason=reason,
                handled_key=handled_key,
            )
        )

    candidates.sort(key=lambda item: item.task_id)
    skipped.sort(key=lambda item: item.get("task_id", ""))
    return candidates, skipped


def _strip_first_heading(section_markdown: str) -> str:
    lines = (section_markdown or "").splitlines()
    if lines and lines[0].startswith("## "):
        return "\n".join(lines[1:]).lstrip("\n")
    return section_markdown


def _payload_path(*, workspace: Path, assignee: str, output_dir: str, prefix: str) -> Path:
    return workspace / output_dir / f"{prefix}_{assignee}_latest.md"


def _run_reset_hint(assignee: str) -> str:
    run_hint = RUN_HINT.get(assignee, "RUN")
    return run_hint.replace(".RUN", ".RUN-RESET") if ".RUN" in run_hint else f"{run_hint}-RESET"


def _refresh_assignee_payload(
    *,
    workspace: Path,
    assignee: str,
    candidates: list[AckWatchdogCandidate],
    generated_at: str,
    orders_path: str,
    output_dir: str,
    payload_prefix: str,
) -> str:
    orders_file = workspace / orders_path
    dispatch_report_file = workspace / DEFAULT_DISPATCH_REPORT_PATH
    section_markdown = ""
    payload_generated_at = generated_at
    if dispatch_report_file.exists():
        try:
            dispatch_report = json.loads(dispatch_report_file.read_text(encoding="utf-8"))
            payload_generated_at = str(dispatch_report.get("generated_at") or generated_at)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            payload_generated_at = generated_at
    if orders_file.exists():
        orders_text = orders_file.read_text(encoding="utf-8")
        section_markdown = split_orders_by_assignee(orders_text).get(assignee, "")

    task_ids = ", ".join(item.task_id for item in candidates)
    role = DISPLAY_NAME.get(assignee, assignee)
    watchdog_lines = [
        f"## 发送给 `{role}` (`{assignee}`)",
        "",
        "### ACK Watchdog（自动重派）",
        "",
        "```text",
        f"【ACK 超时重派 | {task_ids}】",
        f"检测到派发后超过 {candidates[0].threshold_seconds}s 仍无 ACK/无 receipt。",
        f"watchdog_refresh_at={generated_at}",
        f"请先执行 `{_run_reset_hint(assignee)}`，再执行 `{RUN_HINT.get(assignee, 'RUN')}`。",
        "完成后不要手写 ACK，请使用任务块中的 ack 命令生成并原样回复。",
        "```",
        "",
    ]
    trimmed_section = _strip_first_heading(section_markdown)
    if trimmed_section:
        watchdog_lines.append(trimmed_section)
    else:
        watchdog_lines.extend(
            [
                "### 当前无可复用任务段",
                "",
                "请回到最新派单指令包重新读取任务正文。",
            ]
        )
    if "python3 -m ai_collab.cli ack --task-id" not in "\n".join(watchdog_lines):
        watchdog_lines.extend(["", "### ACK 工具输出补充", ""])
        for candidate in candidates:
            watchdog_lines.extend(
                [
                    "```text",
                    f"python3 -m ai_collab.cli ack --task-id {candidate.task_id} --ai {assignee} --status ok",
                    "```",
                    "",
                ]
            )

    payload_text = build_handoff_payload(
        assignee=assignee,
        trigger_phrase="AUTO ACK WATCHDOG REDISPATCH",
        orders_relpath=orders_path,
        section_markdown="\n".join(watchdog_lines),
        generated_at=payload_generated_at,
    )
    payload_file = _payload_path(workspace=workspace, assignee=assignee, output_dir=output_dir, prefix=payload_prefix)
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(payload_text, encoding="utf-8")
    return str(payload_file.relative_to(workspace))


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# ACK Watchdog Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 模式: `{report.get('mode', '')}`")
    lines.append(f"- 超时阈值: `{report.get('threshold_seconds', 0)}s`")
    lines.append(f"- 候选静默任务: `{report.get('candidate_count', 0)}`")
    lines.append(f"- 自动重派: `{report.get('redispatched_count', 0)}`")
    lines.append(f"- 仅告警: `{report.get('alerted_count', 0)}`")
    lines.append(f"- 跳过: `{report.get('skipped_count', 0)}`")
    lines.append(f"- 错误: `{report.get('error_count', 0)}`")
    lines.append("")

    lines.append("## 静默任务")
    lines.append("")
    if report.get("handled_tasks"):
        for item in report["handled_tasks"]:
            lines.append(
                f"- `{item.get('task_id', '')}` assignee=`{item.get('assignee', '')}` "
                f"status=`{item.get('current_status', '')}` action=`{item.get('action', '')}` age=`{item.get('age_seconds', 0)}s`"
            )
            if item.get("payload_file"):
                lines.append(f"  - refreshed payload: `{item.get('payload_file', '')}`")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 跳过项")
    lines.append("")
    if report.get("skipped_tasks"):
        skipped_tasks = list(report["skipped_tasks"])
        for item in skipped_tasks[:20]:
            lines.append(f"- `{item.get('task_id', '')}`: {item.get('reason', '')}")
        remaining = len(skipped_tasks) - 20
        if remaining > 0:
            lines.append(f"- 其余 `{remaining}` 项已折叠（详见 `{report.get('report_file', DEFAULT_REPORT_PATH)}`）")
    else:
        lines.append("- 无")
    lines.append("")
    return "\n".join(lines)


def run_ack_watchdog(
    *,
    workspace: Path,
    dry_run: bool = False,
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
    max_redispatch_count: int = DEFAULT_MAX_REDISPATCH,
    report_path: str = DEFAULT_REPORT_PATH,
    history_path: str = DEFAULT_HISTORY_PATH,
    summary_path: str = DEFAULT_SUMMARY_PATH,
    dispatch_state_path: str = DEFAULT_DISPATCH_STATE_PATH,
    task_state_path: str = DEFAULT_TASK_STATE_PATH,
    receipt_state_path: str = DEFAULT_RECEIPT_STATE_PATH,
    ack_state_path: str = DEFAULT_ACK_STATE_PATH,
    orders_path: str = DEFAULT_ORDERS_PATH,
    output_dir: str = DEFAULT_TRIGGER_OUTPUT_DIR,
    payload_prefix: str = DEFAULT_TRIGGER_PREFIX,
) -> dict[str, Any]:
    state = load_json(workspace / task_state_path, default={"tasks": {}})
    dispatch_state_file = workspace / dispatch_state_path
    dispatch_state = load_json(dispatch_state_file, default={"version": "1.0.0", "items": {}})
    items = dispatch_state.get("items")
    if not isinstance(items, dict):
        items = {}
        dispatch_state["items"] = items
    receipt_state = load_json(workspace / receipt_state_path, default={"version": "1.0.0", "items": {}})
    ack_bridge_state = load_json(workspace / ack_state_path, default={"version": "1.0.0", "items": {}})

    candidates, skipped = collect_ack_watchdog_candidates(
        state=state,
        dispatch_state=dispatch_state,
        receipt_state=receipt_state,
        ack_bridge_state=ack_bridge_state,
        threshold_seconds=threshold_seconds,
        max_redispatch_count=max_redispatch_count,
    )

    generated_at = datetime.now().isoformat()
    handled: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    redispatched_by_assignee: dict[str, list[AckWatchdogCandidate]] = {}
    for candidate in candidates:
        try:
            dispatch_item = items.get(candidate.task_id)
            if not isinstance(dispatch_item, dict):
                continue

            payload_file = ""
            if not dry_run:
                dispatch_item["watchdog_last_handled_at"] = generated_at
                dispatch_item["watchdog_last_handled_key"] = candidate.handled_key
                dispatch_item["watchdog_last_action"] = candidate.action

                if candidate.action == "redispatch":
                    dispatch_item["watchdog_redispatch_count"] = int(dispatch_item.get("watchdog_redispatch_count", 0) or 0) + 1
                    dispatch_item["watchdog_last_redispatched_at"] = generated_at
                    dispatch_item["dispatch_count"] = int(dispatch_item.get("dispatch_count", 0) or 0) + 1
                    dispatch_item["dispatched_at"] = generated_at
                    redispatched_by_assignee.setdefault(candidate.assignee, []).append(candidate)
                else:
                    dispatch_item["watchdog_alert_count"] = int(dispatch_item.get("watchdog_alert_count", 0) or 0) + 1
                    dispatch_item["watchdog_last_alerted_at"] = generated_at

            handled_item = asdict(candidate)
            handled_item["payload_file"] = payload_file
            handled.append(handled_item)
        except Exception as exc:  # noqa: BLE001
            errors.append({"task_id": candidate.task_id, "error": str(exc)})

    if not dry_run:
        for assignee, assignee_candidates in redispatched_by_assignee.items():
            try:
                payload_file = _refresh_assignee_payload(
                    workspace=workspace,
                    assignee=assignee,
                    candidates=assignee_candidates,
                    generated_at=generated_at,
                    orders_path=orders_path,
                    output_dir=output_dir,
                    payload_prefix=payload_prefix,
                )
                for item in handled:
                    if item["assignee"] == assignee and item["action"] == "redispatch":
                        item["payload_file"] = payload_file
            except Exception as exc:  # noqa: BLE001
                errors.append({"task_id": ",".join(x.task_id for x in assignee_candidates), "error": str(exc)})

        if handled:
            write_json(dispatch_state_file, dispatch_state)

    redispatched_count = len([item for item in handled if item.get("action") == "redispatch"])
    alerted_count = len([item for item in handled if item.get("action") == "alert"])
    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "threshold_seconds": threshold_seconds,
        "max_redispatch_count": max_redispatch_count,
        "candidate_count": len(candidates),
        "redispatched_count": redispatched_count,
        "alerted_count": alerted_count,
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "candidate_tasks": [asdict(item) for item in candidates],
        "handled_tasks": handled,
        "skipped_tasks": skipped,
        "errors": errors,
        "dispatch_state_file": dispatch_state_path,
    }

    summary_file = workspace / summary_path
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = str(summary_file.relative_to(workspace))

    report_file = workspace / report_path
    write_json(report_file, report)
    _append_history(workspace / history_path, report)

    return report
