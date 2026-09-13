#!/usr/bin/env python3
"""Long-running test harness.

Subcommands:
  bootstrap  - create harness files (feature_list, progress, checklist, init.sh)
  next       - show the next pending feature and write runtime progress
  pass       - mark a feature as passed
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def longrun_dir(workspace: Path) -> Path:
    return workspace / "collaboration" / "longrun"


def bootstrap(workspace: Path, goal: str) -> int:
    lr = longrun_dir(workspace)
    lr.mkdir(parents=True, exist_ok=True)

    feature_list = {
        "goal": goal,
        "created_at": datetime.now().isoformat(),
        "features": [
            {
                "id": "LR-001",
                "title": "Step 1: Run startup baseline checks",
                "passes": False,
                "notes": "",
            },
            {
                "id": "LR-002",
                "title": "Step 2: Execute primary task",
                "passes": False,
                "notes": "",
            },
            {
                "id": "LR-003",
                "title": "Step 3: Verify and close out",
                "passes": False,
                "notes": "",
            },
        ],
    }
    (lr / "feature_list.json").write_text(
        json.dumps(feature_list, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    (lr / "session_progress.md").write_text(
        "# Session Progress\n\n"
        f"- Goal: {goal}\n"
        f"- Started: {datetime.now().isoformat()}\n"
        "- Status: in_progress\n",
        encoding="utf-8",
    )

    (lr / "session_checklist.md").write_text(
        "# Session Checklist\n\n"
        "- [ ] Run startup baseline checks\n"
        "- [ ] `python3 scripts/reconcile_state_drift.py --workspace . --fail-on-drift`\n"
        "- [ ] Execute primary task\n"
        "- [ ] Verify and close out\n",
        encoding="utf-8",
    )

    (lr / "init.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "# Startup baseline for longrun session\n"
        "git log --oneline -20\n"
        "python3 scripts/reconcile_state_drift.py --workspace . --fail-on-drift || true\n",
        encoding="utf-8",
    )

    print(f"[OK] longrun harness bootstrapped at {lr}")
    return 0


def next_feature(workspace: Path) -> int:
    lr = longrun_dir(workspace)
    fl_path = lr / "feature_list.json"
    if not fl_path.exists():
        print("[FAIL] feature_list.json not found; run bootstrap first", file=sys.stderr)
        return 1

    data = json.loads(fl_path.read_text(encoding="utf-8"))
    pending = [f for f in data.get("features", []) if not f.get("passes")]
    if not pending:
        print("[OK] all features passed")
        return 0

    nxt = pending[0]

    # Write runtime progress
    runtime_dir = workspace / ".cc-claude-codex"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "codex-progress.md").write_text(
        f"# Codex Progress\n\n"
        f"- Next: {nxt['id']} - {nxt['title']}\n"
        f"- Updated: {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )

    print(f"[NEXT] {nxt['id']}: {nxt['title']}")
    return 0


def pass_feature(workspace: Path, feature_id: str, note: str) -> int:
    lr = longrun_dir(workspace)
    fl_path = lr / "feature_list.json"
    if not fl_path.exists():
        print("[FAIL] feature_list.json not found", file=sys.stderr)
        return 1

    data = json.loads(fl_path.read_text(encoding="utf-8"))
    found = False
    for f in data.get("features", []):
        if f.get("id") == feature_id:
            f["passes"] = True
            f["notes"] = note
            found = True
            break

    if not found:
        print(f"[FAIL] feature not found: {feature_id}", file=sys.stderr)
        return 1

    fl_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {feature_id} marked as passed")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("subcommand", nargs="?", default="bootstrap",
                   choices=["bootstrap", "next", "pass"])
    p.add_argument("--workspace", required=True)
    p.add_argument("--goal", default="longrun session")
    p.add_argument("--id")
    p.add_argument("--note", default="")
    args = p.parse_args()

    workspace = Path(args.workspace)

    if args.subcommand == "bootstrap":
        return bootstrap(workspace, args.goal)
    if args.subcommand == "next":
        return next_feature(workspace)
    if args.subcommand == "pass":
        if not args.id:
            print("[FAIL] --id is required for pass", file=sys.stderr)
            return 1
        return pass_feature(workspace, args.id, args.note)
    return 1


if __name__ == "__main__":
    sys.exit(main())
