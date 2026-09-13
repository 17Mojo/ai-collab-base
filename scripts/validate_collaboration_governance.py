#!/usr/bin/env python3
"""Validate collaboration governance files."""
import argparse
import sys
from pathlib import Path

REQUIRED_FILES = [
    "collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md",
    "collaboration/COLLABORATION_GUIDELINES.md",
    "collaboration/PROTOCOL.md",
    "rules/AI-COLLABORATION-STANDARDS.md",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--with-locks", action="store_true")
    p.add_argument("--lock-files", nargs="*", default=[])
    p.add_argument("--report")
    args = p.parse_args()

    workspace = Path(args.workspace)
    issues = []

    # Check required files
    for f in REQUIRED_FILES:
        if not (workspace / f).exists():
            issues.append({"kind": "missing_file", "path": f})

    # Check agents reference file references all required files
    agents_file = workspace / "AGENTS.md"
    if not agents_file.exists():
        issues.append({"kind": "missing_agents_reference", "path": "AGENTS.md"})
    else:
        # Verify AGENTS.md references all required files
        refs = [ln.strip() for ln in agents_file.read_text().splitlines() if ln.strip()]
        missing = [f for f in REQUIRED_FILES if f not in refs]
        if missing:
            issues.append({
                "kind": "missing_agents_reference",
                "path": "AGENTS.md",
                "missing_refs": missing,
            })

    # Check lock files if requested
    if args.with_locks:
        for lock_file in args.lock_files:
            if not (workspace / lock_file).exists():
                issues.append({"kind": "missing_lock_file", "path": lock_file})

    if issues:
        for issue in issues:
            if issue["kind"] == "missing_file":
                print(f"missing required governance file: {issue['path']}")
            elif issue["kind"] == "missing_agents_reference":
                # Check if AGENTS.md has enough refs
                agents_file = workspace / "AGENTS.md"
                if agents_file.exists():
                    refs = [ln for ln in agents_file.read_text().splitlines() if ln.strip()]
                    if len(refs) < 3:
                        print("missing required collaboration reference")
                else:
                    print("missing required collaboration reference")
            elif issue["kind"] == "missing_lock_file":
                print(f"missing required lock file: {issue['path']}")
            else:
                print(f"issue: {issue}")
        return 1

    print("[OK] collaboration governance validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
