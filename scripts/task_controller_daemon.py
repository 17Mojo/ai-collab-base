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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 受管账本写入必须走 ai_collab.governance 的统一互斥原子入口；
# 从仓库根以外启动脚本时也要能找到包。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_HISTORY = "logs/task_controller_history.jsonl"
DEFAULT_REPORT = "logs/task_controller_report.json"

# 视为"已闭环"的终态
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
# 结果文件存在时，期望的任务状态
#
# 〔2026-11-18，台账 N45 已弃用〕这条判据只被 `audit_result_consistency` 的旧副本
# 用过，现已改为委托 ai_collab.result_consistency_audit。**不要再拿它做判断**：
# 它既不看产物是否缺失，也不解析结果文件状态行，还漏掉 ack_without_artifact。
# 保留常量只为不让可能的外部引用当场炸掉。
RESULT_FILE_EXPECTED_STATUSES = {"completed", "testing"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str | None) -> datetime | None:
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


def _age_seconds(updated_at: str | None) -> float:
    dt = _parse_ts(updated_at)
    if dt is None:
        return 0.0
    return (_now() - dt).total_seconds()


def read_state(workspace: Path) -> dict[str, Any]:
    path = workspace / "logs" / "collaboration_state.json"
    if not path.exists():
        return {"tasks": {}, "patches": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": {}, "patches": {}}


def write_state(workspace: Path, state: dict[str, Any]) -> None:
    """锁内重读 + 合并式写回，不整体覆写受管账本。"""
    from ai_collab.governance import merge_state_write

    merge_state_write(workspace / "logs" / "collaboration_state.json", state)


def read_ack_state(workspace: Path, state_path: str = "logs/agent_ack_bridge_state.json") -> dict[str, Any]:
    path = workspace / state_path
    if not path.exists():
        return {"items": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


def has_explicit_ack(task_id: str, ack_state: dict[str, Any]) -> bool:
    item = ack_state.get("items", {}).get(task_id)
    if not item:
        return False
    return item.get("source") == "cli-ack"


def result_file_exists(workspace: Path, task: dict[str, Any]) -> bool:
    rel = task.get("result_file")
    if rel:
        return (workspace / rel).exists()
    # 约定路径回退
    tid = task.get("task_id", "")
    return (workspace / "collaboration" / "results" / f"RESULT_{tid}.md").exists()


# ---------------- 契约检查 ----------------


def check_task_contract(task: dict[str, Any]) -> bool:
    """任务契约是否完整（含 acceptance_commands 与 result_file）。"""
    has_commands = bool(task.get("acceptance_commands"))
    has_result = bool(task.get("result_file"))
    return has_commands and has_result


# ---------------- drift ----------------


def detect_drifts(workspace: Path, state: dict[str, Any], ack_state: dict[str, Any]) -> list[dict[str, Any]]:
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
        drifts.append(
            {
                "kind": "task",
                "item_id": tid,
                "current_status": status,
                "needs_explicit_ack": True,
                "has_explicit_ack": has_explicit_ack(tid, ack_state),
            }
        )
    return drifts


# ---------------- stale ----------------


def detect_stale(state: dict[str, Any], *, pending_timeout: int, blocked_timeout: int) -> list[dict[str, Any]]:
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
    state: dict[str, Any],
    *,
    active_timeout: int,
    prewarn_ratio: float,
) -> list[dict[str, Any]]:
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
            out.append(
                {
                    "kind": "task",
                    "item_id": tid,
                    "age_seconds": age,
                    "threshold": threshold,
                    "already_applied": already,
                }
            )
    return out


# ---------------- patch candidates ----------------


def detect_patch_candidates(state: dict[str, Any]) -> list[dict[str, Any]]:
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
            p
            for p in patches.values()
            if p.get("task_id") == tid and p.get("status") not in {"completed", "merged", "cancelled"}
        ]
        if existing:
            continue
        out.append({"kind": "task", "item_id": tid, "patch_id": f"PATCH-{tid}-001"})
    return out


# ---------------- 结果一致性审计 ----------------


def audit_result_consistency(
    workspace: Path,
    state: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
) -> tuple[int, int, list[dict[str, Any]]]:
    """兼容层：委托 `ai_collab.result_consistency_audit` 的权威实现。

    〔2026-11-18，台账 N45 复查〕这里原本是**第三份**一致性判断：只看
    `status not in RESULT_FILE_EXPECTED_STATUSES`，不解析结果文件的状态行、
    不查产物缺失、不查 `ack_without_artifact`、不校验章节契约，却和权威实现
    产出同名的 `result_consistency_audited` / `result_consistency_issue_count`
    两个指标。而 `--once`（真实的 CLI 入口）走的正是这里——
    `run_controller_once` 反而只有测试在调。于是「守护进程已改为委托」这句话
    曾只对一个没人调的路径成立。

    `state` / `snapshot` 参数保留是为了不打断调用方签名：权威实现自己读盘，
    而调用点保证「先审计、后 write_state」，所以它读到的就是本轮开始时的状态，
    与快照同义。传进来的 state 不再参与判断——这正是要害：判断只有一份。
    """
    report = run_terminal_result_consistency_audit(workspace=Path(workspace))
    details = list(report.get("issues", []) or [])
    return int(report.get("audited_count", 0)), int(report.get("issue_count", 0)), details


