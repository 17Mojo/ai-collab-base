"""Unit tests for daily report generator."""

import json

from ai_collab.daily_report import (
    DailyReport,
    generate_daily_report,
    print_daily_report_summary,
    write_daily_report_json,
    write_daily_report_markdown,
)


class TestDailyReport:
    """Tests for DailyReport dataclass."""

    def test_report_creation(self):
        """Test creating a daily report."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace="/test/workspace",
            ack_stats={"total_acks": 10},
            missing_ack_stats={"bridged_count": 1},
            result_consistency_stats={"audited_count": 5, "issue_count": 1},
            noop_pending_stats={"conflict_count": 2},
            pending_tasks=["TASK-001", "TASK-002"],
        )

        assert report.generated_at == "2026-03-13T07:00:00"
        assert report.workspace == "/test/workspace"
        assert report.ack_stats == {"total_acks": 10}
        assert report.missing_ack_stats == {"bridged_count": 1}
        assert report.result_consistency_stats == {"audited_count": 5, "issue_count": 1}
        assert report.noop_pending_stats == {"conflict_count": 2}
        assert report.pending_tasks == ["TASK-001", "TASK-002"]

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace="/test/workspace",
            ack_stats={"total_acks": 10},
            missing_ack_stats={"bridged_count": 1},
            result_consistency_stats={"audited_count": 5, "issue_count": 1},
            noop_pending_stats={"conflict_count": 2},
            pending_tasks=["TASK-001"],
        )

        result = report.to_dict()

        assert result["generated_at"] == "2026-03-13T07:00:00"
        assert result["workspace"] == "/test/workspace"
        assert result["ack_stats"] == {"total_acks": 10}
        assert result["missing_ack_stats"] == {"bridged_count": 1}
        assert result["result_consistency_stats"] == {"audited_count": 5, "issue_count": 1}
        assert result["noop_pending_stats"] == {"conflict_count": 2}
        assert result["pending_tasks"] == ["TASK-001"]


class TestGenerateDailyReport:
    """Tests for generate_daily_report function."""

    def test_generate_report_with_data(self, tmp_path):
        """Test generating report with data."""
        ack_stats = {
            "total_acks": 10,
            "success_count": 8,
            "failure_count": 2,
            "success_rate": 80.0,
        }
        noop_pending_stats = {
            "total_checks": 5,
            "conflict_count": 2,
            "conflict_rate": 40.0,
            "resolved_count": 1,
            "unresolved_count": 1,
        }
        missing_ack_stats = {
            "candidate_count": 1,
            "bridged_count": 1,
            "already_bridged_count": 0,
            "skipped_count": 0,
            "error_count": 0,
        }
        result_consistency_stats = {
            "audited_count": 9,
            "consistent_count": 8,
            "mismatch_count": 1,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 1,
        }
        pending_tasks = ["TASK-001", "TASK-002"]

        report = generate_daily_report(
            workspace=tmp_path,
            ack_stats=ack_stats,
            missing_ack_stats=missing_ack_stats,
            result_consistency_stats=result_consistency_stats,
            noop_pending_stats=noop_pending_stats,
            pending_tasks=pending_tasks,
        )

        assert report.workspace == str(tmp_path)
        assert report.ack_stats == ack_stats
        assert report.missing_ack_stats == missing_ack_stats
        assert report.result_consistency_stats == result_consistency_stats
        assert report.noop_pending_stats == noop_pending_stats
        assert report.pending_tasks == pending_tasks
        assert report.generated_at is not None
        assert len(report.generated_at) > 0

    def test_generate_report_without_data(self, tmp_path):
        """Test generating report without data."""
        report = generate_daily_report(workspace=tmp_path)

        assert report.workspace == str(tmp_path)
        assert report.ack_stats == {}
        assert report.missing_ack_stats == {}
        assert report.result_consistency_stats == {}
        assert report.noop_pending_stats == {}
        assert report.pending_tasks == []
        assert report.generated_at is not None
        assert len(report.generated_at) > 0


class TestWriteDailyReportJson:
    """Tests for write_daily_report_json function."""

    def test_write_json_report(self, tmp_path):
        """Test writing JSON report."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace=str(tmp_path),
            ack_stats={"total_acks": 10},
            missing_ack_stats={"bridged_count": 1},
            result_consistency_stats={"audited_count": 5, "issue_count": 1},
            noop_pending_stats={"conflict_count": 2},
            pending_tasks=["TASK-001"],
        )

        write_daily_report_json(
            report=report,
            workspace=tmp_path,
            report_path="test_report.json",
        )

        report_file = tmp_path / "test_report.json"
        assert report_file.exists()

        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        assert report_data["generated_at"] == "2026-03-13T07:00:00"
        assert report_data["workspace"] == str(tmp_path)
        assert report_data["ack_stats"] == {"total_acks": 10}
        assert report_data["missing_ack_stats"] == {"bridged_count": 1}
        assert report_data["result_consistency_stats"] == {"audited_count": 5, "issue_count": 1}
        assert report_data["noop_pending_stats"] == {"conflict_count": 2}
        assert report_data["pending_tasks"] == ["TASK-001"]


