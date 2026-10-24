"""Unit tests for scripts/scan_secrets_pii.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "scan_secrets_pii.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scan_secrets_pii", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scan_detects_secret(tmp_path: Path) -> None:
    module = _load_module()
    secret = "sk-" + "ABCDEF" + "GHIJKL" + "MNOPQR" + "STUVWX" + "1234567890"
    (tmp_path / "sample.py").write_text(
        f'OPENAI_API_KEY = "{secret}"\n',
        encoding="utf-8",
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is True
    assert any(item["rule_id"] == "openai_api_key" for item in report["findings"])


def test_scan_ignores_placeholder_secret(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "config.py").write_text(
        'API_KEY = "your-api-key-here"\nTOKEN = "dummy-token-value"\n',
        encoding="utf-8",
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is False


def test_scan_detects_pii_pattern(tmp_path: Path) -> None:
    module = _load_module()
    ssn = "-".join(["123", "45", "6789"])
    (tmp_path / "note.txt").write_text(f"customer_ssn={ssn}\n", encoding="utf-8")

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is True
    assert any(item["rule_id"] == "us_ssn" for item in report["findings"])


def test_node_modules_skipped(tmp_path: Path) -> None:
    module = _load_module()
    nested = tmp_path / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    secret = "sk-" + "ABCDEF" + "GHIJKL" + "MNOPQR" + "STUVWX" + "1234567890"
    (nested / "bundle.js").write_text(
        'var cfg = {"password":"' + secret + '"};\n',
        encoding="utf-8",
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is False


def test_password_short_fixture_not_flagged(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "config.py").write_text('password="pw"\n', encoding="utf-8")

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is False


def test_password_placeholder_literal_not_flagged(tmp_path: Path) -> None:
    module = _load_module()
    (tmp_path / "settings.py").write_text(
        'password = resolve_credentials()\n'
        'password="from-file"\n'
        'password="your-secret-here"\n',
        encoding="utf-8",
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is False


def test_allowlist_exempts_finding(tmp_path: Path) -> None:
    module = _load_module()
    secret = "sk-" + "ABCDEF" + "GHIJKL" + "MNOPQR" + "STUVWX" + "1234567890"
    (tmp_path / "sample.py").write_text(f'KEY = "{secret}"\n', encoding="utf-8")
    baseline = module.scan_workspace(tmp_path)
    assert baseline["has_findings"] is True

    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "secrets-scan-allowlist.txt").write_text(
        "# exempt list\nsample.py:1:test fixture, not a real credential\n",
        encoding="utf-8",
    )

    after = module.scan_workspace(tmp_path)
    assert after["has_findings"] is False

