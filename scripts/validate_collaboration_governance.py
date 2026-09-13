#!/usr/bin/env python3
"""Validate collaboration governance files."""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--report")
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()

    issues = []
    workspace = Path(args.workspace)

    # Check governance file exists
    required_files = [
        "collaboration/PROTOCOL.md",
        "collaboration/COLLABORATION_GUIDELINES.md",
        "rules/AI-OP.md",
    ]

    for f in required_files:
        if not (workspace / f).exists():
            issues.append(f"missing required file: {f}")

    # Check AI collaboration references
    agents_file = workspace / "rules" / "OWNERSHIP.md"
    if not agents_file.exists():
        issues.append("missing agents reference file: rules/OWNERSHIP.md")

    rc = 1 if issues else 0
    result = {"passed": rc == 0, "issues": issues}

    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2))

    if issues:
        print(json.dumps(result, indent=2))
    else:
        print("[OK] governance validation passed")

    return rc


if __name__ == "__main__":
    sys.exit(main())
