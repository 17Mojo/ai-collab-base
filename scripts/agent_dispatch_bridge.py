#!/usr/bin/env python3
"""Agent Dispatch Bridge - 自动派单桥接脚本"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List


def read_state(workspace: Path) -> dict:
    state_file = workspace / "logs" / "collaboration_state.json"
    if not state_file.exists():
        return {"tasks": {}, "global_state": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": {}, "global_state": {}}


def read_dispatch_state(workspace: Path) -> dict:
    state_file = workspace / "logs" / "agent_dispatch_state.json"
    if not state_file.exists():
        return {"items": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


def write_dispatch_state(workspace: Path, state: dict) -> None:
    state_file = workspace / "logs" / "agent_dispatch_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report(workspace: Path, report: dict) -> None:
    report_file = workspace / "logs" / "task_dispatch_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def write_history(workspace: Path, line: str) -> None:
    history_file = workspace / "logs" / "agent_dispatch_history.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def build_update_command(order: dict) -> str:
    task_id = order.get("task_id", "")
    ai = order.get("ai_type", order.get("assignee", "claude_code"))
    return (
        f"python3 -m ai_collab.cli tasks update "
        f"--task-id {task_id} --ai {ai} --status implementing"
    )


def write_orders_markdown(workspace: Path, orders: list, dispatch_state: dict = None, task_lookup: dict = None) -> None:
    md_dir = workspace / "collaboration" / "monitoring"
    md_dir.mkdir(parents=True, exist_ok=True)
    md_file = md_dir / "AGENT_DISPATCH_ORDERS_test.md"
    if dispatch_state is None:
        dispatch_state = {"items": {}}
    if task_lookup is None:
        task_lookup = {}
    lines = [
        "# Agent Dispatch Orders",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Task Status Updates",
        "",
    ]
    for o in orders:
        lines.append("")
        # Check if this task was previously dispatched
        existing = dispatch_state.get("items", {}).get(o["task_id"])
        is_reopened = existing and existing.get("status") == "pending"

        if is_reopened:
            lines.append("### 返工重派说明（必须先读）")
            lines.append("")
            lines.append(f"**任务**: {o['task_id']}")
            lines.append(f"**原状态**: {existing.get('status')}")
            lines.append(f"**新状态**: {o.get('status')}")
            lines.append("")
            # Include notes from task
            task_notes = task_lookup.get(o["task_id"], {}).get("notes", [])
            if task_notes:
                lines.append("**任务 notes (review 反馈)**:")
                lines.append("")
                for note in task_notes:
                    lines.append(f"- {note}")
                lines.append("")
            lines.append("此任务之前已 dispatch，但被 review 拒绝。")
            lines.append("重新 dispatch 前请先读 `notes` 字段了解拒绝原因。")
            lines.append("")
            lines.append("**禁止因为 result_file 已存在或任务曾到过 testing 就回复 noop。**")
            lines.append("")

        lines.append(f"### {o['task_id']}")
        lines.append("")
        lines.append("```bash")
        lines.append(build_update_command(o))
        lines.append("```")
        cmds = o.get("commands", [])
        if cmds:
            lines.append("")
            lines.append("#### Acceptance Commands")
            for c in cmds:
                lines.append(f"- `{c}`")
    md_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_order(task: dict) -> dict:
    return {
        "task_id": task.get("task_id"),
        "ai_type": task.get("ai_type", "claude_code"),
        "assignee": task.get("assignee", "claude_code"),
        "status": task.get("status", "planning"),
        "commands": task.get("acceptance_commands", []),
        "result_file": task.get("result_file", ""),
        "dispatched_at": datetime.now().isoformat(),
    }


def classify_task(task: dict, existing: dict, args) -> dict:
    """Classify a task for dispatch.

    Logic:
    1. New task (not in dispatch_state): always candidate
    2. Existing + --redispatch: reopened/candidate (regardless of --include-pending)
    3. Existing + status=planning (not redispatched): keep in candidate (or already)
    4. Existing + status=implementing (not redispatched): skipped (already)
    5. Existing + status=pending/other (not redispatched): need --include-pending

    Returns: {
        "candidate": bool,    # should appear in candidate_count
        "dispatched": bool,   # should count as dispatched
        "already": bool,      # should count as already_dispatched
        "reopened": bool,      # reopened (redispatch after implementing)
    }
    """
    status = task.get("status", "")
    include_pending = args.include_pending
    redispatch = args.redispatch
    dry_run = args.dry_run

    if not existing:
        # New task: subject to --include-pending filter
        if not include_pending and status != "planning":
            return {"candidate": False, "dispatched": False, "already": False, "reopened": False}
        return {"candidate": True, "dispatched": True, "already": False, "reopened": False}

    # Existing task in dispatch_state
    if redispatch:
        # --redispatch mode: any status reopened
        if status == "implementing":
            return {"candidate": True, "dispatched": True, "already": False, "reopened": True}
        # planning or pending: redispatch
        return {"candidate": True, "dispatched": True, "already": False, "reopened": False}

    # No redispatch
    if status == "planning":
        # Was dispatched, never started → dry-run keeps as candidate
        if dry_run:
            return {"candidate": True, "dispatched": True, "already": False, "reopened": False}
        # No dry-run: still candidate but already (no new dispatch)
        return {"candidate": True, "dispatched": False, "already": True, "reopened": False}

    if status == "implementing":
        # Already implementing: skip
        return {"candidate": False, "dispatched": False, "already": True, "reopened": False}

    # Other status (pending, etc.) - need --include-pending
    if not include_pending:
        return {"candidate": False, "dispatched": False, "already": False, "reopened": False}

    return {"candidate": True, "dispatched": True, "already": False, "reopened": False}


def dispatch_once(args) -> int:
    workspace = Path(args.workspace)
    state = read_state(workspace)
    dispatch_state = read_dispatch_state(workspace)
    tasks = state.get("tasks", {})

    candidates: List[str] = []
    candidate_tasks: List[dict] = []  # Task objects with status
    dispatched: List[str] = []
    already: List[str] = []
    reopened: List[str] = []

    for tid, task in tasks.items():
        existing = dispatch_state.get("items", {}).get(tid)
        result = classify_task(task, existing, args)

        if not result["candidate"]:
            continue

        candidates.append(tid)
        candidate_tasks.append(task)

        if result["reopened"]:
            reopened.append(tid)

        if result["already"]:
            already.append(tid)

        if result["dispatched"]:
            dispatched.append(tid)
            if not args.dry_run:
                order = build_order(task)
                dispatch_state.setdefault("items", {})[tid] = order

    if not args.dry_run:
        write_dispatch_state(workspace, dispatch_state)

    # NotebookLM 增强
    notebooklm_enriched = 0
    if args.enrich_notebooklm and not args.dry_run:
        # dry-run 仍报告（但 0）用于测试
        notebooklm_enriched = enrich_with_notebooklm(
            [t for t in tasks.values() if isinstance(t, dict)],
            mode=args.notebooklm_mode,
        )

    report = {
        "candidate_count": len(candidates),
        "dispatched_count": len(dispatched),
        "notebooklm_enriched": notebooklm_enriched,
        "already_dispatched_count": len(already),
        "reopened_count": len(reopened),
        "dispatched_tasks": dispatched,
        "already_dispatched_tasks": already,
        "candidate_tasks": candidate_tasks,
        "reopened_tasks": reopened,
        "timestamp": datetime.now().isoformat(),
    }

    write_report(workspace, report)
    if args.orders:
        orders = list(dispatch_state.get("items", {}).values())
        # Build task lookup for note extraction
        task_lookup = {tid: task for tid, task in tasks.items()}
        write_orders_markdown(workspace, orders, dispatch_state, task_lookup)
    if args.history and not args.dry_run:
        write_history(workspace, json.dumps({"event": "dispatch", "count": len(dispatched)}))

    # 同时输出 key=value 摘要（用于 shell 解析）
    print(f"mode={args.notebooklm_mode}")
    print(f"candidate_count={report['candidate_count']}")
    print(f"dispatched_count={report['dispatched_count']}")
    print(f"already_dispatched_count={report['already_dispatched_count']}")
    print(f"stale_marked_blocked={report.get('stale_marked_blocked', 0)}")
    print(f"stale_marked_failed={report.get('stale_marked_failed', 0)}")
    print(f"patch_candidates={report.get('patch_candidates', 0)}")
    print(f"patches_created={report.get('patches_created', 0)}")
    print(f"prewarning_detected={report.get('prewarning_detected', 0)}")
    print(f"prewarning_applied={report.get('prewarning_applied', 0)}")
    print(f"task_contract_checked={report.get('task_contract_checked', 0)}")
    print(f"task_contract_invalid={report.get('task_contract_invalid', 0)}")
    print(f"notebooklm_enriched={report.get('notebooklm_enriched', 0)}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", default=".", required=False,
                   help="Workspace path (default: current directory)")
    p.add_argument("--include-pending", action="store_true")
    p.add_argument("--redispatch", action="store_true")
    p.add_argument("--force-workspace", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report")
    p.add_argument("--history")
    p.add_argument("--state")
    p.add_argument("--orders")
    p.add_argument("--enrich-notebooklm", action="store_true",
                   help="Enrich dispatch with NotebookLM knowledge")
    p.add_argument("--notebooklm-mode", default="fallback",
                   choices=["fallback", "mock", "real"],
                   help="NotebookLM integration mode")
    args = p.parse_args()
    return dispatch_once(args)


if __name__ == "__main__":
    sys.exit(main())
