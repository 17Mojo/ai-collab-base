"""
AI 协作开发系统 - CLI 工具

支持命令行操作：激活、检查冲突、查看任务、管理日志等
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 导入 prompt_pack 管理功能
from ai_collab.prompt_pack import AITool, PackCategoryType, PackManager

from ..ack_protocol import (
    SUPPORTED_ASSIGNEES,
    build_ack_line,
    get_ack_bridge_item,
    load_ack_bridge_state,
    normalize_assignee,
    normalize_result_file,
    record_ack_bridge,
    summarize_ack_bridge_state,
)
from ..ack_remediation import run_ack_remediation
from ..ack_watchdog import run_ack_watchdog

# 直接从当前包的子模块导入
from ..activation_handler import ActivationHandler, ActivationMode, AIType, VSCodeIntegration
from ..codex_integration import CodexIntegration

# 导入日报和监控功能
from ..daily_report import (
    generate_daily_report,
    write_daily_report_json,
    write_daily_report_markdown,
)
from ..dispatch_trigger import build_handoff_payload, parse_trigger_phrase, split_orders_by_assignee
from ..missing_ack_monitor import run_missing_ack_monitor
from ..noop_pending_monitor import (
    get_noop_pending_stats,
    write_noop_pending_report,
    write_noop_pending_summary,
)
from ..result_consistency_audit import run_terminal_result_consistency_audit
from ..spawn_agent_guard import run_spawn_agent_guard
from ..state_manager import PatchStatus, StateManager, TaskStatus
from ..workspace_guard import (
    STAGE_DOMAINS,
    inspect_workspace,
    run_workspace_guard,
    stage_domain_changes,
)


def _set_workspace_env(workspace: Optional[str]):
    """统一设置工作区环境变量，避免 VSCode 注入无效路径。"""
    if workspace:
        os.environ["VSCODE_CWD"] = os.path.abspath(workspace)


def _as_int(value: object, fallback: int) -> int:
    """安全转换整数配置值。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _load_json_file(path: Path) -> dict:
    """Best-effort JSON reader for lightweight status/report summaries."""
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_iso_datetime(value: object) -> datetime | None:
    """Parse ISO-like timestamps used by governance reports."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _report_health_line(
    *, name: str, path: Path, payload: dict, stale_after_minutes: int = 180
) -> str:
    """Build a human-readable health line for status output."""
    if not path.exists():
        return f"  {name}: missing ({path})"

    generated_at = (
        _parse_iso_datetime(payload.get("generated_at")) if isinstance(payload, dict) else None
    )
    if generated_at is None:
        return f"  {name}: present / generated_at=unknown ({path})"

    now = datetime.now(generated_at.tzinfo) if generated_at.tzinfo else datetime.now()
    age_minutes = max(0, int((now - generated_at).total_seconds() // 60))
    freshness = "stale" if age_minutes > stale_after_minutes else "fresh"
    return (
        f"  {name}: {freshness} / age={age_minutes}m / "
        f"generated_at={payload.get('generated_at', 'unknown')} ({path})"
    )


def _generate_reports_and_summaries(
    *,
    workspace: str,
    manager: StateManager | None = None,
    receipt_report_path: str | None = None,
) -> None:
    """Generate daily report and monitoring summaries."""
    try:
        workspace_path = Path(workspace)
        if manager is None:
            try:
                manager = StateManager(workspace_path=str(workspace_path))
            except Exception:
                manager = None

        # Get ACK stats from receipt report and ACK bridge evidence state.
        ack_stats = {}
        receipt_report_file = workspace_path / (
            receipt_report_path or "logs/task_receipt_report.json"
        )
        if receipt_report_file.exists():
            try:
                receipt_data = json.loads(receipt_report_file.read_text(encoding="utf-8"))
                ack_stats = {
                    "total_acks": receipt_data.get("completed_count", 0),
                    "success_count": receipt_data.get("completed_count", 0),
                    "failure_count": receipt_data.get("error_count", 0),
                    "success_rate": (
                        round(
                            receipt_data.get("completed_count", 0)
                            / max(receipt_data.get("candidate_count", 1), 1)
                            * 100,
                            2,
                        )
                        if receipt_data.get("candidate_count", 0) > 0
                        else 0.0
                    ),
                }
            except (json.JSONDecodeError, OSError):
                pass

        remediation_report = run_ack_remediation(workspace=workspace_path, dry_run=False)
        missing_ack_report = run_missing_ack_monitor(workspace=workspace_path)
        result_consistency_report = run_terminal_result_consistency_audit(workspace=workspace_path)
        ack_stats.update(summarize_ack_bridge_state(workspace_path))
        missing_ack_stats = {
            "candidate_count": missing_ack_report.get("candidate_count", 0),
            "bridged_count": missing_ack_report.get("bridged_count", 0),
            "already_bridged_count": missing_ack_report.get("already_bridged_count", 0),
            "stale_explicit_ack_count": missing_ack_report.get("stale_explicit_ack_count", 0),
            "other_skipped_count": missing_ack_report.get("other_skipped_count", 0),
            "skipped_count": missing_ack_report.get("skipped_count", 0),
            "error_count": missing_ack_report.get("error_count", 0),
            "remediation_flagged_count": remediation_report.get("flagged_count", 0),
            "remediation_already_flagged_count": remediation_report.get("already_flagged_count", 0),
        }
        result_consistency_stats = {
            "audited_count": result_consistency_report.get("audited_count", 0),
            "consistent_count": result_consistency_report.get("consistent_count", 0),
            "mismatch_count": result_consistency_report.get("mismatch_count", 0),
            "unparseable_count": result_consistency_report.get("unparseable_count", 0),
            "missing_result_count": result_consistency_report.get("missing_result_count", 0),
            "issue_count": result_consistency_report.get("issue_count", 0),
        }
        run_ack_watchdog(workspace=workspace_path, dry_run=False)

        # Get no-op/pending conflict stats
        noop_pending_stats = get_noop_pending_stats().get_summary()

        # Get pending tasks
        pending_tasks = []
        if manager:
            try:
                pending_tasks = [
                    str(task.get("task_id", "")).strip()
                    for task in manager.get_all_tasks()
                    if isinstance(task, dict)
                    and str(task.get("status", "")).strip().lower() == "pending"
                ]
                pending_tasks = [task_id for task_id in pending_tasks if task_id]
            except (AttributeError, TypeError, ValueError):
                pass

        # Generate daily report
        report = generate_daily_report(
            workspace=workspace_path,
            ack_stats=ack_stats,
            missing_ack_stats=missing_ack_stats,
            result_consistency_stats=result_consistency_stats,
            noop_pending_stats=noop_pending_stats,
            pending_tasks=pending_tasks,
        )

        # Write JSON report
        write_daily_report_json(
            report=report,
            workspace=workspace_path,
            report_path="logs/daily_report.json",
        )

        # Write Markdown report
        write_daily_report_markdown(
            report=report,
            workspace=workspace_path,
            report_path="collaboration/monitoring/DAILY_REPORT_latest.md",
        )

        # Write no-op/pending conflict report
        write_noop_pending_report(
            workspace=workspace_path,
            report_path="logs/noop_pending_conflict_report.json",
        )

        # Write no-op/pending conflict summary
        write_noop_pending_summary(
            workspace=workspace_path,
            summary_path="collaboration/monitoring/NOOP_PENDING_CONFLICT_SUMMARY_latest.md",
        )

    except Exception as exc:  # noqa: BLE001
        print(f"警告: 生成报告失败: {exc}")


def _run_workspace_guard_gate(
    *,
    workspace: str,
    config: dict,
    command: str,
    dry_run: bool,
    force_workspace: bool,
) -> bool:
    """执行工作区门禁（阈值 + 分域隔离），并输出结论。"""
    guard_config = (
        config.get("workspaceGuard", {}) if isinstance(config.get("workspaceGuard"), dict) else {}
    )
    mode = "dry-run" if dry_run else "apply"
    report = run_workspace_guard(
        workspace=Path(workspace),
        command=command,
        mode=mode,
        guard_config=guard_config,
        force=force_workspace,
    )

    totals = report.get("totals", {})
    domains = report.get("domains", {})
    print("\n[工作区门禁]")
    print(
        f"  allowed: {report.get('allowed', False)}" f"  mode: {mode}" f"  force: {force_workspace}"
    )
    print(
        "  dirty: "
        f"total={totals.get('total', 0)} "
        f"untracked={totals.get('untracked', 0)} "
        f"deleted={totals.get('deleted', 0)} "
        f"modified={totals.get('modified', 0)}"
    )
    print(
        "  domains: "
        f"source={domains.get('source', 0)} "
        f"ops={domains.get('ops', 0)} "
        f"docs={domains.get('docs', 0)} "
        f"other={domains.get('other', 0)}"
    )
    print(
        "  risk-signals: "
        f"root_deleted={report.get('root_deleted', 0)} "
        f"results_untracked={report.get('results_untracked', 0)}"
    )
    print(f"  report: {report.get('report_file', '')}")
    print(f"  history: {report.get('history_file', '')}")

    warnings = report.get("warnings", [])
    for item in warnings[:5]:
        print(f"  warning: {item}")
    violations = report.get("violations", [])
    for item in violations[:10]:
        print(f"  violation: {item}")

    if not bool(report.get("allowed", False)):
        print("\n门禁阻断：请先压缩工作区变更，或在确认风险后使用 --force-workspace 显式覆盖。")
        return False
    return True


def _run_spawn_agent_guard_gate(
    *,
    workspace: str,
    config: dict,
    actor: str,
    parent_task_id: str | None,
    files: list[str],
    read_only: bool,
) -> bool:
    """执行 spawn_agent 委派前置门禁，并输出结论。"""
    report = run_spawn_agent_guard(
        workspace=Path(workspace),
        actor=actor,
        parent_task_id=parent_task_id,
        files=files,
        read_only=read_only,
        config=config,
    )

    print("\n[spawn_agent 门禁]")
    print(
        f"  allowed: {report.get('allowed', False)}"
        f"  actor: {report.get('actor', '')}"
        f"  mode: {report.get('mode', '')}"
    )
    print(f"  parent_task: {report.get('parent_task_id', 'none')}")
    print(f"  parent_task_source: {report.get('parent_task_source', 'cli')}")
    print(f"  files: {len(report.get('files', []))}")
    print(f"  files_source: {report.get('files_source', 'cli')}")
    print(f"  read_only_source: {report.get('read_only_source', 'cli')}")
    print(f"  report: {report.get('report_file', '')}")
    print(f"  history: {report.get('history_file', '')}")

    warnings = report.get("warnings", [])
    for item in warnings[:5]:
        print(f"  warning: {item}")

    conflicts = report.get("active_conflicts", [])
    for item in conflicts[:10]:
        print(
            "  conflict: "
            f"task={item.get('task_id', '')} "
            f"status={item.get('status', '')} "
            f"files={','.join(item.get('overlapping_files', []))}"
        )

    violations = report.get("violations", [])
    for item in violations[:10]:
        print(f"  violation: {item}")

    if not bool(report.get("allowed", False)):
        print("\n门禁阻断：请先修正 actor / parent task / 写集或保护路径问题，再使用 spawn_agent。")
        return False
    return True


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _normalize_trigger_assignee(raw: str) -> str:
    token = str(raw or "").strip().lower()
    if token in {"claude", "claude_code", "c"}:
        return "claude_code"
    if token in {"codearts", "codearts_agent", "a"}:
        return "codearts_agent"
    if token in {"codex", "x"}:
        return "codex"
    return token


def _resolve_trigger_assignees(config: dict, *, target: str = "all") -> list[str]:
    if target != "all":
        return [_normalize_trigger_assignee(target)]

    enabled = config.get("enabledAIs", [])
    assignees: list[str] = []
    if isinstance(enabled, list):
        for item in enabled:
            normalized = _normalize_trigger_assignee(str(item))
            if (
                normalized in {"claude_code", "codearts_agent", "codex"}
                and normalized not in assignees
            ):
                assignees.append(normalized)

    if not assignees:
        return ["claude_code", "codearts_agent"]
    return assignees


def _generate_trigger_payload_files(
    *,
    workspace: str,
    config: dict,
    orders_relpath: str,
    trigger_phrase: str,
    target: str = "all",
    output_dir_rel: str | None = None,
    payload_prefix: str | None = None,
    generated_at: str | None = None,
) -> dict:
    orders_file = Path(workspace) / orders_relpath
    orders_text = ""
    if orders_file.exists():
        orders_text = orders_file.read_text(encoding="utf-8")
    section_map = split_orders_by_assignee(orders_text)

    trigger_config = config.get("trigger", {}) if isinstance(config.get("trigger"), dict) else {}
    output_dir_rel = output_dir_rel or str(
        trigger_config.get("outputDir", "collaboration/monitoring")
    )
    payload_prefix = payload_prefix or str(trigger_config.get("payloadPrefix", "AGENT_TRIGGER"))

    assignees = _resolve_trigger_assignees(config, target=target)
    generated_at = generated_at or datetime.now().isoformat()
    output_files: list[str] = []
    payloads: dict[str, str] = {}

    for assignee in assignees:
        payload = build_handoff_payload(
            assignee=assignee,
            trigger_phrase=trigger_phrase,
            orders_relpath=orders_relpath,
            section_markdown=section_map.get(assignee),
            generated_at=generated_at,
        )
        payload_file = Path(workspace) / output_dir_rel / f"{payload_prefix}_{assignee}_latest.md"
        payload_file.parent.mkdir(parents=True, exist_ok=True)
        payload_file.write_text(payload, encoding="utf-8")
        output_files.append(str(payload_file.relative_to(workspace)))
        payloads[assignee] = payload

    return {
        "assignees": assignees,
        "output_files": output_files,
        "payloads": payloads,
        "generated_at": generated_at,
        "orders_exists": orders_file.exists(),
        "section_assignees": sorted(section_map.keys()),
    }


def _read_json_if_exists(path: Path) -> dict | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _count_pending_tasks_for_target(*, workspace: str, target: str) -> int:
    """统计目标 assignee 的 pending 任务数量（all 为全量）。"""
    try:
        state = StateManager(workspace_path=workspace)
        tasks = state.get_all_tasks()
    except Exception:
        return 0

    normalized_target = _normalize_trigger_assignee(target)
    count = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        status = str(task.get("status", "")).strip().lower()
        if status != "pending":
            continue
        assignee = _normalize_trigger_assignee(task.get("assignee") or task.get("ai_type") or "")
        if normalized_target == "all" or assignee == normalized_target:
            count += 1
    return count


def _count_reopened_redispatch_tasks_for_target(*, workspace: str, target: str) -> int:
    """统计已派发过且重新进入 active 状态的任务数量。"""
    try:
        state = StateManager(workspace_path=workspace)
        tasks = state.get_all_tasks()
    except Exception:
        return 0

    dispatch_state = (
        _read_json_if_exists(Path(workspace) / "logs" / "agent_dispatch_state.json") or {}
    )
    items = dispatch_state.get("items")
    if not isinstance(items, dict):
        return 0

    normalized_target = _normalize_trigger_assignee(target)
    eligible_statuses = {"implementing", "in_progress", "blocked"}
    count = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if not task_id or task_id not in items:
            continue
        status = str(task.get("status", "")).strip().lower()
        if status not in eligible_statuses:
            continue
        assignee = _normalize_trigger_assignee(task.get("assignee") or task.get("ai_type") or "")
        if normalized_target == "all" or assignee == normalized_target:
            count += 1
    return count


def _auto_enable_dispatch_flags(
    *, workspace: str, target: str, include_pending: bool, redispatch: bool
) -> tuple[bool, bool]:
    """在 pending 或 reopened 场景下自动启用补发开关，避免生成 noop payload。"""
    if include_pending or redispatch:
        return include_pending, redispatch

    pending_count = _count_pending_tasks_for_target(workspace=workspace, target=target)
    reopened_count = _count_reopened_redispatch_tasks_for_target(workspace=workspace, target=target)
    if pending_count <= 0 and reopened_count <= 0:
        return include_pending, redispatch

    reason_parts: list[str] = []
    if pending_count > 0:
        reason_parts.append(f"pending={pending_count}")
    if reopened_count > 0:
        reason_parts.append(f"reopened={reopened_count}")
    print(
        f"\n智能补发: 检测到 target={target} {' '.join(reason_parts)}，"
        "自动启用 --include-pending --redispatch，避免 noop。"
    )
    return True, True


def _resolve_workspace_hygiene_config(config: dict) -> dict:
    raw = (
        config.get("workspaceHygiene", {})
        if isinstance(config.get("workspaceHygiene"), dict)
        else {}
    )
    return {
        "enabled": bool(raw.get("enabled", False)),
        "pollIntervalMinutes": _as_int(raw.get("pollIntervalMinutes"), 15),
        "onReceiptClose": bool(raw.get("onReceiptClose", True)),
        "domainOrder": raw.get("domainOrder", ["ops", "docs", "other"]),
        "includeSource": bool(raw.get("includeSource", False)),
        "autoStage": bool(raw.get("autoStage", True)),
        "maxCandidatesPerRun": _as_int(raw.get("maxCandidatesPerRun"), 300),
        "createCheckpoint": bool(raw.get("createCheckpoint", True)),
        "report": str(raw.get("report", "logs/workspace_forensics/hygiene_latest.json")),
        "history": str(raw.get("history", "logs/workspace_forensics/hygiene_history.jsonl")),
    }


def _normalize_hygiene_domain_order(raw_order: object, include_source: bool) -> list[str]:
    valid = set(STAGE_DOMAINS)
    result: list[str] = []
    if isinstance(raw_order, list):
        for item in raw_order:
            domain = str(item).strip().lower()
            if domain in valid and domain not in result:
                result.append(domain)
    if not result:
        result = ["ops", "docs", "other"]
    if include_source and "source" not in result:
        result.insert(0, "source")
    return result


def cmd_activate(args):
    """激活 AI 协作系统"""
    ai_type_map = {
        "claude": AIType.CLAUDE_CODE,
        "claude_code": AIType.CLAUDE_CODE,
        "copilot": AIType.COPILOT,
        "codearts": AIType.CODEARTS_AGENT,
        "codearts_agent": AIType.CODEARTS_AGENT,
        # codex 当前沿用 Claude 规则集与会话激活路径
        "codex": AIType.CLAUDE_CODE,
    }

    ai_type = ai_type_map.get(args.ai.lower())
    if not ai_type:
        print(f"错误: 未知的 AI 类型 '{args.ai}'")
        print("支持的类型: claude, claude_code, copilot, codearts_agent, codex")
        return 1

    mode_map = {
        "cli": ActivationMode.CLI,
        "command": ActivationMode.COMMAND,
        "event": ActivationMode.EVENT,
        "on_save": ActivationMode.ON_SAVE,
    }
    mode = mode_map.get(args.mode, ActivationMode.CLI)

    # 设置 workspace 路径环境变量
    _set_workspace_env(args.workspace)

    # 激活回调函数
    def on_activated(session_id, rules, context):
        print("\n[激活回调]")
        print(f"  会话ID: {session_id}")
        print(f"  加载规则: {', '.join(rules)}")
        if context:
            print(f"  上下文: {json.dumps(context, ensure_ascii=False, indent=2)}")

    handler = ActivationHandler(
        ai_type=ai_type, workspace_path=args.workspace, on_activated=on_activated
    )

    print("=" * 60)
    print(f"AI 协作系统 - 激活 ({args.ai.upper()})")
    print("=" * 60)

    if args.input:
        # 使用自定义输入
        user_input = args.input
    else:
        # 等待用户输入或使用默认激活词
        user_input = f"开始任务 {ActivationHandler.ACTIVATION_KEYWORD}"

    if handler.check_activation(user_input, mode):
        result = handler.activate(mode)
        try:
            from ..session_autoregistration import register_session_from_activation

            register_session_from_activation(
                workspace=Path(os.path.abspath(args.workspace or os.getcwd())),
                assignee=args.ai,
                session_id=result.get("session_id", ""),
            )
        except Exception:
            # 激活成功不应因自动注册失败而回退。
            pass

        print("\n激活成功!")
        print(f"  AI类型: {result['ai_type']}")
        print(f"  会话ID: {result['session_id']}")
        print(f"  激活时间: {result['activation_time']}")
        print(f"  模式: {result['mode']}")
        print(f"  加载规则: {', '.join(result['rules_loaded'])}")
        print(f"\n  响应: {result['ack_message']}")

        if args.show_rules:
            print("\n[规则内容]")
            rules_content = handler.get_rules_content()
            for rule_file, content in rules_content.items():
                print(f"\n--- {rule_file} ---")
                print(content[:500] + "..." if len(content) > 500 else content)

        return 0
    else:
        print("\n激活失败: 未检测到激活词")
        return 1


def cmd_check(args):
    """检查文件冲突"""
    _set_workspace_env(args.workspace)
    ai_type = args.ai.lower() if args.ai else "claude"

    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print(f"AI 协作系统 - 冲突检查 ({ai_type.upper()})")
    print("=" * 60)

    files_to_check = args.files or []
    if not files_to_check:
        print("\n警告: 未指定检查文件，将从当前工作目录查找")
        # 获取 workspace 下的常见文件
        workspace = args.workspace or VSCodeIntegration.get_workspace_path()
        if workspace:
            for root, dirs, files in os.walk(workspace):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file in files:
                    if file.endswith((".ts", ".tsx", ".js", ".py", ".go")):
                        rel_path = os.path.relpath(os.path.join(root, file), workspace)
                        files_to_check.append(rel_path)
                        if len(files_to_check) >= 10:
                            break
                if len(files_to_check) >= 10:
                    break

    if files_to_check:
        print(f"\n检查文件 ({len(files_to_check)} 个):")
        for f in files_to_check:
            print(f"  - {f}")

    check_mode = "both" if args.mode == "both" else "command"
    conflicts = state.check_conflicts(ai_type, files_to_check, check_mode)

    if conflicts:
        print(f"\n检测到 {len(conflicts)} 个冲突:")
        for i, c in enumerate(conflicts, 1):
            print(f"\n  冲突 {i}:")
            print(f"    任务ID: {c['task_id']}")
            print(f"    AI类型: {c['ai_type']}")
            print(f"    描述: {c['description']}")
            print(f"    状态: {c['status']}")
            print(f"    重叠文件: {c['overlapping_files']}")
            print(f"    检测时间: {c['detected_at']}")

            if args.resolve:
                # 自动尝试解决冲突
                conflict_id = c.get("conflict_id", f"conflict-{datetime.now().timestamp()}")
                if state.resolve_conflict(conflict_id, "待用户决策"):
                    print("    → 冲突已标记为待解决")
        return 1
    else:
        print("\n无冲突，可以安全开发")
        return 0


def cmd_tasks(args):
    """任务管理"""
    _set_workspace_env(args.workspace)
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 任务管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        if args.status == "all":
            tasks = state.get_all_tasks()
        elif args.status == "active":
            tasks = state.get_active_tasks()
        elif args.status == "completed":
            tasks = [t for t in state.get_all_tasks() if t.get("status") == "completed"]
        elif args.status in {"in_progress", "implementing"}:
            tasks = [
                t
                for t in state.get_all_tasks()
                if str(t.get("status", "")).lower() in {"implementing", "in_progress"}
            ]
        else:
            tasks = [t for t in state.get_all_tasks() if t.get("status") == args.status]

        print(f"\n任务列表 ({args.status}, {len(tasks)} 个):")
        if tasks:
            for task in tasks:
                print(f"\n  {task.get('task_id', 'N/A')}")
                print(f"    AI: {task.get('ai_type', 'unknown')}")
                print(f"    描述: {task.get('description', '')}")
                print(f"    状态: {task.get('status', 'unknown')}")
                print(f"    创建时间: {task.get('created_at', 'N/A')}")
                if task.get("files"):
                    print(
                        f"    文件: {', '.join(task['files'][:3])}"
                        + ("..." if len(task["files"]) > 3 else "")
                    )
        else:
            print("  无任务")

    elif cmd == "register":
        task_id = args.task_id or f"TASK-{int(datetime.now().timestamp())}"
        task = state.register_task(
            task_id=task_id,
            ai_type=args.ai,
            description=args.description or "新任务",
            files=args.files or [],
            vscode_context={"source": "cli"},
            change_id=getattr(args, "change_id", None),
            assignee=getattr(args, "assignee", None) or args.ai,
            reviewer=getattr(args, "reviewer", None),
            primary_skill=getattr(args, "primary_skill", None),
            support_skills=getattr(args, "support_skills", None),
            acceptance_commands=getattr(args, "acceptance_commands", None),
            result_file=getattr(args, "result_file", None),
        )
        print(f"\n任务已注册: {task_id}")
        print(f"  AI: {task['ai_type']}")
        print(f"  描述: {task['description']}")

    elif cmd == "validate-contract":
        scope = getattr(args, "scope", None) or "active"
        strict = bool(getattr(args, "strict", False))

        report = state.validate_task_contracts(scope=scope)
        print(
            "\n契约校验结果: "
            f"checked={report['checked_tasks']} skipped={report['skipped_tasks']} "
            f"invalid={report['invalid_count']}"
        )
        if report["issues"]:
            for item in report["issues"]:
                print(f"  - {item['task_id']}")
                print(f"    missing: {item['missing_fields']}")
                print(f"    invalid: {item['invalid_fields']}")
                print(f"    remediation: {item['remediation']}")
        else:
            print("  无契约问题")

        audit_issue_count = 0
        if strict:
            workspace = Path(os.path.abspath(args.workspace or os.getcwd()))
            audit_report = run_terminal_result_consistency_audit(workspace=workspace)
            audit_issue_count = int(audit_report.get("issue_count", 0) or 0)

            print(
                "\n终态结果一致性: "
                f"audited={audit_report.get('audited_count', 0)} "
                f"consistent={audit_report.get('consistent_count', 0)} "
                f"mismatch={audit_report.get('mismatch_count', 0)} "
                f"unparseable={audit_report.get('unparseable_count', 0)} "
                f"missing_result={audit_report.get('missing_result_count', 0)}"
            )
            print(
                "  "
                f"report={audit_report.get('report_file', '')} "
                f"summary={audit_report.get('summary_file', '')}"
            )
            if audit_report.get("issues"):
                for item in audit_report["issues"][:10]:
                    print(
                        "  issue: "
                        f"{item.get('task_id', '')} "
                        f"type={item.get('issue_type', '')} "
                        f"state={item.get('state_status', '')} "
                        f"result={item.get('result_header_status', '') or '<unparseable>'}"
                    )

        if strict and (report["invalid_count"] > 0 or audit_issue_count > 0):
            return 1
    elif cmd == "audit-result-consistency":
        workspace = Path(os.path.abspath(args.workspace or os.getcwd()))
        report = run_terminal_result_consistency_audit(
            workspace=workspace,
            task_id=str(getattr(args, "task_id", "") or "").strip() or None,
            report_path=str(
                getattr(args, "report", "") or "logs/task_result_consistency_report.json"
            ),
            summary_path=str(
                getattr(args, "summary", "")
                or "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"
            ),
        )

        print("\n终态结果一致性审计:")
        print(f"  audited={report.get('audited_count', 0)}")
        print(f"  consistent={report.get('consistent_count', 0)}")
        print(f"  mismatch={report.get('mismatch_count', 0)}")
        print(f"  unparseable={report.get('unparseable_count', 0)}")
        print(f"  missing_result={report.get('missing_result_count', 0)}")
        print(f"  report={report.get('report_file', '')}")
        print(f"  summary={report.get('summary_file', '')}")
        if report.get("issues"):
            for item in report["issues"][:10]:
                print(
                    "  issue: "
                    f"{item.get('task_id', '')} "
                    f"type={item.get('issue_type', '')} "
                    f"state={item.get('state_status', '')} "
                    f"result={item.get('result_header_status', '') or '<unparseable>'}"
                )
        if bool(getattr(args, "strict", False)) and int(report.get("issue_count", 0)) > 0:
            return 1
    elif cmd == "migrate-contract":
        scope = getattr(args, "scope", None) or "all"
        dry_run = bool(getattr(args, "dry_run", False))
        default_change_id = getattr(args, "default_change_id", None)
        migration_reviewer = getattr(args, "migration_reviewer", None)
        report = state.migrate_task_contracts(
            scope=scope,
            dry_run=dry_run,
            default_change_id=default_change_id,
            reviewer=migration_reviewer,
        )
        print(
            "\n契约迁移结果: "
            f"scope={report['scope']} dry_run={report['dry_run']} total={report['total_tasks']} "
            f"legacy_detected={report['legacy_detected']} migrated={report['migrated_count']} "
            f"already_compliant={report['already_compliant']} remaining_legacy={report['remaining_legacy']}"
        )
        if report["migrated_task_ids"]:
            print("  migrated_task_ids:")
            for task_id in report["migrated_task_ids"]:
                print(f"    - {task_id}")
        if report["invalid_after_migration"]:
            print("  invalid_after_migration:")
            for item in report["invalid_after_migration"]:
                print(f"    - {item['task_id']}")
                print(f"      missing: {item['missing_fields']}")
                print(f"      invalid: {item['invalid_fields']}")
        if report["legacy_branch_eliminated"]:
            print("  legacy branch eliminated: yes")
        else:
            print("  legacy branch eliminated: no")
        if report["invalid_after_migration_count"] > 0:
            return 1

    elif cmd == "update":
        if not args.task_id:
            print("\n错误: 需要指定 task_id")
            return 1

        status_map = {
            "pending": TaskStatus.PENDING,
            "planning": TaskStatus.PLANNING,
            "in_progress": TaskStatus.IMPLEMENTING,
            "implementing": TaskStatus.IMPLEMENTING,
            "testing": TaskStatus.TESTING,
            "blocked": TaskStatus.BLOCKED,
            "completed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
            "cancelled": TaskStatus.CANCELLED,
        }
        new_status = status_map.get(args.status, TaskStatus.PENDING)

        try:
            state.update_task_status(
                args.task_id,
                new_status,
                args.note,
                actor=getattr(args, "ai", None),
            )
        except ValueError as exc:
            print(f"\n错误: {exc}")
            return 1
        print(f"\n任务状态已更新: {args.task_id} -> {new_status.value}")

    elif cmd == "takeover":
        if not args.task_id:
            print("\n错误: takeover 需要指定 --task-id")
            return 1
        if not getattr(args, "owner", None):
            print("\n错误: takeover 需要指定 --owner")
            return 1

        actor = getattr(args, "ai", None) or args.owner
        try:
            result = state.takeover_task(
                task_id=args.task_id,
                owner=args.owner,
                actor=actor,
                note=args.note,
                reason=getattr(args, "reason", None),
                source="cli.tasks.takeover",
            )
        except ValueError as exc:
            print(f"\n错误: {exc}")
            return 1
        print(
            "\n任务 owner 已锁定: "
            f"{result['task_id']} -> {result['owner']} "
            f"(previous_owner={result.get('previous_owner') or '<none>'})"
        )

    elif cmd == "repair-assignee":
        if not args.task_id:
            print("\n错误: repair-assignee 需要指定 --task-id")
            return 1
        if not getattr(args, "assignee", None):
            print("\n错误: repair-assignee 需要指定 --assignee")
            return 1

        try:
            result = state.repair_task_assignee(
                task_id=args.task_id,
                assignee=args.assignee,
                actor=getattr(args, "ai", None),
                note=args.note,
                reason=getattr(args, "reason", None),
                source="cli.tasks.repair-assignee",
            )
        except ValueError as exc:
            print(f"\n错误: {exc}")
            return 1

        print(
            "\n任务 assignee 已修复: "
            f"{result['task_id']} "
            f"{result.get('old_assignee') or '<none>'} -> {result['new_assignee']}"
        )

    return 0


def cmd_ack(args):
    """Emit a one-line ACK protocol message from task state or explicit overrides."""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())

    task_id = str(getattr(args, "task_id", "") or "").strip()
    if not task_id:
        print("\n错误: ack 需要指定 --task-id")
        return 1

    explicit_assignee = str(getattr(args, "ai", "") or "").strip().lower()
    explicit_status = str(getattr(args, "status", "") or "").strip().lower()
    explicit_result_file = str(getattr(args, "result_file", "") or "").strip()

    if task_id.lower() == "none":
        assignee = explicit_assignee or "codex"
        status = explicit_status or "noop"
        result_file = explicit_result_file or "none"
        print(
            build_ack_line(
                assignee=assignee, task_id="none", result_file=result_file, status=status
            )
        )
        return 0

    manager = StateManager(workspace_path=workspace)
    _, _, ack_items = load_ack_bridge_state(Path(workspace))
    existing_ack = get_ack_bridge_item(ack_items, task_id)
    task = manager.get_task(task_id)
    if not isinstance(task, dict):
        assignee = explicit_assignee or str(existing_ack.get("assignee") or "").strip().lower()
        if not assignee:
            print(f"\n错误: 任务不存在且未提供 --ai，且无历史 ACK 可推断 assignee: {task_id}")
            return 1
        result_file = (
            explicit_result_file
            or str(existing_ack.get("result_file") or "").strip()
            or f"collaboration/results/RESULT_{task_id}.md"
        )
        status = explicit_status or "ok"
        ack_line = build_ack_line(
            assignee=assignee, task_id=task_id, result_file=result_file, status=status
        )
        result_path = Path(result_file)
        if not result_path.is_absolute():
            result_path = Path(workspace) / result_path
        if assignee in SUPPORTED_ASSIGNEES and (
            existing_ack or explicit_result_file or result_path.exists()
        ):
            completed_at = str(
                existing_ack.get("receipt_completed_at")
                or existing_ack.get("bridged_at")
                or datetime.now().isoformat()
            )
            record_ack_bridge(
                workspace=Path(workspace),
                task_id=task_id,
                assignee=assignee,
                result_file=result_file,
                completed_at=completed_at,
                source="cli-ack",
                bridged_at=datetime.now().isoformat(),
                status=status,
                increment_count=True,
            )
        print(ack_line)
        return 0

    assignee = explicit_assignee or normalize_assignee(task)
    if not assignee:
        print(f"\n错误: 无法推断任务 assignee: {task_id}")
        return 1

    result_file = explicit_result_file or normalize_result_file(task_id, task)
    current_status = str(task.get("status", "")).strip().lower()
    if explicit_status:
        status = explicit_status
    elif current_status == "blocked":
        status = "blocked"
    elif current_status in {"pending", "planning"}:
        status = "noop"
    else:
        status = "ok"

    ack_line = build_ack_line(
        assignee=assignee, task_id=task_id, result_file=result_file, status=status
    )
    if assignee in SUPPORTED_ASSIGNEES:
        completed_at = str(
            task.get("completed_at")
            or task.get("updated_at")
            or task.get("created_at")
            or datetime.now().isoformat()
        )
        record_ack_bridge(
            workspace=Path(workspace),
            task_id=task_id,
            assignee=assignee,
            result_file=result_file,
            completed_at=completed_at,
            source="cli-ack",
            bridged_at=datetime.now().isoformat(),
            status=status,
            increment_count=True,
        )

    print(ack_line)
    return 0


def cmd_ack_remediation(args):
    """Audit and flag legacy non-explicit ACK bridge records."""
    _set_workspace_env(args.workspace)
    workspace = Path(os.path.abspath(args.workspace or os.getcwd()))

    report = run_ack_remediation(
        workspace=workspace,
        dry_run=bool(getattr(args, "dry_run", False)),
        task_id=str(getattr(args, "task_id", "") or "").strip() or None,
        report_path=str(getattr(args, "report", "") or "logs/ack_remediation_report.json"),
        summary_path=str(
            getattr(args, "summary", "")
            or "collaboration/monitoring/ACK_REMEDIATION_SUMMARY_latest.md"
        ),
        state_path=str(getattr(args, "state", "") or "logs/agent_ack_bridge_state.json"),
    )

    print("=" * 60)
    print("AI 协作系统 - ACK Remediation")
    print("=" * 60)
    print("")
    print(f"工作区: {workspace}")
    print(f"模式: {report.get('mode', '')}")
    print(f"候选残留: {report.get('candidate_count', 0)}")
    print(f"新标记: {report.get('flagged_count', 0)}")
    print(f"已标记: {report.get('already_flagged_count', 0)}")
    print(f"错误: {report.get('error_count', 0)}")
    print(f"报告路径: {report.get('report_file', '')}")
    print(f"状态路径: {report.get('ack_bridge_state_file', '')}")
    print(f"摘要文件: {report.get('summary_file', '')}")
    return 0 if int(report.get("error_count", 0)) == 0 else 1


def cmd_sessions(args):
    """Session registry control-plane commands."""
    _set_workspace_env(args.workspace)
    workspace = Path(os.path.abspath(args.workspace or os.getcwd()))
    cmd = getattr(args, "subcommand", "")

    if cmd == "register":
        if not getattr(args, "session_id", None):
            print("\n错误: sessions register 需要指定 --session-id")
            return 1
        if not getattr(args, "assignee", None):
            print("\n错误: sessions register 需要指定 --assignee")
            return 1

        from ..session_registry import register_session

        record = register_session(
            workspace=workspace,
            session_id=str(args.session_id).strip(),
            assignee=str(args.assignee).strip(),
            transport_mode=str(getattr(args, "transport_mode", "") or "manual").strip(),
            session_status=str(getattr(args, "session_status", "") or "active").strip(),
            last_handoff_artifact=str(getattr(args, "last_handoff_artifact", "") or "").strip(),
            health_status=str(getattr(args, "health_status", "") or "healthy").strip(),
            state_path=str(getattr(args, "state", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
        )
        print("\n会话已注册:")
        print(f"  session_id: {record.get('session_id', '')}")
        print(f"  assignee: {record.get('assignee', '')}")
        print(f"  transport_mode: {record.get('transport_mode', '')}")
        print(f"  session_status: {record.get('session_status', '')}")
        print(f"  health_status: {record.get('health_status', '')}")
        return 0

    if cmd == "refresh":
        if not getattr(args, "session_id", None):
            print("\n错误: sessions refresh 需要指定 --session-id")
            return 1

        from ..session_registry import refresh_session

        record = refresh_session(
            workspace=workspace,
            session_id=str(args.session_id).strip(),
            assignee=str(getattr(args, "assignee", "") or "").strip() or None,
            transport_mode=str(getattr(args, "transport_mode", "") or "").strip() or None,
            session_status=str(getattr(args, "session_status", "") or "").strip() or None,
            last_handoff_artifact=str(getattr(args, "last_handoff_artifact", "") or "").strip()
            or None,
            health_status=str(getattr(args, "health_status", "") or "").strip() or None,
            state_path=str(getattr(args, "state", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
        )
        print("\n会话已刷新:")
        print(f"  session_id: {record.get('session_id', '')}")
        print(f"  assignee: {record.get('assignee', '')}")
        print(f"  transport_mode: {record.get('transport_mode', '')}")
        print(f"  session_status: {record.get('session_status', '')}")
        print(f"  health_status: {record.get('health_status', '')}")
        return 0

    if cmd == "inspect":
        from ..session_registry import inspect_sessions

        payload = inspect_sessions(
            workspace=workspace,
            session_id=str(getattr(args, "session_id", "") or "").strip() or None,
            assignee=str(getattr(args, "assignee", "") or "").strip() or None,
            transport_mode=str(getattr(args, "transport_mode", "") or "").strip() or None,
            session_status=str(getattr(args, "session_status", "") or "").strip() or None,
            health_status=str(getattr(args, "health_status", "") or "").strip() or None,
            state_path=str(getattr(args, "state", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Registry:")
        print(f"  total: {payload.get('session_count', 0)}")
        print(f"  healthy: {payload.get('healthy_count', 0)}")
        print(f"  unhealthy: {payload.get('unhealthy_count', 0)}")
        print(f"  state_file: {payload.get('state_file', '')}")
        print(f"  summary_file: {payload.get('summary_file', '')}")

        items = payload.get("sessions", [])
        if items:
            for item in items:
                print(f"\n  {item.get('session_id', '')}")
                print(f"    assignee: {item.get('assignee', '')}")
                print(f"    transport_mode: {item.get('transport_mode', '')}")
                print(f"    session_status: {item.get('session_status', '')}")
                print(f"    health_status: {item.get('health_status', '')}")
                print(f"    last_seen_at: {item.get('last_seen_at', '')}")
        else:
            print("  无会话")
        return 0

    if cmd == "health":
        from ..session_health import run_session_health_aggregation

        report = run_session_health_aggregation(
            workspace=workspace,
            emit_interventions=not bool(getattr(args, "no_interventions", False)),
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
            artifact_dir=str(getattr(args, "artifact_dir", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Health:")
        print(f"  sessions: {report.get('session_count', 0)}")
        print(f"  healthy: {report.get('healthy_count', 0)}")
        print(f"  unhealthy: {report.get('unhealthy_count', 0)}")
        print(f"  incidents: {report.get('incident_count', 0)}")
        print(f"  interventions: {report.get('intervention_count', 0)}")
        print(f"  unregistered: {report.get('unregistered_count', 0)}")
        print(f"  report_file: {report.get('report_file', '')}")
        print(f"  summary_file: {report.get('summary_file', '')}")
        return 0

    if cmd == "interventions":
        from ..intervention_queue import inspect_interventions

        report = inspect_interventions(
            workspace=workspace,
            session_id=str(getattr(args, "session_id", "") or "").strip() or None,
            assignee=str(getattr(args, "assignee", "") or "").strip() or None,
            reason_code=str(getattr(args, "reason_code", "") or "").strip() or None,
            delivery_status=str(getattr(args, "delivery_status", "") or "").strip() or None,
            only_open=bool(getattr(args, "only_open", False)),
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Interventions:")
        print(f"  intervention_count: {report.get('intervention_count', 0)}")
        print(f"  open_count: {report.get('open_count', 0)}")
        print(f"  pending_operator_delivery: {report.get('pending_operator_delivery_count', 0)}")
        print(f"  queued_for_delivery: {report.get('queued_for_delivery_count', 0)}")
        interventions = list(report.get("interventions", []) or [])
        if not interventions:
            print("  无 intervention")
            return 0
        for item in interventions:
            print(f"\n  {item.get('intervention_id', '')}")
            print(f"    assignee: {item.get('assignee', '')}")
            print(f"    session_id: {item.get('session_id', '')}")
            print(f"    reason_code: {item.get('reason_code', '')}")
            print(f"    delivery_status: {item.get('delivery_status', '')}")
            print(f"    message_artifact: {item.get('message_artifact', '')}")
        return 0

    if cmd == "intervention-pack":
        from ..intervention_queue import render_intervention_pack

        report = render_intervention_pack(
            workspace=workspace,
            assignee=str(getattr(args, "assignee", "") or "").strip(),
            only_open=not bool(getattr(args, "include_closed", False)),
            pack_dir=str(getattr(args, "pack_dir", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Intervention Pack:")
        print(f"  assignee: {report.get('assignee', '')}")
        print(f"  intervention_count: {report.get('intervention_count', 0)}")
        print(f"  pack_file: {report.get('pack_file', '')}")
        return 0

    if cmd == "closeout-queue":
        from ..external_closeout_queue import render_external_closeout_queue

        report = render_external_closeout_queue(
            workspace=workspace,
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nExternal Closeout Queue:")
        print(f"  active_task_count: {report.get('active_task_count', 0)}")
        print(f"  open_intervention_count: {report.get('open_intervention_count', 0)}")
        print(f"  blocking_intervention_count: {report.get('blocking_intervention_count', 0)}")
        print(f"  ready_pack_count: {report.get('ready_pack_count', 0)}")
        print(f"  output_file: {report.get('output_file', '')}")
        return 0

    if cmd == "auto-sync":
        from ..session_auto_register import run_session_auto_sync

        report = run_session_auto_sync(
            workspace=workspace,
            dry_run=bool(getattr(args, "dry_run", False)),
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Auto Sync:")
        print(f"  mode: {report.get('mode', '')}")
        print(f"  candidate_count: {report.get('candidate_count', 0)}")
        print(f"  registered_count: {report.get('registered_count', 0)}")
        print(f"  refreshed_count: {report.get('refreshed_count', 0)}")
        print(f"  observation_file: {report.get('observation_file', '')}")
        return 0

    if cmd == "claude-push":
        from ..adapters.claude_adapter import run_claude_push_adapter

        report = run_claude_push_adapter(
            workspace=workspace,
            dry_run=bool(getattr(args, "dry_run", False)),
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
            event_dir=str(getattr(args, "event_dir", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nClaude Adapter:")
        print(f"  mode: {report.get('mode', '')}")
        print(f"  candidate_count: {report.get('candidate_count', 0)}")
        print(f"  queued_count: {report.get('queued_count', 0)}")
        print(f"  artifact_only_count: {report.get('artifact_only_count', 0)}")
        print(f"  failed_count: {report.get('failed_count', 0)}")
        print(f"  report_file: {report.get('report_file', '')}")
        print(f"  summary_file: {report.get('summary_file', '')}")
        return 0

    if cmd == "codearts-pull":
        from ..adapters.codearts_adapter import run_codearts_pull_adapter

        report = run_codearts_pull_adapter(
            workspace=workspace,
            dry_run=bool(getattr(args, "dry_run", False)),
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
            event_dir=str(getattr(args, "event_dir", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nCodeArts Adapter:")
        print(f"  mode: {report.get('mode', '')}")
        print(f"  candidate_count: {report.get('candidate_count', 0)}")
        print(f"  queued_count: {report.get('queued_count', 0)}")
        print(f"  artifact_only_count: {report.get('artifact_only_count', 0)}")
        print(f"  failed_count: {report.get('failed_count', 0)}")
        print(f"  report_file: {report.get('report_file', '')}")
        print(f"  summary_file: {report.get('summary_file', '')}")
        return 0

    if cmd == "codex-adapter":
        from ..adapters.codex_adapter import run_codex_native_adapter

        report = run_codex_native_adapter(
            workspace=workspace,
            dry_run=bool(getattr(args, "dry_run", False)),
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
            runtime_path=str(getattr(args, "runtime_path", "") or "").strip() or None,
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nCodex Adapter:")
        print(f"  mode: {report.get('mode', '')}")
        print(f"  runtime_present: {report.get('runtime_present', False)}")
        print(f"  runtime_fresh: {report.get('runtime_fresh', False)}")
        print(f"  session_registered: {report.get('session_registered', False)}")
        print(f"  report_file: {report.get('report_file', '')}")
        print(f"  summary_file: {report.get('summary_file', '')}")
        return 0

    if cmd == "handoff":
        from ..session_continuation_handoff import run_session_continuation_handoff

        report = run_session_continuation_handoff(
            workspace=workspace,
            objective=str(getattr(args, "objective", "") or "").strip() or None,
            next_slice=str(getattr(args, "next_slice", "") or "").strip() or None,
            completed_items=list(getattr(args, "completed_item", []) or []),
            validation_commands=list(getattr(args, "validation_command", []) or []),
            related_files=list(getattr(args, "related_file", []) or []),
            report_path=str(getattr(args, "report", "") or "").strip() or None,
            history_path=str(getattr(args, "history", "") or "").strip() or None,
            summary_path=str(getattr(args, "summary", "") or "").strip() or None,
            output_dir=str(getattr(args, "output_dir", "") or "").strip() or None,
            dry_run=bool(getattr(args, "dry_run", False)),
        )

        if bool(getattr(args, "json", False)):
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        print("\nSession Continuation Handoff:")
        print(f"  mode: {report.get('mode', '')}")
        print(f"  output_file: {report.get('output_file', '') or '<dry-run>'}")
        print(f"  report_file: {report.get('report_file', '')}")
        print(f"  summary_file: {report.get('summary_file', '')}")
        print(f"  history_file: {report.get('history_file', '')}")
        return 0

    print(f"\n错误: 不支持的 sessions 子命令: {cmd}")
    return 1


def cmd_patches(args):
    """Patch 管理"""
    _set_workspace_env(args.workspace)
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - Patch 管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        status_filter = None if args.status in (None, "all") else args.status
        patches = state.list_patches(status_filter=status_filter, task_id=args.task_id)
        print(f"\nPatch 列表 ({len(patches)} 个):")
        for patch in patches:
            print(
                f"  {patch.get('patch_id', 'N/A')} "
                f"[{patch.get('status', 'unknown')}] "
                f"task={patch.get('task_id', '')} assignee={patch.get('assignee', '')}"
            )
        if not patches:
            print("  无 patch")
        return 0

    if cmd == "create":
        if not args.task_id:
            print("\n错误: create 需要指定 --task-id")
            return 1
        patch_id = args.patch_id or f"PATCH-{int(datetime.now().timestamp())}"
        title = args.title or args.description or "patch"
        patch = state.register_patch(
            patch_id=patch_id,
            task_id=args.task_id,
            title=title,
            files=args.files or [],
            assignee=args.ai or "",
            note=args.note,
            actor=args.ai or "cli",
            source="cli.patches.create",
            reason=args.note or "",
        )
        print(f"\nPatch 已创建: {patch['patch_id']}")
        return 0

    if cmd == "update":
        status_map = {
            "pending": PatchStatus.PENDING,
            "in_progress": PatchStatus.IN_PROGRESS,
            "completed": PatchStatus.COMPLETED,
            "blocked": PatchStatus.BLOCKED,
            "cancelled": PatchStatus.CANCELLED,
        }
        new_status = status_map.get(args.status)
        if not args.patch_id or not new_status:
            print("\n错误: update 需要指定 --patch-id 和合法 --status")
            return 1
        state.update_patch_status(
            patch_id=args.patch_id,
            status=new_status,
            note=args.note,
            actor=args.ai or "cli",
            source="cli.patches.update",
            reason=args.note or "",
        )
        print(f"\nPatch 状态已更新: {args.patch_id} -> {new_status.value}")
        return 0

    if cmd == "assign":
        if not args.patch_id or not args.ai:
            print("\n错误: assign 需要指定 --patch-id 和 --ai")
            return 1
        patch = state.get_patch(args.patch_id)
        if not patch:
            print(f"\n错误: patch 不存在: {args.patch_id}")
            return 1
        patch["assignee"] = args.ai
        patch["updated_at"] = datetime.now().isoformat()
        patch.setdefault("notes", [])
        if args.note:
            patch["notes"].append(f"[{datetime.now().isoformat()}] {args.note}")
        state._save_state()  # noqa: SLF001
        print(f"\nPatch 已分派: {args.patch_id} -> {args.ai}")
        return 0

    if cmd == "claim":
        ai = args.ai or "codex"
        candidates = [
            p
            for p in state.list_patches(status_filter="pending")
            if not p.get("assignee") or p.get("assignee") == ai
        ]
        if not candidates:
            print("\n无可领取 patch")
            return 0
        target = candidates[0]
        target["assignee"] = ai
        target["updated_at"] = datetime.now().isoformat()
        state._save_state()  # noqa: SLF001
        state.update_patch_status(
            patch_id=target["patch_id"],
            status=PatchStatus.IN_PROGRESS,
            note=args.note or f"claimed by {ai}",
            actor=ai,
            source="cli.patches.claim",
            reason=args.note or "claim",
        )
        print(f"\n已领取: {target['patch_id']}")
        return 0

    print(f"\n错误: 未知 patch 子命令: {cmd}")
    return 1


def cmd_conflicts(args):
    """冲突管理"""
    _set_workspace_env(args.workspace)
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 冲突管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        status_filter = args.status or None
        conflicts = state.get_conflicts(status_filter)

        print(f"\n冲突列表 ({len(conflicts)} 个):")
        if conflicts:
            for i, c in enumerate(conflicts, 1):
                print(f"\n  冲突 {i}: {c['conflict_id']}")
                print(f"    任务1: {c['task_id_1']} ({c['ai_type_1']})")
                print(f"    任务2: {c['task_id_2']} ({c['ai_type_2']})")
                print(f"    重叠文件: {c['overlapping_files']}")
                print(f"    状态: {c['status']}")
        else:
            print("  无冲突")

    elif cmd == "resolve":
        if not args.conflict_id:
            print("\n错误: 需要指定 conflict_id")
            return 1

        if state.resolve_conflict(args.conflict_id, args.resolution or "已解决"):
            print(f"\n冲突已解决: {args.conflict_id}")
        else:
            print(f"\n解决失败: 冲突 {args.conflict_id} 不存在")
            return 1

    return 0


def cmd_logs(args):
    """日志管理"""
    from ..dev_logger import DevLogger

    # 设置 workspace 路径环境变量
    _set_workspace_env(args.workspace)

    ai_type = args.ai.lower() if args.ai else "claude-code"

    logger = DevLogger(ai_type)

    print("=" * 60)
    print(f"AI 协作系统 - 日志管理 ({ai_type})")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        logs = logger.list_logs(args.month)

        print(f"\n日志列表 ({len(logs)} 个):")
        for log in logs:
            log_name = os.path.basename(log)
            log_size = os.path.getsize(log)
            mtime = datetime.fromtimestamp(os.path.getmtime(log)).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  [{log_size:6d} bytes] {log_name}  ({mtime})")

    elif cmd == "show" and args.log_file:
        full_path = os.path.join(logger.log_dir, args.month, args.log_file) if args.month else ""
        if not full_path or not os.path.exists(full_path):
            # 查找匹配的文件
            logs = logger.list_logs(args.month)
            for log in logs:
                if args.log_file in log:
                    full_path = log
                    break

        if full_path and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                print(f"\n{f.read()}")
        else:
            print(f"\n错误: 日志文件 '{args.log_file}' 不存在")
            return 1

    return 0


def cmd_init(args):
    """初始化项目"""
    workspace = os.path.abspath(args.workspace or os.getcwd())

    # 设置 workspace 路径环境变量
    _set_workspace_env(workspace)

    print("=" * 60)
    print("AI 协作系统 - 项目初始化")
    print("=" * 60)

    # 创建目录结构
    dirs_to_create = [
        os.path.join(workspace, ".vscode"),
        os.path.join(workspace, "logs", "activations"),
        os.path.join(workspace, "logs", "claude-code"),
        os.path.join(workspace, "logs", "codearts-agent"),
        os.path.join(workspace, "logs", "copilot"),
        os.path.join(workspace, "logs", "backups"),
        os.path.join(workspace, ".git", "ai-collab", "activations"),
    ]

    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)
        print(f"  ✓ 创建目录: {d}")

    # 创建配置文件
    vscode_config = {
        "version": "1.0.0",
        "rulesDir": "./rules",
        "logsDir": "./logs",
        "stateFile": "./logs/collaboration_state.json",
        "handoffFile": "./logs/handoff_status.json",
        "activationKeyword": "2X",
        "conflictCheckOnSave": True,
        "conflictCheckOnCommand": True,
        "enabledAIs": ["claude_code", "codex", "codearts_agent"],
        "controller": {
            "intervalSec": 30,
            "pendingTimeoutSec": 7200,
            "activeTimeoutSec": 1800,
            "blockedTimeoutSec": 3600,
            "prewarnRatio": 0.8,
            "defaultAssignee": "codex",
            "report": "logs/task_controller_report.json",
            "history": "logs/task_controller_history.jsonl",
        },
        "dispatch": {
            "includePending": False,
            "report": "logs/task_dispatch_report.json",
            "history": "logs/task_dispatch_history.jsonl",
            "state": "logs/agent_dispatch_state.json",
            "orders": "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
        },
        "receipt": {
            "report": "logs/task_receipt_report.json",
            "history": "logs/task_receipt_history.jsonl",
            "state": "logs/agent_receipt_state.json",
            "summary": "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md",
        },
        "benefit": {
            "dispatchHistory": ["logs/task_dispatch_history.jsonl"],
            "receiptHistory": ["logs/task_receipt_history.jsonl"],
            "targetRatio": 3.0,
            "window": 14,
            "report": "logs/automation_benefit_report.json",
            "output": "collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md",
        },
        "sessionOrchestration": {
            "registryState": "logs/session_registry_state.json",
            "registryHistory": "logs/session_registry_history.jsonl",
            "registrySummary": "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md",
            "healthReport": "logs/session_health_report.json",
            "healthHistory": "logs/session_health_history.jsonl",
            "healthSummary": "collaboration/monitoring/SESSION_HEALTH_SUMMARY_latest.md",
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
            "interventionPackDir": "collaboration/monitoring/intervention_packs",
            "interventionArtifactDir": "collaboration/monitoring/session_interventions",
            "claudeAdapter": {
                "enabled": False,
                "channel": "",
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/claude_adapter_report.json",
                "history": "logs/claude_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/claude_push_events",
            },
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            },
            "codexAdapter": {
                "runtimeFile": ".cc-claude-codex/runtime.json",
                "staleAfterMinutes": 180,
                "report": "logs/codex_adapter_report.json",
                "history": "logs/codex_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEX_ADAPTER_SUMMARY_latest.md",
            },
            "continuationHandoff": {
                "report": "logs/session_continuation_handoff_report.json",
                "history": "logs/session_continuation_handoff_history.jsonl",
                "summary": "collaboration/monitoring/SESSION_CONTINUATION_HANDOFF_SUMMARY_latest.md",
                "outputDir": "collaboration/results",
                "filenamePrefix": "SESSION_CONTINUATION_HANDOFF",
            },
            "transportModes": ["manual", "bridge"],
        },
        "trigger": {
            "report": "logs/task_trigger_report.json",
            "history": "logs/task_trigger_history.jsonl",
            "outputDir": "collaboration/monitoring",
            "payloadPrefix": "AGENT_TRIGGER",
        },
        "workspaceGuard": {
            "enabled": True,
            "applyOnly": True,
            "requireSourceClean": True,
            "dirtyTotalThreshold": 120,
            "rootDeletedThreshold": 10,
            "sourceDirtyThreshold": 30,
            "resultsUntrackedThreshold": 40,
            "report": "logs/workspace_forensics/workspace_guard_latest.json",
            "history": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "failOnGitError": False,
        },
        "spawnAgentGuard": {
            "enabled": True,
            "allowedLeadAgents": ["codex"],
            "requireParentTask": True,
            "requireWriteSet": True,
            "allowReadOnly": True,
            "protectedPaths": [
                ".vscode/ai-collab.json",
                "logs/collaboration_state.json",
                "logs/agent_dispatch_state.json",
                "logs/agent_receipt_state.json",
            ],
            "protectedPrefixes": [
                "collaboration/tasks/",
                "collaboration/monitoring/AGENT_TRIGGER_",
            ],
            "report": "logs/workspace_forensics/spawn_agent_guard_latest.json",
            "history": "logs/workspace_forensics/spawn_agent_guard_history.jsonl",
        },
        "workspaceHygiene": {
            "enabled": False,
            "pollIntervalMinutes": 15,
            "onReceiptClose": True,
            "domainOrder": ["ops", "docs", "other"],
            "includeSource": False,
            "autoStage": True,
            "maxCandidatesPerRun": 300,
            "createCheckpoint": True,
            "report": "logs/workspace_forensics/hygiene_latest.json",
            "history": "logs/workspace_forensics/hygiene_history.jsonl",
        },
        "agentOrchestration": {
            "autoDetectAgents": True,
            "includeUserAsOperator": True,
            "operatorFirst": False,
            "forceLeadAgent": None,
            "disabledAgents": ["copilot"],
            "intentLeadMap": {
                "architecture": ["codex", "claude_code", "codearts_agent"],
                "implementation": ["claude_code", "codex", "codearts_agent"],
                "testing": ["codearts_agent", "claude_code", "codex"],
                "documentation": ["codearts_agent", "codex", "claude_code"],
                "research": ["codex", "claude_code", "codearts_agent"],
                "operation": ["codex", "claude_code", "codearts_agent"],
            },
            "modelAgentMap": {
                "claude": "claude_code",
                "copilot": "codearts_agent",
                "glm|codearts": "codearts_agent",
                "gpt|codex|openai": "codex",
            },
        },
    }

    config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(vscode_config, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 创建配置: {config_file}")

    # 初始化状态文件
    state = StateManager(workspace_path=workspace)
    print(f"  ✓ 初始化状态: {state.workspace_path}")

    print("\n项目初始化完成!")
    print(f"  工作区: {workspace}")
    print("\n下一步:")
    print("  1. 运行: ai-collab activate --ai claude")
    print("  2. 检测冲突: ai-collab check --files <file-path>")

    return 0


def cmd_clean(args):
    """清理旧日志"""
    from ..dev_logger import DevLogger

    # 设置 workspace 路径环境变量
    _set_workspace_env(args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 清理旧日志")
    print("=" * 60)

    claude_logger = DevLogger("claude-code")
    codearts_logger = DevLogger("codearts-agent")
    copilot_logger = DevLogger("copilot")

    claude_logger.rotate_logs(args.max_files)
    codearts_logger.rotate_logs(args.max_files)
    copilot_logger.rotate_logs(args.max_files)

    # 清理已完成的任务
    state = StateManager(workspace_path=args.workspace)
    result = state.clear_completed_tasks(args.days if args.days else 30)

    print("\n清理完成:")
    print(f"  保留最近日志: {args.max_files} 个")
    print(f"  保留最近任务: {args.days if args.days else 30} 天")
    print(f"  清除任务数: {result['cleared']}")
    print(f"  剩余任务数: {result['remaining']}")

    return 0


def cmd_status(args):
    """显示系统状态"""
    _set_workspace_env(args.workspace)
    state = StateManager(workspace_path=args.workspace)
    workspace = os.path.abspath(
        args.workspace or VSCodeIntegration.get_workspace_path() or os.getcwd()
    )
    workspace_path = Path(workspace)

    print("=" * 60)
    print("AI 协作系统 - 系统状态")
    print("=" * 60)

    print("\n[工作区]")
    print(f"  路径: {workspace or '未设置'}")

    config = VSCodeIntegration.get_project_config()
    print("\n[项目配置]")
    print(f"  版本: {config.get('version', 'N/A')}")
    print(f"  规则目录: {config.get('rulesDir', './rules')}")
    print(f"  日志目录: {config.get('logsDir', './logs')}")
    print(f"  激活词: {config.get('activationKeyword', '2X')}")
    print(f"  启用AI: {', '.join(config.get('enabledAIs', []))}")
    orchestration = config.get("agentOrchestration", {})
    print(f"  动态编排: {'on' if orchestration else 'off'}")
    if orchestration:
        print(f"    - autoDetectAgents: {orchestration.get('autoDetectAgents', True)}")
        print(f"    - operatorFirst: {orchestration.get('operatorFirst', False)}")
        print(f"    - forceLeadAgent: {orchestration.get('forceLeadAgent', None)}")

    print("\n[任务统计]")
    active_tasks = state.get_active_tasks()
    all_tasks = state.get_all_tasks()
    completed = [t for t in all_tasks if t.get("status") == "completed"]

    claude_tasks = [t for t in active_tasks if t.get("ai_type") == "claude_code"]
    codearts_tasks = [t for t in active_tasks if t.get("ai_type") == "codearts_agent"]
    codex_tasks = [t for t in active_tasks if t.get("ai_type") in {"codex", "copilot"}]
    legacy_copilot_tasks = [t for t in active_tasks if t.get("ai_type") == "copilot"]

    print(f"  总任务数: {len(all_tasks)}")
    print(f"  活跃任务: {len(active_tasks)}")
    print(f"    - Claude Code: {len(claude_tasks)}")
    print(f"    - CodeArts Agent: {len(codearts_tasks)}")
    print(f"    - Codex: {len(codex_tasks)}")
    if legacy_copilot_tasks:
        print(f"      legacy copilot: {len(legacy_copilot_tasks)}")
    print(f"  已完成任务: {len(completed)}")

    ack_summary = summarize_ack_bridge_state(workspace_path)
    missing_ack_report = _load_json_file(workspace_path / "logs" / "missing_ack_report.json")
    result_consistency_report = _load_json_file(
        workspace_path / "logs" / "task_result_consistency_report.json"
    )
    daily_report = _load_json_file(workspace_path / "logs" / "daily_report.json")

    print("\n[治理健康]")
    print(f"  ACK bridge 记录: {ack_summary.get('bridge_record_count', 0)}")
    print(f"  显式 ACK 证据: {ack_summary.get('explicit_ack_count', 0)}")
    print(f"  可闭环 ACK: {ack_summary.get('closeout_eligible_ack_count', 0)}")
    print(f"  Claude fallback 残留: {ack_summary.get('claude_legacy_fallback_count', 0)}")
    if missing_ack_report:
        print(f"  显式 ACK 残留任务: {missing_ack_report.get('stale_explicit_ack_count', 0)}")
        print(f"  missing-ack 错误数: {missing_ack_report.get('error_count', 0)}")
    else:
        print("  显式 ACK 残留任务: 未生成 missing_ack_report")
    if result_consistency_report:
        print(
            "  终态结果一致性: "
            f"issues={result_consistency_report.get('issue_count', 0)} / "
            f"audited={result_consistency_report.get('audited_count', 0)}"
        )
    else:
        print("  终态结果一致性: 未生成 task_result_consistency_report")
    if daily_report:
        print(f"  日报时间: {daily_report.get('generated_at', 'unknown')}")
    else:
        print("  日报时间: 未生成 daily_report")

    print("\n[报告健康]")
    print(
        _report_health_line(
            name="missing-ack",
            path=workspace_path / "logs" / "missing_ack_report.json",
            payload=missing_ack_report,
        )
    )
    print(
        _report_health_line(
            name="result-consistency",
            path=workspace_path / "logs" / "task_result_consistency_report.json",
            payload=result_consistency_report,
        )
    )
    print(
        _report_health_line(
            name="daily-report",
            path=workspace_path / "logs" / "daily_report.json",
            payload=daily_report,
        )
    )

    conflicts = state.get_conflicts("open")
    print("\n[冲突状态]")
    print(f"  未解决冲突: {len(conflicts)}")

    if conflicts and args.verbose:
        for c in conflicts[:3]:
            print(f"    - {c['task_id_1']} vs {c['task_id_2']}")

    return 0


def _load_steps_from_file(file_path: str) -> List[str]:
    """从文本文件加载步骤（每行一个步骤）。"""
    steps: List[str] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            step = line.strip()
            if step and not step.startswith("#"):
                steps.append(step)
    return steps


def _emit_plan_tasks(
    state: StateManager,
    plan: dict,
    related_files: Optional[List[str]] = None,
    task_prefix: str = "TASK-PLAN",
) -> List[str]:
    """将角色计划转换为可执行任务，避免辅助 agent 闲置。"""
    related_files = related_files or []
    created: List[str] = []
    timestamp = int(datetime.now().timestamp())
    utilization = plan.get("utilization_plan", [])

    def _default_primary_skill(agent: str, role: str) -> str:
        agent_lower = agent.lower()
        role_lower = role.lower()
        if agent_lower == "codex":
            return "duoai-coordinator"
        if agent_lower == "claude_code":
            return "backend-architect" if role_lower == "lead" else "planning-with-files"
        if agent_lower in {"codearts_agent", "copilot"}:
            return "api-test-pro"
        return "planning-with-files"

    for idx, item in enumerate(utilization, 1):
        agent = item.get("agent", "unknown")
        if agent == "user":
            continue
        role = item.get("role", "support")
        task_text = item.get("task", "执行并行协作任务")
        task_id = f"{task_prefix}-{timestamp}-{idx:02d}"
        primary_skill = _default_primary_skill(agent, role)
        try:
            state.register_task(
                task_id=task_id,
                ai_type=agent,
                description=f"[{role}] {task_text}",
                files=related_files,
                vscode_context={"source": "dynamic-orchestrator"},
                change_id="bugfix/no-spec",
                assignee=agent,
                reviewer="codex",
                primary_skill=primary_skill,
                support_skills=["planning-with-files", "systematic-debugging"],
                acceptance_commands=[
                    "python3 -m ai_collab.cli status -v",
                    "python3 -m ai_collab.cli tasks validate-contract --scope active --strict",
                ],
                result_file=f"collaboration/results/RESULT_{task_id}.md",
            )
            created.append(task_id)
        except ValueError:
            continue
    return created


def _emit_plan_patches(
    state: StateManager,
    plan: dict,
    task_id: str,
    related_files: Optional[List[str]] = None,
    patch_prefix: str = "PATCH-PLAN",
) -> List[str]:
    """将角色计划转换为 patch 分派。"""
    related_files = related_files or []
    created: List[str] = []
    timestamp = int(datetime.now().timestamp())
    utilization = plan.get("utilization_plan", [])

    for idx, item in enumerate(utilization, 1):
        agent = item.get("agent", "unknown")
        if agent == "user":
            continue
        role = item.get("role", "support")
        patch_text = item.get("task", "并行 patch")
        patch_id = f"{patch_prefix}-{timestamp}-{idx:02d}"
        try:
            state.register_patch(
                patch_id=patch_id,
                task_id=task_id,
                title=f"[{role}] {patch_text}",
                files=related_files,
                assignee=agent,
                actor="system",
                source="dynamic-orchestrator",
                reason="emit-patches",
            )
            created.append(patch_id)
        except ValueError:
            continue
    return created


def cmd_codex(args):
    """CC Claude Codex 集成命令"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    integration = CodexIntegration(workspace)

    print("=" * 60)
    print("AI 协作系统 - Codex 集成")
    print("=" * 60)

    if args.subcommand == "init":
        status_file = integration.ensure_initialized(args.goal or "", args.context or "")
        print("\n初始化完成:")
        print(f"  工作区: {workspace}")
        print(f"  状态文件: {status_file}")
        return 0

    if args.subcommand == "progress":
        steps = list(args.step or [])
        if args.steps_file:
            steps.extend(_load_steps_from_file(args.steps_file))

        plan = None
        if args.intent or args.model or args.force_lead:
            plan = integration.plan_roles(
                intent=args.intent or args.goal or "",
                models=args.model or [],
                operator=args.operator or "user",
                force_lead=args.force_lead,
            )

        follow_patterns = args.follow or ""
        if plan:
            follow_parts = [
                follow_patterns.strip(),
                f"Dynamic lead={plan['lead_agent']}",
                f"Support={','.join(plan['support_agents']) if plan['support_agents'] else 'none'}",
            ]
            follow_patterns = "; ".join([p for p in follow_parts if p])

        progress_file = integration.write_progress(
            goal=args.goal or "Codex batch task",
            steps=steps,
            tech_stack=args.tech_stack or "",
            follow_patterns=follow_patterns,
            avoid_patterns=args.avoid or "",
            related_files=args.file or [],
            test_cmd=args.test_cmd or "",
        )

        print(f"\n进度文件已生成: {progress_file}")
        print(f"  步骤数: {len(steps) if steps else 1}")

        if plan:
            print("\n动态角色计划:")
            print(f"  Lead: {plan['lead_agent']}")
            print(
                f"  Support: {', '.join(plan['support_agents']) if plan['support_agents'] else 'none'}"
            )

            if args.emit_tasks:
                state = StateManager(workspace_path=workspace)
                created = _emit_plan_tasks(state, plan, related_files=args.file or [])
                print(f"  并行任务创建: {len(created)}")
                for task_id in created:
                    print(f"    - {task_id}")
            if getattr(args, "emit_patches", False):
                state = StateManager(workspace_path=workspace)
                patch_task_id = args.task_id or f"TASK-PLAN-{int(datetime.now().timestamp())}"
                patches = _emit_plan_patches(
                    state, plan, task_id=patch_task_id, related_files=args.file or []
                )
                print(f"  并行 Patch 创建: {len(patches)}")
                for patch_id in patches:
                    print(f"    - {patch_id}")
        return 0

    if args.subcommand == "run":
        if args.intent or args.model or args.force_lead:
            plan = integration.plan_roles(
                intent=args.intent or "",
                models=args.model or [],
                operator=args.operator or "user",
                force_lead=args.force_lead,
            )
            print("\n动态角色计划:")
            print(f"  Lead: {plan['lead_agent']}")
            print(
                f"  Support: {', '.join(plan['support_agents']) if plan['support_agents'] else 'none'}"
            )

        progress_check = integration.validate_progress()
        if progress_check["issues"]:
            print("\n进度预检:")
            for issue in progress_check["issues"]:
                print(f"  - {issue}")

        try:
            result = integration.run_codex(
                readonly=args.readonly,
                max_timeout=args.max_timeout or 0,
                stale_timeout=args.stale_timeout or 120,
                sandbox=args.sandbox,
            )
        except RuntimeError as e:
            print(f"\n错误: {e}")
            return 1

        print("\n执行结果:")
        print(f"  exit_reason: {result.exit_reason}")
        print(f"  return_code: {result.return_code}")
        print(f"  耗时: {result.duration_seconds}s")
        print(f"  日志: {result.log_file}")
        print(f"  输出: {result.output_file}")

        if args.sync:
            state = StateManager(workspace_path=workspace)
            sync_result = integration.sync_to_state(state, task_id=args.task_id)
            print("\n状态同步完成:")
            print(f"  任务ID: {sync_result['task_id']}")
            print(f"  状态: {sync_result['status']}")
            print(f"  进度: {sync_result['done_steps']}/{sync_result['total_steps']}")

        return 0 if result.return_code == 0 else 1

    if args.subcommand == "exec":
        steps = list(args.step or [])
        if args.steps_file:
            steps.extend(_load_steps_from_file(args.steps_file))

        plan = integration.plan_roles(
            intent=args.intent or args.goal or "Codex pipeline task",
            models=args.model or [],
            operator=args.operator or "user",
            force_lead=args.force_lead,
        )
        print("\n动态角色计划:")
        print(f"  Lead: {plan['lead_agent']}")
        print(
            f"  Support: {', '.join(plan['support_agents']) if plan['support_agents'] else 'none'}"
        )

        if args.emit_tasks:
            state = StateManager(workspace_path=workspace)
            created = _emit_plan_tasks(state, plan, related_files=args.file or [])
            print(f"  并行任务创建: {len(created)}")
            for task_id in created:
                print(f"    - {task_id}")
        if getattr(args, "emit_patches", False):
            state = StateManager(workspace_path=workspace)
            patch_task_id = args.task_id or f"TASK-PLAN-{int(datetime.now().timestamp())}"
            patches = _emit_plan_patches(
                state, plan, task_id=patch_task_id, related_files=args.file or []
            )
            print(f"  并行 Patch 创建: {len(patches)}")
            for patch_id in patches:
                print(f"    - {patch_id}")

        follow_patterns = args.follow or ""
        follow_parts = [
            follow_patterns.strip(),
            f"Dynamic lead={plan['lead_agent']}",
            f"Support={','.join(plan['support_agents']) if plan['support_agents'] else 'none'}",
        ]
        follow_patterns = "; ".join([p for p in follow_parts if p])

        progress_file = integration.write_progress(
            goal=args.goal or "Codex pipeline task",
            steps=steps,
            tech_stack=args.tech_stack or "",
            follow_patterns=follow_patterns,
            avoid_patterns=args.avoid or "",
            related_files=args.file or [],
            test_cmd=args.test_cmd or "",
        )
        print(f"\n进度文件已生成: {progress_file}")
        print(f"  步骤数: {len(steps) if steps else 1}")

        progress_check = integration.validate_progress()
        if progress_check["issues"]:
            print("\n进度预检:")
            for issue in progress_check["issues"]:
                print(f"  - {issue}")

        try:
            result = integration.run_codex(
                readonly=args.readonly,
                max_timeout=args.max_timeout or 0,
                stale_timeout=args.stale_timeout or 120,
                sandbox=args.sandbox,
            )
        except RuntimeError as e:
            print(f"\n错误: {e}")
            return 1

        print("\n执行结果:")
        print(f"  exit_reason: {result.exit_reason}")
        print(f"  return_code: {result.return_code}")
        print(f"  耗时: {result.duration_seconds}s")
        print(f"  日志: {result.log_file}")
        print(f"  输出: {result.output_file}")

        state = StateManager(workspace_path=workspace)
        sync_result = integration.sync_to_state(state, task_id=args.task_id)
        print("\n状态同步完成:")
        print(f"  任务ID: {sync_result['task_id']}")
        print(f"  状态: {sync_result['status']}")
        print(f"  进度: {sync_result['done_steps']}/{sync_result['total_steps']}")

        return 0 if result.return_code == 0 else 1

    if args.subcommand == "sync":
        state = StateManager(workspace_path=workspace)
        sync_result = integration.sync_to_state(state, task_id=args.task_id)
        print("\n状态同步完成:")
        print(f"  任务ID: {sync_result['task_id']}")
        print(f"  状态: {sync_result['status']}")
        print(f"  进度: {sync_result['done_steps']}/{sync_result['total_steps']}")
        print(f"  目标: {sync_result['goal']}")
        return 0

    if args.subcommand == "plan":
        plan = integration.plan_roles(
            intent=args.intent or args.goal or "",
            models=args.model or [],
            operator=args.operator or "user",
            force_lead=args.force_lead,
        )

        print("\n动态角色计划:")
        print(f"  意图分类: {plan['intent_category']}")
        print(f"  Lead: {plan['lead_agent']}")
        print(
            f"  Support: {', '.join(plan['support_agents']) if plan['support_agents'] else 'none'}"
        )
        print(
            f"  可用代理: {', '.join(plan['available_agents']) if plan['available_agents'] else 'none'}"
        )
        print(f"  模型映射代理: {', '.join(plan['model_agents']) if plan['model_agents'] else 'none'}")
        print(f"  原因: {'; '.join(plan['reasons'])}")
        print("\n  并行利用计划:")
        for item in plan["utilization_plan"]:
            print(f"    - [{item['role']}] {item['agent']}: {item['task']}")

        if args.emit_tasks:
            state = StateManager(workspace_path=workspace)
            created = _emit_plan_tasks(state, plan, related_files=args.file or [])
            print(f"\n  自动创建任务: {len(created)}")
            for task_id in created:
                print(f"    - {task_id}")
        if getattr(args, "emit_patches", False):
            state = StateManager(workspace_path=workspace)
            patch_task_id = args.task_id or f"TASK-PLAN-{int(datetime.now().timestamp())}"
            patches = _emit_plan_patches(
                state, plan, task_id=patch_task_id, related_files=args.file or []
            )
            print(f"\n  自动创建 Patch: {len(patches)}")
            for patch_id in patches:
                print(f"    - {patch_id}")
        return 0

    if args.subcommand == "hooks":
        action = args.hook_action or "status"
        if action == "install":
            result = integration.install_hooks()
        elif action == "uninstall":
            result = integration.uninstall_hooks()
        elif action == "doctor":
            result = integration.doctor_hooks(repair=True)
        else:
            result = integration.hooks_status()

        print(f"\nHook {result.action} 结果:")
        print(f"  设置文件: {result.settings_file}")
        print(f"  安装状态: {'installed' if result.installed else 'not fully installed'}")
        for name, ok in result.details.items():
            if name in {"Stop", "PreCompact", "SessionStart", "PreToolUse"}:
                print(f"  - {name}: {'ON' if ok else 'OFF'}")
        issues = result.details.get("issues")
        if isinstance(issues, list) and issues:
            print("  诊断问题:")
            for item in issues:
                print(f"    - {item}")
        if result.action == "doctor":
            print(f"  自动修复: {'YES' if result.details.get('repaired') else 'NO'}")
        return 0

    print("\n错误: 未知 codex 子命令")
    return 1


