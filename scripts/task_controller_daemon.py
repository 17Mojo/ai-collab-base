#!/usr/bin/env python3
"""Task Controller Daemon - 任务控制器守护进程"""
import argparse
import json
import sys
from pathlib import Path


class FakeStateManager:
    """Minimal StateManager for testing."""
    pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--interval-sec", type=int)
    p.add_argument("--max-iterations", type=int)
    p.add_argument("--pending-timeout-sec", type=int)
    p.add_argument("--active-timeout-sec", type=int)
    p.add_argument("--blocked-timeout-sec", type=int)
    p.add_argument("--prewarn-ratio", type=float)
    p.add_argument("--history")
    p.add_argument("--default-assignee")
    p.add_argument("--report")
    args = p.parse_args()

    out = {"processed": 0, "timed_out": 0}
    if args.report:
        Path(args.report).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


# Expose StateManager for tests
StateManager = FakeStateManager


if __name__ == "__main__":
    sys.exit(main())