class TestWriteDailyReportMarkdown:
    """Tests for write_daily_report_markdown function."""

    def test_write_markdown_report_with_data(self, tmp_path):
        """Test writing markdown report with data."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace=str(tmp_path),
            ack_stats={
                "total_acks": 10,
                "success_count": 8,
                "failure_count": 2,
                "success_rate": 80.0,
                "bridge_record_count": 12,
                "explicit_ack_count": 3,
                "non_explicit_ack_count": 9,
                "closeout_eligible_ack_count": 10,
                "claude_explicit_ack_count": 1,
                "claude_legacy_fallback_count": 2,
            },
            missing_ack_stats={
                "candidate_count": 2,
                "bridged_count": 1,
                "already_bridged_count": 1,
                "stale_explicit_ack_count": 2,
                "other_skipped_count": 0,
                "skipped_count": 2,
                "error_count": 0,
            },
            result_consistency_stats={
                "audited_count": 9,
                "consistent_count": 8,
                "mismatch_count": 1,
                "unparseable_count": 0,
                "missing_result_count": 0,
                "issue_count": 1,
            },
            noop_pending_stats={
                "total_checks": 5,
                "conflict_count": 2,
                "conflict_rate": 40.0,
                "resolved_count": 1,
                "unresolved_count": 1,
            },
            pending_tasks=["TASK-001", "TASK-002"],
        )

        write_daily_report_markdown(
            report=report,
            workspace=tmp_path,
            report_path="test_report.md",
        )

        report_file = tmp_path / "test_report.md"
        assert report_file.exists()

        report_text = report_file.read_text(encoding="utf-8")
        assert "# Daily Report" in report_text
        assert "ACK 统计" in report_text
        assert "Receipt 闭环数: `10`" in report_text
        assert "Receipt 成功率: `80.0%`" in report_text
        assert "ACK bridge 记录数: `12`" in report_text
        assert "显式 ACK 证据数: `3`" in report_text
        assert "Claude 历史 fallback 残留: `2`" in report_text
        assert "ACK 补桥统计" in report_text
        assert "新补桥: `1`" in report_text
        assert "显式 ACK 残留: `2`" in report_text
        assert "终态结果一致性统计" in report_text
        assert "审计任务数: `9`" in report_text
        assert "mismatch: `1`" in report_text
        assert "No-Op 与 Pending 冲突统计" in report_text
        assert "冲突次数: `2`" in report_text
        assert "Pending 任务" in report_text
        assert "TASK-001" in report_text
        assert "运维操作" in report_text
        assert "ack_remediation_report.json" in report_text

    def test_write_markdown_report_without_data(self, tmp_path):
        """Test writing markdown report without data."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace=str(tmp_path),
        )

        write_daily_report_markdown(
            report=report,
            workspace=tmp_path,
            report_path="test_report.md",
        )

        report_file = tmp_path / "test_report.md"
        assert report_file.exists()

        report_text = report_file.read_text(encoding="utf-8")
        assert "# Daily Report" in report_text
        assert "ACK 统计" in report_text
        assert "- 无数据" in report_text
        assert "ACK 补桥统计" in report_text
        assert "No-Op 与 Pending 冲突统计" in report_text
        assert "Pending 任务" in report_text


class TestPrintDailyReportSummary:
    """Tests for print_daily_report_summary function."""

    def test_print_summary_with_data(self, tmp_path, capsys):
        """Test printing summary with data."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace=str(tmp_path),
            ack_stats={
                "total_acks": 10,
                "success_count": 8,
                "failure_count": 2,
                "success_rate": 80.0,
                "bridge_record_count": 12,
                "explicit_ack_count": 3,
                "non_explicit_ack_count": 9,
                "closeout_eligible_ack_count": 10,
                "claude_explicit_ack_count": 1,
                "claude_legacy_fallback_count": 2,
            },
            missing_ack_stats={
                "candidate_count": 2,
                "bridged_count": 1,
                "already_bridged_count": 1,
                "stale_explicit_ack_count": 2,
                "other_skipped_count": 0,
                "skipped_count": 2,
                "error_count": 0,
            },
            result_consistency_stats={
                "audited_count": 9,
                "consistent_count": 8,
                "mismatch_count": 1,
                "unparseable_count": 0,
                "missing_result_count": 0,
                "issue_count": 1,
            },
            noop_pending_stats={
                "total_checks": 5,
                "conflict_count": 2,
                "conflict_rate": 40.0,
                "resolved_count": 1,
                "unresolved_count": 1,
            },
            pending_tasks=["TASK-001"],
        )

        print_daily_report_summary(report=report)
        captured = capsys.readouterr()

        assert "Daily Report Summary" in captured.out
        assert "ACK Statistics:" in captured.out
        assert "Receipt Closeouts: 10" in captured.out
        assert "Receipt Success Rate: 80.0%" in captured.out
        assert "ACK Bridge Records: 12" in captured.out
        assert "Explicit ACK Evidence: 3" in captured.out
        assert "Claude Legacy Fallback: 2" in captured.out
        assert "Missing ACK Bridge Statistics:" in captured.out
        assert "Bridged: 1" in captured.out
        assert "Stale Explicit ACK: 2" in captured.out
        assert "Terminal Result Consistency:" in captured.out
        assert "Audited: 9" in captured.out
        assert "Mismatch: 1" in captured.out
        assert "No-Op and Pending Conflict Statistics:" in captured.out
        assert "Conflicts: 2" in captured.out
        assert "Pending Tasks:" in captured.out
        assert "TASK-001" in captured.out

    def test_print_summary_without_data(self, tmp_path, capsys):
        """Test printing summary without data."""
        report = DailyReport(
            generated_at="2026-03-13T07:00:00",
            workspace=str(tmp_path),
        )

        print_daily_report_summary(report=report)
        captured = capsys.readouterr()

        assert "Daily Report Summary" in captured.out
        assert "No data" in captured.out
        assert "None" in captured.out