def cmd_controller(args):
    """工单控制器命令（常驻轮询器）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    controller_config = (
        config.get("controller", {}) if isinstance(config.get("controller"), dict) else {}
    )

    interval_sec_arg = getattr(args, "interval_sec", None)
    pending_timeout_arg = getattr(args, "pending_timeout_sec", None)
    active_timeout_arg = getattr(args, "active_timeout_sec", None)
    blocked_timeout_arg = getattr(args, "blocked_timeout_sec", None)
    prewarn_ratio_arg = getattr(args, "prewarn_ratio", None)
    history_arg = getattr(args, "history", None)
    max_iterations_arg = getattr(args, "max_iterations", None)
    interval_sec = (
        interval_sec_arg
        if interval_sec_arg is not None
        else _as_int(controller_config.get("intervalSec"), 30)
    )
    pending_timeout_sec = (
        pending_timeout_arg
        if pending_timeout_arg is not None
        else _as_int(controller_config.get("pendingTimeoutSec"), 7200)
    )
    active_timeout_sec = (
        active_timeout_arg
        if active_timeout_arg is not None
        else _as_int(controller_config.get("activeTimeoutSec"), 1800)
    )
    blocked_timeout_sec = (
        blocked_timeout_arg
        if blocked_timeout_arg is not None
        else _as_int(controller_config.get("blockedTimeoutSec"), 3600)
    )
    prewarn_ratio = (
        float(prewarn_ratio_arg)
        if prewarn_ratio_arg is not None
        else float(controller_config.get("prewarnRatio", 0.8))
    )
    default_assignee = args.default_assignee or str(
        controller_config.get("defaultAssignee", "codex")
    )
    report_path = args.report or str(
        controller_config.get("report", "logs/task_controller_report.json")
    )
    history_path = history_arg or str(
        controller_config.get("history", "logs/task_controller_history.jsonl")
    )

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"
    if not script_path.exists():
        print(f"\n错误: 控制器脚本不存在: {script_path}")
        return 1

    cmd = [
        sys.executable or "python3",
        str(script_path),
        "--workspace",
        workspace,
        "--interval-sec",
        str(interval_sec),
        "--pending-timeout-sec",
        str(pending_timeout_sec),
        "--active-timeout-sec",
        str(active_timeout_sec),
        "--blocked-timeout-sec",
        str(blocked_timeout_sec),
        "--prewarn-ratio",
        str(prewarn_ratio),
        "--default-assignee",
        default_assignee,
        "--report",
        report_path,
        "--history",
        history_path,
    ]

    if args.once:
        cmd.append("--once")
    if args.dry_run:
        cmd.append("--dry-run")
    if max_iterations_arg is not None and max_iterations_arg > 0:
        cmd.extend(["--max-iterations", str(max_iterations_arg)])

    print("=" * 60)
    print("AI 协作系统 - 工单控制器")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"轮询间隔: {interval_sec}s")
    print(f"pending 超时: {pending_timeout_sec}s")
    print(f"active 超时: {active_timeout_sec}s")
    print(f"blocked 超时: {blocked_timeout_sec}s")
    print(f"prewarn 比例: {prewarn_ratio}")
    print(f"默认补丁执行者: {default_assignee}")
    print(f"报告路径: {report_path}")
    print(f"历史路径: {history_path}")
    print(f"模式: {'dry-run' if args.dry_run else 'apply'}{' + once' if args.once else ''}")

    result = subprocess.run(cmd, check=False)
    code = int(result.returncode)
    if code != 0:
        return code

    return 0


def cmd_dispatch(args):
    """自动派单桥接命令（生成 Agent 指令包）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    dispatch_config = config.get("dispatch", {}) if isinstance(config.get("dispatch"), dict) else {}

    include_pending = bool(args.include_pending)
    if not include_pending:
        include_pending = bool(dispatch_config.get("includePending", False))

    force_workspace = bool(getattr(args, "force_workspace", False))
    report_path = args.report or str(
        dispatch_config.get("report", "logs/task_dispatch_report.json")
    )
    history_path = args.history or str(
        dispatch_config.get("history", "logs/task_dispatch_history.jsonl")
    )
    state_path = args.state or str(dispatch_config.get("state", "logs/agent_dispatch_state.json"))
    orders_path = args.orders or str(
        dispatch_config.get("orders", "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md")
    )

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "agent_dispatch_bridge.py"
    if not script_path.exists():
        print(f"\n错误: 自动派单脚本不存在: {script_path}")
        return 1

    guard_allowed = _run_workspace_guard_gate(
        workspace=workspace,
        config=config,
        command="dispatch",
        dry_run=bool(args.dry_run),
        force_workspace=force_workspace,
    )
    if not guard_allowed:
        return 2

    cmd = [
        sys.executable or "python3",
        str(script_path),
        "--workspace",
        workspace,
        "--report",
        report_path,
        "--history",
        history_path,
        "--state",
        state_path,
        "--orders",
        orders_path,
    ]
    if include_pending:
        cmd.append("--include-pending")
    if args.redispatch:
        cmd.append("--redispatch")
    if args.dry_run:
        cmd.append("--dry-run")

    print("=" * 60)
    print("AI 协作系统 - 自动派单桥接")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"include_pending: {include_pending}")
    print(f"redispatch: {bool(args.redispatch)}")
    print(f"force_workspace: {force_workspace}")
    print(f"模式: {'dry-run' if args.dry_run else 'apply'}")
    print(f"报告路径: {report_path}")
    print(f"历史路径: {history_path}")
    print(f"状态路径: {state_path}")
    print(f"指令包: {orders_path}")

    result = subprocess.run(cmd, check=False)
    code = int(result.returncode)
    if code != 0:
        return code

    if not bool(args.dry_run):
        payload_sync = _generate_trigger_payload_files(
            workspace=workspace,
            config=config,
            orders_relpath=orders_path,
            trigger_phrase="AUTO DISPATCH SYNC",
            target="all",
        )
        print("[dispatch->trigger autosync]")
        print(f"  generated_at: {payload_sync.get('generated_at')}")
        print(f"  assignees: {', '.join(payload_sync.get('assignees', []))}")
        print(f"  source_orders_exists: {payload_sync.get('orders_exists', False)}")
        for path in payload_sync.get("output_files", []):
            print(f"  payload: {path}")

    # Generate reports and summaries
    _generate_reports_and_summaries(workspace=workspace)

    return 0


