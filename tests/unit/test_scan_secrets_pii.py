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


def test_bare_numeric_password_detected(tmp_path: Path) -> None:
    """纯数字裸值密码必须被检出。

    `password_literal_bare` 要求「含数字且含字母」，纯数字（PIN 形态）会漏掉；
    这条用例守护 `password_literal_bare_numeric` 规则不被删掉。
    """
    module = _load_module()
    # 字面量拆开写，避免本文件自身被密钥扫描器命中（扫描面包含测试源码）
    (tmp_path / "config.py").write_text(
        "pass" + "word = " + "12345678" + "\n", encoding="utf-8"
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is True
    assert any(
        item["rule_id"] == "password_literal_bare_numeric" for item in report["findings"]
    )


def test_bare_short_password_detected(tmp_path: Path) -> None:
    """短裸值密码（字母开头、数字结尾、6–11 位）必须被检出。

    改造前旧规则会命中裸值短密码，两段式改造后一度漏检，
    由 `password_literal_bare_short` 补回。
    """
    module = _load_module()
    (tmp_path / "config.py").write_text(
        "pass" + "word = " + "hunter2" + "\n", encoding="utf-8"
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is True
    assert any(
        item["rule_id"] == "password_literal_bare_short" for item in report["findings"]
    )


def test_bare_identifier_still_not_flagged(tmp_path: Path) -> None:
    """补规则不得把标识符形态重新变成噪声。

    「标识符调用」「类型标注」「None」「算法名」四种形态都应保持不被命中。
    """
    module = _load_module()
    (tmp_path / "config.py").write_text(
        "pass" + "word = resolve_credentials(...)\n"
        "pass" + "word: str\n"
        "pass" + "word = None\n"
        "pass" + "word = sha1\n",
        encoding="utf-8",
    )

    report = module.scan_workspace(tmp_path)
    assert report["has_findings"] is False


def test_long_bare_password_not_double_reported(tmp_path: Path) -> None:
    """12 位以上裸值只由 `password_literal_bare` 记一条，不重复计两条。"""
    module = _load_module()
    (tmp_path / "config.py").write_text(
        "pass" + "word = " + "abcdefghij12" + "\n", encoding="utf-8"
    )

    report = module.scan_workspace(tmp_path)
    password_rules = [
        item["rule_id"]
        for item in report["findings"]
        if item["rule_id"].startswith("password")
    ]
    assert password_rules == ["password_literal_bare"]
