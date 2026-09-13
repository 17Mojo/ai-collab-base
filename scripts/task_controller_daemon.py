#!/usr/bin/env python3
"""Task Controller Daemon - 任务控制器守护进程.

职责:
- drift 检测与对账（结果文件存在但状态未闭环）
- stale 检测与升级（pending→blocked，blocked→failed）
- prewarning（超时前预警）
- 复核结论驱动的 patch 创建
- 结果一致性审计
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_HISTORY = "logs/task_controller_history.jsonl"
DEFAULT_REPORT = "logs/task_controller_report.json"

# 视为"已闭环"的终态
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
# 结果文件存在时，期望的任务状态
RESULT_FILE_EXPECTED_STATUSES = {"completed", "testing"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        ts = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _age_seconds(updated_at: Optional[str]) -> float:
    dt = _parse_ts(updated_at)
    if dt is None:
        return 0.0
    return (_now() - dt).total_seconds()


def read_state(workspace: Path) -> Dict[str, Any]:
    path = workspace / "logs" / "collaboration_state.json"
    if not path.exists():
        return {"tasks": {}, "patches": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": {}, "patches": {}}


def write_state(workspace: Path, state: Dict[str, Any]) -> None:
    path = workspace / "logs" / "collaboration_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def read_ack_state(workspace: Path, state_path: str = "logs/agent_ack_bridge_state.json") -> Dict[str, Any]:
    path = workspace / state_path
    if not path.exists():
        return {"items": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


def has_explicit_ack(task_id: str, ack_state: Dict[str, Any]) -> bool:
    item = ack_state.get("items", {}).get(task_id)
    if not item:
        return False
    return item.get("source") == "cli-ack"


def result_file_exists(workspace: Path, task: Dict[str, Any]) -> bool:
    rel = task.get("result_file")
    if rel:
        return (workspace / rel).exists()
    # 约定路径回退
    tid = task.get("task_id", "")
    return (workspace / "collaboration" / "results" / f"RESULT_{tid}.md").exists()


# ---------------- 契约检查 ----------------

def check_task_contract(task: Dict[str, Any]) -> bool:
    """任务契约是否完整（含 acceptance_commands 与 result_file）。"""
    has_commands = bool(task.get("acceptance_commands"))
    has_result = bool(task.get("result_file"))
    return has_commands and has_result


# ---------------- drift ----------------

def detect_drifts(workspace: Path, state: Dict[str, Any], ack_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """检测 drift：结果文件存在但状态未闭环。"""
    drifts = []
    active = set(state.get("active_tasks", []))
    for tid, task in state.get("tasks", {}).items():
        if tid not in active:
            continue
        status = task.get("status", "")
        if status in TERMINAL_STATUSES:
            continue
        if not result_file_exists(workspace, task):
            continue
        # 所有 drift 收口都需要显式 ACK（无论 AI 类型）
        drifts.append({
            "kind": "task",
            "item_id": tid,
            "current_status": status,
            "needs_explicit_ack": True,
            "has_explicit_ack": has_explicit_ack(tid, ack_state),
        })
    return drifts


# ---------------- stale ----------------

def detect_stale(state: Dict[str, Any], *, pending_timeout: int, blocked_timeout: int) -> List[Dict[str, Any]]:
    """检测超时任务。"""
    stale = []
    active = set(state.get("active_tasks", []))
    for tid, task in state.get("tasks", {}).items():
        if tid not in active:
            continue
        status = task.get("status", "")
        if status in TERMINAL_STATUSES:
            continue
        age = _age_seconds(task.get("updated_at"))
        if status == "pending" and pending_timeout and age > pending_timeout:
            stale.append({"kind": "task", "item_id": tid, "current_status": status, "target": "blocked"})
        elif status == "blocked" and blocked_timeout and age > blocked_timeout:
            stale.append({"kind": "task", "item_id": tid, "current_status": status, "target": "failed"})
        elif status == "implementing" and pending_timeout and age > pending_timeout:
            # implementing 超时同样标记 blocked（若无结果文件）
            if not result_file_exists(Path(state.get("workspace", ".")), task):
                stale.append({"kind": "task", "item_id": tid, "current_status": status, "target": "blocked"})
    return stale


# ---------------- prewarning ----------------

def detect_prewarning(
    workspace: Path,
    state: Dict[str, Any],
    *,
    active_timeout: int,
    prewarn_ratio: float,
) -> List[Dict[str, Any]]:
    """检测接近超时的任务（预警）。"""
    out = []
    active = set(state.get("active_tasks", []))
    for tid, task in state.get("tasks", {}).items():
        if tid not in active:
            continue
        if task.get("status") != "implementing":
            continue
        if not active_timeout:
            continue
        age = _age_seconds(task.get("updated_at"))
        threshold = active_timeout * prewarn_ratio
        if age >= threshold and age < active_timeout:
            alerts = task.get("controller_alerts") or {}
            already = bool(alerts.get("prewarning"))
            out.append({
                "kind": "task",
                "item_id": tid,
                "age_seconds": age,
                "threshold": threshold,
                "already_applied": already,
            })
    return out


# ---------------- patch candidates ----------------

def detect_patch_candidates(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """检测需要跟进 patch 的复核结论。"""
    out = []
    patches = state.get("patches", {})
    for tid, task in state.get("tasks", {}).items():
        conclusion = task.get("review_conclusion") or task.get("conclusion")
        if conclusion != "action_required":
            continue
        if task.get("status") not in TERMINAL_STATUSES:
            continue
        # 是否已有 open patch
        existing = [
            p for p in patches.values()
            if p.get("task_id") == tid and p.get("status") not in {"completed", "merged", "cancelled"}
        ]
        if existing:
            continue
        out.append({"kind": "task", "item_id": tid, "patch_id": f"PATCH-{tid}-001"})
    return out


# ---------------- 结果一致性审计 ----------------

def audit_result_consistency(
    workspace: Path,
    state: Dict[str, Any],
    *,
    snapshot: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """审计结果一致性（优先使用本轮开始时的快照）。"""
    basis = snapshot if snapshot is not None else state
    audited = 0
    issues = []
    for tid, task in basis.get("tasks", {}).items():
        if not result_file_exists(workspace, task):
            continue
        audited += 1
        status = task.get("status", "")
        if status not in RESULT_FILE_EXPECTED_STATUSES:
            issues.append({"kind": "task", "item_id": tid, "issue": "result_file exists but status not closed"})
    return audited, len(issues), issues


# ---------------- 主流程 ----------------

def run_once(args) -> int:
    workspace = Path(args.workspace)
    state = read_state(workspace)
    state.setdefault("workspace", str(workspace))
    state.setdefault("tasks", {})
    state.setdefault("patches", {})
    ack_state = read_ack_state(workspace)

    # 审计快照（反映本轮开始时的状态）
    audit_snapshot = json.loads(json.dumps(state))

    dry_run = args.dry_run
    errors: List[Dict[str, Any]] = []

    # 1. drift
    drifts = detect_drifts(workspace, state, ack_state)
    drift_applied = 0
    for d in drifts:
        if dry_run:
            continue
        if d["needs_explicit_ack"] and not d["has_explicit_ack"]:
            errors.append({
                "kind": d["kind"],
                "item_id": d["item_id"],
                "error": "explicit ACK required before auto-complete",
            })
            continue
        tid = d["item_id"]
        state["tasks"][tid]["status"] = "completed"
        state["tasks"][tid]["completed_at"] = _now().isoformat()
        state["tasks"][tid]["updated_at"] = _now().isoformat()
        drift_applied += 1

    # 2. stale
    stales = detect_stale(
        state,
        pending_timeout=args.pending_timeout_sec,
        blocked_timeout=args.blocked_timeout_sec,
    )
    stale_marked_blocked = 0
    stale_marked_failed = 0
    for s in stales:
        if dry_run:
            continue
        tid = s["item_id"]
        target = s["target"]
        state["tasks"][tid]["status"] = target
        state["tasks"][tid]["updated_at"] = _now().isoformat()
        if target == "blocked":
            stale_marked_blocked += 1
        elif target == "failed":
            stale_marked_failed += 1

    # 3. prewarning
    prewarns = detect_prewarning(
        workspace, state,
        active_timeout=args.active_timeout_sec,
        prewarn_ratio=args.prewarn_ratio,
    )
    prewarning_applied = 0
    for p in prewarns:
        if dry_run:
            continue
        if p["already_applied"]:
            continue
        tid = p["item_id"]
        task = state["tasks"][tid]
        notes = task.setdefault("notes", [])
        notes.append(f"[prewarning] task near timeout (age={p['age_seconds']:.0f}s)")
        alerts = task.setdefault("controller_alerts", {})
        alerts["prewarning"] = {"at": _now().isoformat(), "age_seconds": p["age_seconds"]}
        # 注意：不更新 updated_at，保留心跳时间，使后续运行仍可检测到
        prewarning_applied += 1

    # 4. patch candidates
    patch_candidates = detect_patch_candidates(state)
    patches_created = 0
    for pc in patch_candidates:
        if dry_run:
            continue
        tid = pc["item_id"]
        pid = pc["patch_id"]
        if pid in state["patches"]:
            continue
        task = state["tasks"][tid]
        state["patches"][pid] = {
            "patch_id": pid,
            "task_id": tid,
            "title": f"Follow-up for {tid}",
            "assignee": args.default_assignee or task.get("assignee", "codex"),
            "status": "pending",
            "created_at": _now().isoformat(),
            "updated_at": _now().isoformat(),
            "completed_at": None,
            "result_file": None,
            "notes": [],
        }
        patches_created += 1

    # 5. 契约检查
    active = set(state.get("active_tasks", []))
    contract_checked = 0
    contract_invalid = 0
    for tid in active:
        task = state["tasks"].get(tid)
        if not task:
            continue
        contract_checked += 1
        if not check_task_contract(task):
            contract_invalid += 1

    # 6. 结果一致性
    consistency_audited, consistency_issues, consistency_details = audit_result_consistency(
        workspace, state, snapshot=audit_snapshot
    )

    if not dry_run:
        write_state(workspace, state)

    report = {
        "mode": "dry-run" if dry_run else "apply",
        "drift_detected": len(drifts),
        "drift_applied": drift_applied,
        "prewarning_detected": len(prewarns),
        "prewarning_applied": prewarning_applied,
        "stale_detected": len(stales),
        "stale_marked_blocked": stale_marked_blocked,
        "stale_marked_failed": stale_marked_failed,
        "patch_candidates": len(patch_candidates),
        "patches_created": patches_created,
        "task_contract_checked": contract_checked,
        "task_contract_invalid": contract_invalid,
        "result_consistency_audited": consistency_audited,
        "result_consistency_issue_count": consistency_issues,
        "result_consistency_issues": consistency_details,
        "error_count": len(errors),
        "errors": errors,
        "timestamp": _now().isoformat(),
    }

    if args.report:
        rp = workspace / args.report
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # history（始终写）
    hp = workspace / (args.history or DEFAULT_HISTORY)
    hp.parent.mkdir(parents=True, exist_ok=True)
    history_item = {
        "mode": report["mode"],
        "prewarning_detected": report["prewarning_detected"],
        "prewarning_applied": report["prewarning_applied"],
        "stale_detected": report["stale_detected"],
        "stale_marked_blocked": report["stale_marked_blocked"],
        "stale_marked_failed": report["stale_marked_failed"],
        "drift_detected": report["drift_detected"],
        "drift_applied": report["drift_applied"],
        "patches_created": report["patches_created"],
        "result_consistency_audited": report["result_consistency_audited"],
        "result_consistency_issue_count": report["result_consistency_issue_count"],
        "error_count": report["error_count"],
        "timestamp": report["timestamp"],
    }
    with hp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history_item, ensure_ascii=False) + "\n")

    print(json.dumps(report, indent=2, ensure_ascii=False))

    # 退出码：apply 模式下若存在未解决 error 则返回 1
    if not dry_run and errors:
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--interval-sec", type=int)
    p.add_argument("--max-iterations", type=int)
    p.add_argument("--pending-timeout-sec", type=int, default=1800)
    p.add_argument("--active-timeout-sec", type=int, default=3600)
    p.add_argument("--blocked-timeout-sec", type=int, default=7200)
    p.add_argument("--prewarn-ratio", type=float, default=0.8)
    p.add_argument("--history")
    p.add_argument("--default-assignee")
    p.add_argument("--report")
    args = p.parse_args()
    return run_once(args)


# 兼容测试导入
StateManager = None


if __name__ == "__main__":
    sys.exit(main())