def cmd_trigger(args):
    """暗语触发命令（2X -> dispatch -> agent payload）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    activation_keyword = str(config.get("activationKeyword", "2X"))

    try:
        intent = parse_trigger_phrase(args.phrase, keyword=activation_keyword)
    except ValueError as exc:
        print(f"\n错误: 无效暗语: {exc}")
        return 2
    if intent.action != "dispatch":
        print(f"\n错误: 当前仅支持 DISPATCH，收到 action={intent.action}")
        return 2

    target = str(args.target or intent.target).strip().lower()
    if target not in {"all", "claude_code", "codearts_agent", "codex"}:
        print(f"\n错误: 不支持的 target: {target}")
        return 2
    if args.copy and target == "all":
        print("\n错误: --copy 仅支持单目标，请使用 --target claude_code、codearts_agent 或 codex")
        return 2

    include_pending, redispatch = _auto_enable_dispatch_flags(
        workspace=workspace,
        target=target,
        include_pending=bool(args.include_pending),
        redispatch=bool(args.redispatch),
    )

    dispatch_args = argparse.Namespace(
        workspace=workspace,
        dry_run=bool(args.dry_run),
        include_pending=include_pending,
        redispatch=redispatch,
        force_workspace=bool(getattr(args, "force_workspace", False)),
        report=args.dispatch_report,
        history=args.dispatch_history,
        state=args.dispatch_state,
        orders=args.dispatch_orders,
    )
    dispatch_code = cmd_dispatch(dispatch_args)
    if dispatch_code != 0:
        return dispatch_code

    dispatch_config = config.get("dispatch", {}) if isinstance(config.get("dispatch"), dict) else {}
    orders_relpath = dispatch_args.orders or str(
        dispatch_config.get("orders", "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md")
    )
    orders_file = Path(workspace) / orders_relpath
    if not orders_file.exists():
        print(f"\n错误: 派单指令包不存在: {orders_file}")
        return 1

    trigger_config = config.get("trigger", {}) if isinstance(config.get("trigger"), dict) else {}
    output_dir_rel = args.output_dir or str(
        trigger_config.get("outputDir", "collaboration/monitoring")
    )
    payload_prefix = str(trigger_config.get("payloadPrefix", "AGENT_TRIGGER"))
    trigger_report_rel = args.report or str(
        trigger_config.get("report", "logs/task_trigger_report.json")
    )
    trigger_history_rel = args.history or str(
        trigger_config.get("history", "logs/task_trigger_history.jsonl")
    )

    payload_sync = _generate_trigger_payload_files(
        workspace=workspace,
        config=config,
        orders_relpath=str(orders_file.relative_to(workspace)),
        trigger_phrase=intent.raw_phrase,
        target=target,
        output_dir_rel=output_dir_rel,
        payload_prefix=payload_prefix,
    )
    assignees = payload_sync["assignees"]
    output_files = payload_sync["output_files"]
    payloads = payload_sync["payloads"]
    generated_at = payload_sync["generated_at"]

    if args.copy:
        assignee = assignees[0]
        copy_result = subprocess.run(["pbcopy"], input=payloads[assignee], text=True, check=False)
        if copy_result.returncode != 0:
            print("\n错误: 拷贝到剪贴板失败（pbcopy 不可用）")
            return 1

    report = {
        "generated_at": generated_at,
        "workspace": workspace,
        "mode": "dry-run" if args.dry_run else "apply",
        "trigger_phrase": intent.raw_phrase,
        "action": intent.action,
        "target": target,
        "dispatch_orders": str(orders_file.relative_to(workspace)),
        "dispatch_report": dispatch_args.report
        or str(dispatch_config.get("report", "logs/task_dispatch_report.json")),
        "output_files": output_files,
        "copied_to_clipboard": bool(args.copy),
    }

    report_file = Path(workspace) / trigger_report_rel
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    history_file = Path(workspace) / trigger_history_rel
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(report, ensure_ascii=False) + "\n")

    print("=" * 60)
    print("AI 协作系统 - 暗语触发派单")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"暗语: {intent.raw_phrase}")
    print(f"目标: {target}")
    print(f"派单指令包: {orders_file.relative_to(workspace)}")
    for path in output_files:
        print(f"会话指令: {path}")
    print(f"报告路径: {trigger_report_rel}")
    print(f"历史路径: {trigger_history_rel}")

    return 0


def cmd_2x(args):
    """极简暗语入口：2x claude/codearts/codex/all。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    raw_target = str(args.target).strip().lower()
    force_workspace = bool(getattr(args, "force_workspace", False))
    target_map = {
        "claude": ("2X DISPATCH CLAUDE", "claude_code", True),
        "c": ("2X DISPATCH CLAUDE", "claude_code", True),
        "codearts": ("2X DISPATCH CodeArts", "codearts_agent", True),
        "a": ("2X DISPATCH CodeArts", "codearts_agent", True),
        "codex": ("2X DISPATCH CODEX", "codex", True),
        "x": ("2X DISPATCH CODEX", "codex", True),
        "all": ("2X DISPATCH", "all", False),
    }
    if raw_target not in target_map:
        print(f"\n错误: 不支持的 2x 目标: {args.target}")
        return 2

    # 智能模式：2x all 在无待派发任务但存在 testing 任务时，自动切到 receipt 收口。
    if raw_target == "all" and not bool(getattr(args, "dispatch_only", False)):
        try:
            state = StateManager(workspace_path=workspace)
            all_tasks = state.get_all_tasks()
        except Exception:
            all_tasks = []
        planning_or_pending = 0
        testing = 0
        for task in all_tasks:
            if not isinstance(task, dict):
                continue
            status = str(task.get("status", "")).strip().lower()
            if status in {"planning", "pending"}:
                planning_or_pending += 1
            elif status == "testing":
                testing += 1

        if planning_or_pending == 0 and testing > 0:
            receipt_args = argparse.Namespace(
                workspace=args.workspace,
                dry_run=bool(args.dry_run),
                reclose=False,
                force_workspace=force_workspace,
                report=None,
                history=None,
                state=None,
                summary=None,
            )
            print(f"\n2x all 智能收口: 未发现 planning/pending，检测到 testing={testing}，自动执行 receipt。")
            return cmd_receipt(receipt_args)

    phrase, target, default_copy = target_map[raw_target]
    copy_enabled = default_copy and (not bool(args.no_copy))
    include_pending, redispatch = _auto_enable_dispatch_flags(
        workspace=workspace,
        target=target,
        include_pending=bool(args.include_pending),
        redispatch=bool(args.redispatch),
    )

    trigger_args = argparse.Namespace(
        workspace=workspace,
        phrase=phrase,
        target=target,
        dry_run=bool(args.dry_run),
        include_pending=include_pending,
        redispatch=redispatch,
        force_workspace=force_workspace,
        dispatch_report=None,
        dispatch_history=None,
        dispatch_state=None,
        dispatch_orders=None,
        output_dir=None,
        report=None,
        history=None,
        copy=copy_enabled,
    )
    return cmd_trigger(trigger_args)


