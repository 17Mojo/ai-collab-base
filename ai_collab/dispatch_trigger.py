"""Utilities for trigger phrase based dispatch handoff generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SECTION_HEADING = re.compile(r"^##\s+发送给\s+`[^`]+`\s+\(`(?P<assignee>[^`]+)`\)\s*$")

ACTION_ALIASES = {
    "dispatch": "dispatch",
    "d": "dispatch",
    "派单": "dispatch",
}

TARGET_ALIASES = {
    "all": "all",
    "*": "all",
    "claude": "claude_code",
    "claude_code": "claude_code",
    "c": "claude_code",
    "codearts": "codearts_agent",
    "codearts_agent": "codearts_agent",
    "a": "codearts_agent",
    "codex": "codex",
    "x": "codex",
}

DISPLAY_NAME = {
    "claude_code": "Claude",
    "codearts_agent": "CodeArts",
    "codex": "Codex",
}

RUN_HINT = {
    "claude_code": "C.RUN",
    "codearts_agent": "A.RUN",
    "codex": "X.RUN",
}

ACK_HINT = {
    "claude_code": "C.ACK",
    "codearts_agent": "A.ACK",
    "codex": "X.ACK",
}

REFRESH_TRIGGER_PHRASES = {
    "claude_code": "2X DISPATCH Claude",
    "codearts_agent": "2X DISPATCH CodeArts",
    "codex": "2X DISPATCH CODEX",
    "all": "2X DISPATCH",
}


@dataclass(frozen=True)
class TriggerIntent:
    """Normalized trigger intent from a phrase like `2X DISPATCH CLAUDE`."""

    keyword: str
    action: str
    target: str
    raw_phrase: str


def parse_trigger_phrase(phrase: str, *, keyword: str = "2X") -> TriggerIntent:
    """Parse and validate trigger phrase."""
    raw = (phrase or "").strip()
    if not raw:
        raise ValueError("trigger phrase is empty")

    parts = [token.strip() for token in raw.split() if token.strip()]
    if not parts:
        raise ValueError("trigger phrase is empty")
    if parts[0].upper() != keyword.upper():
        raise ValueError(f"trigger keyword mismatch: expected {keyword}")

    tail = parts[1:]
    action = "dispatch"
    target = "all"

    if not tail:
        return TriggerIntent(keyword=keyword, action=action, target=target, raw_phrase=raw)

    first = tail[0].lower()
    if first in ACTION_ALIASES:
        action = ACTION_ALIASES[first]
        tail = tail[1:]
    elif first in TARGET_ALIASES:
        target = TARGET_ALIASES[first]
        tail = tail[1:]
    else:
        raise ValueError(f"unsupported trigger token: {tail[0]}")

    if tail:
        second = tail[0].lower()
        if second not in TARGET_ALIASES:
            raise ValueError(f"unsupported trigger target: {tail[0]}")
        target = TARGET_ALIASES[second]
        tail = tail[1:]

    if tail:
        raise ValueError(f"unexpected trigger tokens: {' '.join(tail)}")

    return TriggerIntent(keyword=keyword, action=action, target=target, raw_phrase=raw)


def split_orders_by_assignee(markdown: str) -> dict[str, str]:
    """Split dispatch orders markdown into assignee-scoped sections."""
    lines = (markdown or "").splitlines()
    sections: dict[str, list[str]] = {}
    current_assignee: str | None = None
    buffer: list[str] = []

    def _flush() -> None:
        nonlocal buffer, current_assignee
        if current_assignee is None:
            return
        sections[current_assignee] = list(buffer)
        buffer = []
        current_assignee = None

    for line in lines:
        match = SECTION_HEADING.match(line.strip())
        if match:
            _flush()
            current_assignee = match.group("assignee").strip()
            buffer = [line]
            continue
        if current_assignee is not None:
            buffer.append(line)

    _flush()
    return {assignee: "\n".join(chunk).strip() for assignee, chunk in sections.items()}


def build_payload_refresh_command(assignee: str | None) -> str:
    """Return a syntactically valid freshness-repair command for one assignee."""
    normalized = str(assignee or "").strip().lower()
    phrase = REFRESH_TRIGGER_PHRASES.get(normalized)
    if not phrase:
        return "python3 -m ai_collab.cli dispatch"
    return f"python3 -m ai_collab.cli trigger --phrase '{phrase}' --target {normalized}"


def build_handoff_payload(
    *,
    assignee: str,
    trigger_phrase: str,
    orders_relpath: str,
    section_markdown: str | None,
    generated_at: str | None = None,
) -> str:
    """Build a ready-to-send payload for one assignee session."""
    timestamp = generated_at or datetime.now().isoformat(timespec="seconds")
    name = DISPLAY_NAME.get(assignee, assignee)
    refresh_command = build_payload_refresh_command(assignee)
    lines: list[str] = []
    lines.append("# Agent Session Dispatch Payload（自动生成）")
    lines.append("")
    lines.append(f"- Trigger: `{trigger_phrase}`")
    lines.append(f"- Assignee: `{assignee}` ({name})")
    lines.append(f"- GeneratedAt: `{timestamp}`")
    lines.append(f"- SourceOrders: `{orders_relpath}`")
    lines.append("")
    lines.append("## 新鲜度校验（必须执行）")
    lines.append("")
    lines.append("在执行任务前，必须先校验本 payload 的新鲜度：")
    lines.append("")
    lines.append("```bash")
    lines.append("# 1. 检查 dispatch report 中的 generated_at")
    lines.append("cat logs/task_dispatch_report.json | grep generated_at")
    lines.append("")
    lines.append("# 2. 对比本 payload 的 GeneratedAt 与 dispatch report")
    lines.append("# 如果时间差 > 5 分钟，则 payload 已过期")
    lines.append("")
    lines.append("# 3. 如果 payload 已过期，执行一键修复：")
    lines.append(refresh_command)
    lines.append("```")
    lines.append("")
    lines.append("**判定规则**：")
    lines.append("- ✅ 新鲜：时间差 ≤ 5 分钟")
    lines.append("- ⚠️  过期：时间差 > 5 分钟")
    lines.append("")
    lines.append("**过期处理**：")
    lines.append("1. 立即停止执行")
    lines.append("2. 执行一键修复命令重新生成 payload")
    lines.append("3. 使用新生成的 payload 继续执行")
    lines.append("")
    lines.append("请将本文件完整发送到对应 Agent 会话，避免手工抽段造成漏项。")
    lines.append("")
    run_hint = RUN_HINT.get(assignee, "RUN")
    ack_hint = ACK_HINT.get(assignee, "ACK")
    lines.append("## 会话执行约束（必须遵守）")
    lines.append("")
    lines.append(f"- 收到 `{run_hint}` 后必须先读取本文件，再执行任务块。")
    lines.append("- 系统级 RUN 只允许执行：`python3 -m ai_collab.cli run`（内置工作区门禁）。")
    lines.append(
        "- 禁止改为执行全局串联命令：`python3 -m ai_collab.cli dispatch && python3 -m ai_collab.cli receipt && python3 -m ai_collab.cli benefit`。"
    )
    lines.append(
        f"- 完成后仅回复一行 ACK；优先使用任务块中的 `python3 -m ai_collab.cli ack ...` 生成并原样回复：`{ack_hint}|task=<ids>|status=<ok/blocked/noop>|result=<paths>`。"
    )
    lines.append("")

    payload_section = (section_markdown or "").strip()
    if payload_section:
        lines.append(payload_section)
    else:
        lines.append(f"## 发送给 `{name}` (`{assignee}`)")
        lines.append("")
        lines.append("当前无待派发任务。")
        lines.append(f"请回复：`{ack_hint}|task=none|status=noop|result=none`")

    lines.append("")
    return "\n".join(lines)


def check_payload_freshness(
    *,
    payload_generated_at: str,
    dispatch_report_path: str | Path,
    assignee: str | None = None,
    threshold_minutes: int = 5,
    record_stats: bool = True,
) -> dict:
    """
    Check if a trigger payload is fresh by comparing with dispatch report.

    Args:
        payload_generated_at: ISO timestamp from payload GeneratedAt field
        dispatch_report_path: Path to dispatch report JSON file
        threshold_minutes: Maximum allowed age difference in minutes
        record_stats: Whether to record this check in global statistics

    Returns:
        dict with keys: is_fresh, age_minutes, dispatch_generated_at, warning, fix_command
    """
    refresh_command = build_payload_refresh_command(assignee)
    try:
        # Parse payload timestamp
        payload_time = datetime.fromisoformat(payload_generated_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        result = {
            "is_fresh": False,
            "age_minutes": None,
            "dispatch_generated_at": None,
            "warning": f"无法解析 payload 时间戳: {payload_generated_at}",
            "fix_command": None,
        }
        if record_stats:
            get_freshness_stats().record_check(result)
        return result

    # Read dispatch report
    try:
        report_path = Path(dispatch_report_path)
        if not report_path.exists():
            result = {
                "is_fresh": False,
                "age_minutes": None,
                "dispatch_generated_at": None,
                "warning": f"Dispatch report 不存在: {report_path}",
                "fix_command": refresh_command,
            }
            if record_stats:
                get_freshness_stats().record_check(result)
            return result

        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        dispatch_generated_at = report_data.get("generated_at")
        if not dispatch_generated_at:
            result = {
                "is_fresh": False,
                "age_minutes": None,
                "dispatch_generated_at": None,
                "warning": "Dispatch report 缺少 generated_at 字段",
                "fix_command": refresh_command,
            }
            if record_stats:
                get_freshness_stats().record_check(result)
            return result

        # Parse dispatch timestamp
        dispatch_time = datetime.fromisoformat(dispatch_generated_at.replace("Z", "+00:00"))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        result = {
            "is_fresh": False,
            "age_minutes": None,
            "dispatch_generated_at": None,
            "warning": f"无法读取 dispatch report: {exc}",
            "fix_command": refresh_command,
        }
        if record_stats:
            get_freshness_stats().record_check(result)
        return result

    # Calculate age difference
    age_delta = abs(payload_time - dispatch_time)
    age_minutes = age_delta.total_seconds() / 60.0
    is_fresh = age_minutes <= threshold_minutes

    # Build result
    result = {
        "is_fresh": is_fresh,
        "age_minutes": round(age_minutes, 2),
        "payload_generated_at": payload_generated_at,
        "dispatch_generated_at": dispatch_generated_at,
        "threshold_minutes": threshold_minutes,
        "warning": None,
        "fix_command": None,
    }

    if not is_fresh:
        result["warning"] = (
            f"⚠️  Payload 已过期！\n"
            f"  - Payload 生成时间: {payload_generated_at}\n"
            f"  - Dispatch 生成时间: {dispatch_generated_at}\n"
            f"  - 时间差: {age_minutes:.2f} 分钟 (阈值: {threshold_minutes} 分钟)\n"
            f"  - 请立即执行一键修复命令重新生成 payload"
        )
        result["fix_command"] = refresh_command

    if record_stats:
        get_freshness_stats().record_check(result)

    return result


class FreshnessStats:
    """Statistics tracker for payload freshness checks."""

    def __init__(self):
        self.total_checks = 0
        self.fresh_count = 0
        self.stale_count = 0
        self.error_count = 0
        self.stale_events: list[dict] = []

    def record_check(self, result: dict) -> None:
        """Record a freshness check result."""
        self.total_checks += 1

        if result.get("is_fresh") is True:
            self.fresh_count += 1
        elif result.get("is_fresh") is False:
            self.stale_count += 1
            self.stale_events.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "payload_generated_at": result.get("payload_generated_at"),
                    "dispatch_generated_at": result.get("dispatch_generated_at"),
                    "age_minutes": result.get("age_minutes"),
                }
            )
        else:
            self.error_count += 1

    def get_summary(self) -> dict:
        """Get summary statistics."""
        return {
            "total_checks": self.total_checks,
            "fresh_count": self.fresh_count,
            "stale_count": self.stale_count,
            "error_count": self.error_count,
            "fresh_rate": (
                round(self.fresh_count / self.total_checks * 100, 2)
                if self.total_checks > 0
                else 0.0
            ),
            "stale_rate": (
                round(self.stale_count / self.total_checks * 100, 2)
                if self.total_checks > 0
                else 0.0
            ),
            "stale_events": self.stale_events,
        }

    def print_summary(self) -> None:
        """Print summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("Payload Freshness Statistics")
        print("=" * 60)
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Fresh: {summary['fresh_count']} ({summary['fresh_rate']}%)")
        print(f"Stale: {summary['stale_count']} ({summary['stale_rate']}%)")
        print(f"Errors: {summary['error_count']}")

        if summary["stale_events"]:
            print("\nStale Events:")
            for i, event in enumerate(summary["stale_events"], 1):
                print(f"  {i}. {event['timestamp']}")
                print(f"     Age: {event['age_minutes']} minutes")
                print(f"     Payload: {event['payload_generated_at']}")
                print(f"     Dispatch: {event['dispatch_generated_at']}")
        print("=" * 60)


# Global stats instance
_freshness_stats = FreshnessStats()


def get_freshness_stats() -> FreshnessStats:
    """Get global freshness statistics instance."""
    return _freshness_stats


def reset_freshness_stats() -> None:
    """Reset global freshness statistics."""
    global _freshness_stats
    _freshness_stats = FreshnessStats()
