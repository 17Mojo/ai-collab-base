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
