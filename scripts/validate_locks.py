#!/usr/bin/env python3
"""Validate task locks report."""
import argparse
import re
import sys
from pathlib import Path


VALID_STATUSES = {"planning", "implementing", "testing", "completed", "cancelled"}
HEADER = "| 状态 | owner | task | start | note |"
DIVIDER = "|---|---|---|---|---|"
ROW_RE = re.compile(r"^\|\s*`?([a-zA-Z]+)`?\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(.*?)\s*\|$")


def validate(path: Path) -> int:
    if not path.exists():
        print(f"Lock report not found: {path}", file=sys.stderr)
        return 1
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    if HEADER not in lines or DIVIDER not in lines:
        print(f"Lock report missing table header: {path}", file=sys.stderr)
        return 1
    body_started = False
    rc = 0
    for line in lines:
        if line.strip() == HEADER:
            body_started = True
            continue
        if line.strip() == DIVIDER:
            continue
        if not body_started:
            continue
        m = ROW_RE.match(line)
        if not m:
            print(f"Invalid row format: {line}", file=sys.stderr)
            rc = 1
            continue
        status = m.group(1).lower()
        if status not in VALID_STATUSES:
            print(f"unknown status '{m.group(1).upper()}'")
            rc = 1
    if rc == 0:
        print("[OK] lock validation passed")
    return rc


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--files", required=True)
    args = p.parse_args()
    return validate(Path(args.files))


if __name__ == "__main__":
    sys.exit(main())
