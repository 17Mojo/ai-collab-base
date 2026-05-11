"""Audit terminal task state against result artifact status headers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import write_json
from .state_manager import StateManager


def _sort_by_task_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda entry: str(entry.get("task_id") or ""))

DEFAULT_REPORT_PATH = "logs/task_result_consistency_report.json"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"
TERMINAL_STATUSES = {"completed", "failed", "blocked", "cancelled"}
RESULT_STATUS_SCAN_LIMIT = 40

STATUS_KEY_PATTERN = re.compile(
    r"^(?:[-*+]\s+|\d+\.\s+)?(?P<key>\*{0,2}(?:status|状态|任务状态|执行状态|当前(?:控制面|任务|执行)?状态)\*{0,2})\s*[:：]\s*(?P<value>.+?)\s*$",
    flags=re.IGNORECASE,
)


@dataclass
class TerminalResultAuditEntry:
    task_id: str
    state_status: str
    result_header_status: str
    result_file: str
    ai_type: str
    assignee: str
    ownership_owner: str
    has_owner_lock: bool
    issue_type: str = ""
    reason: str = ""


def _load_result_text(workspace: Path, result_file: str) -> tuple[str, str]:
    candidate = Path(result_file)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    try:
        return candidate.read_text(encoding="utf-8"), ""
    except FileNotFoundError:
        return "", f"result_file not found: {result_file}"
    except OSError as exc:
        return "", f"unable to read result_file: {result_file}; error={exc}"


def _clean_status_token(value: object) -> str:
    token = str(value or "").strip()
    token = token.strip("` ")
    token = re.sub(r"[*_~`]+", "", token)
    token = re.sub(r"\s+", " ", token)
    return token.lower()


def normalize_task_status(value: object) -> str:
    token = _clean_status_token(value)
    if not token:
        return ""
    if any(marker in token for marker in ("->", "=>", "→", "⟶", "变为")):
        return ""
    if any(item in token for item in ("failed", "失败")):
        return "failed"
    if any(item in token for item in ("blocked", "阻塞", "阻断")):
        return "blocked"
    if any(item in token for item in ("cancelled", "canceled", "取消")):
        return "cancelled"
    if any(item in token for item in ("normal", "正常")):
        return "completed"
    if any(item in token for item in ("testing", "测试中", "待测试")):
        return "testing"
    if any(item in token for item in ("implementing", "implementation", "实现中", "开发中")):
        return "implementing"
    if "in progress" in token or "in_progress" in token or "进行中" in token:
        return "in_progress"
    if any(item in token for item in ("planning", "计划中")):
        return "planning"
    if any(item in token for item in ("pending", "待处理", "待执行")):
        return "pending"
    if any(item in token for item in ("completed", "complete", "done", "完成", "已完成", "全部完成", "✅")):
        return "completed"
    if token.startswith("ok") or " ok" in token or "通过" in token or "pass" in token:
        return "completed"
    return ""


def parse_result_header_status(content: str) -> str:
    if not content.strip():
        return ""

    for raw_line in content.splitlines()[:RESULT_STATUS_SCAN_LIMIT]:
        line = raw_line.strip()
        if not line:
            continue
        match = STATUS_KEY_PATTERN.match(line)
        if match:
            return normalize_task_status(match.group("value"))
    return ""


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Task Result Consistency Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.get('generated_at', '')}`")
    lines.append(f"- 工作区: `{report.get('workspace', '')}`")
    lines.append(f"- 审计任务数: `{report.get('audited_count', 0)}`")
    lines.append(f"- 一致: `{report.get('consistent_count', 0)}`")
    lines.append(f"- mismatch: `{report.get('mismatch_count', 0)}`")
    lines.append(f"- unparseable: `{report.get('unparseable_count', 0)}`")
    lines.append(f"- missing result: `{report.get('missing_result_count', 0)}`")
    lines.append("")

    issues: list[dict[str, Any]] = _sort_by_task_id(list(report.get("issues", []) or []))
    lines.append("## Issues")
    lines.append("")
    if not issues:
        lines.append("- 无")
        lines.append("")
        return "\n".join(lines)

    for item in issues:
        lines.append(
            f"- `{item.get('task_id', '')}` "
            f"issue=`{item.get('issue_type', '')}` "
            f"state=`{item.get('state_status', '')}` "
            f"result=`{item.get('result_header_status', '') or '<unparseable>'}`"
        )
        lines.append(f"  result_file: `{item.get('result_file', '')}`")
        lines.append(f"  reason: {item.get('reason', '')}")
    lines.append("")
    return "\n".join(lines)


def run_terminal_result_consistency_audit(
    *,
    workspace: Path,
    task_id: str | None = None,
    report_path: str = DEFAULT_REPORT_PATH,
    summary_path: str = DEFAULT_SUMMARY_PATH,
) -> dict[str, Any]:
    manager = StateManager(workspace_path=str(workspace))
    selected_task_id = str(task_id or "").strip()

    audited_tasks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    consistent_count = 0
    mismatch_count = 0
    unparseable_count = 0
    missing_result_count = 0

    for task in manager.get_all_tasks():
        if not isinstance(task, dict):
            continue
        current_task_id = str(task.get("task_id") or "").strip()
        if not current_task_id:
            continue
        if selected_task_id and current_task_id != selected_task_id:
            continue

        state_status = normalize_task_status(task.get("status"))
        if state_status not in TERMINAL_STATUSES:
            continue

        result_file = str(task.get("result_file") or "").strip()
        ownership = task.get("ownership") if isinstance(task.get("ownership"), dict) else {}
        entry = TerminalResultAuditEntry(
            task_id=current_task_id,
            state_status=state_status,
            result_header_status="",
            result_file=result_file,
            ai_type=str(task.get("ai_type") or "").strip().lower(),
            assignee=str(task.get("assignee") or "").strip().lower(),
            ownership_owner=str(ownership.get("owner") or "").strip().lower(),
            has_owner_lock=bool(ownership.get("lock_active", False)),
        )

        if not result_file:
            entry.issue_type = "missing_result_file"
            entry.reason = "terminal task missing result_file"
            missing_result_count += 1
            issues.append(asdict(entry))
            audited_tasks.append(asdict(entry))
            continue

        content, load_error = _load_result_text(workspace, result_file)
        if load_error:
            entry.issue_type = "missing_result_file"
            entry.reason = load_error
            missing_result_count += 1
            issues.append(asdict(entry))
            audited_tasks.append(asdict(entry))
            continue

        entry.result_header_status = parse_result_header_status(content)
        if not entry.result_header_status:
            entry.issue_type = "unparseable_result_header"
            entry.reason = "result artifact missing parseable top-level status header"
            unparseable_count += 1
            issues.append(asdict(entry))
            audited_tasks.append(asdict(entry))
            continue

        if entry.result_header_status != state_status:
            entry.issue_type = "terminal_status_mismatch"
            entry.reason = "task terminal state and result header status differ"
            mismatch_count += 1
            issues.append(asdict(entry))
            audited_tasks.append(asdict(entry))
            continue

        consistent_count += 1
        audited_tasks.append(asdict(entry))

    generated_at = datetime.now().isoformat()
    issues = _sort_by_task_id(issues)
    audited_tasks = _sort_by_task_id(audited_tasks)

    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "task_id": selected_task_id,
        "audited_count": len(audited_tasks),
        "consistent_count": consistent_count,
        "mismatch_count": mismatch_count,
        "unparseable_count": unparseable_count,
        "missing_result_count": missing_result_count,
        "issue_count": len(issues),
        "issues": issues,
        "tasks": audited_tasks,
    }

    summary_file = workspace / summary_path
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = str(summary_file.relative_to(workspace))

    report_file = workspace / report_path
    report["report_file"] = str(report_file.relative_to(workspace))
    write_json(report_file, report)
    return report