# ---------------- 主流程 ----------------

# ---------------- 模块级接口（供集成测试与外部调用） ----------------


class StateManager:
    """StateManager 适配器（供外部/测试注入替换）。"""

    def __init__(self, *, workspace_path: str):
        self.workspace_path = workspace_path
        self._state = read_state(Path(workspace_path))

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def validate_task_contracts(self, scope: str = "active") -> dict[str, Any]:
        active = set(self._state.get("active_tasks", []))
        checked = 0
        invalid = 0
        issues: list[dict[str, Any]] = []
        for tid in active:
            task = self._state.get("tasks", {}).get(tid)
            if not task:
                continue
            checked += 1
            if not check_task_contract(task):
                invalid += 1
                issues.append({"task_id": tid, "issue": "missing acceptance_commands or result_file"})
        return {"checked_tasks": checked, "skipped_tasks": 0, "invalid_count": invalid, "issues": issues}


def detect_state_drifts(state: dict[str, Any], workspace: Path) -> list[dict[str, Any]]:
    """模块级 drift 检测（供集成调用）。"""
    ack_state = read_ack_state(Path(workspace))
    return detect_drifts(Path(workspace), state, ack_state)


def detect_prewarning_tasks(
    *,
    workspace: Path,
    state: dict[str, Any],
    active_timeout_sec: int,
    prewarn_ratio: float,
) -> list[dict[str, Any]]:
    return detect_prewarning(
        Path(workspace),
        state,
        active_timeout=active_timeout_sec,
        prewarn_ratio=prewarn_ratio,
    )


def detect_stale_tasks(
    *,
    state: dict[str, Any],
    pending_timeout_sec: int,
    blocked_timeout_sec: int,
) -> list[dict[str, Any]]:
    return detect_stale(
        state,
        pending_timeout=pending_timeout_sec,
        blocked_timeout=blocked_timeout_sec,
    )


def run_terminal_result_consistency_audit(*, workspace: Path) -> dict[str, Any]:
    """结果一致性审计 —— 委托给 `ai_collab.result_consistency_audit` 的唯一实现。

    〔2026-11-18，台账 N45〕这里原本有一份**独立的弱化副本**：
    - 不校验终态（把 `testing` 也算成「一致」）；
    - 仍用 N41 之前的 `"## 执行命令" in text` 子串判据；
    - 不解析结果文件的状态行，因此永远不会报 `terminal_status_mismatch`；
    - **却覆写同一个报告文件**（`logs/task_result_consistency_report.json`
      与 `collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md`）。

    后果是「谁后跑谁说了算」：守护进程跑一次，就把真实现的审计结论覆盖成
    一份弱化结论，而读这两个文件的正是人。改为委托后，两条入口不会再给出
    互相矛盾的结论（与 N41 同型：同一判据不许有两份实现）。
    """
    from ai_collab.result_consistency_audit import (
        run_terminal_result_consistency_audit as _audit,
    )

    return _audit(workspace=Path(workspace))