def cmd_receipt(args):
    """自动回执桥接命令（将 testing 任务收口到 completed）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    receipt_config = config.get("receipt", {}) if isinstance(config.get("receipt"), dict) else {}

    force_workspace = bool(getattr(args, "force_workspace", False))
    report_path = args.report or str(receipt_config.get("report", "logs/task_receipt_report.json"))
    history_path = args.history or str(
        receipt_config.get("history", "logs/task_receipt_history.jsonl")
    )
    state_path = args.state or str(receipt_config.get("state", "logs/agent_receipt_state.json"))
    summary_path = args.summary or str(
        receipt_config.get("summary", "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md")
    )

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "agent_receipt_bridge.py"
    if not script_path.exists():
        print(f"\n错误: 自动回执脚本不存在: {script_path}")
        return 1

    guard_allowed = _run_workspace_guard_gate(
        workspace=workspace,
        config=config,
        command="receipt",
        dry_run=bool(args.dry_run),
        force_workspace=force_workspace,
    )
    if not guard_allowed:
        return 2

    cmd = [
        sys.executable or "python3",
        str(script_path),
        "--workspace",
        workspace,
        "--report",
        report_path,
        "--history",
        history_path,
        "--state",
        state_path,
        "--summary",
        summary_path,
    ]
    if args.reclose:
        cmd.append("--reclose")
    if args.dry_run:
        cmd.append("--dry-run")

    print("=" * 60)
    print("AI 协作系统 - 自动回执桥接")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"reclose: {bool(args.reclose)}")
    print(f"force_workspace: {force_workspace}")
    print(f"模式: {'dry-run' if args.dry_run else 'apply'}")
    print(f"报告路径: {report_path}")
    print(f"历史路径: {history_path}")
    print(f"状态路径: {state_path}")
    print(f"摘要文件: {summary_path}")

    result = subprocess.run(cmd, check=False)
    code = int(result.returncode)
    if code != 0:
        return code
    if bool(args.dry_run):
        return 0

    receipt_report = _read_json_if_exists(Path(workspace) / report_path) or {}
    completed_count = _as_int(receipt_report.get("completed_count"), 0)
    hygiene_config = _resolve_workspace_hygiene_config(config)
    if completed_count > 0 and bool(hygiene_config.get("onReceiptClose", True)):
        print("\n[post-receipt hygiene] completed_count>0, trigger workspace hygiene ...")
        try:
            hygiene_report = _execute_hygiene_once(
                workspace=workspace,
                config=config,
                dry_run=False,
                force_workspace=force_workspace,
                trigger_source="post-receipt",
                include_source_override=None,
                auto_stage_override=bool(hygiene_config.get("autoStage", True)),
                max_candidates_override=None,
            )
            print(
                "[post-receipt hygiene] "
                f"blocked={hygiene_report.get('blocked', False)} "
                f"errors={hygiene_report.get('error_count', 0)} "
                f"report={hygiene_report.get('report_file', '')}"
            )
        except Exception as exc:
            print(
                f"[post-receipt hygiene] warning: hygiene failed but receipt already completed: {exc}"
            )

    # Generate reports and summaries
    _generate_reports_and_summaries(
        workspace=workspace,
        receipt_report_path=report_path,
    )

    return 0


def cmd_run(args):
    """标准 RUN 流程：dispatch -> receipt -> benefit（内置工作区门禁）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())

    print("=" * 60)
    print("AI 协作系统 - RUN 流程")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"模式: {'dry-run' if args.dry_run else 'apply'}")

    dispatch_args = argparse.Namespace(
        workspace=workspace,
        dry_run=bool(args.dry_run),
        include_pending=bool(args.include_pending),
        redispatch=bool(args.redispatch),
        force_workspace=bool(getattr(args, "force_workspace", False)),
        report=getattr(args, "dispatch_report", None),
        history=getattr(args, "dispatch_history", None),
        state=getattr(args, "dispatch_state", None),
        orders=getattr(args, "dispatch_orders", None),
    )
    dispatch_code = cmd_dispatch(dispatch_args)
    if dispatch_code != 0:
        print(f"\nRUN 中断: dispatch 失败 (code={dispatch_code})")
        return dispatch_code

    receipt_args = argparse.Namespace(
        workspace=workspace,
        dry_run=bool(args.dry_run),
        reclose=bool(args.reclose),
        force_workspace=bool(getattr(args, "force_workspace", False)),
        report=getattr(args, "receipt_report", None),
        history=getattr(args, "receipt_history", None),
        state=getattr(args, "receipt_state", None),
        summary=getattr(args, "receipt_summary", None),
    )
    receipt_code = cmd_receipt(receipt_args)
    if receipt_code != 0:
        print(f"\nRUN 中断: receipt 失败 (code={receipt_code})")
        return receipt_code

    benefit_args = argparse.Namespace(
        workspace=workspace,
        dry_run=bool(args.dry_run),
        dispatch_history=getattr(args, "benefit_dispatch_history", None),
        receipt_history=getattr(args, "benefit_receipt_history", None),
        target_ratio=getattr(args, "target_ratio", None),
        window=getattr(args, "window", None),
        report=getattr(args, "benefit_report", None),
        output=getattr(args, "benefit_output", None),
    )
    benefit_code = cmd_benefit(benefit_args)
    if benefit_code != 0:
        print(f"\nRUN 中断: benefit 失败 (code={benefit_code})")
        return benefit_code

    print("\nRUN 完成: dispatch + receipt + benefit")

    # Generate reports and summaries
    _generate_reports_and_summaries(
        workspace=workspace,
        receipt_report_path=getattr(args, "receipt_report", None),
    )

    return 0


