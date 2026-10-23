"""**派单即入队**接线的守卫（2026-10-23）。

背景：
干预队列原本**只有** `ai_collab/session_health.py` 的 ACK 静默看门狗会写，
于是「派单 → 对方开始干」之间要空等 120s
（`ai_collab/ack_watchdog.py` 的 `DEFAULT_THRESHOLD_SECONDS`）。

`cmd_trigger` 现在在派单当场就把触发 payload 挂进干预队列，
让下一轮 adapter 轮询直接投出去。

本文件守三条不变量：

1. 入队后的状态必须是 `pending_operator_delivery` ——
   **不能**是 `queued_for_delivery`，那是「在途」，
   会被 codearts adapter 的在途过滤器整个跳过
   （`ai_collab/intervention_queue.py` 的 `IN_FLIGHT_DELIVERY_STATUSES`）；
2. 重复派单**不得**开出第二条干预 ——
   否则 adapter 投两次，对方那边两个并发会话改同一个工作区；
3. dry-run **不得**入队（dry-run 的语义是「只看不写」）。
"""

import json
from pathlib import Path

from ai_collab.adapters.codearts_adapter import run_codearts_pull_adapter
from ai_collab.cli import (
    _deliver_dispatch_interventions,
    _enqueue_dispatch_interventions,
    _generate_trigger_payload_files,
)
from ai_collab.intervention_queue import (
    IN_FLIGHT_DELIVERY_STATUSES,
    ack_intervention,
    inspect_interventions,
)


