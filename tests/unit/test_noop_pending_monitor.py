"""Unit tests for no-op and pending conflict monitoring."""

import json

from ai_collab.noop_pending_monitor import (
    NoOpPendingAlert,
    NoOpPendingStats,
    check_noop_pending_conflict,
    get_noop_pending_stats,
    reset_noop_pending_stats,
    write_noop_pending_report,
    write_noop_pending_summary,
)


class TestNoOpPendingAlert:
    """Tests for NoOpPendingAlert dataclass."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001", "TASK-002"],
            message="Test alert",
        )

        assert alert.timestamp == "2026-03-12T12:00:00"
        assert alert.assignee == "claude_code"
        assert alert.payload_file == "test.md"
        assert alert.pending_tasks == ["TASK-001", "TASK-002"]
        assert alert.message == "Test alert"


class TestNoOpPendingStats:
    """Tests for NoOpPendingStats class."""

    def test_record_conflict(self):
        """Test recording a conflict."""
        stats = NoOpPendingStats()
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test",
        )

        stats.record_conflict(alert)

        assert stats.total_checks == 1
        assert stats.conflict_count == 1
        assert len(stats.alerts) == 1

    def test_record_resolved(self):
        """Test recording a resolved conflict."""
        stats = NoOpPendingStats()
        stats.record_resolved()

        assert stats.resolved_count == 1

    def test_get_summary(self):
        """Test getting summary statistics."""
        stats = NoOpPendingStats()
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test",
        )
        stats.record_conflict(alert)
        stats.record_resolved()

        summary = stats.get_summary()

        assert summary["total_checks"] == 1
        assert summary["conflict_count"] == 1
        assert summary["resolved_count"] == 1
        assert summary["unresolved_count"] == 0
        assert summary["conflict_rate"] == 100.0
        assert len(summary["alerts"]) == 1

    def test_get_summary_empty(self):
        """Test getting summary with no conflicts."""
        stats = NoOpPendingStats()
        summary = stats.get_summary()

        assert summary["total_checks"] == 0
        assert summary["conflict_count"] == 0
        assert summary["conflict_rate"] == 0.0

    def test_print_summary(self, capsys):
        """Test printing summary to console."""
        stats = NoOpPendingStats()
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test alert",
        )
        stats.record_conflict(alert)

        stats.print_summary()
        captured = capsys.readouterr()

        assert "No-Op and Pending Conflict Statistics" in captured.out
        assert "Total Checks: 1" in captured.out
        assert "Conflicts: 1 (100.0%)" in captured.out
        assert "Conflict Alerts:" in captured.out


class TestCheckNoOpPendingConflict:
    """Tests for check_noop_pending_conflict function."""

    def test_conflict_detected(self, tmp_path):
        """Test detecting a conflict."""
        # Create no-op payload
        payload_file = tmp_path / "payload.md"
        payload_file.write_text("当前无待派发任务\n")

        alert = check_noop_pending_conflict(
            payload_file=payload_file,
            assignee="claude_code",
            pending_tasks=["TASK-001", "TASK-002"],
            record_stats=False,
        )

        assert alert is not None
        assert alert.assignee == "claude_code"
        assert alert.pending_tasks == ["TASK-001", "TASK-002"]
        assert "No-Op Payload 与 Pending 任务冲突" in alert.message

    def test_no_conflict_with_tasks(self, tmp_path):
        """Test no conflict when payload has tasks."""
        # Create payload with tasks
        payload_file = tmp_path / "payload.md"
        payload_file.write_text("## 发送给 Claude\n\nTASK-001\n")

        alert = check_noop_pending_conflict(
            payload_file=payload_file,
            assignee="claude_code",
            pending_tasks=["TASK-001"],
            record_stats=False,
        )

        assert alert is None

    def test_no_conflict_no_pending(self, tmp_path):
        """Test no conflict when no pending tasks."""
        # Create no-op payload
        payload_file = tmp_path / "payload.md"
        payload_file.write_text("当前无待派发任务\n")

        alert = check_noop_pending_conflict(
            payload_file=payload_file,
            assignee="claude_code",
            pending_tasks=[],
            record_stats=False,
        )

        assert alert is None

    def test_missing_payload_file(self, tmp_path):
        """Test handling missing payload file."""
        alert = check_noop_pending_conflict(
            payload_file=tmp_path / "nonexistent.md",
            assignee="claude_code",
            pending_tasks=["TASK-001"],
            record_stats=False,
        )

        assert alert is None

    def test_stats_recording(self, tmp_path):
        """Test that stats are recorded by default."""
        reset_noop_pending_stats()

        # Create no-op payload
        payload_file = tmp_path / "payload.md"
        payload_file.write_text("当前无待派发任务\n")

        check_noop_pending_conflict(
            payload_file=payload_file,
            assignee="claude_code",
            pending_tasks=["TASK-001"],
            record_stats=True,
        )

        stats = get_noop_pending_stats()
        assert stats.total_checks == 1
        assert stats.conflict_count == 1

        reset_noop_pending_stats()


class TestGlobalStats:
    """Tests for global statistics functions."""

    def test_get_noop_pending_stats(self):
        """Test getting global stats instance."""
        stats = get_noop_pending_stats()
        assert isinstance(stats, NoOpPendingStats)

    def test_reset_noop_pending_stats(self):
        """Test resetting global stats."""
        # Record some conflicts
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test",
        )
        get_noop_pending_stats().record_conflict(alert)
        assert get_noop_pending_stats().total_checks == 1

        # Reset
        reset_noop_pending_stats()
        assert get_noop_pending_stats().total_checks == 0


class TestWriteNoOpPendingReport:
    """Tests for write_noop_pending_report function."""

    def test_write_report(self, tmp_path):
        """Test writing report to file."""
        reset_noop_pending_stats()

        # Record a conflict
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test",
        )
        get_noop_pending_stats().record_conflict(alert)

        # Write report
        write_noop_pending_report(
            workspace=tmp_path,
            report_path="test_report.json",
        )

        # Verify report
        report_file = tmp_path / "test_report.json"
        assert report_file.exists()

        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        assert report_data["total_checks"] == 1
        assert report_data["conflict_count"] == 1
        assert "generated_at" in report_data
        assert "workspace" in report_data

        reset_noop_pending_stats()


class TestWriteNoOpPendingSummary:
    """Tests for write_noop_pending_summary function."""

    def test_write_summary(self, tmp_path):
        """Test writing summary to markdown file."""
        reset_noop_pending_stats()

        # Record a conflict
        alert = NoOpPendingAlert(
            timestamp="2026-03-12T12:00:00",
            assignee="claude_code",
            payload_file="test.md",
            pending_tasks=["TASK-001"],
            message="Test alert",
        )
        get_noop_pending_stats().record_conflict(alert)

        # Write summary
        write_noop_pending_summary(
            workspace=tmp_path,
            summary_path="test_summary.md",
        )

        # Verify summary
        summary_file = tmp_path / "test_summary.md"
        assert summary_file.exists()

        summary_text = summary_file.read_text(encoding="utf-8")
        assert "# No-Op and Pending Conflict Summary" in summary_text
        assert "总检查次数: `1`" in summary_text
        assert "冲突次数: `1`" in summary_text
        assert "冲突告警" in summary_text
        assert "运维查看入口" in summary_text

        reset_noop_pending_stats()

    def test_write_summary_no_conflicts(self, tmp_path):
        """Test writing summary with no conflicts."""
        reset_noop_pending_stats()

        # Write summary
        write_noop_pending_summary(
            workspace=tmp_path,
            summary_path="test_summary.md",
        )

        # Verify summary
        summary_file = tmp_path / "test_summary.md"
        assert summary_file.exists()

        summary_text = summary_file.read_text(encoding="utf-8")
        assert "# No-Op and Pending Conflict Summary" in summary_text
        assert "总检查次数: `0`" in summary_text
        assert "冲突次数: `0`" in summary_text
        assert "- 无" in summary_text

        reset_noop_pending_stats()