def cmd_workspace_guard(args):
    """工作区门禁诊断命令。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()

    print("=" * 60)
    print("AI 协作系统 - 工作区门禁")
    print("=" * 60)
    print(f"\n工作区: {workspace}")

    allowed = _run_workspace_guard_gate(
        workspace=workspace,
        config=config,
        command=str(getattr(args, "for_command", "workspace-guard")),
        dry_run=bool(args.dry_run),
        force_workspace=bool(getattr(args, "force_workspace", False)),
    )
    return 0 if allowed else 2


def cmd_spawn_agent_guard(args):
    """spawn_agent 前置门禁诊断命令。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = dict(VSCodeIntegration.get_project_config())
    spawn_config = (
        dict(config.get("spawnAgentGuard", {}))
        if isinstance(config.get("spawnAgentGuard"), dict)
        else {}
    )
    if getattr(args, "report", None):
        spawn_config["report"] = args.report
    if getattr(args, "history", None):
        spawn_config["history"] = args.history
    config["spawnAgentGuard"] = spawn_config

    print("=" * 60)
    print("AI 协作系统 - spawn_agent 门禁")
    print("=" * 60)
    print(f"\n工作区: {workspace}")

    allowed = _run_spawn_agent_guard_gate(
        workspace=workspace,
        config=config,
        actor=str(getattr(args, "actor", "codex")),
        parent_task_id=getattr(args, "parent_task", None),
        files=list(getattr(args, "files", []) or []),
        read_only=bool(getattr(args, "read_only", False)),
    )
    return 0 if allowed else 2


def _print_stage_report(workspace: str, domain: str, report: dict, phase: str) -> None:
    """输出单次分域暂存报告。"""
    print("=" * 60)
    print(f"AI 协作系统 - 安全暂存 ({domain}) [{phase}]")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"模式: {report.get('mode')}")
    print(f"候选文件: {report.get('candidate_count', 0)}")
    status_counts = report.get("status_counts", {})
    print(
        "状态分布: "
        f"untracked={status_counts.get('untracked', 0)} "
        f"deleted={status_counts.get('deleted', 0)} "
        f"modified={status_counts.get('modified', 0)}"
    )
    print(f"报告路径: {report.get('report_file', '')}")
    print(f"历史路径: {report.get('history_file', '')}")

    sample_paths = report.get("sample_paths", [])
    if sample_paths:
        print("样例路径:")
        for path in sample_paths[:10]:
            print(f"  - {path}")
        if len(sample_paths) > 10:
            print(f"  - ... (+{len(sample_paths) - 10} more)")
    else:
        print("无可暂存文件。")


def _cmd_stage_domain(args, domain: str) -> int:
    """按域安全暂存 git 变更，避免误用 git add ."""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    report = stage_domain_changes(
        workspace=Path(workspace),
        domain=domain,
        dry_run=bool(args.dry_run),
    )
    if not bool(report.get("ok", False)):
        print(f"\n错误: 安全暂存失败: {report.get('error', 'unknown error')}")
        return 1

    _print_stage_report(workspace, domain, report, "preview" if bool(args.dry_run) else "apply")
    return 0


def cmd_stage_source(args):
    return _cmd_stage_domain(args, "source")


def cmd_stage_ops(args):
    return _cmd_stage_domain(args, "ops")


def cmd_stage_docs(args):
    return _cmd_stage_domain(args, "docs")


def cmd_stage_other(args):
    return _cmd_stage_domain(args, "other")


def cmd_stage_safe(args):
    """一键分域安全暂存：默认 ops -> docs -> other（先预览后执行）。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    domains = ["ops", "docs", "other"]
    if bool(getattr(args, "include_source", False)):
        domains.insert(0, "source")

    print("=" * 60)
    print("AI 协作系统 - 一键安全暂存 (stage-safe)")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"域顺序: {' -> '.join(domains)}")
    print("策略: 先预览，再执行")

    preview_reports: dict[str, dict] = {}
    for domain in domains:
        report = stage_domain_changes(
            workspace=Path(workspace),
            domain=domain,
            dry_run=True,
        )
        if not bool(report.get("ok", False)):
            print(f"\n错误: {domain} 预览失败: {report.get('error', 'unknown error')}")
            return 1
        preview_reports[domain] = report
        _print_stage_report(workspace, domain, report, "preview")

    total_candidates = sum(int(preview_reports[d].get("candidate_count", 0)) for d in domains)
    print(f"\n预览汇总: total_candidates={total_candidates}")
    if bool(args.dry_run):
        print("stage-safe dry-run 完成（未执行暂存）")
        return 0

    for domain in domains:
        candidate_count = int(preview_reports[domain].get("candidate_count", 0))
        if candidate_count <= 0:
            continue
        report = stage_domain_changes(
            workspace=Path(workspace),
            domain=domain,
            dry_run=False,
        )
        if not bool(report.get("ok", False)):
            print(f"\n错误: {domain} 执行失败: {report.get('error', 'unknown error')}")
            return 1
        _print_stage_report(workspace, domain, report, "apply")

    print("\nstage-safe 完成。")
    return 0


def _compact_stage_report(report: dict) -> dict:
    return {
        "candidate_count": int(report.get("candidate_count", 0)),
        "status_counts": dict(report.get("status_counts", {})),
        "sample_paths": list(report.get("sample_paths", []))[:10],
    }


def _execute_hygiene_once(
    *,
    workspace: str,
    config: dict,
    dry_run: bool,
    force_workspace: bool,
    trigger_source: str,
    include_source_override: bool | None = None,
    auto_stage_override: bool | None = None,
    max_candidates_override: int | None = None,
) -> dict:
    workspace_path = Path(workspace)
    guard_config = (
        config.get("workspaceGuard", {}) if isinstance(config.get("workspaceGuard"), dict) else {}
    )
    hygiene_config = _resolve_workspace_hygiene_config(config)

    include_source = (
        bool(include_source_override)
        if include_source_override is not None
        else bool(hygiene_config["includeSource"])
    )
    auto_stage = (
        bool(auto_stage_override)
        if auto_stage_override is not None
        else bool(hygiene_config["autoStage"])
    )
    max_candidates = (
        int(max_candidates_override)
        if max_candidates_override is not None
        else int(hygiene_config["maxCandidatesPerRun"])
    )
    domain_order = _normalize_hygiene_domain_order(hygiene_config["domainOrder"], include_source)
    mode = "dry-run" if dry_run else "apply"

    before = inspect_workspace(workspace_path)
    guard_report = run_workspace_guard(
        workspace=workspace_path,
        command=f"hygiene:{trigger_source}",
        mode=mode,
        guard_config=guard_config,
        force=force_workspace,
    )

    preview_reports: dict[str, dict] = {}
    apply_reports: dict[str, dict] = {}
    errors: list[str] = []
    total_candidates = 0
    for domain in domain_order:
        preview = stage_domain_changes(workspace=workspace_path, domain=domain, dry_run=True)
        preview_reports[domain] = preview
        if not bool(preview.get("ok", False)):
            errors.append(f"{domain}: preview failed: {preview.get('error', 'unknown error')}")
            continue
        total_candidates += int(preview.get("candidate_count", 0))

    blocked_reasons: list[str] = []
    if not bool(guard_report.get("allowed", False)):
        blocked_reasons.extend(list(guard_report.get("violations", [])))
    if max_candidates > 0 and total_candidates > max_candidates:
        blocked_reasons.append(
            f"candidate_count={total_candidates} exceeds maxCandidatesPerRun={max_candidates}"
        )

    can_apply = (not dry_run) and auto_stage and not errors and not blocked_reasons
    if can_apply:
        for domain in domain_order:
            candidate_count = int(preview_reports.get(domain, {}).get("candidate_count", 0))
            if candidate_count <= 0:
                continue
            applied = stage_domain_changes(workspace=workspace_path, domain=domain, dry_run=False)
            apply_reports[domain] = applied
            if not bool(applied.get("ok", False)):
                errors.append(f"{domain}: apply failed: {applied.get('error', 'unknown error')}")

    after = inspect_workspace(workspace_path)
    generated_at = datetime.now().isoformat()
    report = {
        "generated_at": generated_at,
        "workspace": workspace,
        "trigger_source": trigger_source,
        "mode": mode,
        "domain_order": domain_order,
        "include_source": include_source,
        "auto_stage": auto_stage,
        "max_candidates_per_run": max_candidates,
        "total_candidates": int(total_candidates),
        "guard_allowed": bool(guard_report.get("allowed", False)),
        "guard_violations": list(guard_report.get("violations", [])),
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "error_count": len(errors),
        "errors": errors,
        "before": before if isinstance(before, dict) else {"ok": False},
        "after": after if isinstance(after, dict) else {"ok": False},
        "preview": {domain: _compact_stage_report(rep) for domain, rep in preview_reports.items()},
        "apply": {domain: _compact_stage_report(rep) for domain, rep in apply_reports.items()},
        "create_checkpoint": bool(hygiene_config["createCheckpoint"]),
        "ok": len(errors) == 0,
    }

    report_rel = str(hygiene_config["report"])
    history_rel = str(hygiene_config["history"])
    report_file = workspace_path / report_rel
    history_file = workspace_path / history_rel
    _write_json(report_file, report)
    snapshot = {
        "generated_at": generated_at,
        "trigger_source": trigger_source,
        "mode": mode,
        "total_candidates": int(total_candidates),
        "blocked": bool(blocked_reasons),
        "error_count": len(errors),
        "domains": domain_order,
    }
    _append_jsonl(history_file, snapshot)

    report["report_file"] = str(report_file)
    report["history_file"] = str(history_file)
    report["guard_report_file"] = str(guard_report.get("report_file", ""))
    report["guard_history_file"] = str(guard_report.get("history_file", ""))
    return report


def _print_hygiene_report(report: dict) -> None:
    print("=" * 60)
    print("AI 协作系统 - 工作区治理 (hygiene)")
    print("=" * 60)
    print(f"\n工作区: {report.get('workspace', '')}")
    print(f"触发源: {report.get('trigger_source', '')}")
    print(f"模式: {report.get('mode', '')}")
    print(f"域顺序: {' -> '.join(report.get('domain_order', []))}")
    print(f"候选总量: {report.get('total_candidates', 0)}")
    print(f"guard_allowed: {report.get('guard_allowed', False)}")
    print(f"blocked: {report.get('blocked', False)}")
    if report.get("blocked_reasons"):
        for reason in report["blocked_reasons"][:10]:
            print(f"  block_reason: {reason}")
    print(f"errors: {report.get('error_count', 0)}")
    print(f"report: {report.get('report_file', '')}")
    print(f"history: {report.get('history_file', '')}")


def cmd_hygiene(args):
    """工作区/暂存区治理命令：支持一次执行与周期轮询。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    hygiene_config = _resolve_workspace_hygiene_config(config)

    interval_sec = (
        int(args.interval_sec)
        if getattr(args, "interval_sec", None) is not None
        else max(60, int(hygiene_config["pollIntervalMinutes"]) * 60)
    )
    max_iterations = max(0, int(getattr(args, "max_iterations", 0) or 0))
    run_loop = bool(getattr(args, "loop", False))

    iteration = 0
    while True:
        report = _execute_hygiene_once(
            workspace=workspace,
            config=config,
            dry_run=bool(args.dry_run),
            force_workspace=bool(getattr(args, "force_workspace", False)),
            trigger_source=str(getattr(args, "trigger_source", "manual")),
            include_source_override=(
                True if bool(getattr(args, "include_source", False)) else None
            ),
            auto_stage_override=(
                None if getattr(args, "auto_stage", None) is None else bool(args.auto_stage)
            ),
            max_candidates_override=getattr(args, "max_candidates", None),
        )
        _print_hygiene_report(report)

        if report.get("error_count", 0) > 0:
            return 1
        if bool(report.get("blocked", False)) and not bool(args.dry_run):
            return 2

        iteration += 1
        if not run_loop:
            break
        if max_iterations > 0 and iteration >= max_iterations:
            break
        import time

        time.sleep(max(1, interval_sec))
    return 0


