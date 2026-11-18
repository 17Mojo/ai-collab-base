"""Audit terminal task state against result artifact status headers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .ack_protocol import DEFAULT_ACK_BRIDGE_STATE_PATH, load_ack_bridge_state, write_json
from .state_manager import StateManager


def _sort_by_task_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda entry: str(entry.get("task_id") or ""))


DEFAULT_REPORT_PATH = "logs/task_result_consistency_report.json"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"

TERMINAL_STATUSES = {"completed", "failed", "blocked", "cancelled"}

# ── 产物要求按状态分流（台账 N42）──────────────────────────────────────────
# 修复前：只要状态在 TERMINAL_STATUSES 里就要求产物，于是「取消」的任务
# 也必须交一份交付物——取消的语义恰恰是「不交付」。结果是任何一次取消
# 都会让审计永久挂一条 missing_result_file，真缺产物时反而被当成老噪音。
#
# 修复后：
#   completed        —— 声称「做完并交付」，**必须**有产物；
#   failed / blocked —— 失败结局，允许没有产物，但**必须留下原因**（notes 非空），
#                       否则无从区分「没做」与「没记」；
#   cancelled        —— 主动放弃，不要求产物也不要求原因。
ARTIFACT_REQUIRED_TERMINAL_STATUSES = {"completed"}
ARTIFACT_OPTIONAL_TERMINAL_STATUSES = {"failed", "blocked", "cancelled"}
FAILURE_REASON_REQUIRED_STATUSES = {"failed", "blocked"}

RESULT_STATUS_SCAN_LIMIT = 40

# ACK 行里的 status 取值（PROTOCOL：ok / blocked / noop）。
_ACK_STATUS_RE = re.compile(r"\|status=([A-Za-z]+)\|")

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


def load_ok_acked_tasks(
    workspace: Path, *, state_path: str = DEFAULT_ACK_BRIDGE_STATE_PATH
) -> dict[str, dict[str, Any]]:
    """读显式 ACK 桥状态，只返回 `status=ok` 的条目 `{task_id: item}`。

    N42 的另一半：`ack` 成功会写入桥状态，此后看门狗把这任务视作「已 ACK」而排除，
    一致性审计又只看终态——于是「已 ACK 但产物其实不存在、任务停在 testing」
    同时躲开两张网，可以无限期无人发现。这里把 ACK 状态读出来供非终态任务对照。
    """
    try:
        _state_file, _payload, items = load_ack_bridge_state(workspace, state_path=state_path)
    except (OSError, ValueError):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for task_id, item in (items or {}).items():
        if not isinstance(item, dict):
            continue
        match = _ACK_STATUS_RE.search(str(item.get("ack_line") or ""))
        status = (match.group(1) if match else "").strip().lower()
        if status in {"ok", "completed"}:
            result[str(task_id)] = item
    return result


def _has_recorded_reason(task: dict[str, Any]) -> bool:
    """失败类任务是否留下了「为什么没交付」的记录。

    只认笔记与显式原因字段；不认 description——那是「要做什么」，不是「为什么没做成」。
    """
    notes = task.get("notes")
    if isinstance(notes, list) and any(str(note).strip() for note in notes):
        return True
    return any(str(task.get(key) or "").strip() for key in ("reason", "conclusion", "detail"))


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
    lines.append(f"- 允许无产物: `{report.get('artifact_optional_count', 0)}`")
    lines.append(f"- 失败缺原因: `{report.get('missing_failure_reason_count', 0)}`")
    lines.append(f"- 已 ACK 无产物: `{report.get('ack_without_artifact_count', 0)}`")
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
    artifact_optional_count = 0
    missing_failure_reason_count = 0
    ack_without_artifact_count = 0

    ok_acked = load_ok_acked_tasks(workspace)

    def _make_entry(current_task_id: str, state_status: str, task: dict[str, Any]) -> TerminalResultAuditEntry:
        ownership_raw = task.get("ownership")
        ownership: dict[str, Any] = ownership_raw if isinstance(ownership_raw, dict) else {}
        return TerminalResultAuditEntry(
            task_id=current_task_id,
            state_status=state_status,
            result_header_status="",
            result_file=str(task.get("result_file") or "").strip(),
            ai_type=str(task.get("ai_type") or "").strip().lower(),
            assignee=str(task.get("assignee") or "").strip().lower(),
            ownership_owner=str(ownership.get("owner") or "").strip().lower(),
            has_owner_lock=bool(ownership.get("lock_active", False)),
        )

    def _record_optional_artifact_absence(
        entry: TerminalResultAuditEntry, state_status: str, task: dict[str, Any], detail: str
    ) -> None:
        """终态但属「允许无产物」的状态：按需检查是否留下了原因（N42）。"""
        nonlocal artifact_optional_count, missing_failure_reason_count
        artifact_optional_count += 1
        if state_status in FAILURE_REASON_REQUIRED_STATUSES and not _has_recorded_reason(task):
            entry.issue_type = "missing_failure_reason"
            entry.reason = f"{state_status} task has no result artifact and no recorded reason; {detail}"
            missing_failure_reason_count += 1
            issues.append(asdict(entry))
        audited_tasks.append(asdict(entry))

    for task in manager.get_all_tasks():
        if not isinstance(task, dict):
            continue
        current_task_id = str(task.get("task_id") or "").strip()
        if not current_task_id:
            continue
        if selected_task_id and current_task_id != selected_task_id:
            continue

        state_status = normalize_task_status(task.get("status"))

        # ── 非终态：只审「已显式 ACK 却拿不出产物」这一种矛盾（N42 另一半）──
        if state_status not in TERMINAL_STATUSES:
            ack_item = ok_acked.get(current_task_id)
            if not ack_item:
                continue
            entry = _make_entry(current_task_id, state_status, task)
            if not entry.result_file:
                entry.issue_type = "ack_without_artifact"
                entry.reason = (
                    "explicit ACK status=ok, but task declares no result_file and state is "
                    f"still '{state_status}' (watchdog excludes ACKed tasks; terminal audit skips non-terminal)"
                )
                ack_without_artifact_count += 1
                issues.append(asdict(entry))
                audited_tasks.append(asdict(entry))
                continue
            content, load_error = _load_result_text(workspace, entry.result_file)
            if load_error:
                entry.issue_type = "ack_without_artifact"
                entry.reason = (
                    f"explicit ACK status=ok, but artifact unusable ({load_error}); state is still '{state_status}'"
                )
                ack_without_artifact_count += 1
                issues.append(asdict(entry))
                audited_tasks.append(asdict(entry))
                continue
            # 产物在、只是还没被 receipt 收口 —— 正常过渡态。
            entry.result_header_status = parse_result_header_status(content)
            consistent_count += 1
            audited_tasks.append(asdict(entry))
            continue

        entry = _make_entry(current_task_id, state_status, task)

        if not entry.result_file:
            if state_status in ARTIFACT_REQUIRED_TERMINAL_STATUSES:
                entry.issue_type = "missing_result_file"
                entry.reason = "terminal task missing result_file"
                missing_result_count += 1
                issues.append(asdict(entry))
                audited_tasks.append(asdict(entry))
            else:
                _record_optional_artifact_absence(entry, state_status, task, "result_file is empty")
            continue

        content, load_error = _load_result_text(workspace, entry.result_file)
        if load_error:
            if state_status in ARTIFACT_REQUIRED_TERMINAL_STATUSES:
                entry.issue_type = "missing_result_file"
                entry.reason = load_error
                missing_result_count += 1
                issues.append(asdict(entry))
                audited_tasks.append(asdict(entry))
            else:
                _record_optional_artifact_absence(entry, state_status, task, load_error)
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
        "artifact_optional_count": artifact_optional_count,
        "missing_failure_reason_count": missing_failure_reason_count,
        "ack_without_artifact_count": ack_without_artifact_count,
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