def run_ack_watchdog(*, workspace: Path, dry_run: bool) -> dict[str, Any]:
    """ACK watchdog —— 委托 `ai_collab.ack_watchdog.run_ack_watchdog`，但**强制 dry-run**。

    〔2026-11-18，台账 N45〕此前这里是恒返回
    `{candidate_count: 0, redispatched_count: 0, alerted_count: 0}` 的空壳。
    它只被读这三个计数，所以从输出上完全看不出「这里根本没做扫描」——
    看到 0 的人会以为「没有超阈未 ACK 的任务」。改为委托真实现后，
    candidate_count 是真实扫描结果。

    但**不**把守护进程自己的 dry_run 透传下去。真实现的 apply 模式会：
    `dispatched_at=now`、`dispatch_count+1`、`watchdog_redispatch_count+1`，
    并重写 `collaboration/monitoring/AGENT_TRIGGER_<assignee>_latest.md`
    ——那是 agent 读取的派单入口，等于在本进程里重新下达指令；还会对
    该 assignee 的在途 intervention 执行 rearm。守护进程的定位是周期巡检，
    不是派单器，所以固定 `dry_run=True`：

      - 拿到真实 candidate_count（可观测，不再是假 0）；
      - 报告 mode 恒为 "dry-run"，读的人不会误以为本轮重派过；
      - 零重派风险。

    要真正执行重派，用 `python3 -m ai_collab.cli check`，或显式调用
    `ai_collab.ack_watchdog.run_ack_watchdog(dry_run=False)`。
    把它升格为 apply 需要单独裁定，不要在这里悄悄改（`stubbed: False`
    表示「已接真实现」，便于上层区分本轮是「没候选」还是「没扫描」）。
    """
    from ai_collab.ack_watchdog import DEFAULT_REPORT_PATH as _REPORT_PATH
    from ai_collab.ack_watchdog import run_ack_watchdog as _watchdog

    report = _watchdog(workspace=Path(workspace), dry_run=True)

    # 注意真实现的口径：它的 `redispatched_count` / `alerted_count` 是
    # 「按计划该这么做」的数量，dry-run 下也照样计数（因为 report 在
    # `if not dry_run` 之外汇总 handled）。守护进程既然强制 dry-run，
    # **实际动作恒为 0**，所以那两个字段必须报实际值，把计划值单列成
    # would_*。否则报告会写「redispatched 1」而守护进程其实什么都没做。
    return {
        "candidate_count": int(report.get("candidate_count", 0) or 0),
        "redispatched_count": 0,
        "alerted_count": 0,
        "would_redispatch_count": int(report.get("redispatched_count", 0) or 0),
        "would_alert_count": int(report.get("alerted_count", 0) or 0),
        # 下面两个字段是给读报告的人用的：0 到底是「没候选」还是「没扫描」
        "mode": report.get("mode", "dry-run"),
        "stubbed": False,
        # 调用方的 dry_run 被刻意忽略，回传以便自查
        "daemon_dry_run": dry_run,
        "report_file": _REPORT_PATH,
        "summary_file": report.get("summary_file"),
    }


def run_controller_once(
    *,
    workspace,
    pending_timeout_sec: int,
    active_timeout_sec: int,
    blocked_timeout_sec: int,
    prewarn_ratio: float,
    dry_run: bool,
    default_assignee: str | None = None,
) -> dict[str, Any]:
    """控制器单轮执行（模块级，供集成调用）。"""
    workspace = Path(workspace)
    state = read_state(workspace)
    state.setdefault("workspace", str(workspace))
    state.setdefault("tasks", {})
    state.setdefault("patches", {})
    errors: list[dict[str, Any]] = []

    # 契约检查（通过 StateManager 以支持注入）
    manager = StateManager(workspace_path=str(workspace))
    try:
        contract = manager.validate_task_contracts(scope="active")
    except AssertionError:
        contract = {"checked_tasks": 0, "skipped_tasks": 0, "invalid_count": 0, "issues": []}

    # drift
    drifts = detect_state_drifts(state, workspace)
    drift_applied = 0
    for d in drifts:
        if dry_run:
            continue
        if d.get("needs_explicit_ack") and not d.get("has_explicit_ack"):
            errors.append(
                {
                    "kind": d["kind"],
                    "item_id": d["item_id"],
                    "error": "explicit ACK required before auto-complete",
                }
            )
            continue
        tid = d["item_id"]
        state["tasks"][tid]["status"] = "completed"
        state["tasks"][tid]["completed_at"] = _now().isoformat()
        state["tasks"][tid]["updated_at"] = _now().isoformat()
        drift_applied += 1

    # prewarning
    prewarns = detect_prewarning_tasks(
        workspace=workspace,
        state=state,
        active_timeout_sec=active_timeout_sec,
        prewarn_ratio=prewarn_ratio,
    )
    prewarning_applied = 0
    for p in prewarns:
        if dry_run or p["already_applied"]:
            continue
        tid = p["item_id"]
        task = state["tasks"][tid]
        task.setdefault("notes", []).append(f"[prewarning] near timeout (age={p['age_seconds']:.0f}s)")
        task.setdefault("controller_alerts", {})["prewarning"] = {
            "at": _now().isoformat(),
            "age_seconds": p["age_seconds"],
        }
        prewarning_applied += 1

    # stale
    stales = detect_stale_tasks(
        state=state,
        pending_timeout_sec=pending_timeout_sec,
        blocked_timeout_sec=blocked_timeout_sec,
    )
    stale_blocked = 0
    stale_failed = 0
    for s in stales:
        if dry_run:
            continue
        tid = s["item_id"]
        target = s["target"]
        state["tasks"][tid]["status"] = target
        state["tasks"][tid]["updated_at"] = _now().isoformat()
        if target == "blocked":
            stale_blocked += 1
        elif target == "failed":
            stale_failed += 1

    # patch candidates
    pcs = detect_patch_candidates(state)
    patches_created = 0
    for pc in pcs:
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
            "assignee": default_assignee or task.get("assignee", "codex"),
            "status": "pending",
            "created_at": _now().isoformat(),
            "updated_at": _now().isoformat(),
            "completed_at": None,
            "result_file": None,
            "notes": [],
        }
        patches_created += 1

    # 结果一致性
    consistency = run_terminal_result_consistency_audit(workspace=workspace)

    # ACK watchdog
    ack_result = run_ack_watchdog(workspace=workspace, dry_run=dry_run)

    if not dry_run:
        write_state(workspace, state)

    report = {
        "mode": "dry-run" if dry_run else "apply",
        "drift_detected": len(drifts),
        "drift_applied": drift_applied,
        "prewarning_detected": len(prewarns),
        "prewarning_applied": prewarning_applied,
        "stale_detected": len(stales),
        "stale_marked_blocked": stale_blocked,
        "stale_marked_failed": stale_failed,
        "patch_candidates": len(pcs),
        "patches_created": patches_created,
        "task_contract_checked": contract["checked_tasks"],
        "task_contract_invalid": contract["invalid_count"],
        "result_consistency_audited": consistency["audited_count"],
        "result_consistency_consistent": consistency["consistent_count"],
        "result_consistency_mismatch": consistency["mismatch_count"],
        "result_consistency_unparseable": consistency["unparseable_count"],
        "result_consistency_missing_result": consistency["missing_result_count"],
        "result_consistency_issue_count": consistency["issue_count"],
        "result_consistency_report_file": consistency["report_file"],
        "result_consistency_summary_file": consistency["summary_file"],
        "ack_watchdog_candidate_count": ack_result["candidate_count"],
        "ack_watchdog_redispatched_count": ack_result["redispatched_count"],
        "ack_watchdog_alerted_count": ack_result["alerted_count"],
        # 强制 dry-run：上面两个「实际动作」恒为 0，计划值在这里
        "ack_watchdog_would_redispatch_count": ack_result.get("would_redispatch_count", 0),
        "ack_watchdog_would_alert_count": ack_result.get("would_alert_count", 0),
        # 「0 个候选」和「没扫描」必须能从报告里分开（台账 N45）
        "ack_watchdog_mode": ack_result.get("mode", "dry-run"),
        "ack_watchdog_stubbed": ack_result.get("stubbed", False),
        "error_count": len(errors),
        "errors": errors,
        "timestamp": _now().isoformat(),
    }
    return report