def cmd_benefit(args):
    """自动化收益看板命令。"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    config = VSCodeIntegration.get_project_config()
    benefit_config = config.get("benefit", {}) if isinstance(config.get("benefit"), dict) else {}

    dispatch_histories = (
        args.dispatch_history
        or benefit_config.get("dispatchHistory")
        or ["logs/task_dispatch_history.jsonl"]
    )
    receipt_histories = (
        args.receipt_history
        or benefit_config.get("receiptHistory")
        or ["logs/task_receipt_history.jsonl"]
    )
    if isinstance(dispatch_histories, str):
        dispatch_histories = [dispatch_histories]
    if isinstance(receipt_histories, str):
        receipt_histories = [receipt_histories]

    target_ratio = (
        float(args.target_ratio)
        if args.target_ratio is not None
        else float(benefit_config.get("targetRatio", 3.0))
    )
    window = int(args.window) if args.window is not None else int(benefit_config.get("window", 14))
    report_path = args.report or str(
        benefit_config.get("report", "logs/automation_benefit_report.json")
    )
    output_path = args.output or str(
        benefit_config.get(
            "output", "collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md"
        )
    )

    script_path = (
        Path(__file__).resolve().parents[2]
        / "collaboration"
        / "scripts"
        / "build_automation_benefit_dashboard.py"
    )
    if not script_path.exists():
        print(f"\n错误: 收益看板脚本不存在: {script_path}")
        return 1

    cmd = [
        sys.executable or "python3",
        str(script_path),
        "--workspace",
        workspace,
        "--target-ratio",
        str(target_ratio),
        "--window",
        str(window),
        "--report",
        report_path,
        "--output",
        output_path,
    ]
    for path in dispatch_histories:
        cmd.extend(["--dispatch-history", str(path)])
    for path in receipt_histories:
        cmd.extend(["--receipt-history", str(path)])
    if args.dry_run:
        cmd.append("--dry-run")

    print("=" * 60)
    print("AI 协作系统 - 自动化收益看板")
    print("=" * 60)
    print(f"\n工作区: {workspace}")
    print(f"模式: {'dry-run' if args.dry_run else 'apply'}")
    print(f"target_ratio: {target_ratio}")
    print(f"window: {window}")
    print(f"dispatch_histories: {dispatch_histories}")
    print(f"receipt_histories: {receipt_histories}")
    print(f"报告路径: {report_path}")
    print(f"看板路径: {output_path}")

    result = subprocess.run(cmd, check=False)
    return int(result.returncode)


def cmd_pack(args):
    """Prompt Pack 管理命令"""
    _set_workspace_env(args.workspace)
    workspace = os.path.abspath(args.workspace or os.getcwd())
    packs_root = os.path.join(workspace, "packs")

    print("=" * 60)
    print("Prompt Pack 管理系统")
    print("=" * 60)

    manager = PackManager(Path(packs_root))

    if args.subcommand == "list":
        category_map = {
            "domain": PackCategoryType.DOMAIN,
            "project": PackCategoryType.PROJECT,
            "stage": PackCategoryType.STAGE,
            "role": PackCategoryType.ROLE,
        }
        category = category_map.get(args.category) if args.category else None

        available = manager.list_available_packs(category)

        print(f"\n可用 Pack ({len(available)} 个):")
        if category:
            print(f"  类别: {category.value}")

        if available:
            for pack_name in available:
                try:
                    pack = manager.load_pack(pack_name)
                    print(f"\n  {pack_name} (v{pack.manifest.version})")
                    print(f"    描述: {pack.manifest.description}")
                    print(f"    作者: {pack.manifest.author}")
                    if pack.manifest.tags:
                        print(f"    标签: {', '.join(pack.manifest.tags)}")
                except Exception as e:
                    print(f"\n  {pack_name} (加载失败: {e})")
        else:
            print("  无可用 Pack")

    elif args.subcommand == "show":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        tool_map = {
            "claude_code": AITool.CLAUDE_CODE,
            "github_copilot": AITool.GITHUB_COPILOT,
            "codex_agent": AITool.CODEX_AGENT,
            "codearts_agent": AITool.CODEARTS_AGENT,
        }
        tool = tool_map.get(args.tool, AITool.CLAUDE_CODE)

        try:
            pack = manager.load_pack(args.name)

            print(f"\n{pack.manifest.name} (v{pack.manifest.version})")
            print(f"  类别: {pack.manifest.category.value}")
            print(f"  版本: {pack.manifest.version}")
            print(f"  描述: {pack.manifest.description}")
            print(f"  作者: {pack.manifest.author}")
            print(f"  兼容工具: {', '.join([t.value for t in pack.manifest.compatible_tools])}")
            if pack.manifest.dependencies:
                print(f"  依赖: {', '.join(pack.manifest.dependencies)}")
            print(f"  规则文件数: {len(pack.rules)}")

            if args.context:
                print("\n[上下文字符串]")
                context = pack.to_context(tool)
                if context:
                    print(context[:1000] + "..." if len(context) > 1000 else context)
                else:
                    print("  无可用上下文")
        except FileNotFoundError:
            print(f"\n错误: Pack '{args.name}' 不存在")
            return 1

    elif args.subcommand == "activate":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        tool_map = {
            "claude_code": AITool.CLAUDE_CODE,
            "github_copilot": AITool.GITHUB_COPILOT,
            "codex_agent": AITool.CODEX_AGENT,
            "codearts_agent": AITool.CODEARTS_AGENT,
        }
        tool = tool_map.get(args.tool, AITool.CLAUDE_CODE)

        try:
            packed_context = manager.get_packed_context(args.name, tool, include_dependencies=True)

            if packed_context:
                print(f"\nPack '{args.name}' 上下文:")
                print("=" * 60)
                print(packed_context)
                print("=" * 60)
            else:
                print(f"\n错误: Pack '{args.name}' 无可用上下文")
                return 1
        except FileNotFoundError:
            print(f"\n错误: Pack '{args.name}' 不存在")
            return 1

    elif args.subcommand == "recommend":
        tool_map = {
            "claude_code": AITool.CLAUDE_CODE,
            "github_copilot": AITool.GITHUB_COPILOT,
            "codex_agent": AITool.CODEX_AGENT,
            "codearts_agent": AITool.CODEARTS_AGENT,
        }
        tool = tool_map.get(args.tool, AITool.CLAUDE_CODE)

        if not args.description:
            print("\n错误: 需要 --description 参数")
            return 1

        recommended = manager.get_best_pack(args.description, tool)

        if recommended:
            print(f"\n推荐 Pack: {recommended.manifest.name} (v{recommended.manifest.version})")
            print(f"  描述: {recommended.manifest.description}")
            print(f"  兼容工具: {', '.join([t.value for t in recommended.manifest.compatible_tools])}")
        else:
            print("\n未找到匹配的 Pack")

    # 版本管理
    # 版本管理
    elif args.subcommand == "version":
        return _handle_version_command(args, packs_root)

    # 兼容性检查
    elif args.subcommand == "check-compat":
        if not args.source or not args.target:
            print("\n错误: 需要 --source 和 --target 参数")
            return 1
        # Map args to expected format
        compat_args = type(
            "Args", (), {"source_version": args.source, "target_version": args.target}
        )()
        return _handle_compat_check(compat_args, packs_root)

    # Pack 商店
    elif args.subcommand in ["search", "browse", "trending"]:
        store_args = type(
            "Args",
            (),
            {
                "store_subcommand": args.subcommand,
                "query": getattr(args, "query", ""),
                "category": getattr(args, "category", None),
                "sort": getattr(args, "sort", "popularity"),
                "limit": getattr(args, "limit", 20),
            },
        )()
        return _handle_store_command(store_args, packs_root)

    # 评分系统
    elif args.subcommand == "rate":
        rating_args = type(
            "Args",
            (),
            {
                "rating_subcommand": args.rating_subcommand,
                "name": args.name,
                "user": getattr(args, "user", None),
                "rating": getattr(args, "rating", None),
                "title": getattr(args, "title", None),
                "content": getattr(args, "content", None),
                "detailed": getattr(args, "detailed", False),
            },
        )()
        return _handle_rating_command(rating_args, packs_root, workspace)

    # 权限管理
    elif args.subcommand == "share":
        share_args = type(
            "Args",
            (),
            {
                "share_subcommand": args.share_subcommand,
                "name": args.name,
                "target_user": getattr(args, "target_user", None),
                "level": getattr(args, "level", None),
                "user": getattr(args, "as_user", "owner"),
                "set_public": getattr(args, "set", None),
            },
        )()
        return _handle_sharing_command(share_args, packs_root)

    # Pack 验证
    elif args.subcommand == "validate":
        if not args.path:
            print("\n错误: 需要 --path 参数")
            return 1

        return _handle_validate_command(args, workspace)

    # Pack 模板
    elif args.subcommand == "template":
        if not args.name or not args.category:
            print("\n错误: 需要 --name 和 --category 参数")
            return 1

        return _handle_template_command(args, packs_root)

    # Pack 导出/导入
    elif args.subcommand == "export":
        if not args.source:
            print("\n错误: 需要 --source 参数")
            return 1

        return _handle_export_command(args, packs_root, workspace)

    elif args.subcommand == "import":
        if not args.source:
            print("\n错误: 需要 --source 参数")
            return 1

        return _handle_import_command(args, packs_root, workspace)

    return 0


def _handle_version_command(args, packs_root):
    """处理版本管理命令"""
    from ai_collab.prompt_pack import PromptPack
    from ai_collab.prompt_pack.version import PackVersionManager, VersionBumpType

    pack_dir = Path(packs_root) / args.name

    if not pack_dir.exists():
        print(f"\n✗ 错误: Pack '{args.name}' 不存在")
        return 1

    # Initialize version manager for this pack
    try:
        PromptPack(pack_dir)
        version_manager = PackVersionManager(pack_dir)
    except Exception as e:
        print(f"\n✗ 错误: 无法加载 Pack '{args.name}': {e}")
        return 1

    if args.version_subcommand == "bump":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        bump_type_map = {
            "major": VersionBumpType.MAJOR,
            "minor": VersionBumpType.MINOR,
            "patch": VersionBumpType.PATCH,
        }
        bump_type = bump_type_map.get(args.type, VersionBumpType.PATCH)

        try:
            new_version = version_manager.bump_version(bump_type)
            print(f"\n✓ Pack '{args.name}' 版本已更新")
            print(f"  新版本: {new_version}")
        except FileNotFoundError:
            print(f"\n✗ 错误: Pack '{args.name}' 不存在")
            return 1

    elif args.version_subcommand == "history":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        try:
            history = version_manager.get_version_history()
            if not history:
                print(f"\nPack '{args.name}' 无版本历史")
            else:
                print(f"\nPack '{args.name}' 版本历史:")
                for idx, record in enumerate(history, 1):
                    print(
                        f"  {idx}. v{record.version} - {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if hasattr(record, "changelog") and record.changelog:
                        print(f"     变更日志: {record.changelog}")
        except FileNotFoundError:
            print(f"\n✗ 错误: Pack '{args.name}' 不存在")
            return 1
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            return 1

    return 0


def _handle_compat_check(args, packs_root):
    """处理兼容性检查命令"""
    from ai_collab.prompt_pack.version import PackVersion

    try:
        source = PackVersion.parse(args.source_version)
        target = PackVersion.parse(args.target_version)

        # Simple semantic compatibility check
        print(f"\n兼容性检查: v{source} → v{target}")
        print(f"  源版本: {source}")
        print(f"  目标版本: {target}")

        # Check major version bump
        if target.major > source.major:
            print("  兼容性: ⚠️  BACKWARDS_INCOMPATIBLE")
            print("  原因: 主版本号增加，可能包含破坏性变更")
            return 1
        elif target.major == source.major and target.minor > source.minor:
            print("  兼容性: ✅ COMPATIBLE (新增功能)")
            print("  说明: 小版本号增加，向后兼容")
            return 0
        elif (
            target.major == source.major
            and target.minor == source.minor
            and target.patch > source.patch
        ):
            print("  兼容性: ✅ COMPATIBLE (修复)")
            print("  说明: 补丁版本号增加，向后兼容")
            return 0
        elif target < source:
            print("  兼容性: ⚠️  FORWARD_INCOMPATIBLE")
            print("  原因: 目标版本低于源版本，可能不支持")
            return 1
        else:
            print("  兼容性: ✅ COMPATIBLE")
            return 0
    except ValueError as e:
        print(f"\n✗ 错误: {e}")
        return 1


def _handle_store_command(args, packs_root):
    """处理 Pack 商店命令"""
    from ai_collab.prompt_pack.schema import PackCategoryType
    from ai_collab.prompt_pack.store import PackSortType, create_pack_store

    search_engine = create_pack_store(".", packs_root)

    if args.store_subcommand == "search":
        results = search_engine.search(
            args.query,
            sort_by=getattr(PackSortType, args.sort.upper(), PackSortType.POPULARITY),
            limit=args.limit,
        )

        print(f"\n搜索结果 ('{args.query}'): {len(results)} 个 Pack")
        if results:
            for pack in results:
                print(f"\n  {pack.name} (v{pack.version})")
                print(f"    类别: {pack.category.value}")
                print(f"    描述: {pack.description}")
                print(f"    作者: {pack.author}")
                print(f"    评分: {pack.rating:.1f} ({pack.review_count} 评论)")
                if pack.tags:
                    print(f"    标签: {', '.join(pack.tags)}")
        else:
            print("  无匹配结果")

    elif args.store_subcommand == "browse":
        category_map = {
            "domain": PackCategoryType.DOMAIN,
            "project": PackCategoryType.PROJECT,
            "stage": PackCategoryType.STAGE,
            "role": PackCategoryType.ROLE,
        }
        category = category_map.get(args.category)

        if not category:
            print("\n错误: 需要 --category 参数")
            return 1

        results = search_engine.browse_by_category(
            category, sort_by=getattr(PackSortType, args.sort.upper(), PackSortType.POPULARITY)
        )

        print(f"\n{category.value} 类别的 Pack: {len(results)} 个")
        for pack in results:
            print(f"  {pack.name} (v{pack.version}) - {pack.rating:.1f}★")

    elif args.store_subcommand == "trending":
        packs = search_engine.get_trending_packs(days=7, limit=args.limit)
        print("\n热门 Pack (7天内):")
        for idx, pack in enumerate(packs, 1):
            print(f"  {idx}. {pack.name} (v{pack.version})")
            print(f"     {pack.rating:.1f}★ | {pack.downloads} 下载")

    return 0


def _handle_rating_command(args, packs_root, workspace):
    """处理评分命令"""
    from ai_collab.prompt_pack.rating import RatingSystem

    rating_system = RatingSystem(".", workspace)

    if args.rating_subcommand == "add":
        if not all([args.name, args.user, args.rating, args.title]):
            print("\n错误: 需要 --name, --user, --rating, --title 参数")
            return 1

        try:
            review = rating_system.add_review(
                pack_name=args.name,
                user=args.user,
                rating=args.rating,
                title=args.title,
                content=args.content or "",
            )
            print("\n✓ 评论已添加")
            print(f"  Pack: {args.name}")
            print(f"  用户: {args.user}")
            print(f"  评分: {args.rating}★")
        except ValueError as e:
            print(f"\n✗ 错误: {e}")
            return 1

    elif args.rating_subcommand == "list":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        reviews = rating_system.get_reviews(args.name)
        summary = rating_system.get_rating_summary(args.name)

        print(f"\n{args.name} 的评论 ({len(reviews)} 条)")
        print(f"  平均评分: {summary.average_rating:.1f}★")
        print("  评分分布: ", end="")
        for star in range(1, 6):
            count = summary.rating_distribution[star]
            print(f"{star}★: {count}  ", end="")
        print()

        if args.detailed:
            print()
            for review in reviews:
                print(f"\n  {review.title} ({review.rating}★)")
                print(f"    用户: {review.user}")
                print(f"    内容: {review.content}")
                print(f"    有帮助: {review.helpful_count} 人")

    elif args.rating_subcommand == "helpful":
        if not args.name or not args.review_id:
            print("\n错误: 需要 --name 和 --review-id 参数")
            return 1

        result = rating_system.mark_review_helpful(args.name, args.review_id)
        if result:
            print("\n✓ 已标记为有帮助")
        else:
            print("\n✗ 评论不存在")
            return 1

    return 0


def _handle_validate_command(args, workspace):
    """处理 Pack 验证命令"""
    pack_path = Path(args.path)

    if not pack_path.exists():
        print(f"\n✗ 错误: Pack 文件不存在: {pack_path}")
        return 1

    print(f"\n验证 Pack: {pack_path}")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. JSON 语法验证
    try:
        with open(pack_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("✓ JSON 语法正确")
    except json.JSONDecodeError as e:
        errors.append(f"JSON 语法错误: {e}")
        print(f"✗ JSON 语法错误: {e}")
        return 1

    # 2. 必需字段验证
    required_top_level = ["metadata", "domain", "workflow", "quality_metrics"]
    for field in required_top_level:
        if field not in data:
            errors.append(f"缺少必需字段: {field}")
            print(f"✗ 缺少必需字段: {field}")
        else:
            print(f"✓ 必需字段存在: {field}")

    # 3. metadata 字段验证
    if "metadata" in data:
        required_metadata = [
            "pack_id",
            "pack_name",
            "version",
            "type",
            "description",
            "designer",
            "created_at",
            "updated_at",
        ]
        for field in required_metadata:
            if field not in data["metadata"]:
                errors.append(f"metadata 缺少必需字段: {field}")
                print(f"✗ metadata 缺少: {field}")
            else:
                print(f"✓ metadata.{field}")

    # 4. Schema 合规性验证
    if "quality_metrics" in data and "metrics" in data["quality_metrics"]:
        metrics = data["quality_metrics"]["metrics"]
        total_weight = sum(m.get("weight", 0) for m in metrics.values())
        if abs(total_weight - 1.0) > 0.01:
            warnings.append(f"质量指标权重总和不为 1.0: {total_weight:.3f}")
            print(f"⚠  质量指标权重总和: {total_weight:.3f} (应为 1.0)")
        else:
            print(f"✓ 质量指标权重总和: {total_weight:.3f}")

    # 5. workflow 步骤验证
    if "workflow" in data and "steps" in data["workflow"]:
        steps = data["workflow"]["steps"]
        step_ids = [s.get("id") for s in steps if "id" in s]
        if len(step_ids) != len(set(step_ids)):
            duplicates = [sid for sid in step_ids if step_ids.count(sid) > 1]
            errors.append(f"workflow 步骤 ID 重复: {set(duplicates)}")
            print(f"✗ workflow 步骤 ID 重复: {set(duplicates)}")
        else:
            print(f"✓ workflow 步骤 ID 唯一 ({len(steps)} 个步骤)")

    # 输出结果
    print("=" * 60)
    if errors:
        print(f"验证失败: {len(errors)} 个错误, {len(warnings)} 个警告")
        for err in errors:
            print(f"  ✗ {err}")
        for warn in warnings:
            print(f"  ⚠  {warn}")
        return 1
    else:
        print(f"验证通过{': ' + f'{len(warnings)} 个警告' if warnings else ''}")
        for warn in warnings:
            print(f"  ⚠  {warn}")
        return 0


def _handle_template_command(args, packs_root):
    """处理 Pack 模板生成命令"""
    from datetime import datetime

    pack_name = args.name
    category = args.category

    # 创建模板数据
    template = {
        "metadata": {
            "pack_id": pack_name.lower().replace(" ", "-"),
            "pack_name": pack_name,
            "version": "1.0.0",
            "type": "custom",
            "description": f"{pack_name} - 自动生成的模板",
            "designer": "AI Collab Team",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "category": category,
            "tags": [category],
            "language": "zh",
            "estimated_efficiency_gain": "50%",
        },
        "domain": {
            "primary_domain": category,
            "secondary_domains": [],
            "target_platforms": ["generic"],
            "target_audience": "通用用户",
            "brand_tone": "专业",
            "compliance_rules": ["符合平台规范"],
        },
        "workflow": {
            "steps": [
                {
                    "id": "step_1_input",
                    "name": "输入阶段",
                    "type": "local",
                    "description": "收集输入信息",
                    "input_fields": ["input_data"],
                    "output_field": "processed_input",
                    "ai_models": None,
                    "parallel": False,
                },
                {
                    "id": "step_2_generate",
                    "name": "生成阶段",
                    "type": "generation",
                    "description": "生成内容",
                    "input_fields": ["processed_input"],
                    "output_field": "generated_output",
                    "ai_models": ["qianwen", "zhipu"],
                    "parallel": True,
                },
            ],
            "max_parallel_steps": 3,
            "allow_parallel": True,
        },
        "quality_metrics": {
            "metrics": {
                "accuracy": {
                    "description": "准确性",
                    "check_method": "fact_check",
                    "weight": 0.5,
                    "min_threshold": 0.8,
                },
                "quality": {
                    "description": "质量",
                    "check_method": "quality_check",
                    "weight": 0.5,
                    "min_threshold": 0.8,
                },
            },
            "normalization_method": "linear",
            "validation_tolerance": 0.01,
        },
        "example_library": {
            "good_examples": [],
            "bad_examples": [],
            "few_shot_template": "输入: {input}\n输出: {output}",
        },
        "generation_params": {
            "diversity_enhancement": True,
            "output_versions": 3,
            "diversity_dimensions": ["emotional_tone", "narrative_style"],
            "confidence_display": True,
            "critical_facts_only": True,
            "temperature": 0.7,
            "output_format": "text",
            "require_code_blocks": False,
        },
        "optimization": {
            "enabled": True,
            "strategy": "feedback_driven",
            "auto_refine_threshold": 60.0,
            "periodic_review_days": 30,
            "allowed_actions": ["auto_refine_low_scoring"],
        },
        "performance_tracking": {
            "enabled": True,
            "metrics": ["execution_time", "generation_success_rate"],
            "retention_days": 90,
            "post_publish_tracking": None,
        },
        "collaboration": {
            "shared_with": [],
            "edit_permission": [],
            "use_permission": [],
            "is_public": False,
        },
        "system_prompt": f"你是一个专业的{category}助手，能够提供高质量的帮助。",
        "quality_validation_rules": "1. 输出内容准确\n2. 格式规范\n3. 语言流畅",
    }

    # 保存模板到 packs/examples/
    examples_dir = Path(packs_root) / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    output_path = examples_dir / f"{template['metadata']['pack_id']}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print("\n✓ Pack 模板已生成")
    print(f"  名称: {pack_name}")
    print(f"  类别: {category}")
    print(f"  保存路径: {output_path}")
    print("\n请编辑模板以定制您的 Pack")

    return 0


def _handle_export_command(args, packs_root, workspace):
    """处理 Pack 导出命令"""
    source_pack = args.source  # Pack 名称或路径
    output_dir = getattr(args, "output", None) or "packs/exports"

    # 判断是 Pack 名称还是文件路径
    source_path = Path(source_pack)
    if source_path.exists() and source_path.is_file():
        # 直接导出文件
        pack_file = source_path
        pack_name = source_path.stem
    else:
        # 从 packs/ 目录查找
        PackManager(Path(packs_root))

        # 先查找 examples 目录
        examples_dir = Path(packs_root) / "examples"

        # 如果源已带 .json，检查文件直接存在
        pack_file = None
        if source_pack.endswith(".json"):
            pack_file = examples_dir / source_pack
            if not pack_file.exists():
                pack_file = None

        # 如果没找到，搜索所有 .json 文件
        if not pack_file or not pack_file.exists():
            target_stem = source_pack
            if target_stem.endswith(".json"):
                target_stem = target_stem[:-5]

            # 在 examples 目录搜索
            for pattern in ["*.json", "**/*.json"]:
                found = list(examples_dir.rglob(pattern))
                for f in found:
                    if f.stem == target_stem:
                        pack_file = f
                        break
                if pack_file and pack_file.exists():
                    break

        if not pack_file or not pack_file.exists():
            print(f"\n✗ 错误: 找不到 Pack '{source_pack}'")
            print(f"  搜索路径: {examples_dir}")
            available = list(examples_dir.glob("*.json"))
            if available:
                print(f"  可用的 Pack 文件: {', '.join([f.stem for f in available])}")
            return 1

        pack_name = pack_file.stem

    # 创建输出目录
    export_dir = Path(output_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    # 创建导出文件名（带时间戳）
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = export_dir / f"{pack_name}_export_{timestamp}.json"

    # 复制文件
    import shutil

    shutil.copy2(pack_file, export_file)

    print("\n✓ Pack 已导出")
    print(f"  源: {pack_file}")
    print(f"  目标: {export_file}")
    print(f"  大小: {export_file.stat().st_size} 字节")

    return 0


def _handle_import_command(args, packs_root, workspace):
    """处理 Pack 导入命令"""
    source_file = Path(args.source)

    if not source_file.exists():
        print(f"\n✗ 错误: 源文件不存在: {source_file}")
        return 1

    print(f"\n导入 Pack: {source_file}")
    print("=" * 60)

    # 验证 JSON 格式
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("✓ JSON 格式正确")
    except json.JSONDecodeError as e:
        print(f"✗ JSON 格式错误: {e}")
        return 1

    # 获取 Pack 信息
    pack_id = data.get("metadata", {}).get("pack_id", "unknown")
    pack_name = data.get("metadata", {}).get("pack_name", "Unknown Pack")

    # 确定目标目录
    target_dir = getattr(args, "target", "examples")
    dest_dir = Path(packs_root) / target_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / f"{pack_id}.json"

    # 检查是否已存在
    if dest_file.exists():
        overwrite = getattr(args, "force", False)
        if not overwrite:
            print(f"\n⚠  Pack '{pack_id}' 已存在于目标目录")
            print(f"  目标路径: {dest_file}")
            print("  使用 --force 参数覆盖")
            return 1
        print("  覆盖现有文件")

    # 复制文件
    import shutil

    shutil.copy2(source_file, dest_file)

    print("\n✓ Pack 导入成功")
    print(f"  Pack ID: {pack_id}")
    print(f"  Pack 名称: {pack_name}")
    print(f"  目标路径: {dest_file}")

    return 0


def _handle_sharing_command(args, packs_root):
    """处理权限管理命令"""
    from ai_collab.prompt_pack.sharing import PermissionLevel, create_permission_manager

    perm_manager = create_permission_manager("packs", packs_root, args.user or "owner")

    if args.share_subcommand == "grant":
        if not all([args.name, args.target_user, args.level]):
            print("\n错误: 需要 --name, --target-user, --level 参数")
            return 1

        level_map = {
            "read": PermissionLevel.READ,
            "write": PermissionLevel.WRITE,
            "admin": PermissionLevel.ADMIN,
        }
        level = level_map.get(args.level, PermissionLevel.READ)

        try:
            perm_manager.grant_permission(args.name, args.target_user, level)
            print(f"\n✓ 已授予 {args.target_user} {args.level.value} 权限")
        except PermissionError as e:
            print(f"\n✗ 权限错误: {e}")
            return 1

    elif args.share_subcommand == "revoke":
        if not all([args.name, args.target_user]):
            print("\n错误: 需要 --name 和 --target-user 参数")
            return 1

        result = perm_manager.revoke_permission(args.name, args.target_user)
        if result:
            print(f"\n✓ 已撤销 {args.target_user} 的权限")
        else:
            print("\n✗ 权限不存在")

    elif args.share_subcommand == "list":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        perms = perm_manager.get_user_permissions(args.name)
        print(f"\nPack '{args.name}' 权限信息:")
        print(f"  拥有者: {perms['is_owner']}")
        print(f"  读取权限: {perms['has_read']}")
        print(f"  写入权限: {perms['has_write']}")
        print(f"  管理权限: {perms['has_admin']}")
        if perms.get("permission_level"):
            print(f"  权限级别: {perms['permission_level']}")
        if perms.get("team"):
            print(f"  所属团队: {perms['team']}")

    elif args.share_subcommand == "public":
        if not args.name:
            print("\n错误: 需要 --name 参数")
            return 1

        is_public = args.set_public.lower() in ["true", "yes", "1"]
        perm_manager.set_pack_public(args.name, is_public)
        status = "公开" if is_public else "私密"
        print(f"\n✓ Pack '{args.name}' 已设置为 {status}")

    return 0


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="AI 协作开发系统 - Claude Code + GitHub Copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 激活 Claude Code
  ai-collab activate --ai claude

  # 检查文件冲突
  ai-collab check --ai claude --files src/api.ts

  # 初始化项目
  ai-collab init

  # 查看系统状态
  ai-collab status

  # 查看活跃任务
  ai-collab tasks list --status active

  # 极简派单
  ai-collab 2x claude
  ai-collab 2x codearts
  ai-collab 2x all

  # Prompt Pack 版本管理
  ai-collab pack bump --name demo-pack --type patch
  ai-collab pack history --name demo-pack

  # 兼容性检查
  ai-collab pack check-version --source 1.0.0 --target 1.1.0

  # Pack 商店
  ai-collab pack search --query "demo"
  ai-collab pack browse --category domain
  ai-collab pack trending

  # 评分系统
  ai-collab pack add-rating --name demo-pack --rating 5 --title "很棒"

  # 权限管理
  ai-collab pack grant-perm --name demo-pack --user bob --level write
        """,
    )

    parser.add_argument("-w", "--workspace", help="工作区路径")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 2.0.0")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # activate 命令
    activate_parser = subparsers.add_parser("activate", help="激活 AI 协作系统")
    activate_parser.add_argument(
        "--ai",
        choices=["claude", "claude_code", "copilot", "codearts_agent", "codex"],
        default="claude",
        help="AI 类型",
    )
    activate_parser.add_argument(
        "--mode", choices=["cli", "command", "event", "on_save"], default="cli", help="激活模式"
    )
    activate_parser.add_argument("--input", help="自定义激活输入")
    activate_parser.add_argument("--show-rules", action="store_true", help="显示规则内容")

    # check 命令
    check_parser = subparsers.add_parser("check", help="检查文件冲突")
    check_parser.add_argument(
        "--ai", choices=["claude", "copilot", "codearts_agent", "codex"], help="检查的 AI 类型"
    )
    check_parser.add_argument("--files", nargs="*", help="要检查的文件列表")
    check_parser.add_argument(
        "--mode", choices=["on_save", "command", "both"], default="both", help="检查模式"
    )
    check_parser.add_argument("--resolve", action="store_true", help="自动标记冲突")

    # tasks 命令
    tasks_parser = subparsers.add_parser("tasks", help="任务管理")
    tasks_parser.add_argument(
        "subcommand",
        choices=[
            "list",
            "register",
            "update",
            "takeover",
            "repair-assignee",
            "validate-contract",
            "audit-result-consistency",
            "migrate-contract",
        ],
        help="子命令",
    )
    tasks_parser.add_argument(
        "--status",
        choices=[
            "all",
            "active",
            "completed",
            "pending",
            "planning",
            "in_progress",
            "implementing",
            "testing",
            "blocked",
            "failed",
            "cancelled",
        ],
        default="active",
        help="任务状态过滤",
    )
    tasks_parser.add_argument("--task-id", help="任务ID")
    tasks_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codearts_agent", "codex"], help="AI 类型"
    )
    tasks_parser.add_argument("--description", help="任务描述")
    tasks_parser.add_argument("--files", nargs="*", help="涉及文件")
    tasks_parser.add_argument("--note", help="备注")
    tasks_parser.add_argument("--owner", help="接管后 owner（takeover 专用）")
    tasks_parser.add_argument("--reason", help="接管/修复原因（takeover/repair-assignee 专用）")
    tasks_parser.add_argument("--change-id", help="关联 OpenSpec change_id 或 bugfix/no-spec")
    tasks_parser.add_argument("--assignee", help="任务执行者（register 默认与 --ai 一致；repair-assignee 必填）")
    tasks_parser.add_argument("--reviewer", help="任务审核者")
    tasks_parser.add_argument("--primary-skill", help="主技能标识")
    tasks_parser.add_argument("--support-skills", nargs="*", help="支持技能列表")
    tasks_parser.add_argument("--acceptance-commands", nargs="*", help="验收命令列表")
    tasks_parser.add_argument("--result-file", help="结果文件路径")
    tasks_parser.add_argument("--report", help="审计报告路径（audit-result-consistency 专用）")
    tasks_parser.add_argument("--summary", help="审计摘要路径（audit-result-consistency 专用）")
    tasks_parser.add_argument(
        "--scope",
        choices=["active", "all"],
        default=None,
        help="契约校验/迁移范围（validate-contract/migrate-contract）",
    )
    tasks_parser.add_argument("--strict", action="store_true", help="契约校验失败时返回非零状态码")
    tasks_parser.add_argument("--dry-run", action="store_true", help="迁移任务契约时仅预览不落盘")
    tasks_parser.add_argument("--default-change-id", help="迁移任务契约时使用的默认 change_id")
    tasks_parser.add_argument("--migration-reviewer", help="迁移任务契约时使用的默认 reviewer")

    # sessions 命令
    sessions_parser = subparsers.add_parser("sessions", help="会话注册表与控制面基线")
    sessions_parser.add_argument(
        "subcommand",
        choices=[
            "register",
            "refresh",
            "inspect",
            "health",
            "interventions",
            "intervention-pack",
            "closeout-queue",
            "auto-sync",
            "claude-push",
            "codearts-pull",
            "codex-adapter",
            "handoff",
        ],
        help="子命令",
    )
    sessions_parser.add_argument("--session-id", help="会话 ID")
    sessions_parser.add_argument(
        "--assignee", choices=["claude_code", "codearts_agent", "codex"], help="会话 assignee"
    )
    sessions_parser.add_argument("--transport-mode", choices=["manual", "bridge"], help="传输模式")
    sessions_parser.add_argument("--session-status", help="会话状态，例如 active/idle/blocked")
    sessions_parser.add_argument("--health-status", help="健康状态，例如 healthy/unhealthy")
    sessions_parser.add_argument("--last-handoff-artifact", help="最近一次 handoff / payload 工件路径")
    sessions_parser.add_argument(
        "--reason-code", help="intervention reason_code 过滤（interventions 子命令专用）"
    )
    sessions_parser.add_argument(
        "--delivery-status", help="intervention delivery_status 过滤（interventions 子命令专用）"
    )
    sessions_parser.add_argument(
        "--pack-dir", help="intervention pack 输出目录（intervention-pack 子命令专用）"
    )
    sessions_parser.add_argument("--state", help="registry state 路径（相对 workspace）")
    sessions_parser.add_argument("--history", help="history 路径（相对 workspace）")
    sessions_parser.add_argument("--summary", help="summary 路径（相对 workspace）")
    sessions_parser.add_argument("--report", help="report 路径（相对 workspace）")
    sessions_parser.add_argument("--runtime-path", help="Codex runtime 路径（codex-adapter 子命令专用）")
    sessions_parser.add_argument("--artifact-dir", help="intervention artifact 输出目录（health 子命令专用）")
    sessions_parser.add_argument(
        "--event-dir", help="adapter event 输出目录（claude-push/codearts-pull 子命令专用）"
    )
    sessions_parser.add_argument("--output-dir", help="handoff 输出目录（handoff 子命令专用）")
    sessions_parser.add_argument("--objective", help="handoff 的当前目标摘要")
    sessions_parser.add_argument("--next-slice", help="handoff 的下一步建议")
    sessions_parser.add_argument("--completed-item", action="append", help="handoff 已完成事项，可重复传入")
    sessions_parser.add_argument("--validation-command", action="append", help="handoff 验证命令，可重复传入")
    sessions_parser.add_argument("--related-file", action="append", help="handoff 相关文件，可重复传入")
    sessions_parser.add_argument(
        "--no-interventions", action="store_true", help="仅聚合健康状态，不写 intervention queue"
    )
    sessions_parser.add_argument(
        "--only-open", action="store_true", help="仅显示 open interventions（interventions 子命令专用）"
    )
    sessions_parser.add_argument(
        "--include-closed", action="store_true", help="intervention-pack 包含 closed interventions"
    )
    sessions_parser.add_argument(
        "--dry-run", action="store_true", help="仅生成报告/工件，不推进实际 delivery 状态"
    )
    sessions_parser.add_argument("--json", action="store_true", help="输出 JSON")

    # ack 命令
    ack_parser = subparsers.add_parser("ack", help="输出标准 ACK 协议行")
    ack_parser.add_argument("--task-id", required=True, help="任务 ID；无任务时可用 none")
    ack_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codearts_agent", "codex"], help="AI 类型"
    )
    ack_parser.add_argument(
        "--status",
        choices=["ok", "blocked", "noop", "completed"],
        help="ACK 状态（默认根据任务状态推断）",
    )
    ack_parser.add_argument("--result-file", help="结果文件路径（默认从任务状态推断）")

    ack_remediation_parser = subparsers.add_parser(
        "ack-remediation", help="审计并标记历史非显式 ACK bridge 残留"
    )
    ack_remediation_parser.add_argument(
        "--dry-run", action="store_true", help="仅检测，不写回 ACK bridge 状态"
    )
    ack_remediation_parser.add_argument("--task-id", help="仅处理指定任务 ID")
    ack_remediation_parser.add_argument("--report", help="报告路径（相对 workspace）")
    ack_remediation_parser.add_argument("--summary", help="摘要路径（相对 workspace）")
    ack_remediation_parser.add_argument("--state", help="ACK bridge 状态路径（相对 workspace）")

    # patches 命令
    patches_parser = subparsers.add_parser("patches", help="Patch 管理")
    patches_parser.add_argument(
        "subcommand", choices=["list", "create", "update", "assign", "claim"], help="子命令"
    )
    patches_parser.add_argument("--patch-id", help="Patch ID")
    patches_parser.add_argument("--task-id", help="关联任务ID")
    patches_parser.add_argument(
        "--status",
        choices=["all", "pending", "in_progress", "completed", "blocked", "cancelled"],
        default="all",
        help="Patch 状态过滤",
    )
    patches_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codex", "codearts_agent"], help="AI 类型"
    )
    patches_parser.add_argument("--title", help="Patch 标题")
    patches_parser.add_argument("--description", help="Patch 描述")
    patches_parser.add_argument("--files", nargs="*", help="涉及文件")
    patches_parser.add_argument("--note", help="备注")

    # conflicts 命令
    conflicts_parser = subparsers.add_parser("conflicts", help="冲突管理")
    conflicts_parser.add_argument("subcommand", choices=["list", "resolve"], help="子命令")
    conflicts_parser.add_argument("--status", choices=["open", "resolved"], help="状态过滤")
    conflicts_parser.add_argument("--conflict-id", help="冲突ID")
    conflicts_parser.add_argument("--resolution", help="解决方案")

    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="日志管理")
    logs_parser.add_argument("subcommand", choices=["list", "show"], help="子命令")
    logs_parser.add_argument(
        "--ai", choices=["claude-code", "codearts-agent", "copilot"], help="AI 类型"
    )
    logs_parser.add_argument("--month", help="月份过滤 (YYYY-MM)")
    logs_parser.add_argument("--log-file", help="日志文件名")

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    # 兼容写法：允许 `ai-collab init --workspace .`（全局 `-w/--workspace` 仍可用）
    init_parser.add_argument("--workspace", help="工作区路径（兼容写法，可放在 init 后）")

    # clean 命令
    clean_parser = subparsers.add_parser("clean", help="清理旧日志")
    clean_parser.add_argument("--max-files", type=int, default=30, help="保留日志文件数")
    clean_parser.add_argument("--days", type=int, help="保留任务天数")

    # status 命令
    status_parser = subparsers.add_parser("status", help="显示系统状态")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # codex 命令
    codex_parser = subparsers.add_parser("codex", help="CC Claude Codex 集成")
    codex_parser.add_argument(
        "subcommand",
        choices=["init", "progress", "run", "exec", "sync", "plan", "hooks"],
        help="子命令",
    )
    codex_parser.add_argument("--goal", help="任务目标（init/progress/exec）")
    codex_parser.add_argument("--intent", help="操作人意图（用于动态角色编排）")
    codex_parser.add_argument("--operator", default="user", help="操作人标识（默认 user）")
    codex_parser.add_argument("--model", action="append", help="参与模型（可重复）")
    codex_parser.add_argument("--force-lead", help="强制指定主导 agent")
    codex_parser.add_argument("--emit-tasks", action="store_true", help="将角色计划自动落成并行任务")
    codex_parser.add_argument("--emit-patches", action="store_true", help="将角色计划自动落成并行 patch")
    codex_parser.add_argument("--context", help="任务上下文（init）")
    codex_parser.add_argument("--step", action="append", help="执行步骤（可重复）")
    codex_parser.add_argument("--steps-file", help="步骤文件（每行一个步骤）")
    codex_parser.add_argument("--tech-stack", help="技术栈约束")
    codex_parser.add_argument("--follow", help="遵循的模式")
    codex_parser.add_argument("--avoid", help="避免的模式")
    codex_parser.add_argument("--file", action="append", help="相关文件（可重复）")
    codex_parser.add_argument("--test-cmd", help="测试命令")
    codex_parser.add_argument("--readonly", action="store_true", help="只读模式运行 codex")
    codex_parser.add_argument("--max-timeout", type=int, help="最大执行超时（秒）")
    codex_parser.add_argument("--stale-timeout", type=int, help="无日志活动超时（秒）")
    codex_parser.add_argument("--sandbox", help="覆盖 sandbox 模式")
    codex_parser.add_argument("--sync", action="store_true", help="run 后同步到 ai_collab 状态")
    codex_parser.add_argument("--task-id", help="同步状态时使用的任务ID")
    codex_parser.add_argument(
        "--hook-action",
        "--action",
        dest="hook_action",
        choices=["install", "status", "uninstall", "doctor"],
        help="hooks 子命令动作",
    )

    # controller 命令
    controller_parser = subparsers.add_parser("controller", help="工单控制器（常驻轮询）")
    controller_parser.add_argument("--once", action="store_true", help="仅执行一轮")
    controller_parser.add_argument("--dry-run", action="store_true", help="仅检测，不修改状态")
    controller_parser.add_argument("--interval-sec", type=int, help="轮询间隔（秒）")
    controller_parser.add_argument("--max-iterations", type=int, help="最大迭代次数（0 或不填表示无限）")
    controller_parser.add_argument(
        "--pending-timeout-sec", type=int, help="pending/planning 超时阈值（秒）"
    )
    controller_parser.add_argument(
        "--active-timeout-sec", type=int, help="implementing/testing 超时阈值（秒）"
    )
    controller_parser.add_argument("--blocked-timeout-sec", type=int, help="blocked 超时阈值（秒）")
    controller_parser.add_argument("--prewarn-ratio", type=float, help="预警阈值比例（0.1-0.95）")
    controller_parser.add_argument("--default-assignee", help="自动补丁默认执行者")
    controller_parser.add_argument("--report", help="报告路径（相对 workspace）")
    controller_parser.add_argument("--history", help="历史快照路径（相对 workspace）")

    # dispatch 命令
    dispatch_parser = subparsers.add_parser("dispatch", help="自动派单桥接（生成 Agent 执行指令包）")
    dispatch_parser.add_argument("--dry-run", action="store_true", help="仅生成报告与指令包，不写派单状态")
    dispatch_parser.add_argument(
        "--include-pending", action="store_true", help="将 pending 任务纳入派发候选"
    )
    dispatch_parser.add_argument("--redispatch", action="store_true", help="允许重复派发已派发过的任务")
    dispatch_parser.add_argument("--report", help="报告路径（相对 workspace）")
    dispatch_parser.add_argument("--history", help="历史快照路径（相对 workspace）")
    dispatch_parser.add_argument("--state", help="派单状态路径（相对 workspace）")
    dispatch_parser.add_argument("--orders", help="派单指令包路径（相对 workspace）")
    dispatch_parser.add_argument("--force-workspace", action="store_true", help="忽略工作区门禁并强制执行（高风险）")

    # trigger 命令
    trigger_parser = subparsers.add_parser("trigger", help="暗语触发派单（2X DISPATCH）")
    trigger_parser.add_argument(
        "--phrase", required=True, help="暗语，例如: '2X DISPATCH' 或 '2X DISPATCH CLAUDE'"
    )
    trigger_parser.add_argument(
        "--target",
        choices=["all", "claude_code", "codearts_agent", "codex"],
        help="覆盖暗语中的目标（默认取暗语）",
    )
    trigger_parser.add_argument("--dry-run", action="store_true", help="透传到 dispatch --dry-run")
    trigger_parser.add_argument(
        "--include-pending", action="store_true", help="透传到 dispatch --include-pending"
    )
    trigger_parser.add_argument(
        "--redispatch", action="store_true", help="透传到 dispatch --redispatch"
    )
    trigger_parser.add_argument("--dispatch-report", help="透传到 dispatch --report")
    trigger_parser.add_argument("--dispatch-history", help="透传到 dispatch --history")
    trigger_parser.add_argument("--dispatch-state", help="透传到 dispatch --state")
    trigger_parser.add_argument("--dispatch-orders", help="透传到 dispatch --orders")
    trigger_parser.add_argument(
        "--force-workspace", action="store_true", help="透传到 dispatch --force-workspace"
    )
    trigger_parser.add_argument("--output-dir", help="会话派单文件输出目录（相对 workspace）")
    trigger_parser.add_argument("--report", help="trigger 报告路径（相对 workspace）")
    trigger_parser.add_argument("--history", help="trigger 历史路径（相对 workspace）")
    trigger_parser.add_argument("--copy", action="store_true", help="将单目标派单内容复制到剪贴板（macOS pbcopy）")

    # 2x 快捷命令
    quick_2x_parser = subparsers.add_parser("2x", help="极简派单入口：2x claude/codearts/codex/all")
    quick_2x_parser.add_argument(
        "target",
        choices=["claude", "codearts", "codex", "all", "c", "a", "x"],
        help="快捷目标",
    )
    quick_2x_parser.add_argument("--dry-run", action="store_true", help="透传到 trigger --dry-run")
    quick_2x_parser.add_argument(
        "--include-pending", action="store_true", help="透传到 trigger --include-pending"
    )
    quick_2x_parser.add_argument(
        "--redispatch", action="store_true", help="透传到 trigger --redispatch"
    )
    quick_2x_parser.add_argument("--no-copy", action="store_true", help="单目标时禁用自动复制剪贴板")
    quick_2x_parser.add_argument("--dispatch-only", action="store_true", help="禁用智能收口，仅执行派单逻辑")
    quick_2x_parser.add_argument("--force-workspace", action="store_true", help="透传工作区门禁覆盖参数（高风险）")

    # receipt 命令
    receipt_parser = subparsers.add_parser("receipt", help="自动回执桥接（testing -> completed）")
    receipt_parser.add_argument("--dry-run", action="store_true", help="仅检测，不更新任务状态")
    receipt_parser.add_argument("--reclose", action="store_true", help="允许重复处理已回执任务")
    receipt_parser.add_argument("--report", help="报告路径（相对 workspace）")
    receipt_parser.add_argument("--history", help="历史快照路径（相对 workspace）")
    receipt_parser.add_argument("--state", help="回执状态路径（相对 workspace）")
    receipt_parser.add_argument("--summary", help="回执摘要路径（相对 workspace）")
    receipt_parser.add_argument("--force-workspace", action="store_true", help="忽略工作区门禁并强制执行（高风险）")

    # run 命令
    run_parser = subparsers.add_parser("run", help="标准 RUN 流程：dispatch -> receipt -> benefit")
    run_parser.add_argument(
        "--dry-run", action="store_true", help="透传 dry-run 到 dispatch/receipt/benefit"
    )
    run_parser.add_argument(
        "--include-pending", action="store_true", help="透传到 dispatch --include-pending"
    )
    run_parser.add_argument("--redispatch", action="store_true", help="透传到 dispatch --redispatch")
    run_parser.add_argument("--reclose", action="store_true", help="透传到 receipt --reclose")
    run_parser.add_argument("--force-workspace", action="store_true", help="忽略工作区门禁并强制执行（高风险）")
    run_parser.add_argument("--dispatch-report", help="透传到 dispatch --report")
    run_parser.add_argument("--dispatch-history", help="透传到 dispatch --history")
    run_parser.add_argument("--dispatch-state", help="透传到 dispatch --state")
    run_parser.add_argument("--dispatch-orders", help="透传到 dispatch --orders")
    run_parser.add_argument("--receipt-report", help="透传到 receipt --report")
    run_parser.add_argument("--receipt-history", help="透传到 receipt --history")
    run_parser.add_argument("--receipt-state", help="透传到 receipt --state")
    run_parser.add_argument("--receipt-summary", help="透传到 receipt --summary")
    run_parser.add_argument(
        "--benefit-dispatch-history", action="append", help="透传到 benefit --dispatch-history"
    )
    run_parser.add_argument(
        "--benefit-receipt-history", action="append", help="透传到 benefit --receipt-history"
    )
    run_parser.add_argument("--target-ratio", type=float, help="透传到 benefit --target-ratio")
    run_parser.add_argument("--window", type=int, help="透传到 benefit --window")
    run_parser.add_argument("--benefit-report", help="透传到 benefit --report")
    run_parser.add_argument("--benefit-output", help="透传到 benefit --output")

    # workspace-guard 命令
    workspace_guard_parser = subparsers.add_parser("workspace-guard", help="工作区门禁诊断（阈值+分域）")
    workspace_guard_parser.add_argument("--dry-run", action="store_true", help="按 dry-run 模式评估门禁")
    workspace_guard_parser.add_argument(
        "--for-command", default="workspace-guard", help="门禁评估的命令上下文名"
    )
    workspace_guard_parser.add_argument("--force-workspace", action="store_true", help="模拟强制覆盖门禁")

    spawn_guard_parser = subparsers.add_parser("spawn-agent-guard", help="Codex spawn_agent 前置门禁诊断")
    spawn_guard_parser.add_argument("--actor", default="codex", help="委派发起者，默认 codex")
    spawn_guard_parser.add_argument("--parent-task", help="父任务 ID（例如 TASK-XXX）")
    spawn_guard_parser.add_argument("--files", nargs="*", default=[], help="写入委派涉及的文件列表")
    spawn_guard_parser.add_argument("--read-only", action="store_true", help="声明为只读委派，允许空写集")
    spawn_guard_parser.add_argument("--report", help="覆盖 spawnAgentGuard.report")
    spawn_guard_parser.add_argument("--history", help="覆盖 spawnAgentGuard.history")

    # hygiene 命令
    hygiene_parser = subparsers.add_parser("hygiene", help="工作区/暂存区自动治理（可一次执行或轮询）")
    hygiene_parser.add_argument("--dry-run", action="store_true", help="仅预览治理结果，不执行暂存")
    hygiene_parser.add_argument("--loop", action="store_true", help="进入周期轮询模式")
    hygiene_parser.add_argument(
        "--interval-sec", type=int, help="轮询间隔秒数（默认读取 workspaceHygiene.pollIntervalMinutes）"
    )
    hygiene_parser.add_argument("--max-iterations", type=int, default=0, help="最大迭代次数（0 表示无限）")
    hygiene_parser.add_argument("--include-source", action="store_true", help="将 source 域纳入治理顺序")
    hygiene_parser.add_argument(
        "--auto-stage", dest="auto_stage", action="store_true", help="显式开启 apply 暂存（覆盖配置）"
    )
    hygiene_parser.add_argument(
        "--no-auto-stage", dest="auto_stage", action="store_false", help="显式关闭 apply 暂存（覆盖配置）"
    )
    hygiene_parser.set_defaults(auto_stage=None)
    hygiene_parser.add_argument("--max-candidates", type=int, help="单轮候选上限（超过则阻断）")
    hygiene_parser.add_argument("--force-workspace", action="store_true", help="忽略工作区门禁并强制执行（高风险）")
    hygiene_parser.add_argument("--trigger-source", default="manual", help="触发来源标识（用于审计日志）")

    # stage 命令（分域安全暂存）
    stage_source_parser = subparsers.add_parser("stage-source", help="按 source 域安全暂存（替代 git add .）")
    stage_source_parser.add_argument("--dry-run", action="store_true", help="仅预览候选文件，不执行暂存")

    stage_ops_parser = subparsers.add_parser(
        "stage-ops", help="按 ops 域安全暂存（results/monitoring/logs）"
    )
    stage_ops_parser.add_argument("--dry-run", action="store_true", help="仅预览候选文件，不执行暂存")

    stage_docs_parser = subparsers.add_parser("stage-docs", help="按 docs 域安全暂存（文档/研究/规范）")
    stage_docs_parser.add_argument("--dry-run", action="store_true", help="仅预览候选文件，不执行暂存")
    stage_other_parser = subparsers.add_parser("stage-other", help="按 other 域安全暂存（其余残留变更）")
    stage_other_parser.add_argument("--dry-run", action="store_true", help="仅预览候选文件，不执行暂存")
    stage_safe_parser = subparsers.add_parser(
        "stage-safe", help="一键分域安全暂存（默认 ops->docs->other，先预览再执行）"
    )
    stage_safe_parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行暂存")
    stage_safe_parser.add_argument(
        "--include-source", action="store_true", help="将 source 域加入序列（source->ops->docs->other）"
    )

    # benefit 命令
    benefit_parser = subparsers.add_parser("benefit", help="自动化收益看板（>3 目标追踪）")
    benefit_parser.add_argument("--dry-run", action="store_true", help="仅计算，不写报告与看板文件")
    benefit_parser.add_argument("--dispatch-history", action="append", help="dispatch 历史路径（可重复）")
    benefit_parser.add_argument("--receipt-history", action="append", help="receipt 历史路径（可重复）")
    benefit_parser.add_argument("--target-ratio", type=float, help="目标效率比阈值")
    benefit_parser.add_argument("--window", type=int, help="展示最近 N 天")
    benefit_parser.add_argument("--report", help="报告路径（相对 workspace）")
    benefit_parser.add_argument("--output", help="看板路径（相对 workspace）")

    # pack 命令 - 结构化为嵌套子命令
    pack_parser = subparsers.add_parser("pack", help="Prompt Pack 管理")
    pack_subparsers = pack_parser.add_subparsers(dest="subcommand", help="Pack 子命令")

    # pack list
    list_parser = pack_subparsers.add_parser("list", help="列出可用 Pack")
    list_parser.add_argument(
        "--category", choices=["domain", "project", "stage", "role"], help="按类别过滤"
    )

    # pack show
    show_parser = pack_subparsers.add_parser("show", help="显示 Pack 详情")
    show_parser.add_argument("--name", required=True, help="Pack 名称")
    show_parser.add_argument(
        "--tool",
        choices=["claude_code", "github_copilot", "codex_agent", "codearts_agent"],
        help="目标 AI 工具",
    )
    show_parser.add_argument("--context", action="store_true", help="显示上下文字符串")

    # pack activate
    activate_parser = pack_subparsers.add_parser("activate", help="激活 Pack")
    activate_parser.add_argument("--name", required=True, help="Pack 名称")
    activate_parser.add_argument(
        "--tool",
        choices=["claude_code", "github_copilot", "codex_agent", "codearts_agent"],
        help="目标 AI 工具",
    )

    # pack recommend
    recommend_parser = pack_subparsers.add_parser("recommend", help="推荐 Pack")
    recommend_parser.add_argument("--description", required=True, help="任务描述")
    recommend_parser.add_argument(
        "--tool",
        choices=["claude_code", "github_copilot", "codex_agent", "codearts_agent"],
        help="目标 AI 工具",
    )

    # pack version 子命令
    version_parser = pack_subparsers.add_parser("version", help="版本管理")
    version_subparsers = version_parser.add_subparsers(dest="version_subcommand", help="版本子命令")

    bump_parser = version_subparsers.add_parser("bump", help="升级版本")
    bump_parser.add_argument("--name", required=True, help="Pack 名称")
    bump_parser.add_argument(
        "--type", choices=["major", "minor", "patch"], default="patch", help="版本类型"
    )

    history_parser = version_subparsers.add_parser("history", help="查看版本历史")
    history_parser.add_argument("--name", required=True, help="Pack 名称")

    # pack check-compat 子命令
    check_parser = pack_subparsers.add_parser("check-compat", help="兼容性检查")
    check_parser.add_argument("--source", required=True, help="源版本号")
    check_parser.add_argument("--target", required=True, help="目标版本号")

    # pack store 子命令
    store_parser = pack_subparsers.add_parser("search", help="搜索 Pack")
    store_parser.add_argument("--query", default="", help="搜索查询")
    store_parser.add_argument(
        "--sort",
        default="popularity",
        choices=["popularity", "rating", "newest", "name", "downloads"],
        help="排序方式",
    )
    store_parser.add_argument("--limit", type=int, default=20, help="结果数量限制")

    browse_parser = pack_subparsers.add_parser("browse", help="按类别浏览")
    browse_parser.add_argument(
        "--category", required=True, choices=["domain", "project", "stage", "role"], help="类别"
    )
    browse_parser.add_argument(
        "--sort",
        default="popularity",
        choices=["popularity", "rating", "newest", "name", "downloads"],
        help="排序方式",
    )

    trending_parser = pack_subparsers.add_parser("trending", help="热门 Pack")
    trending_parser.add_argument("--limit", type=int, default=10, help="数量限制")

    # pack rate 子命令
    rate_parser = pack_subparsers.add_parser("rate", help="评分系统")
    rate_subparsers = rate_parser.add_subparsers(dest="rating_subcommand", help="评分子命令")

    add_rating_parser = rate_subparsers.add_parser("add", help="添加评分")
    add_rating_parser.add_argument("--name", required=True, help="Pack 名称")
    add_rating_parser.add_argument("--user", required=True, help="用户名")
    add_rating_parser.add_argument(
        "--rating", required=True, type=int, choices=[1, 2, 3, 4, 5], help="评分"
    )
    add_rating_parser.add_argument("--title", required=True, help="标题")
    add_rating_parser.add_argument("--content", help="内容")

    list_ratings_parser = rate_subparsers.add_parser("list", help="查看评分")
    list_ratings_parser.add_argument("--name", required=True, help="Pack 名称")
    list_ratings_parser.add_argument("--detailed", action="store_true", help="详细信息")

    # pack share 子命令
    share_parser = pack_subparsers.add_parser("share", help="权限管理")
    share_subparsers = share_parser.add_subparsers(dest="share_subcommand", help="共享子命令")

    grant_parser = share_subparsers.add_parser("grant", help="授予权限")
    grant_parser.add_argument("--name", required=True, help="Pack 名称")
    grant_parser.add_argument("--user", dest="target_user", required=True, help="目标用户")
    grant_parser.add_argument(
        "--level", required=True, choices=["read", "write", "admin"], help="权限级别"
    )
    grant_parser.add_argument("--as-user", help="以该用户身份操作")

    revoke_parser = share_subparsers.add_parser("revoke", help="撤销权限")
    revoke_parser.add_argument("--name", required=True, help="Pack 名称")
    revoke_parser.add_argument("--user", dest="target_user", required=True, help="目标用户")

    list_perms_parser = share_subparsers.add_parser("list", help="查看权限")
    list_perms_parser.add_argument("--name", required=True, help="Pack 名称")

    public_parser = share_subparsers.add_parser("public", help="设置公开展示")
    public_parser.add_argument("--name", required=True, help="Pack 名称")
    public_parser.add_argument(
        "--set", required=True, choices=["true", "false"], help="true=公开, false=私密"
    )

    # pack validate
    validate_parser = pack_subparsers.add_parser("validate", help="验证 Pack 文件")
    validate_parser.add_argument("--path", required=True, help="Pack 文件路径")

    # pack template
    template_parser = pack_subparsers.add_parser("template", help="生成 Pack 模板")
    template_parser.add_argument("--name", required=True, help="Pack 名称")
    template_parser.add_argument("--category", required=True, help="Pack 类别")

    # pack export
    export_parser = pack_subparsers.add_parser("export", help="导出 Pack")
    export_parser.add_argument("--source", required=True, help="源 Pack 名称或路径")
    export_parser.add_argument("--output", help="输出目录（默认：packs/exports）")

    # pack import
    import_parser = pack_subparsers.add_parser("import", help="导入 Pack")
    import_parser.add_argument("--source", required=True, help="Pack 文件路径")
    import_parser.add_argument("--target", help="目标目录（默认：examples）")
    import_parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")

    args = parser.parse_args()

    # 命令路由
    if args.command == "activate":
        return cmd_activate(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "tasks":
        return cmd_tasks(args)
    elif args.command == "sessions":
        return cmd_sessions(args)
    elif args.command == "ack":
        return cmd_ack(args)
    elif args.command == "ack-remediation":
        return cmd_ack_remediation(args)
    elif args.command == "patches":
        return cmd_patches(args)
    elif args.command == "conflicts":
        return cmd_conflicts(args)
    elif args.command == "logs":
        return cmd_logs(args)
    elif args.command == "init":
        return cmd_init(args)
    elif args.command == "clean":
        return cmd_clean(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "codex":
        return cmd_codex(args)
    elif args.command == "controller":
        return cmd_controller(args)
    elif args.command == "dispatch":
        return cmd_dispatch(args)
    elif args.command == "trigger":
        return cmd_trigger(args)
    elif args.command == "2x":
        return cmd_2x(args)
    elif args.command == "receipt":
        return cmd_receipt(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "workspace-guard":
        return cmd_workspace_guard(args)
    elif args.command == "spawn-agent-guard":
        return cmd_spawn_agent_guard(args)
    elif args.command == "hygiene":
        return cmd_hygiene(args)
    elif args.command == "stage-source":
        return cmd_stage_source(args)
    elif args.command == "stage-ops":
        return cmd_stage_ops(args)
    elif args.command == "stage-docs":
        return cmd_stage_docs(args)
    elif args.command == "stage-other":
        return cmd_stage_other(args)
    elif args.command == "stage-safe":
        return cmd_stage_safe(args)
    elif args.command == "benefit":
        return cmd_benefit(args)
    elif args.command == "pack":
        return cmd_pack(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
