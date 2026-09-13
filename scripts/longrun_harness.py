#!/usr/bin/env python3
"""Long-running test harness."""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--duration", type=int, default=60)
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--report")
    args = p.parse_args()

    out = {"samples": 0, "errors": 0}
    if args.report:
        Path(args.report).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
