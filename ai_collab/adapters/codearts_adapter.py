"""CodeArts-oriented pull adapter with auditable fallback semantics."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..ack_protocol import load_json, write_json
from ..adapters.contract import SessionAdapterContract, build_adapter_heartbeat
from ..intervention_queue import (
    DEFAULT_BRIDGE_DELIVERY_STATUS,
    IN_FLIGHT_DELIVERY_STATUSES,
    ack_intervention,
    inspect_interventions,
)
from ..session_registry import inspect_sessions, register_session

DEFAULT_REPORT_PATH = "logs/codearts_adapter_report.json"
DEFAULT_HISTORY_PATH = "logs/codearts_adapter_history.jsonl"
DEFAULT_SUMMARY_PATH = "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md"
DEFAULT_EVENT_DIR = "collaboration/monitoring/codearts_pull_events"
DELIVERY_RECEIPT_RELATIVE = "logs/codearts_delivery_receipt.json"
EXACT_MESSAGE_PATTERN = re.compile(
    r"## Exact Forward Message\s+```text\s*(?P<message>.*?)\s*```",
    flags=re.DOTALL,
)


def _load_codearts_adapter_config(workspace: Path) -> dict[str, Any]:
    config_file = workspace / ".vscode" / "ai-collab.json"
    payload = load_json(config_file, default={})
    session_config = payload.get("sessionOrchestration")
    if not isinstance(session_config, dict):
        return {}
    raw = session_config.get("codeartsAdapter")
    return raw if isinstance(raw, dict) else {}


def _resolve_paths(
    *,
    workspace: Path,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    event_dir: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    config = _load_codearts_adapter_config(workspace)
    resolved_report = workspace / str(report_path or config.get("report", DEFAULT_REPORT_PATH))
    resolved_history = workspace / str(history_path or config.get("history", DEFAULT_HISTORY_PATH))
    resolved_summary = workspace / str(summary_path or config.get("summary", DEFAULT_SUMMARY_PATH))
    resolved_event_dir = workspace / str(event_dir or config.get("eventDir", DEFAULT_EVENT_DIR))
    return resolved_report, resolved_history, resolved_summary, resolved_event_dir


def _adapter_mode(workspace: Path) -> tuple[bool, str, str]:
    config = _load_codearts_adapter_config(workspace)
    enabled = bool(config.get("enabled", False))
    bridge_command = str(config.get("bridgeCommand") or "").strip()
    delivery_status = (
        str(config.get("deliveryStatusOnSuccess") or DEFAULT_BRIDGE_DELIVERY_STATUS).strip().lower()
    )
    return enabled, bridge_command, delivery_status


def _adapter_model_config(workspace: Path) -> tuple[list[str], str]:
    """模型池与轮换策略（来自 `.vscode/ai-collab.json` 的 codeartsAdapter 块）。

    `models` 支持两种写法：

    - `"glm-5.3"` —— 只给 modelID，providerID 由桥接脚本实时从 kernel
      注册表解析（provider 换名/换家时不会因为配置写死而失效）；
    - `{"providerID": "inferhub-provider", "modelID": "glm-5.3"}` —— 显式指定。
    """
    config = _load_codearts_adapter_config(workspace)
    raw_models = config.get("models")
    models: list[str] = []
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, dict):
                provider = str(item.get("providerID") or "").strip()
                model = str(item.get("modelID") or "").strip()
                if model:
                    models.append(f"{provider}/{model}" if provider else model)
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    models.append(text)
    policy = str(config.get("modelPolicy") or "round_robin").strip().lower()
    return models, policy


def _prior_model_pinned_count(history_file: Path) -> int:
    """历史上**钉了模型**的投递次数（轮换指针）。

    只数真正带上模型的投递：早期没钉模型的投递不该推进轮换指针，
    否则第一次钉模型就会从池子中间开始，看起来像"随机选的"。
    """
    if not history_file.exists():
        return 0
    total = 0
    try:
        for line in history_file.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            try:
                total += int(payload.get("model_pinned_count") or 0)
            except (TypeError, ValueError):
                continue
    except OSError:
        return 0
    return total


def select_delivery_model(
    *, models: list[str], policy: str, prior_count: int
) -> str:
    """按策略挑一个模型；返回空串表示"不钉模型，由 kernel 决定"。"""
    if not models:
        return ""
    if policy in ("none", "off", "disabled"):
        return ""
    if policy in ("fixed", "first", "pinned"):
        return models[0]
    return models[prior_count % len(models)]


def _append_history(path: Path, payload: dict[str, Any]) -> None:
    snapshot = {
        "generated_at": payload.get("generated_at"),
        "mode": payload.get("mode"),
        "candidate_count": payload.get("candidate_count", 0),
        "queued_count": payload.get("queued_count", 0),
        "artifact_only_count": payload.get("artifact_only_count", 0),
        "failed_count": payload.get("failed_count", 0),
        # 钉了模型的投递次数：模型池轮换指针的依据（只数真正带模型的）。
        "model_pinned_count": payload.get("model_pinned_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def _load_artifact_message(path: Path) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "", f"unable to read artifact: {exc}"
    match = EXACT_MESSAGE_PATTERN.search(text)
    if match:
        return str(match.group("message")).strip(), ""
    return text.strip(), ""


def build_codearts_pull_event_markdown(
    *,
    intervention: dict[str, Any],
    exact_message: str,
    bridge_enabled: bool,
    artifact_file: Path,
) -> str:
    lines = [
        "# CodeArts Pull Event（自动生成）",
        "",
        f"- generated_at: `{datetime.now().isoformat()}`",
        f"- intervention_id: `{intervention.get('intervention_id', '')}`",
        f"- assignee: `{intervention.get('assignee', '')}`",
        f"- session_id: `{intervention.get('session_id', '')}`",
        f"- reason_code: `{intervention.get('reason_code', '')}`",
        f"- delivery_status: `{intervention.get('delivery_status', '')}`",
        f"- bridge_enabled: `{bridge_enabled}`",
        f"- source_artifact: `{artifact_file}`",
        "",
        "## Pull Snapshot",
        "",
        "```text",
        exact_message,
        "```",
        "",
    ]
    return "\n".join(lines)


def _event_file(event_dir: Path, intervention_id: str) -> Path:
    return event_dir / f"CODEARTS_PULL_EVENT_{intervention_id}_latest.md"


def _read_delivery_receipt(workspace: Path, intervention_id: str) -> dict[str, Any]:
    """读桥接落盘的投递回执，按 intervention_id 匹配。

    读不到 / 解析失败 / intervention_id 对不上 → 空字典（调用方把
    model_used 等字段留空字符串，绝不拿"请求的模型"冒充"实际用的模型"）。
    """
    receipt_file = workspace / DELIVERY_RECEIPT_RELATIVE
    if not receipt_file.exists():
        return {}
    try:
        payload = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if str(payload.get("intervention_id") or "").strip() != intervention_id:
        return {}
    return payload


def _run_bridge_command(
    *,
    workspace: Path,
    command: str,
    event_file: Path,
    artifact_file: Path,
    intervention: dict[str, Any],
    model: str = "",
    channel: str = "",
    model_fallback: str = "",
) -> subprocess.CompletedProcess[str]:
    rendered = command.format(
        workspace=str(workspace),
        event_file=str(event_file),
        artifact_file=str(artifact_file),
        intervention_id=str(intervention.get("intervention_id") or ""),
        session_id=str(intervention.get("session_id") or ""),
        assignee=str(intervention.get("assignee") or ""),
        reason_code=str(intervention.get("reason_code") or ""),
        model=model,
        channel=channel,
        model_fallback=model_fallback,
    )
    if platform.system() == "Windows":
        cmd = ["cmd", "/C", rendered]
    else:
        cmd = ["/bin/sh", "-lc", rendered]
    return subprocess.run(
        cmd,
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )


def build_summary_markdown(*, report: dict[str, Any]) -> str:
    lines = [
        "# CodeArts Adapter Summary（自动生成）",
        "",
        f"- generated_at: `{report.get('generated_at', '')}`",
        f"- mode: `{report.get('mode', '')}`",
        f"- candidate_count: `{report.get('candidate_count', 0)}`",
        f"- queued_count: `{report.get('queued_count', 0)}`",
        f"- artifact_only_count: `{report.get('artifact_only_count', 0)}`",
        f"- failed_count: `{report.get('failed_count', 0)}`",
        f"- skipped_in_flight_count: `{report.get('skipped_in_flight_count', 0)}`",
        f"- model_pool: `{', '.join(str(m) for m in (report.get('model_pool') or [])) or '（未配置）'}`",
        f"- model_policy: `{report.get('model_policy', '')}`",
        f"- model_pinned_count: `{report.get('model_pinned_count', 0)}`",
        "",
        "## Deliveries",
        "",
    ]
    if report.get("model_wiring_warning"):
        lines.extend([f"> ⚠️ {report['model_wiring_warning']}", ""])
    deliveries = list(report.get("deliveries", []) or [])
    if deliveries:
        for item in deliveries:
            # model = 请求的模型（本地选择）；model_used = 回执里实际用掉的
            # 模型（桥接落盘的回执取证）——两者语义不同，绝不互相顶替。
            used = str(item.get("model_used") or "")
            used_note = used or "（无回执）"
            applied = item.get("model_applied")
            if applied is True:
                applied_note = "true"
            elif applied is False:
                applied_note = "false"
            elif applied is None:
                applied_note = "null"
            else:
                applied_note = "（无回执）"
            fallback = item.get("fallback_used")
            fallback_note = (
                "true" if fallback is True else "false" if fallback is False else "（无回执）"
            )
            lines.append(
                f"- `{item.get('intervention_id', '')}` action=`{item.get('action', '')}` "
                f"status=`{item.get('delivery_status', '')}` "
                f"model=`{item.get('model', '') or '（kernel 决定）'}` "
                f"model_used=`{used_note}` model_applied=`{applied_note}` "
                f"fallback_used=`{fallback_note}`"
            )
            if item.get("event_file"):
                lines.append(f"  event_file: `{item.get('event_file', '')}`")
    else:
        lines.append("- 无")
    skipped = list(report.get("skipped_in_flight_ids", []) or [])
    if skipped:
        lines.append("")
        lines.append("## Skipped (In Flight)")
        lines.append("")
        lines.append("已投递、等待对方 ACK，未重复投递：")
        lines.append("")
        for item in skipped:
            lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)


def run_codearts_pull_adapter(
    *,
    workspace: Path,
    dry_run: bool = False,
    report_path: str | None = None,
    history_path: str | None = None,
    summary_path: str | None = None,
    event_dir: str | None = None,
    allow_delivery: bool = True,
    force_redeliver: bool = False,
) -> dict[str, Any]:
    report_file, history_file, summary_file, event_root = _resolve_paths(
        workspace=workspace,
        report_path=report_path,
        history_path=history_path,
        summary_path=summary_path,
        event_dir=event_dir,
    )
    enabled, bridge_command, delivery_status_on_success = _adapter_mode(workspace)
    payload = inspect_interventions(workspace=workspace, assignee="codearts_agent", only_open=True)
    candidates = list(payload.get("interventions", []) or [])

    # 模型池接线：模型只有在 bridgeCommand 真的带 {model} 占位符时才送得出去。
    # 没接线就如实记进报告 —— 静默不生效是最难查的一类。
    model_pool, model_policy = _adapter_model_config(workspace)
    model_pointer = _prior_model_pinned_count(history_file)
    model_wired = "{model}" in bridge_command
    model_pinned_count = 0
    model_wiring_warning = ""
    if model_pool and not model_wired:
        model_wiring_warning = (
            "bridgeCommand 未包含 {model} 占位符，模型池未接线（本次投递不钉模型）"
        )

    # 在途（已投递、等 ACK）的 intervention 不重复投递——否则每轮轮询都会在
    # 对方那边新建一个会话，两个会话并发改同一个工作区。
    in_flight_ids: list[str] = []
    if not force_redeliver:
        keep: list[dict[str, Any]] = []
        for intervention in candidates:
            status = str(intervention.get("delivery_status") or "").strip().lower()
            if status in IN_FLIGHT_DELIVERY_STATUSES:
                in_flight_ids.append(str(intervention.get("intervention_id") or ""))
                continue
            keep.append(intervention)
        candidates = keep

    deliveries: list[dict[str, Any]] = []
    queued_count = 0
    artifact_only_count = 0
    failed_count = 0

    for intervention in candidates:
        intervention_id = str(intervention.get("intervention_id") or "").strip()
        artifact_relpath = str(intervention.get("message_artifact") or "").strip()
        artifact_file = workspace / artifact_relpath if artifact_relpath else workspace
        exact_message, error = _load_artifact_message(artifact_file)
        delivery: dict[str, Any] = {
            "intervention_id": intervention_id,
            "session_id": str(intervention.get("session_id") or ""),
            "delivery_status": str(intervention.get("delivery_status") or ""),
            "event_file": "",
            "action": "",
            "error": "",
            "model": "",
            # 实际用掉的模型（来自桥接回执）：读不到/对不上时留空字符串，
            # 绝不拿"请求的模型"（model 字段）冒充。model_applied /
            # fallback_used 读到回执后是 bool（model_applied 还可能是 None）。
            "model_used": "",
            "model_applied": "",
            "fallback_used": "",
        }

        if error:
            if not dry_run:
                ack_report = ack_intervention(
                    workspace=workspace,
                    intervention_id=intervention_id,
                    delivery_status="failed",
                    delivery_mode="bridge"
                    if enabled and bridge_command and allow_delivery
                    else None,
                )
                updated = ack_report.get("intervention", {})
                delivery["delivery_status"] = str(updated.get("delivery_status") or "failed")
            delivery["action"] = "failed"
            delivery["error"] = error
            failed_count += 1
            deliveries.append(delivery)
            continue

        event_file = _event_file(event_root, intervention_id)
        event_file.parent.mkdir(parents=True, exist_ok=True)
        event_file.write_text(
            build_codearts_pull_event_markdown(
                intervention=intervention,
                exact_message=exact_message,
                bridge_enabled=enabled and bool(bridge_command) and allow_delivery and not dry_run,
                artifact_file=artifact_file,
            ),
            encoding="utf-8",
        )
        delivery["event_file"] = str(event_file.relative_to(workspace))

        if dry_run or not allow_delivery or not enabled or not bridge_command:
            delivery["action"] = "artifact_only"
            artifact_only_count += 1
            deliveries.append(delivery)
            continue

        model = ""
        model_fallback = ""
        # 默认仍是 cron（kernel 自建会话）；只有真的钉上模型才切 new_session。
        channel = "cron"
        if model_pool and model_wired:
            model = select_delivery_model(
                models=model_pool, policy=model_policy, prior_count=model_pointer
            )
            if model:
                # 钉了模型就必须走 new_session —— cron 通道由 kernel 决定模型。
                channel = "new_session"
                model_pointer += 1
                model_pinned_count += 1
                # 降级链渲染：模型池里除本单选中模型之外的其余模型，
                # 按池内顺序用逗号连接（模板里没有 {model_fallback} 占位符时
                # 渲染是无害 no-op —— str.format 忽略未用到的键）。
                model_fallback = ",".join(m for m in model_pool if m != model)
        delivery["model"] = model

        result = _run_bridge_command(
            workspace=workspace,
            command=bridge_command,
            event_file=event_file,
            artifact_file=artifact_file,
            intervention=intervention,
            model=model,
            channel=channel,
            model_fallback=model_fallback,
        )
        if result.returncode == 0:
            # 读桥接落盘的回执，把"实际用的模型"取证进报告（R5）。
            # 对不上或读不到 → 字段保持空字符串，绝不拿请求值顶替。
            receipt = _read_delivery_receipt(workspace, intervention_id)
            if receipt:
                used = receipt.get("model_used")
                if isinstance(used, str):
                    delivery["model_used"] = used
                applied = receipt.get("model_applied")
                if isinstance(applied, bool) or applied is None:
                    delivery["model_applied"] = applied
                fallback = receipt.get("fallback_used")
                if isinstance(fallback, bool):
                    delivery["fallback_used"] = fallback
            ack_report = ack_intervention(
                workspace=workspace,
                intervention_id=intervention_id,
                delivery_status=delivery_status_on_success,
                delivery_mode="bridge",
            )
            updated = ack_report.get("intervention", {})
            delivery["action"] = "queued"
            delivery["delivery_status"] = str(
                updated.get("delivery_status") or delivery_status_on_success
            )
            queued_count += 1
        else:
            ack_report = ack_intervention(
                workspace=workspace,
                intervention_id=intervention_id,
                delivery_status="failed",
                delivery_mode="bridge",
            )
            updated = ack_report.get("intervention", {})
            delivery["action"] = "failed"
            delivery["delivery_status"] = str(updated.get("delivery_status") or "failed")
            delivery["error"] = (result.stderr or result.stdout or "").strip() or (
                f"bridge command exited with code {result.returncode}"
            )
            failed_count += 1
        deliveries.append(delivery)

    report = {
        "generated_at": datetime.now().isoformat(),
        "workspace": str(workspace),
        "mode": "dry-run" if dry_run else "apply",
        "adapter_enabled": enabled,
        "allow_delivery": allow_delivery,
        "candidate_count": len(candidates),
        "queued_count": queued_count,
        "artifact_only_count": artifact_only_count,
        "failed_count": failed_count,
        "skipped_in_flight_count": len(in_flight_ids),
        "skipped_in_flight_ids": in_flight_ids,
        "force_redeliver": force_redeliver,
        "model_pool": model_pool,
        "model_policy": model_policy,
        "model_pinned_count": model_pinned_count,
        "deliveries": deliveries,
    }
    if model_wiring_warning:
        report["model_wiring_warning"] = model_wiring_warning

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(build_summary_markdown(report=report), encoding="utf-8")
    report["summary_file"] = str(summary_file.relative_to(workspace))
    report["report_file"] = str(report_file.relative_to(workspace))
    report["history_file"] = str(history_file.relative_to(workspace))
    write_json(report_file, report)
    _append_history(history_file, report)
    return report


def register_codearts_session(
    *,
    workspace: Path,
    session_id: str,
    transport_mode: str = "manual",
    session_status: str = "active",
    last_handoff_artifact: str = "",
    health_status: str = "healthy",
) -> dict[str, Any]:
    return register_session(
        workspace=workspace,
        session_id=session_id,
        assignee="codearts_agent",
        transport_mode=transport_mode,
        session_status=session_status,
        last_handoff_artifact=last_handoff_artifact,
        health_status=health_status,
    )


def ack_codearts_delivery(
    *,
    workspace: Path,
    intervention_id: str,
    delivery_status: str = "delivered",
    delivery_mode: str | None = None,
) -> dict[str, Any]:
    return ack_intervention(
        workspace=workspace,
        intervention_id=intervention_id,
        delivery_status=delivery_status,
        delivery_mode=delivery_mode,
    )


def heartbeat_codearts_adapter(*, workspace: Path) -> dict[str, Any]:
    report_file, history_file, summary_file, event_root = _resolve_paths(workspace=workspace)
    enabled, bridge_command, _ = _adapter_mode(workspace)
    queue = inspect_interventions(workspace=workspace, assignee="codearts_agent", only_open=True)
    registry = inspect_sessions(workspace=workspace, assignee="codearts_agent")
    sessions = list(registry.get("sessions", []) or [])
    latest = sessions[-1] if sessions else {}
    return build_adapter_heartbeat(
        workspace=workspace,
        name="codearts",
        assignee="codearts_agent",
        capability="pull",
        adapter_enabled=enabled,
        bridge_configured=bool(bridge_command),
        open_intervention_count=int(queue.get("intervention_count", 0)),
        session_id=str(latest.get("session_id") or ""),
        session_status=str(latest.get("session_status") or ""),
        transport_mode=str(latest.get("transport_mode") or ""),
        report_file=report_file,
        history_file=history_file,
        summary_file=summary_file,
        event_dir=event_root,
    )


def get_codearts_adapter_contract() -> SessionAdapterContract:
    return SessionAdapterContract(
        name="codearts",
        assignee="codearts_agent",
        capability="pull",
        register_session=register_codearts_session,
        pull_interventions=run_codearts_pull_adapter,
        ack_delivery=ack_codearts_delivery,
        heartbeat=heartbeat_codearts_adapter,
    )
