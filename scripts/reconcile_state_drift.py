#!/usr/bin/env python3
"""Reconcile state drift between agents."""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


RECONCILEABLE_TASK_STATUSES = {"deferred", "in_progress", "planning", "implementing", "testing"}
RECONCILEABLE_PATCH_STATUSES = {"blocked", "in_progress", "planning"}


def read_state(workspace):
    state_file = workspace / "logs" / "collaboration_state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_ack_state(workspace):
    state_file = workspace / "logs" / "agent_ack_bridge_state.json"
    if not state_file.exists():
        return {"items": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


NEGATIVE_SIGNAL_PATTERNS = [
    "未完成", "未集成", "需要返工", "需要继续",
    "TODO", "FIXME", "TBD",
]


def has_negative_signals(result_file_path):
    """Check if result file contains negative signals."""
    if not result_file_path.exists():
        return False
    try:
        content_text = result_file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return any(pat in content_text for pat in NEGATIVE_SIGNAL_PATTERNS)


def has_explicit_ack(task_id, ack_state):
    item = ack_state.get("items", {}).get(task_id)
    if not item:
        return False
    return item.get("source") == "cli-ack"


def find_drift_tasks(state, ack_state):
    drifts = []
    tasks = state.get("tasks", {})
    active_tasks = set(state.get("active_tasks", []))

    for tid, task in tasks.items():
        if tid not in active_tasks:
            continue
        status = task.get("status", "")
        if status in {"cancelled", "completed", "failed"}:
            continue
        if status not in RECONCILEABLE_TASK_STATUSES:
            continue

        candidate = f"collaboration/results/RESULT_{tid}.md"
        ws_path = Path(state.get("workspace", ""))
        if ws_path and (ws_path / candidate).exists():
            # Check for negative signals
            if has_negative_signals(ws_path / candidate):
                drifts.append({
                    "kind": "task",
                    "item_id": tid,
                    "current_status": status,
                    "issue": "result file contains negative signals",
                    "candidate_status": "implementing",
                    "needs_explicit_ack": False,
                    "contains_negative_signals": True,
                })
                continue
            ai_type = task.get("ai_type", "")
            assignee = task.get("assignee", "")
            if "claude" in ai_type.lower() or assignee == "claude_code":
                if not has_explicit_ack(tid, ack_state):
                    drifts.append({
                        "kind": "task",
                        "item_id": tid,
                        "current_status": status,
                        "issue": "active but result file exists, missing explicit ack",
                        "candidate_status": "completed",
                        "needs_explicit_ack": True,
                    })
                    continue
            drifts.append({
                "kind": "task",
                "item_id": tid,
                "current_status": status,
                "issue": "active but result file exists",
                "candidate_status": "completed",
                "needs_explicit_ack": False,
            })

    return drifts


def find_drift_patches(state):
    drifts = []
    patches = state.get("patches", {})

    for pid, patch in patches.items():
        status = patch.get("status", "")
        if status in {"cancelled", "completed", "failed", "merged"}:
            continue

        task_id = patch.get("task_id")
        task = state.get("tasks", {}).get(task_id, {}) if task_id else {}
        task_status = task.get("status", "")

        # Patch is drift if:
        # 1. status is blocked/in_progress/planning AND not in completed state
        # 2. AND its task is associated with active task (any state)
        if task_id and task:
            # Task exists: check if patch should follow task's resolution
            if task_status == "completed" or task.get("completed_at"):
                # Task completed but patch not completed
                if status not in {"completed", "merged"}:
                    drifts.append({
                        "kind": "patch",
                        "item_id": pid,
                        "task_id": task_id,
                        "current_status": status,
                        "issue": "associated task completed",
                        "candidate_status": "completed",
                    })
            elif status == "blocked" and task_id in state.get("active_tasks", []):
                # Blocked patch with active task
                drifts.append({
                    "kind": "patch",
                    "item_id": pid,
                    "task_id": task_id,
                    "current_status": status,
                    "issue": "blocked patch for active task",
                    "candidate_status": "completed",
                })
        elif status in RECONCILEABLE_PATCH_STATUSES:
            # No task association
            drifts.append({
                "kind": "patch",
                "item_id": pid,
                "task_id": task_id,
                "current_status": status,
                "issue": "patch in active state without resolution",
                "candidate_status": "completed",
            })
    return drifts


def apply_drift(state, drifts):
    applied = []
    errors = []
    for drift in drifts:
        if drift.get("needs_explicit_ack"):
            errors.append({
                "item_id": drift["item_id"],
                "kind": drift["kind"],
                "error": "explicit ACK required for claude_code task",
            })
            continue
        if drift.get("contains_negative_signals"):
            errors.append({
                "item_id": drift["item_id"],
                "kind": drift["kind"],
                "error": "result file contains_negative_signals, not auto-completing",
            })
            continue
        kind = drift["kind"]
        item_id = drift["item_id"]
        target = drift.get("candidate_status", "completed")
        if kind == "task" and item_id in state.get("tasks", {}):
            state["tasks"][item_id]["status"] = target
            state["tasks"][item_id]["updated_at"] = "2026-03-01T11:00:00+08:00"
            if target == "completed":
                state["tasks"][item_id]["completed_at"] = "2026-03-01T11:00:00+08:00"
            applied.append(drift)
        elif kind == "patch" and item_id in state.get("patches", {}):
            state["patches"][item_id]["status"] = target
            state["patches"][item_id]["updated_at"] = "2026-03-01T11:00:00+08:00"
            if target == "completed":
                state["patches"][item_id]["completed_at"] = "2026-03-01T11:00:00+08:00"
            applied.append(drift)
    return applied, errors


def reconcile(args):
    workspace = Path(args.workspace)
    state = read_state(workspace)
    if not state:
        print("No state file found", file=sys.stderr)
        return 1

    ack_state = read_ack_state(workspace)
    state.setdefault("workspace", str(workspace))

    task_drifts = find_drift_tasks(state, ack_state)
    patch_drifts = find_drift_patches(state)
    all_drifts = task_drifts + patch_drifts

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "drift_count": len(all_drifts),
        "applied_count": 0,
        "error_count": 0,
        "drifts": all_drifts,
    }

    if args.apply:
        applied, errors = apply_drift(state, all_drifts)
        report["applied_count"] = len(applied)
        report["error_count"] = len(errors)
        report["errors"] = errors
        state_file = workspace / "logs" / "collaboration_state.json"
        state_file.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if args.report:
        report_path = workspace / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if args.apply:
        if errors:
            # Write report even on error
            if args.report:
                report_path = workspace / args.report
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            return 1
        return 0
    if args.fail_on_drift and all_drifts:
        return 1
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report")
    p.add_argument("--fail-on-drift", action="store_true")
    args = p.parse_args()
    return reconcile(args)


if __name__ == "__main__":
    sys.exit(main())
