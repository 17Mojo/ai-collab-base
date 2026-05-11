"""Unit tests for trigger payload freshness checking."""

import json
from datetime import datetime, timedelta

from ai_collab.dispatch_trigger import (
    FreshnessStats,
    check_payload_freshness,
    get_freshness_stats,
    reset_freshness_stats,
)


class TestCheckPayloadFreshness:
    """Tests for check_payload_freshness function."""

    def test_fresh_payload_within_threshold(self, tmp_path):
        """Test that a payload within threshold is marked as fresh."""
        now = datetime.now()
        payload_time = now.isoformat()
        dispatch_time = (now - timedelta(minutes=2)).isoformat()

        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": dispatch_time}))

        result = check_payload_freshness(
            payload_generated_at=payload_time,
            dispatch_report_path=dispatch_report,
            threshold_minutes=5,
            record_stats=False,
        )

        assert result["is_fresh"] is True
        assert result["age_minutes"] == 2.0
        assert result["warning"] is None
        assert result["fix_command"] is None

    def test_stale_payload_exceeds_threshold(self, tmp_path):
        """Test that a payload exceeding threshold is marked as stale."""
        now = datetime.now()
        payload_time = (now - timedelta(minutes=10)).isoformat()
        dispatch_time = now.isoformat()

        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": dispatch_time}))

        result = check_payload_freshness(
            payload_generated_at=payload_time,
            dispatch_report_path=dispatch_report,
            assignee="claude_code",
            threshold_minutes=5,
            record_stats=False,
        )

        assert result["is_fresh"] is False
        assert result["age_minutes"] == 10.0
        assert "Payload 已过期" in result["warning"]
        assert (
            result["fix_command"]
            == "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH Claude' --target claude_code"
        )

    def test_payload_exactly_at_threshold(self, tmp_path):
        """Test that a payload exactly at threshold is marked as fresh."""
        now = datetime.now()
        payload_time = now.isoformat()
        dispatch_time = (now - timedelta(minutes=5)).isoformat()

        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": dispatch_time}))

        result = check_payload_freshness(
            payload_generated_at=payload_time,
            dispatch_report_path=dispatch_report,
            threshold_minutes=5,
            record_stats=False,
        )

        assert result["is_fresh"] is True
        assert result["age_minutes"] == 5.0

    def test_invalid_payload_timestamp(self, tmp_path):
        """Test handling of invalid payload timestamp."""
        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": datetime.now().isoformat()}))

        result = check_payload_freshness(
            payload_generated_at="invalid-timestamp",
            dispatch_report_path=dispatch_report,
            record_stats=False,
        )

        assert result["is_fresh"] is False
        assert "无法解析 payload 时间戳" in result["warning"]
        assert result["fix_command"] is None

    def test_missing_dispatch_report(self, tmp_path):
        """Test handling of missing dispatch report."""
        result = check_payload_freshness(
            payload_generated_at=datetime.now().isoformat(),
            dispatch_report_path=tmp_path / "nonexistent.json",
            assignee="codearts_agent",
            record_stats=False,
        )

        assert result["is_fresh"] is False
        assert "Dispatch report 不存在" in result["warning"]
        assert (
            result["fix_command"]
            == "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH CodeArts' --target codearts_agent"
        )

    def test_dispatch_report_missing_generated_at(self, tmp_path):
        """Test handling of dispatch report without generated_at field."""
        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"other_field": "value"}))

        result = check_payload_freshness(
            payload_generated_at=datetime.now().isoformat(),
            dispatch_report_path=dispatch_report,
            assignee="codex",
            record_stats=False,
        )

        assert result["is_fresh"] is False
        assert "缺少 generated_at 字段" in result["warning"]
        assert (
            result["fix_command"]
            == "python3 -m ai_collab.cli trigger --phrase '2X DISPATCH CODEX' --target codex"
        )

    def test_invalid_dispatch_report_json(self, tmp_path):
        """Test handling of invalid JSON in dispatch report."""
        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text("invalid json")

        result = check_payload_freshness(
            payload_generated_at=datetime.now().isoformat(),
            dispatch_report_path=dispatch_report,
            record_stats=False,
        )

        assert result["is_fresh"] is False
        assert "无法读取 dispatch report" in result["warning"]
        assert "dispatch" in result["fix_command"]

    def test_timezone_handling(self, tmp_path):
        """Test that timezone differences are handled correctly."""
        now = datetime.now()
        payload_time = now.isoformat()
        dispatch_time = (now - timedelta(minutes=3)).isoformat()

        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": dispatch_time}))

        result = check_payload_freshness(
            payload_generated_at=payload_time,
            dispatch_report_path=dispatch_report,
            threshold_minutes=5,
            record_stats=False,
        )

        assert result["is_fresh"] is True
        assert result["age_minutes"] == 3.0


