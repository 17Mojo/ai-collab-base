import json
from pathlib import Path

from ai_collab.adapters.codearts_adapter import run_codearts_pull_adapter
from ai_collab.intervention_queue import enqueue_intervention, inspect_interventions


def _write_workspace_config(workspace: Path, codearts_adapter: dict | None = None) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            }
        },
    }
    if codearts_adapter:
        config["sessionOrchestration"]["codeartsAdapter"].update(codearts_adapter)

    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_intervention_artifact(workspace: Path, relpath: str, message: str) -> None:
    artifact = workspace / relpath
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "\n".join(
            [
                "# Session Intervention Artifact",
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


def test_codearts_adapter_generates_artifact_only_when_bridge_disabled(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace, {"enabled": False})

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_ack_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请先拉取并补发 ACK。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-001",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["artifact_only_count"] == 1
    assert report["queued_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "artifact_only"
    assert delivery["event_file"] == (
        "collaboration/monitoring/codearts_pull_events/"
        "CODEARTS_PULL_EVENT_intervention-codearts-001_latest.md"
    )
    event_text = (workspace / delivery["event_file"]).read_text(encoding="utf-8")
    assert "请先拉取并补发 ACK。" in event_text

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "pending_operator_delivery"
    assert (workspace / report["report_file"]).exists()
    assert (workspace / report["summary_file"]).exists()
    assert (workspace / report["history_file"]).exists()


def test_codearts_adapter_queues_delivery_when_bridge_command_succeeds(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/codearts_bridge_delivery.txt\"",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_payload_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请拉取最新 intervention。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="stale_payload",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-002",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["queued_count"] == 1
    assert report["artifact_only_count"] == 0
    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["delivery_status"] == "queued_for_delivery"
    assert (workspace / "codearts_bridge_delivery.txt").exists()

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "queued_for_delivery"
    assert queue["interventions"][0]["delivery_mode"] == "bridge"


def test_codearts_adapter_does_not_redeliver_in_flight_intervention(tmp_path: Path):
    """已投递、等待对方 ACK 的 intervention 不得重复投递。

    实测事故：22:01:05 投递一次，22:55:27 同一轮健康检查又投一次，
    于是在 CodeArts 那边建了两个会话，并发改同一个工作区。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/codearts_bridge_delivery.txt\"",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_inflight_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请补发 ACK。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="ack_silence_after_run",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-inflight",
    )

    first = run_codearts_pull_adapter(workspace=workspace)
    assert first["queued_count"] == 1

    second = run_codearts_pull_adapter(workspace=workspace)

    assert second["candidate_count"] == 0
    assert second["queued_count"] == 0
    assert second["skipped_in_flight_count"] == 1
    assert second["skipped_in_flight_ids"] == ["intervention-codearts-inflight"]
    assert second["deliveries"] == []


def test_codearts_adapter_force_redeliver_requeues_in_flight_intervention(tmp_path: Path):
    """运维确实需要重投时，用 force_redeliver 显式开口子。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/codearts_bridge_delivery.txt\"",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_forced_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请补发 ACK。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="ack_silence_after_run",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-forced",
    )

    run_codearts_pull_adapter(workspace=workspace)
    forced = run_codearts_pull_adapter(workspace=workspace, force_redeliver=True)

    assert forced["candidate_count"] == 1
    assert forced["queued_count"] == 1
    assert forced["skipped_in_flight_count"] == 0
    assert forced["force_redeliver"] is True


def test_codearts_adapter_retries_failed_intervention(tmp_path: Path):
    """投递失败属于可重试状态，必须能再次投递。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "exit 9",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_retry_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请重试。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="stale_payload",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-retry",
    )

    first = run_codearts_pull_adapter(workspace=workspace)
    assert first["failed_count"] == 1

    second = run_codearts_pull_adapter(workspace=workspace)

    assert second["candidate_count"] == 1
    assert second["failed_count"] == 1
    assert second["skipped_in_flight_count"] == 0


def test_codearts_adapter_marks_failed_when_bridge_command_fails(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "exit 9",
        },
    )

    artifact_relpath = "collaboration/monitoring/session_interventions/SESSION_INTERVENTION_codearts_result_latest.md"
    _write_intervention_artifact(workspace, artifact_relpath, "请修复结果文件状态头。")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="terminal_status_mismatch",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id="intervention-codearts-003",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["failed_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "failed"
    assert delivery["delivery_status"] == "failed"
    assert delivery["error"] != ""

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "failed"
    assert queue["interventions"][0]["delivery_mode"] == "bridge"


def test_codearts_adapter_marks_failed_when_artifact_is_missing(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="missing_result_file",
        severity="high",
        message_artifact="collaboration/monitoring/session_interventions/DOES_NOT_EXIST.md",
        intervention_id="intervention-codearts-004",
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["candidate_count"] == 1
    assert report["failed_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "failed"
    assert "unable to read artifact" in delivery["error"]

    queue = inspect_interventions(workspace=workspace, only_open=True)
    assert queue["intervention_count"] == 1
    assert queue["interventions"][0]["delivery_status"] == "failed"


# ---------------------------------------------------------------------------
# 模型池接线
# ---------------------------------------------------------------------------


def _enqueue_one(workspace: Path, *, intervention_id: str, message: str) -> None:
    artifact_relpath = (
        "collaboration/monitoring/session_interventions/"
        f"SESSION_INTERVENTION_{intervention_id}_latest.md"
    )
    _write_intervention_artifact(workspace, artifact_relpath, message)
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="stale_payload",
        severity="high",
        message_artifact=artifact_relpath,
        intervention_id=intervention_id,
    )


def test_codearts_adapter_pins_model_into_bridge_command(tmp_path: Path):
    """配了模型池 → bridgeCommand 必须收到 {model}，且通道切到 new_session。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\"; "
                "printf '%s' \"{channel}\" > \"{workspace}/channel.txt\""
            ),
            "models": ["glm-5.3", "deepseek-v4.1-flash", "kimi-k3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-model-1", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert report["model_pool"] == ["glm-5.3", "deepseek-v4.1-flash", "kimi-k3"]
    assert report["model_pinned_count"] == 1
    assert report["deliveries"][0]["model"] == "glm-5.3"
    assert (workspace / "model.txt").read_text(encoding="utf-8") == "glm-5.3"
    assert (workspace / "channel.txt").read_text(encoding="utf-8") == "new_session"


def test_codearts_adapter_rotates_model_pool_across_rounds(tmp_path: Path):
    """轮换：每轮换一个模型，指针只被"钉了模型"的投递推进。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s\\n' \"{model}\" >> \"{workspace}/models.txt\""
            ),
            "models": ["glm-5.3", "deepseek-v4.1-flash", "kimi-k3"],
            "modelPolicy": "round_robin",
        },
    )

    for index in range(3):
        _enqueue_one(
            workspace,
            intervention_id=f"int-rot-{index}",
            message=f"第 {index} 轮",
        )
        report = run_codearts_pull_adapter(workspace=workspace)
        assert report["queued_count"] == 1

    models = (workspace / "models.txt").read_text(encoding="utf-8").split()
    assert models == ["glm-5.3", "deepseek-v4.1-flash", "kimi-k3"]


def test_codearts_adapter_without_model_pool_keeps_cron_channel(tmp_path: Path):
    """没配模型池 → 保持旧行为（cron 通道，模型由 kernel 决定）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{channel}\" > \"{workspace}/channel.txt\"; "
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
        },
    )
    _enqueue_one(workspace, intervention_id="int-nomodel", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert report["model_pinned_count"] == 0
    assert report["deliveries"][0]["model"] == ""
    assert (workspace / "channel.txt").read_text(encoding="utf-8") == "cron"
    assert (workspace / "model.txt").read_text(encoding="utf-8") == ""


def test_codearts_adapter_warns_when_bridge_command_has_no_model_placeholder(
    tmp_path: Path,
):
    """模型池配了但命令里没有 {model} → 如实告警，不能静默不生效。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "cp \"{event_file}\" \"{workspace}/out.txt\"",
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-nowire", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert report["model_pinned_count"] == 0
    assert "未接线" in report["model_wiring_warning"]


def test_codearts_adapter_fixed_policy_always_uses_first_model(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": "printf '%s\\n' \"{model}\" >> \"{workspace}/models.txt\"",
            "models": ["glm-5.3", "kimi-k3"],
            "modelPolicy": "fixed",
        },
    )

    for index in range(2):
        _enqueue_one(workspace, intervention_id=f"int-fixed-{index}", message="x")
        run_codearts_pull_adapter(workspace=workspace)

    models = (workspace / "models.txt").read_text(encoding="utf-8").split()
    assert models == ["glm-5.3", "glm-5.3"]


# ---------------------------------------------------------------------------
# 投递回执取证：delivery 记录里区分「请求的模型」与「实际用的模型」
#
# 桥接脚本投递成功后会把回执写到 logs/codearts_delivery_receipt.json；
# 适配器按 intervention_id 匹配读回执。对不上或读不到 → 字段留空字符串，
# 绝不拿"请求的模型"（model 字段）冒充"实际用的模型"（model_used 字段）。
# ---------------------------------------------------------------------------


def _write_delivery_receipt(workspace: Path, payload: dict) -> None:
    receipt_dir = workspace / "logs"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / "codearts_delivery_receipt.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_codearts_adapter_reads_model_used_from_delivery_receipt(tmp_path: Path):
    """用例 8：delivery 里 model_used 必须是回执里的值，不是请求值。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3", "kimi-k3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-receipt-1", message="请执行。")
    _write_delivery_receipt(
        workspace,
        {
            "intervention_id": "int-receipt-1",
            "session_id": "ses_x",
            "model_requested": "inferhub-provider/glm-5.3",
            "model_used": "inferhub-provider/kimi-k3",
            "model_applied": False,
            "fallback_used": True,
            "model_attempts": [
                {"model": "inferhub-provider/glm-5.3", "ok": False, "error": "静默回落"},
                {"model": "inferhub-provider/kimi-k3", "ok": True, "error": ""},
            ],
            "generated_at": "2026-10-23T18:00:00",
        },
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["model"] == "glm-5.3"
    assert delivery["model_used"] == "inferhub-provider/kimi-k3"
    assert delivery["model_applied"] is False
    assert delivery["fallback_used"] is True

    summary_text = (workspace / report["summary_file"]).read_text(encoding="utf-8")
    assert "model=`glm-5.3`" in summary_text
    assert "model_used=`inferhub-provider/kimi-k3`" in summary_text
    assert "model_applied=`false`" in summary_text
    assert "fallback_used=`true`" in summary_text


def test_codearts_adapter_ignores_receipt_for_other_intervention(tmp_path: Path):
    """用例 9（对不上）：回执的 intervention_id 不匹配 → 字段留空字符串。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-receipt-2", message="请执行。")
    _write_delivery_receipt(
        workspace,
        {
            "intervention_id": "int-other",
            "session_id": "ses_y",
            "model_requested": "inferhub-provider/glm-5.3",
            "model_used": "inferhub-provider/kimi-k3",
            "model_applied": False,
            "fallback_used": True,
            "model_attempts": [],
            "generated_at": "2026-10-23T18:00:00",
        },
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["model"] == "glm-5.3"
    assert delivery["model_used"] == ""
    assert delivery["model_applied"] == ""
    assert delivery["fallback_used"] == ""


def test_codearts_adapter_leaves_model_used_empty_without_receipt(tmp_path: Path):
    """用例 9（读不到）：没有回执文件 → 字段留空，不许请求值顶替。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-noreceipt", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["model"] == "glm-5.3"
    assert delivery["model_used"] == ""
    assert delivery["model_applied"] == ""
    assert delivery["fallback_used"] == ""


def test_codearts_adapter_tolerates_corrupt_receipt(tmp_path: Path):
    """回执文件损坏（非 JSON）→ 当没有回执处理，不影响投递成功。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-corrupt", message="请执行。")
    receipt_dir = workspace / "logs"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / "codearts_delivery_receipt.json").write_text(
        "not a json {{{", encoding="utf-8"
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["model_used"] == ""
    assert delivery["model_applied"] == ""
    assert delivery["fallback_used"] == ""


def test_codearts_adapter_receipt_model_applied_null_is_kept_verbatim(tmp_path: Path):
    """回执里 model_applied 为 null（无法证实）→ 原样保留 None，不臆造成 false。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-nullapplied", message="请执行。")
    _write_delivery_receipt(
        workspace,
        {
            "intervention_id": "int-nullapplied",
            "session_id": "ses_z",
            "model_requested": "inferhub-provider/glm-5.3",
            "model_used": "",
            "model_applied": None,
            "fallback_used": False,
            "model_attempts": [
                {"model": "inferhub-provider/glm-5.3", "ok": True, "error": ""}
            ],
            "generated_at": "2026-10-23T18:00:00",
        },
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    delivery = report["deliveries"][0]
    assert delivery["model_used"] == ""
    assert delivery["model_applied"] is None
    assert delivery["fallback_used"] is False


# ---------------------------------------------------------------------------
# 降级链渲染（R6）：{model_fallback} 占位符
# ---------------------------------------------------------------------------


def test_codearts_adapter_renders_model_fallback_placeholder(tmp_path: Path):
    """{model_fallback} = 模型池里除选中模型之外的其余模型（池内顺序、逗号连接）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model_fallback}\" > \"{workspace}/fallback.txt\"; "
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3", "deepseek-v4.1-flash", "kimi-k3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-fb-1", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert (workspace / "fallback.txt").read_text(encoding="utf-8") == (
        "deepseek-v4.1-flash,kimi-k3"
    )


def test_codearts_adapter_renders_empty_model_fallback_without_model(tmp_path: Path):
    """没配模型池（不钉模型）→ {model_fallback} 渲染成空串。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model_fallback}\" > \"{workspace}/fallback.txt\"; "
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
        },
    )
    _enqueue_one(workspace, intervention_id="int-fb-2", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert (workspace / "fallback.txt").read_text(encoding="utf-8") == ""


def test_codearts_adapter_renders_empty_model_fallback_for_single_model_pool(
    tmp_path: Path,
):
    """池里只有一个模型 → 没有可降级候选，{model_fallback} 渲染成空串。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model_fallback}\" > \"{workspace}/fallback.txt\"; "
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-fb-3", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert (workspace / "fallback.txt").read_text(encoding="utf-8") == ""


def test_codearts_adapter_model_fallback_placeholder_is_optional(tmp_path: Path):
    """模板里没有 {model_fallback} 占位符 → 渲染是无害 no-op（既有模板不破）。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3", "kimi-k3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-fb-4", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    assert (workspace / "model.txt").read_text(encoding="utf-8") == "glm-5.3"


# ---------------------------------------------------------------------------
# R1b：等回执超时 ≠ 投递失败 —— 回执里的 accepted_without_receipt 要透出
# ---------------------------------------------------------------------------


def test_codearts_adapter_reads_accepted_without_receipt_from_receipt(tmp_path: Path):
    """被接受但没等到回执 → delivery 里 accepted_without_receipt=True。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-accepted-1", message="请执行。")
    _write_delivery_receipt(
        workspace,
        {
            "intervention_id": "int-accepted-1",
            "session_id": "ses_x",
            "model_requested": "inferhub-provider/glm-5.3",
            "model_used": "",
            "model_applied": None,
            "fallback_used": False,
            "accepted_without_receipt": True,
            "model_attempts": [
                {
                    "model": "inferhub-provider/glm-5.3",
                    "ok": True,
                    "error": "",
                    "accepted_without_receipt": True,
                }
            ],
            "generated_at": "2026-10-23T19:00:00",
        },
    )

    report = run_codearts_pull_adapter(workspace=workspace)

    assert report["queued_count"] == 1
    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["accepted_without_receipt"] is True
    # 没有回执里就没有这个字段 → 留空字符串（与 model_used 同口径）。
    assert delivery["model_used"] == ""
    assert delivery["model_applied"] is None

    summary_text = (workspace / report["summary_file"]).read_text(encoding="utf-8")
    assert "accepted_without_receipt=`true`" in summary_text


def test_codearts_adapter_leaves_accepted_without_receipt_empty_without_receipt(
    tmp_path: Path,
):
    """没有回执文件 → accepted_without_receipt 留空，不许猜。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(
        workspace,
        {
            "enabled": True,
            "bridgeCommand": (
                "printf '%s' \"{model}\" > \"{workspace}/model.txt\""
            ),
            "models": ["glm-5.3"],
            "modelPolicy": "round_robin",
        },
    )
    _enqueue_one(workspace, intervention_id="int-accepted-2", message="请执行。")

    report = run_codearts_pull_adapter(workspace=workspace)

    delivery = report["deliveries"][0]
    assert delivery["action"] == "queued"
    assert delivery["accepted_without_receipt"] == ""
