"""UI accessibility hard-gate tests for extension surfaces.

新架构下（chrome-extension/）的 a11y 守护点：
- Chrome Popup HTML: chrome-extension/public/popup.html（lang/charset/viewport/title/buttons/data-testid/语义标签 <header>/<main>/<section>/<footer>）
- Chrome Popup CSS: popup.html 使用内联 <style>，无独立 styles.css；按真实现状检查 :hover / :focus-visible / :active / :disabled
- VSCode Extension: products/vscode-extension/ 已重构为 native_host.py（无 package.json）

历史变更：
- 2026-09-19 6700c70：硬门禁仅留基线（lang/charset/viewport/title/buttons/testids + :hover/:disabled），语义标签作软告警
- 2026-09-19 本次：popup.html 已改用 <header>/<main>/<section>/<footer> + aria-labelledby + role="status" aria-live="polite"，并补 :focus-visible / :active 样式 → 硬门禁回填语义标签与键盘焦点
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHROME_POPUP_HTML = Path("chrome-extension/public/popup.html")
VSCODE_NATIVE_HOST = Path("products/vscode-extension/native_host.py")


def _failed_checks(checks: dict[str, bool]) -> list[str]:
    return [name for name, passed in checks.items() if not passed]


def _extract_inline_style(html_content: str) -> str | None:
    """提取 HTML 中的第一个 <style> 块内容"""
    match = re.search(r"<style[^>]*>(.*?)</style>", html_content, re.DOTALL)
    return match.group(1) if match else None


def _chrome_html_check() -> tuple[list[str], list[str]]:
    """硬门禁：基线 + 语义标签（popup.html 已用 <header>/<main>/<section>/<footer>）"""
    if not CHROME_POPUP_HTML.exists():
        return ["file_missing"], []

    html_content = CHROME_POPUP_HTML.read_text(encoding="utf-8")
    checks = {
        "has_lang_attr": 'lang="' in html_content,
        "has_meta_charset": 'charset="UTF-8"' in html_content,
        "has_meta_viewport": "viewport" in html_content,
        "has_title": "<title>" in html_content,
        "has_buttons": "<button" in html_content,
        "has_testids": "data-testid=" in html_content,
        "has_header_landmark": "<header" in html_content,
        "has_main_landmark": "<main" in html_content,
        "has_section_landmark": "<section" in html_content,
        "has_footer_landmark": "<footer" in html_content,
    }
    semantic_elements = ["<header", "<footer", "<main", "<nav", "<section", "<article"]
    found_semantic = [element for element in semantic_elements if element in html_content]
    failed_checks = _failed_checks(checks)
    return failed_checks, found_semantic


def _chrome_css_check() -> list[str]:
    """popup.html 使用内联 <style>；检查 :hover / :focus-visible / :active / :disabled"""
    if not CHROME_POPUP_HTML.exists():
        return ["file_missing"]

    html_content = CHROME_POPUP_HTML.read_text(encoding="utf-8")
    css_content = _extract_inline_style(html_content)
    if css_content is None:
        return ["no_inline_style"]

    checks = {
        "has_hover_styles": ":hover" in css_content,
        "has_focus_styles": ":focus-visible" in css_content,
        "has_active_styles": ":active" in css_content,
        "has_disabled_styles": ":disabled" in css_content,
    }
    return _failed_checks(checks)


def _vscode_native_host_check() -> list[str]:
    """products/vscode-extension/ 已重构为 native_host.py（无 package.json）"""
    if not VSCODE_NATIVE_HOST.exists():
        return ["file_missing"]

    content = VSCODE_NATIVE_HOST.read_text(encoding="utf-8")
    checks = {
        "has_shebang": content.startswith("#!"),
        "has_docstring": '"""' in content or "'''" in content,
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
    failed_checks = _vscode_native_host_check()
    assert not failed_checks, (
        "VSCode extension native_host accessibility checks failed: "
        + ", ".join(failed_checks)
    )


def generate_accessibility_report() -> dict[str, Any]:
    """Generate accessibility compliance report from live checks."""
    html_failed, semantic = _chrome_html_check()
    css_failed = _chrome_css_check()
    package_failed = _vscode_native_host_check()
    overall_failed = bool(html_failed or css_failed or package_failed)
    semantic_missing = not semantic

    recommendations = [
        "Add automated axe-core tests for runtime accessibility checking",
        "Implement visual regression tests with Playwright snapshots",
        "Add keyboard-only navigation test cases",
        "Run screen-reader regression checks in release checklist",
        "Consider adding :focus-visible to interactive <li class='pack-item'> if/when they become focusable (currently <li> are not tab-focusable)",
    ]
    if semantic_missing:
        recommendations.append(
            "popup.html 缺少 <main>/<section>/<header>/<nav> 等语义标签；建议改造 .header/.content/.status 为语义标签以提升 a11y（不阻塞当前门禁）"
        )

    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "version": "2.0.0",
        "status": "FAIL" if overall_failed else "PASS",
        "checks": {
            "chrome_extension": {
                "html_structure": "FAIL" if html_failed else "PASS",
                "css_accessibility": "FAIL" if css_failed else "PASS",
                "html_failed_checks": html_failed,
                "css_failed_checks": css_failed,
                "semantic_elements_found": semantic,
                "semantic_elements_missing": semantic_missing,
            },
            "vscode_extension": {
                "native_host": "FAIL" if package_failed else "PASS",
                "native_host_failed_checks": package_failed,
            },
        },
        "recommendations": recommendations,
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
        + f"vscode={report['checks']['vscode_extension']['native_host_failed_checks']}"
    )


def main() -> int:
    test_accessibility_baseline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
