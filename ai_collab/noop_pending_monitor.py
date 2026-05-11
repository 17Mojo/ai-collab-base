"""No-op and pending conflict monitoring for agent receipt bridge."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class NoOpPendingAlert:
    """Alert for no-op and pending conflict."""

    timestamp: str
    assignee: str
    payload_file: str
    pending_tasks: list[str]
    message: str


@dataclass
class NoOpPendingStats:
    """Statistics for no-op and pending conflicts."""

    total_checks: int = 0
    conflict_count: int = 0
    resolved_count: int = 0
    alerts: list[NoOpPendingAlert] = field(default_factory=list)

    def record_conflict(self, alert: NoOpPendingAlert) -> None:
        """Record a conflict alert."""
        self.total_checks += 1
        self.conflict_count += 1
        self.alerts.append(alert)

    def record_resolved(self) -> None:
        """Record a resolved conflict."""
        self.resolved_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        return {
            "total_checks": self.total_checks,
            "conflict_count": self.conflict_count,
            "resolved_count": self.resolved_count,
            "unresolved_count": self.conflict_count - self.resolved_count,
            "conflict_rate": (
                round(self.conflict_count / self.total_checks * 100, 2)
                if self.total_checks > 0
                else 0.0
            ),
            "alerts": [
                {
                    "timestamp": alert.timestamp,
                    "assignee": alert.assignee,
                    "payload_file": alert.payload_file,
                    "pending_tasks": alert.pending_tasks,
                    "message": alert.message,
                }
                for alert in self.alerts
            ],
        }

    def print_summary(self) -> None:
        """Print summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("No-Op and Pending Conflict Statistics")
        print("=" * 60)
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Conflicts: {summary['conflict_count']} ({summary['conflict_rate']}%)")
        print(f"Resolved: {summary['resolved_count']}")
        print(f"Unresolved: {summary['unresolved_count']}")

        if summary['alerts']:
            print("\nConflict Alerts:")
            for i, alert in enumerate(summary['alerts'], 1):
                print(f"  {i}. {alert['timestamp']}")
                print(f"     Assignee: {alert['assignee']}")
                print(f"     Payload: {alert['payload_file']}")
                print(f"     Pending Tasks: {', '.join(alert['pending_tasks'])}")
                print(f"     Message: {alert['message']}")
        print("=" * 60)


# Global stats instance
_noop_pending_stats = NoOpPendingStats()


def get_noop_pending_stats() -> NoOpPendingStats:
    """Get global no-op and pending statistics instance."""
    return _noop_pending_stats


def reset_noop_pending_stats() -> None:
    """Reset global no-op and pending statistics."""
    global _noop_pending_stats
    _noop_pending_stats = NoOpPendingStats()


def check_noop_pending_conflict(
    *,
    payload_file: str | Path,
    assignee: str,
    pending_tasks: list[str],
    record_stats: bool = True,
) -> NoOpPendingAlert | None:
    """
    Check for no-op and pending conflict.

    Args:
        payload_file: Path to the trigger payload file
        assignee: Assignee of the payload
        pending_tasks: List of pending task IDs for this assignee
        record_stats: Whether to record this check in global statistics

    Returns:
        NoOpPendingAlert if conflict detected, None otherwise
    """
    payload_path = Path(payload_file)
    if not payload_path.exists():
        return None

    try:
        payload_text = payload_path.read_text(encoding="utf-8")
    except (OSError, IOError):
        return None

    # Check if payload is no-op (contains "当前无待派发任务")
    is_noop = "当前无待派发任务" in payload_text

    # Check for conflict: no-op payload but pending tasks exist
    if is_noop and pending_tasks:
        alert = NoOpPendingAlert(
            timestamp=datetime.now().isoformat(),
            assignee=assignee,
            payload_file=str(payload_path),
            pending_tasks=pending_tasks,
            message=(
                f"⚠️  No-Op Payload 与 Pending 任务冲突！\n"
                f"  - Payload 文件: {payload_path}\n"
                f"  - Assignee: {assignee}\n"
                f"  - Payload 状态: 无待派发任务 (no-op)\n"
                f"  - Pending 任务: {len(pending_tasks)} 个\n"
                f"  - 任务列表: {', '.join(pending_tasks)}\n"
                f"  - 可能原因: dispatch 未包含 pending 任务，或 payload 未更新\n"
                f"  - 建议操作: 重新执行 dispatch 并重新生成 payload"
            ),
        )

        if record_stats:
            get_noop_pending_stats().record_conflict(alert)

        return alert

    return None


def write_noop_pending_report(
    *,
    workspace: Path,
    report_path: str = "logs/noop_pending_conflict_report.json",
) -> None:
    """Write no-op and pending conflict report to file."""
    stats = get_noop_pending_stats()
    report = stats.get_summary()
    report["generated_at"] = datetime.now().isoformat()
    report["workspace"] = str(workspace)

    report_file = workspace / report_path
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_noop_pending_summary(
    *,
    workspace: Path,
    summary_path: str = "collaboration/monitoring/NOOP_PENDING_CONFLICT_SUMMARY_latest.md",
) -> None:
    """Write no-op and pending conflict summary to markdown file."""
    stats = get_noop_pending_stats()
    summary = stats.get_summary()
    generated_at = datetime.now().isoformat()

    lines: list[str] = []
    lines.append("# No-Op and Pending Conflict Summary（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{generated_at}`")
    lines.append(f"- 总检查次数: `{summary['total_checks']}`")
    lines.append(f"- 冲突次数: `{summary['conflict_count']}`")
    lines.append(f"- 冲突率: `{summary['conflict_rate']}%`")
    lines.append(f"- 已解决: `{summary['resolved_count']}`")
    lines.append(f"- 未解决: `{summary['unresolved_count']}`")
    lines.append("")

    if summary['alerts']:
        lines.append("## 冲突告警")
        lines.append("")
        for i, alert in enumerate(summary['alerts'], 1):
            lines.append(f"### {i}. {alert['timestamp']}")
            lines.append("")
            lines.append(f"- **Assignee**: `{alert['assignee']}`")
            lines.append(f"- **Payload**: `{alert['payload_file']}`")
            lines.append(f"- **Pending Tasks**: {', '.join(alert['pending_tasks'])}")
            lines.append("")
            lines.append("**告警消息**:")
            lines.append("")
            lines.append("```")
            lines.append(alert['message'])
            lines.append("```")
            lines.append("")
    else:
        lines.append("## 冲突告警")
        lines.append("")
        lines.append("- 无")
        lines.append("")

    lines.append("## 运维查看入口")
    lines.append("")
    lines.append("```bash")
    lines.append("# 查看详细报告")
    lines.append("cat logs/noop_pending_conflict_report.json")
    lines.append("")
    lines.append("# 查看监控摘要")
    lines.append("cat collaboration/monitoring/NOOP_PENDING_CONFLICT_SUMMARY_latest.md")
    lines.append("")
    lines.append("# 重置统计")
    lines.append("python3 -c \"from ai_collab.noop_pending_monitor import reset_noop_pending_stats; reset_noop_pending_stats()\"")
    lines.append("```")
    lines.append("")

    summary_file = workspace / summary_path
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text("\n".join(lines), encoding="utf-8")
