#!/usr/bin/env python3
"""Scan workspace for secrets and PII."""
import argparse
import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

RULES = [
    {
        "rule_id": "openai_api_key",
        "pattern": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "placeholder_indicators": ["your-", "dummy-", "xxxx", "replace-me", "<", "{"],
    },
    {
        "rule_id": "google_api_key",
        "pattern": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        "placeholder_indicators": ["your-", "dummy-", "xxxx", "replace-me", "<", "{"],
    },
    {
        "rule_id": "github_token",
        "pattern": re.compile(r"ghp_[A-Za-z0-9]{36}"),
        "placeholder_indicators": ["your-", "dummy-", "xxxx", "replace-me", "<", "{"],
    },
]

RULES += [
    {
        "rule_id": "password_literal",
        "pattern": re.compile(r'''(?i)password\s*[=:]\s*(["'])([^"'\n]{3,})\1'''),
        "placeholder_indicators": [
            "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
            "pw", "none", "secret", "test", "from-file", "env-provided",
            "resolve_credentials", "os.environ",
        ],
    },
    {
        "rule_id": "password_literal_bare",
        "pattern": re.compile(r'''(?i)password\s*[=:]\s*([A-Za-z0-9][A-Za-z0-9\-]{11,})'''),
        "placeholder_indicators": [
            "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
            "resolve_credentials", "os.environ",
        ],
    },
    {
        # 纯数字裸值密码（PIN 形态）：见下方正则，6 位以上纯数字。
        # 上面 B 段要求「含数字且含字母」，纯数字会漏掉，这里补一条独立规则。
        # 阈值 6 位，且不跨行、不吃标识符。
        "rule_id": "password_literal_bare_numeric",
        "pattern": re.compile(r'''(?i)password[ \t]*[=:][ \t]*(\d{6,})(?![0-9])'''),
        "placeholder_indicators": [
            "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
        ],
    },
    {
        # 短裸值密码（6–11 位、字母开头数字结尾）：见下方正则。
        # 12 位以上交给 B 段，避免同一处命中记两条；不含短横线，
        # 因此「标识符调用」形态（见 R2 契约正文）不会被误命中。
        "rule_id": "password_literal_bare_short",
        "pattern": re.compile(
            r'''(?i)password[ \t]*[=:][ \t]*([A-Za-z][A-Za-z0-9]{4,14}\d)(?![A-Za-z0-9_\-])'''
        ),
        "placeholder_indicators": [
            "your-", "dummy-", "xxxx", "change-me", "<", "{", "todo",
        ],
    },
    {
        "rule_id": "us_ssn",
        "pattern": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "placeholder_indicators": [],
    },
]


def is_placeholder(value: str, indicators: list) -> bool:
    value_lower = value.lower()
    return any(ind in value_lower for ind in indicators)


def _load_allowlist(workspace: Path) -> set:
    """Load secrets-scan allowlist entries.

    Format per line: ``<relative-file>:<line>:<reason>``; ``#`` lines are
    comments. Missing / unreadable file yields an empty set (never errors).
    """
    allow = set()
    allow_path = workspace / "config" / "secrets-scan-allowlist.txt"
    try:
        text = allow_path.read_text(encoding="utf-8")
    except Exception:
        return allow
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) >= 2:
            allow.add(f"{parts[0]}:{parts[1]}")
    return allow


def scan_workspace(workspace: Path) -> dict:
    """Scan workspace for secrets and PII."""
    findings = []
    scanned_files = 0

    if not workspace.exists():
        return {"has_findings": False, "findings": [], "scanned_files": 0}

    allow = _load_allowlist(workspace)

    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if EXCLUDED_DIRS & set(path.parts):
            continue
        if path.suffix not in {
            ".py", ".md", ".json", ".env", ".txt",
            ".yml", ".yaml", ".js", ".ts",
        }:
            continue
        scanned_files += 1
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = str(path.relative_to(workspace))
        for rule in RULES:
            for match in rule["pattern"].finditer(content):
                value = match.group(match.lastindex) if match.lastindex else match.group(0)
                if is_placeholder(value, rule["placeholder_indicators"]):
                    continue
                if rule["rule_id"] == "password_literal_bare":
                    has_digit = any(ch.isdigit() for ch in value)
                    has_alpha = any(ch.isalpha() for ch in value)
                    if not (has_digit and has_alpha):
                        continue
                if rule["rule_id"] == "password_literal_bare_short" and len(value) >= 12:
                    # 12 位以上由 password_literal_bare 覆盖，避免同一处命中记两条
                    continue
                matched_text = match.group(0)
                line_num = content.count("\n", 0, match.span()[0]) + 1
                if f"{rel_path}:{line_num}" in allow:
                    continue
                findings.append(
                    {
                        "rule_id": rule["rule_id"],
                        "file": rel_path,
                        "line": line_num,
                        "match": matched_text,
                    }
                )

    return {
        "has_findings": len(findings) > 0,
        "findings": findings,
        "scanned_files": scanned_files,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--output")
    args = p.parse_args()

    report = scan_workspace(Path(args.workspace))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            __import__("json").dumps(report, indent=2, ensure_ascii=False)
        )

    if report["has_findings"]:
        for item in report["findings"]:
            print(f"[{item['rule_id']}] {item['file']}:{item['line']} - {item['match']}")
        print(f"[FAIL] {len(report['findings'])} findings", file=sys.stderr)
    else:
        print("[OK] no secrets found")

    return 1 if report["has_findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
