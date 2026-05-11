"""UI accessibility hard-gate tests for extension surfaces."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CHROME_POPUP_HTML = Path("products/prompt-pack-extension/chrome/src/popup/index.html")
CHROME_POPUP_CSS = Path("products/prompt-pack-extension/chrome/src/popup/styles.css")
VSCODE_PACKAGE_JSON = Path("products/vscode-extension/package.json")


def _failed_checks(checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in checks.items() if not passed]


def _chrome_html_check() -> tuple[list[str], list[str]]:
    if not CHROME_POPUP_HTML.exists():
        return ["file_missing"], []

    html_content = CHROME_POPUP_HTML.read_text(encoding="utf-8")
    checks = {
        "has_lang_attr": 'lang="' in html_content or "lang='" in html_content,
        "has_meta_charset": 'charset="UTF-8"' in html_content or "charset='UTF-8'" in html_content,
        "has_meta_viewport": "viewport" in html_content,
        "has_title": "<title>" in html_content,
        "has_buttons": "<button" in html_content,
        "has_aria_labels": "aria-label" in html_content,
        "has_aria_live_region": "aria-live" in html_content,
    }
    semantic_elements = ["<header", "<footer", "<main", "<nav", "<section", "<article"]
    found_semantic = [element for element in semantic_elements if element in html_content]
    failed_checks = _failed_checks(checks)
    if not found_semantic:
        failed_checks.append("has_semantic_landmarks")
    return failed_checks, found_semantic


def _chrome_css_check() -> list[str]:
    if not CHROME_POPUP_CSS.exists():
        return ["file_missing"]

    css_content = CHROME_POPUP_CSS.read_text(encoding="utf-8")
    checks = {
        "has_focus_styles": ":focus" in css_content,
        "has_hover_styles": ":hover" in css_content,
        "has_active_styles": ":active" in css_content,
        "has_disabled_styles": ":disabled" in css_content or ".disabled" in css_content,
    }
    return _failed_checks(checks)


def _vscode_package_check() -> list[str]:
    if not VSCODE_PACKAGE_JSON.exists():
        return ["file_missing"]

    package_data = json.loads(VSCODE_PACKAGE_JSON.read_text(encoding="utf-8"))
    checks = {
        "has_display_name": "displayName" in package_data,
        "has_description": "description" in package_data,
        "has_categories": "categories" in package_data,
        "has_keywords": isinstance(package_data.get("keywords"), list)
        and len(package_data.get("keywords", [])) > 0,
    }
    return _failed_checks(checks)


def test_chrome_extension_html_structure() -> None:
    failed_checks, found_semantic = _chrome_html_check()
    assert not failed_checks, (
        "Chrome popup HTML accessibility checks failed: "
        + ", ".join(failed_checks)
        + f"; semantic elements={found_semantic}"
    )


def test_chrome_extension_css_accessibility() -> None:
    failed_checks = _chrome_css_check()
    assert not failed_checks, "Chrome popup CSS accessibility checks failed: " + ", ".join(
        failed_checks
    )


def test_vscode_extension_package() -> None:
    failed_checks = _vscode_package_check()
    assert not failed_checks, "VSCode extension package accessibility checks failed: " + ", ".join(
        failed_checks
    )


def generate_accessibility_report() -> dict[str, Any]:
    """Generate accessibility compliance report from live checks."""
    html_failed, semantic = _chrome_html_check()
    css_failed = _chrome_css_check()
    package_failed = _vscode_package_check()
    overall_failed = bool(html_failed or css_failed or package_failed)

    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "version": "1.1.0",
        "status": "FAIL" if overall_failed else "PASS",
        "checks": {
            "chrome_extension": {
                "html_structure": "FAIL" if html_failed else "PASS",
                "css_accessibility": "FAIL" if css_failed else "PASS",
                "html_failed_checks": html_failed,
                "css_failed_checks": css_failed,
                "semantic_elements_found": semantic,
            },
            "vscode_extension": {
                "package_metadata": "FAIL" if package_failed else "PASS",
                "package_failed_checks": package_failed,
            },
        },
        "recommendations": [
            "Add automated axe-core tests for runtime accessibility checking",
            "Implement visual regression tests with Playwright snapshots",
            "Add keyboard-only navigation test cases",
            "Run screen-reader regression checks in release checklist",
        ],
    }


def test_accessibility_baseline() -> None:
    """Main accessibility gate test with report output."""
    report = generate_accessibility_report()
    report_path = Path("logs/accessibility_baseline_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    assert report["status"] == "PASS", (
        "UI accessibility gate failed. "
        + f"chrome_html={report['checks']['chrome_extension']['html_failed_checks']} "
        + f"chrome_css={report['checks']['chrome_extension']['css_failed_checks']} "
        + f"vscode={report['checks']['vscode_extension']['package_failed_checks']}"
    )


def main() -> int:
    test_accessibility_baseline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
