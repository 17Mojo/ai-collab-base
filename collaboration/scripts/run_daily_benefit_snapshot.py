#!/usr/bin/env python3
"""Run daily benefit snapshot."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--output")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    out = {
        "date": datetime.now().isoformat(),
        "dispatch_tasks": 0,
        "receipt_tasks": 0,
        "ratio": 0,
        "达标": False,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(out, indent=2))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
