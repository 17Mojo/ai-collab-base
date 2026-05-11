from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_FILE = PROJECT_ROOT / "local-backend" / "monitoring" / "prometheus" / "alert_rules.yml"
RUNBOOK_FILE = PROJECT_ROOT / "docs" / "ALERTING_RUNBOOK.md"


def test_alert_rules_cover_core_categories():
    text = RULES_FILE.read_text(encoding="utf-8")

    required_alerts = [
        "PromptPackApiErrorRateWarning",
        "PromptPackApiLatencyP95Warning",
        "PromptPackPackApiFailureRatioWarning",
    ]
    for alert_name in required_alerts:
        assert f"alert: {alert_name}" in text

    assert "prompt_pack_http_requests_total" in text
    assert "prompt_pack_http_request_duration_seconds_bucket" in text
    assert "prompt_pack_http_exceptions_total" in text


def test_alert_rules_have_explicit_thresholds():
    text = RULES_FILE.read_text(encoding="utf-8")

    for threshold in ["> 0.05", "> 0.10", "> 0.25", "> 0.50", "> 0.15", "> 0.30"]:
        assert threshold in text

    for window in ["for: 10m", "for: 5m", "for: 2m"]:
        assert window in text


def test_runbook_contains_drill_steps():
    text = RUNBOOK_FILE.read_text(encoding="utf-8")

    for section in ["错误率告警演练", "延迟告警演练", "失败比例告警演练", "异常突增告警演练"]:
        assert section in text
    assert "告警响应流程（最小闭环）" in text