def run_once(args) -> int:
    workspace = Path(args.workspace)
    state = read_state(workspace)
    state.setdefault("workspace", str(workspace))
    state.setdefault("tasks", {})
    state.setdefault("patches", {})
    ack_state = read_ack_state(workspace)

    # 审计快照（反映本轮开始时的状态，供结果一致性审计使用）
    audit_snapshot = json.loads(json.dumps(state))

    dry_run = args.dry_run
    errors: list[dict[str, Any]] = []

    # 1. drift
    drifts = detect_drifts(workspace, state, ack_state)
    drift_applied = 0
    for d in drifts:
        if dry_run:
            continue
        if d["needs_explicit_ack"] and not d["has_explicit_ack"]:
            errors.append(
                {
                    "kind": d["kind"],
                    "item_id": d["item_id"],
                    "error": "explicit ACK required before auto-complete",
                }
            )
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
        workspace,
        state,
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

    # 7. ACK 看门狗（强制 dry-run：只观测候选数，绝不重派）
    #
    # 〔2026-11-18，台账 N45 复查〕此前 `--once` 这条真实入口**根本不调看门狗**，
    # 只有 `run_controller_once` 调——而那个函数只有测试在用。于是「看门狗恒
    # 返回 0」实际是更糟的情况：连 0 都不是它算的，报告里压根没有这几个字段。
    # 放在 write_state 之后，是为了让 apply 模式下的看门狗看到本轮已收敛的状态，
    # 而不是它自己即将重派的旧状态。
    ack_result = run_ack_watchdog(workspace=workspace, dry_run=dry_run)

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
        "ack_watchdog_candidate_count": ack_result["candidate_count"],
        "ack_watchdog_redispatched_count": ack_result["redispatched_count"],
        "ack_watchdog_alerted_count": ack_result["alerted_count"],
        "ack_watchdog_would_redispatch_count": ack_result.get("would_redispatch_count", 0),
        "ack_watchdog_would_alert_count": ack_result.get("would_alert_count", 0),
        "ack_watchdog_mode": ack_result.get("mode", "dry-run"),
        "ack_watchdog_stubbed": ack_result.get("stubbed", False),
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
        "ack_watchdog_candidate_count": report["ack_watchdog_candidate_count"],
        "ack_watchdog_would_redispatch_count": report["ack_watchdog_would_redispatch_count"],
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


if __name__ == "__main__":
    sys.exit(main())
