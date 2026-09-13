#!/usr/bin/env python3
"""Scan workspace for secrets and PII."""
import argparse
import re
import sys
from pathlib import Path
from typing import Optional


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
    {
        "rule_id": "password_literal",
        "pattern": re.compile(r'(?i)password\s*[=:]\s*["\']?([^\s"\'<{]+)["\']?'),
        "placeholder_indicators": ["your-", "dummy-", "xxxx", "change-me", "<", "{", "todo"],
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


def scan_workspace(workspace: Path) -> dict:
    """Scan workspace for secrets and PII.

    Returns:
        {
            "has_findings": bool,
            "findings": [
                {
                    "rule_id": str,
                    "file": str,
                    "line": int,
                    "match": str,
                }
            ],
            "scanned_files": int,
        }
    """
    findings = []
    scanned_files = 0

    if not workspace.exists():
        return {"has_findings": False, "findings": [], "scanned_files": 0}

    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".md", ".json", ".env", ".txt", ".yml", ".yaml", ".js", ".ts"}:
            continue
        scanned_files += 1
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for rule in RULES:
            for match in rule["pattern"].finditer(content):
                matched_text = match.group(0)
                if is_placeholder(matched_text, rule["placeholder_indicators"]):
                    continue
                line_num = content[: match.start()].count("\n") + 1
                findings.append(
                    {
                        "rule_id": rule["rule_id"],
                        "file": str(path.relative_to(workspace)),
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
