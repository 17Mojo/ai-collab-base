"""Daily report generator for ACK, no-op, and pending conflicts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DailyReport:
    """Daily report for ACK, no-op, and pending conflicts."""

    generated_at: str
    workspace: str
    ack_stats: dict[str, Any] = field(default_factory=dict)
    missing_ack_stats: dict[str, Any] = field(default_factory=dict)
    result_consistency_stats: dict[str, Any] = field(default_factory=dict)
    noop_pending_stats: dict[str, Any] = field(default_factory=dict)
    pending_tasks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "generated_at": self.generated_at,
            "workspace": self.workspace,
            "ack_stats": self.ack_stats,
            "missing_ack_stats": self.missing_ack_stats,
            "result_consistency_stats": self.result_consistency_stats,
            "noop_pending_stats": self.noop_pending_stats,
            "pending_tasks": self.pending_tasks,
        }


def generate_daily_report(
    *,
    workspace: Path,
    ack_stats: dict[str, Any] | None = None,
    missing_ack_stats: dict[str, Any] | None = None,
    result_consistency_stats: dict[str, Any] | None = None,
    noop_pending_stats: dict[str, Any] | None = None,
    pending_tasks: list[str] | None = None,
) -> DailyReport:
    """
    Generate daily report for ACK, no-op, and pending conflicts.

    Args:
        workspace: Workspace path
        ack_stats: ACK statistics (optional)
        result_consistency_stats: terminal result consistency statistics (optional)
        noop_pending_stats: No-op and pending conflict statistics (optional)
        pending_tasks: List of pending task IDs (optional)

    Returns:
        DailyReport instance
    """
    return DailyReport(
        generated_at=datetime.now().isoformat(),
        workspace=str(workspace),
        ack_stats=ack_stats or {},
        missing_ack_stats=missing_ack_stats or {},
        result_consistency_stats=result_consistency_stats or {},
        noop_pending_stats=noop_pending_stats or {},
        pending_tasks=pending_tasks or [],
    )


def write_daily_report_json(
    *,
    report: DailyReport,
    workspace: Path,
    report_path: str = "logs/daily_report.json",
) -> None:
    """Write daily report to JSON file."""
    report_file = workspace / report_path
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def write_daily_report_markdown(
    *,
    report: DailyReport,
    workspace: Path,
    report_path: str = "collaboration/monitoring/DAILY_REPORT_latest.md",
) -> None:
    """Write daily report to markdown file."""
    lines: list[str] = []
    lines.append("# Daily Report（自动生成）")
    lines.append("")
    lines.append(f"- 生成时间: `{report.generated_at}`")
    lines.append(f"- 工作区: `{report.workspace}`")
    lines.append("")

    # ACK Statistics
    lines.append("## ACK 统计")
    lines.append("")
    if report.ack_stats:
        lines.append(f"- Receipt 闭环数: `{report.ack_stats.get('total_acks', 0)}`")
        lines.append(f"- Receipt 成功数: `{report.ack_stats.get('success_count', 0)}`")
        lines.append(f"- Receipt 失败数: `{report.ack_stats.get('failure_count', 0)}`")
        lines.append(f"- Receipt 成功率: `{report.ack_stats.get('success_rate', 0.0)}%`")
        if "bridge_record_count" in report.ack_stats:
            lines.append(f"- ACK bridge 记录数: `{report.ack_stats.get('bridge_record_count', 0)}`")
        if "explicit_ack_count" in report.ack_stats:
            lines.append(f"- 显式 ACK 证据数: `{report.ack_stats.get('explicit_ack_count', 0)}`")
        if "non_explicit_ack_count" in report.ack_stats:
            lines.append(f"- 非显式 bridge 记录数: `{report.ack_stats.get('non_explicit_ack_count', 0)}`")
        if "closeout_eligible_ack_count" in report.ack_stats:
            lines.append(f"- 可闭环 ACK 记录数: `{report.ack_stats.get('closeout_eligible_ack_count', 0)}`")
        if "claude_explicit_ack_count" in report.ack_stats:
            lines.append(f"- Claude 显式 ACK: `{report.ack_stats.get('claude_explicit_ack_count', 0)}`")
        if "claude_legacy_fallback_count" in report.ack_stats:
            lines.append(f"- Claude 历史 fallback 残留: `{report.ack_stats.get('claude_legacy_fallback_count', 0)}`")
    else:
        lines.append("- 无数据")
    lines.append("")

    # Missing ACK bridge statistics
    lines.append("## ACK 补桥统计")
    lines.append("")
    if report.missing_ack_stats:
        lines.append(f"- 候选任务: `{report.missing_ack_stats.get('candidate_count', 0)}`")
        lines.append(f"- 新补桥: `{report.missing_ack_stats.get('bridged_count', 0)}`")
        lines.append(f"- 已补桥跳过: `{report.missing_ack_stats.get('already_bridged_count', 0)}`")
        if "stale_explicit_ack_count" in report.missing_ack_stats:
            lines.append(f"- 显式 ACK 残留: `{report.missing_ack_stats.get('stale_explicit_ack_count', 0)}`")
        if "other_skipped_count" in report.missing_ack_stats:
            lines.append(f"- 其他规则跳过: `{report.missing_ack_stats.get('other_skipped_count', 0)}`")
        lines.append(f"- 规则跳过: `{report.missing_ack_stats.get('skipped_count', 0)}`")
        lines.append(f"- 错误数: `{report.missing_ack_stats.get('error_count', 0)}`")
    else:
        lines.append("- 无数据")
    lines.append("")

    # Result consistency statistics
    lines.append("## 终态结果一致性统计")
    lines.append("")
    if report.result_consistency_stats:
        lines.append(f"- 审计任务数: `{report.result_consistency_stats.get('audited_count', 0)}`")
        lines.append(f"- 一致任务数: `{report.result_consistency_stats.get('consistent_count', 0)}`")
        lines.append(f"- mismatch: `{report.result_consistency_stats.get('mismatch_count', 0)}`")
        lines.append(f"- unparseable: `{report.result_consistency_stats.get('unparseable_count', 0)}`")
        lines.append(f"- missing_result: `{report.result_consistency_stats.get('missing_result_count', 0)}`")
        lines.append(f"- issue_count: `{report.result_consistency_stats.get('issue_count', 0)}`")
    else:
        lines.append("- 无数据")
    lines.append("")

    # No-Op and Pending Conflict Statistics
    lines.append("## No-Op 与 Pending 冲突统计")
    lines.append("")
    if report.noop_pending_stats:
        lines.append(f"- 总检查次数: `{report.noop_pending_stats.get('total_checks', 0)}`")
        lines.append(f"- 冲突次数: `{report.noop_pending_stats.get('conflict_count', 0)}`")
        lines.append(f"- 冲突率: `{report.noop_pending_stats.get('conflict_rate', 0.0)}%`")
        lines.append(f"- 已解决: `{report.noop_pending_stats.get('resolved_count', 0)}`")
        lines.append(f"- 未解决: `{report.noop_pending_stats.get('unresolved_count', 0)}`")
    else:
        lines.append("- 无数据")
    lines.append("")

    # Pending Tasks
    lines.append("## Pending 任务")
    lines.append("")
    if report.pending_tasks:
        for task_id in report.pending_tasks:
            lines.append(f"- `{task_id}`")
    else:
        lines.append("- 无")
    lines.append("")

    # Operations
    lines.append("## 运维操作")
    lines.append("")
    lines.append("```bash")
    lines.append("# 查看详细报告")
    lines.append("cat logs/daily_report.json")
    lines.append("")
    lines.append("# 查看监控摘要")
    lines.append("cat collaboration/monitoring/DAILY_REPORT_latest.md")
    lines.append("")
    lines.append("# 查看 ACK 详情")
    lines.append("cat logs/task_receipt_report.json")
    lines.append("")
    lines.append("# 查看 ACK 补桥详情")
    lines.append("cat logs/missing_ack_report.json")
    lines.append("")
    lines.append("# 查看 ACK remediation 详情")
    lines.append("cat logs/ack_remediation_report.json")
    lines.append("")
    lines.append("# 查看冲突详情")
    lines.append("cat logs/noop_pending_conflict_report.json")
    lines.append("```")
    lines.append("")

    report_file = workspace / report_path
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines), encoding="utf-8")


def print_daily_report_summary(*, report: DailyReport) -> None:
    """Print daily report summary to console."""
    print("\n" + "=" * 60)
    print("Daily Report Summary")
    print("=" * 60)
    print(f"Generated At: {report.generated_at}")
    print(f"Workspace: {report.workspace}")
    print("")

    print("ACK Statistics:")
    if report.ack_stats:
        print(f"  Receipt Closeouts: {report.ack_stats.get('total_acks', 0)}")
        print(f"  Receipt Success: {report.ack_stats.get('success_count', 0)}")
        print(f"  Receipt Failure: {report.ack_stats.get('failure_count', 0)}")
        print(f"  Receipt Success Rate: {report.ack_stats.get('success_rate', 0.0)}%")
        if "bridge_record_count" in report.ack_stats:
            print(f"  ACK Bridge Records: {report.ack_stats.get('bridge_record_count', 0)}")
        if "explicit_ack_count" in report.ack_stats:
            print(f"  Explicit ACK Evidence: {report.ack_stats.get('explicit_ack_count', 0)}")
        if "non_explicit_ack_count" in report.ack_stats:
            print(f"  Non-explicit Bridge Records: {report.ack_stats.get('non_explicit_ack_count', 0)}")
        if "closeout_eligible_ack_count" in report.ack_stats:
            print(f"  Closeout-Eligible ACK Records: {report.ack_stats.get('closeout_eligible_ack_count', 0)}")
        if "claude_explicit_ack_count" in report.ack_stats:
            print(f"  Claude Explicit ACK: {report.ack_stats.get('claude_explicit_ack_count', 0)}")
        if "claude_legacy_fallback_count" in report.ack_stats:
            print(f"  Claude Legacy Fallback: {report.ack_stats.get('claude_legacy_fallback_count', 0)}")
    else:
        print("  No data")
    print("")

    print("Missing ACK Bridge Statistics:")
    if report.missing_ack_stats:
        print(f"  Candidates: {report.missing_ack_stats.get('candidate_count', 0)}")
        print(f"  Bridged: {report.missing_ack_stats.get('bridged_count', 0)}")
        print(f"  Already Bridged: {report.missing_ack_stats.get('already_bridged_count', 0)}")
        if "stale_explicit_ack_count" in report.missing_ack_stats:
            print(f"  Stale Explicit ACK: {report.missing_ack_stats.get('stale_explicit_ack_count', 0)}")
        if "other_skipped_count" in report.missing_ack_stats:
            print(f"  Other Skipped: {report.missing_ack_stats.get('other_skipped_count', 0)}")
        print(f"  Skipped: {report.missing_ack_stats.get('skipped_count', 0)}")
        print(f"  Errors: {report.missing_ack_stats.get('error_count', 0)}")
    else:
        print("  No data")
    print("")

    print("Terminal Result Consistency:")
    if report.result_consistency_stats:
        print(f"  Audited: {report.result_consistency_stats.get('audited_count', 0)}")
        print(f"  Consistent: {report.result_consistency_stats.get('consistent_count', 0)}")
        print(f"  Mismatch: {report.result_consistency_stats.get('mismatch_count', 0)}")
        print(f"  Unparseable: {report.result_consistency_stats.get('unparseable_count', 0)}")
        print(f"  Missing Result: {report.result_consistency_stats.get('missing_result_count', 0)}")
        print(f"  Issue Count: {report.result_consistency_stats.get('issue_count', 0)}")
    else:
        print("  No data")
    print("")

    print("No-Op and Pending Conflict Statistics:")
    if report.noop_pending_stats:
        print(f"  Total Checks: {report.noop_pending_stats.get('total_checks', 0)}")
        print(f"  Conflicts: {report.noop_pending_stats.get('conflict_count', 0)}")
        print(f"  Conflict Rate: {report.noop_pending_stats.get('conflict_rate', 0.0)}%")
        print(f"  Resolved: {report.noop_pending_stats.get('resolved_count', 0)}")
        print(f"  Unresolved: {report.noop_pending_stats.get('unresolved_count', 0)}")
    else:
        print("  No data")
    print("")

    print("Pending Tasks:")
    if report.pending_tasks:
        for task_id in report.pending_tasks:
            print(f"  - {task_id}")
    else:
        print("  None")
    print("=" * 60)