class TestFreshnessStats:
    """Tests for FreshnessStats class."""

    def test_record_fresh_check(self):
        """Test recording a fresh check."""
        stats = FreshnessStats()
        result = {"is_fresh": True, "age_minutes": 2.0}

        stats.record_check(result)

        assert stats.total_checks == 1
        assert stats.fresh_count == 1
        assert stats.stale_count == 0
        assert stats.error_count == 0

    def test_record_stale_check(self):
        """Test recording a stale check."""
        stats = FreshnessStats()
        result = {
            "is_fresh": False,
            "age_minutes": 10.0,
            "payload_generated_at": "2026-03-12T10:00:00",
            "dispatch_generated_at": "2026-03-12T10:10:00",
        }

        stats.record_check(result)

        assert stats.total_checks == 1
        assert stats.fresh_count == 0
        assert stats.stale_count == 1
        assert len(stats.stale_events) == 1
        assert stats.stale_events[0]["age_minutes"] == 10.0

    def test_record_error_check(self):
        """Test recording an error check."""
        stats = FreshnessStats()
        result = {"is_fresh": None, "warning": "Error"}

        stats.record_check(result)

        assert stats.total_checks == 1
        assert stats.fresh_count == 0
        assert stats.stale_count == 0
        assert stats.error_count == 1

    def test_get_summary(self):
        """Test getting summary statistics."""
        stats = FreshnessStats()
        stats.record_check({"is_fresh": True, "age_minutes": 2.0})
        stats.record_check({"is_fresh": True, "age_minutes": 3.0})
        stats.record_check(
            {
                "is_fresh": False,
                "age_minutes": 10.0,
                "payload_generated_at": "2026-03-12T10:00:00",
                "dispatch_generated_at": "2026-03-12T10:10:00",
            }
        )

        summary = stats.get_summary()

        assert summary["total_checks"] == 3
        assert summary["fresh_count"] == 2
        assert summary["stale_count"] == 1
        assert summary["error_count"] == 0
        assert summary["fresh_rate"] == 66.67
        assert summary["stale_rate"] == 33.33
        assert len(summary["stale_events"]) == 1

    def test_get_summary_empty(self):
        """Test getting summary with no checks."""
        stats = FreshnessStats()
        summary = stats.get_summary()

        assert summary["total_checks"] == 0
        assert summary["fresh_rate"] == 0.0
        assert summary["stale_rate"] == 0.0

    def test_print_summary(self, capsys):
        """Test printing summary to console."""
        stats = FreshnessStats()
        stats.record_check({"is_fresh": True, "age_minutes": 2.0})
        stats.record_check(
            {
                "is_fresh": False,
                "age_minutes": 10.0,
                "payload_generated_at": "2026-03-12T10:00:00",
                "dispatch_generated_at": "2026-03-12T10:10:00",
            }
        )

        stats.print_summary()
        captured = capsys.readouterr()

        assert "Payload Freshness Statistics" in captured.out
        assert "Total Checks: 2" in captured.out
        assert "Fresh: 1 (50.0%)" in captured.out
        assert "Stale: 1 (50.0%)" in captured.out
        assert "Stale Events:" in captured.out


class TestGlobalStats:
    """Tests for global statistics functions."""

    def test_get_freshness_stats(self):
        """Test getting global stats instance."""
        stats = get_freshness_stats()
        assert isinstance(stats, FreshnessStats)

    def test_reset_freshness_stats(self):
        """Test resetting global stats."""
        # Record some checks
        get_freshness_stats().record_check({"is_fresh": True, "age_minutes": 2.0})
        assert get_freshness_stats().total_checks == 1

        # Reset
        reset_freshness_stats()
        assert get_freshness_stats().total_checks == 0

    def test_stats_recording_in_check(self, tmp_path):
        """Test that check_payload_freshness records stats by default."""
        reset_freshness_stats()

        now = datetime.now()
        payload_time = now.isoformat()
        dispatch_time = (now - timedelta(minutes=2)).isoformat()

        dispatch_report = tmp_path / "dispatch_report.json"
        dispatch_report.write_text(json.dumps({"generated_at": dispatch_time}))

        check_payload_freshness(
            payload_generated_at=payload_time,
            dispatch_report_path=dispatch_report,
            threshold_minutes=5,
            record_stats=True,
        )

        stats = get_freshness_stats()
        assert stats.total_checks == 1
        assert stats.fresh_count == 1

        reset_freshness_stats()