def _write_workspace_config(workspace: Path, codearts_adapter: dict | None = None) -> None:
    adapter = {
        "enabled": False,
        "bridgeCommand": "",
        "deliveryStatusOnSuccess": "queued_for_delivery",
        "report": "logs/codearts_adapter_report.json",
        "history": "logs/codearts_adapter_history.jsonl",
        "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
        "eventDir": "collaboration/monitoring/codearts_pull_events",
    }
    if codearts_adapter:
        adapter.update(codearts_adapter)
    config = {"version": "1.0.0", "sessionOrchestration": {"codeartsAdapter": adapter}}

    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_payload(workspace: Path, relpath: str, message: str) -> None:
    payload = workspace / relpath
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text(
        "\n".join(
            [
                "# Session Handoff Payload",
                "",
                "## Exact Forward Message",
                "",
                "```text",
                message,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _enqueue(workspace: Path, payload_files: dict[str, str], dry_run: bool = False):
    return _enqueue_dispatch_interventions(
        workspace=str(workspace),
        payload_files=payload_files,
        trigger_phrase="2X DISPATCH CodeArts",
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# 1. 状态必须是 pending_operator_delivery
# ---------------------------------------------------------------------------


def test_enqueue_dispatch_intervention_uses_pending_operator_delivery(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    queued = _enqueue(workspace, {"codearts_agent": relpath})

    assert len(queued) == 1
    assert queued[0]["action"] == "queued"
    assert queued[0]["delivery_status"] == "pending_operator_delivery"
    assert queued[0]["message_artifact"] == relpath

    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert len(items) == 1
    assert items[0]["delivery_status"] == "pending_operator_delivery"
    assert items[0]["assignee"] == "codearts_agent"
    assert items[0]["message_artifact"] == relpath
    # 核心不变量：不能落进「在途」集合，否则 adapter 会跳过它
    assert items[0]["delivery_status"] not in IN_FLIGHT_DELIVERY_STATUSES


def test_enqueued_dispatch_intervention_is_picked_up_by_codearts_adapter(tmp_path: Path):
    """入队后 adapter 必须能看见它（不被在途过滤器跳过）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace, {"enabled": False})
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    _enqueue(workspace, {"codearts_agent": relpath})

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["skipped_in_flight_count"] == 0
    assert report["deliveries"][0]["action"] == "artifact_only"


# ---------------------------------------------------------------------------
# 2. 同一 assignee 不得开出第二条干预
# ---------------------------------------------------------------------------


def test_repeat_dispatch_reuses_open_intervention(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    first = _enqueue(workspace, {"codearts_agent": relpath})
    second = _enqueue(workspace, {"codearts_agent": relpath})

    assert first[0]["action"] == "queued"
    assert second[0]["action"] == "reused_open"
    assert second[0]["intervention_id"] == first[0]["intervention_id"]

    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert len(items) == 1


def test_repeat_dispatch_after_failure_creates_new_intervention(tmp_path: Path):
    """上一条已 failed 时不能复用 —— 复用等于永远投不出去。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    first = _enqueue(workspace, {"codearts_agent": relpath})

    ack_intervention(
        workspace=workspace,
        intervention_id=first[0]["intervention_id"],
        delivery_status="failed",
        delivery_mode="manual",
    )

    second = _enqueue(workspace, {"codearts_agent": relpath})

    assert second[0]["action"] == "queued"
    assert second[0]["intervention_id"] != first[0]["intervention_id"]


# ---------------------------------------------------------------------------
# 3. dry-run 不得入队
# ---------------------------------------------------------------------------


def test_dry_run_does_not_enqueue_intervention(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    queued = _enqueue(workspace, {"codearts_agent": relpath}, dry_run=True)

    assert queued == []
    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert items == []


# ---------------------------------------------------------------------------
# 4. 多 assignee 覆盖
# ---------------------------------------------------------------------------


def test_enqueue_covers_every_assignee(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    payload_files = {}
    for assignee in ("codearts_agent", "codex"):
        relpath = f"collaboration/monitoring/AGENT_TRIGGER_{assignee}_latest.md"
        _write_payload(workspace, relpath, "RUN")
        payload_files[assignee] = relpath

    queued = _enqueue(workspace, payload_files)

    assert {item["assignee"] for item in queued} == {"codearts_agent", "codex"}
    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert {item["assignee"] for item in items} == {"codearts_agent", "codex"}


# ---------------------------------------------------------------------------
# 5. payload 文件映射
# ---------------------------------------------------------------------------


def test_generate_trigger_payload_files_exposes_payload_files(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    sync = _generate_trigger_payload_files(
        workspace=str(workspace),
        config={},
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
        trigger_phrase="2X DISPATCH",
        target="codearts_agent",
    )

    assert "codearts_agent" in sync["payload_files"]
    relpath = sync["payload_files"]["codearts_agent"]
    assert relpath in sync["output_files"]
    assert (workspace / relpath).exists()


# ---------------------------------------------------------------------------
# 6. 派单即送达
# ---------------------------------------------------------------------------


def test_delivery_is_skipped_in_dry_run(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    result = _deliver_dispatch_interventions(
        workspace=str(workspace),
        assignees=["codearts_agent"],
        dry_run=True,
    )

    assert result["skipped"] == "dry_run"


def test_delivery_is_skipped_without_codearts_target(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    result = _deliver_dispatch_interventions(
        workspace=str(workspace),
        assignees=["claude_code"],
        dry_run=False,
    )

    assert result["skipped"] == "no_codearts_target"


def test_delivery_runs_adapter_for_codearts_target(tmp_path: Path):
    """入队后立刻投递：适配器看到 1 条候选并成功投递。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/bridge_delivery.txt\"",
        },
    )
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload(workspace, relpath, "A.RUN")

    _enqueue(workspace, {"codearts_agent": relpath})
    result = _deliver_dispatch_interventions(
        workspace=str(workspace),
        assignees=["codearts_agent"],
        dry_run=False,
    )

    assert result.get("error") is None
    assert result["candidate_count"] == 1
    assert result["queued_count"] == 1
    assert result["failed_count"] == 0
    assert (workspace / "bridge_delivery.txt").exists()

    # 投递成功后状态翻成「在途」，避免下一轮重复投递开出第二个会话
    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert items[0]["delivery_status"] == "queued_for_delivery"


# ---------------------------------------------------------------------------
# 4. ACK 落地必须收口派单干预（2026-10-23 真机实测修的缺陷）
#
# 现象：11:10 那一轮派单投出去了，CodeArts 11:16 就回了 ACK，
# 但干预一直停在 `queued_for_delivery`（在途）。在途项会被 codearts
# adapter 的在途过滤器**整个跳过且不报错** —— 于是**第二轮派单被静默吞掉**，
# 对方根本收不到，只能等 120s 的 ACK 看门狗重新武装。
# ---------------------------------------------------------------------------


def _write_payload_with_tasks(workspace: Path, relpath: str, task_ids: list[str]) -> None:
    payload = workspace / relpath
    payload.parent.mkdir(parents=True, exist_ok=True)
    body = ["# Session Handoff Payload", ""]
    for task_id in task_ids:
        body.extend([f"### {task_id}", "", "任务内容", ""])
    payload.write_text("\n".join(body), encoding="utf-8")


def _bridge_ack(workspace: Path, task_id: str, assignee: str = "codearts_agent") -> None:
    from ai_collab.ack_protocol import record_ack_bridge

    record_ack_bridge(
        workspace=workspace,
        task_id=task_id,
        assignee=assignee,
        result_file=f"collaboration/results/RESULT-{task_id}.md",
        completed_at="2026-10-23T12:00:00",
        source="cli-ack",
        bridged_at="2026-10-23T12:00:01",
    )


def test_dispatch_intervention_records_round_task_ids(tmp_path: Path):
    """干预记录必须带上本轮任务清单 —— 收口判断全靠它。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload_with_tasks(workspace, relpath, ["TASK-IDS-001", "TASK-IDS-002"])

    queued = _enqueue(workspace, {"codearts_agent": relpath})

    assert queued[0]["task_ids"] == ["TASK-IDS-001", "TASK-IDS-002"]
    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert items[0]["task_ids"] == ["TASK-IDS-001", "TASK-IDS-002"]


def test_ack_closes_in_flight_dispatch_intervention(tmp_path: Path):
    """ACK 落地后，在途的派单干预必须收口。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload_with_tasks(workspace, relpath, ["TASK-ACK-001"])

    queued = _enqueue(workspace, {"codearts_agent": relpath})
    intervention_id = queued[0]["intervention_id"]

    # 适配器投递成功 → 翻成在途
    ack_intervention(
        workspace=workspace,
        intervention_id=intervention_id,
        delivery_status="queued_for_delivery",
        delivery_mode="bridge",
    )
    in_flight = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert in_flight[0]["delivery_status"] in IN_FLIGHT_DELIVERY_STATUSES

    # ACK 落地
    _bridge_ack(workspace, "TASK-ACK-001")

    still_open = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert still_open == []


def test_second_dispatch_is_not_swallowed_after_ack(tmp_path: Path):
    """ACK 落地后的第二轮派单必须能投出去 —— 不能被在途过滤器静默跳过。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace, {"enabled": False})
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload_with_tasks(workspace, relpath, ["TASK-ACK-002"])

    first = _enqueue(workspace, {"codearts_agent": relpath})
    ack_intervention(
        workspace=workspace,
        intervention_id=first[0]["intervention_id"],
        delivery_status="queued_for_delivery",
        delivery_mode="bridge",
    )
    _bridge_ack(workspace, "TASK-ACK-002")

    # 第二轮派单：必须开出新干预，而不是复用那条在途记录
    second = _enqueue(workspace, {"codearts_agent": relpath})
    assert second[0]["action"] == "queued"
    assert second[0]["intervention_id"] != first[0]["intervention_id"]
    assert second[0]["delivery_status"] == "pending_operator_delivery"

    report = run_codearts_pull_adapter(workspace=workspace)
    assert report["candidate_count"] == 1
    assert report["skipped_in_flight_count"] == 0


def test_second_dispatch_is_still_blocked_while_round_is_unfinished(tmp_path: Path):
    """上一轮没回 ACK 时，在途记录必须继续拦住第二轮 —— 不能开出并发会话。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    relpath = "collaboration/monitoring/AGENT_TRIGGER_codearts_agent_latest.md"
    _write_payload_with_tasks(workspace, relpath, ["TASK-ACK-003"])

    first = _enqueue(workspace, {"codearts_agent": relpath})
    ack_intervention(
        workspace=workspace,
        intervention_id=first[0]["intervention_id"],
        delivery_status="queued_for_delivery",
        delivery_mode="bridge",
    )

    second = _enqueue(workspace, {"codearts_agent": relpath})

    assert second[0]["action"] == "reused_open"
    assert second[0]["intervention_id"] == first[0]["intervention_id"]
    items = inspect_interventions(workspace=workspace, only_open=True)["interventions"]
    assert len(items) == 1
