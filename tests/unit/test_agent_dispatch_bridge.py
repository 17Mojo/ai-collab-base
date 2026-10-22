import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_dispatch_bridge.py"


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-03T14:00:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def _write_state(workspace: Path, payload: dict) -> None:
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_dispatch(workspace: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--report",
        "logs/task_dispatch_report.json",
        "--history",
        "logs/task_dispatch_history.jsonl",
        "--state",
        "logs/agent_dispatch_state.json",
        "--orders",
        "collaboration/monitoring/AGENT_DISPATCH_ORDERS_test.md",
    ]
    cmd.extend(list(extra_args))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_dispatch_writes_orders_and_state(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-001"] = {
        "task_id": "TASK-DISPATCH-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_cli.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-001.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    report_file = workspace / "logs" / "task_dispatch_report.json"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0

    state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "TASK-DISPATCH-001" in dispatch_state["items"]

    orders_file = workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    orders = orders_file.read_text(encoding="utf-8")
    assert "TASK-DISPATCH-001" in orders
    assert (
        "python3 -m ai_collab.cli tasks update --task-id TASK-DISPATCH-001 --ai claude_code --status implementing"
        in orders
    )


def test_dispatch_skips_already_dispatched_without_redispatch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-002"] = {
        "task_id": "TASK-DISPATCH-002",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-002.md",
    }
    _write_state(workspace, payload)

    first = _run_dispatch(workspace)
    assert first.returncode == 0, first.stderr
    second = _run_dispatch(workspace)
    assert second.returncode == 0, second.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 0
    assert report["already_dispatched_count"] == 1


def test_dispatch_dry_run_keeps_candidate_even_if_already_dispatched(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-DRY-001"] = {
        "task_id": "TASK-DISPATCH-DRY-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-DRY-001.md",
    }
    _write_state(workspace, payload)

    dispatch_state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-DISPATCH-DRY-001": {
                        "task_id": "TASK-DISPATCH-DRY-001",
                        "assignee": "codearts_agent",
                        "status": "planning",
                        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-DRY-001.md",
                        "updated_at": "2026-03-03T14:00:00+08:00",
                        "dispatched_at": "2026-03-03T14:00:30+08:00",
                        "dispatch_count": 1,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _run_dispatch(workspace, "--dry-run")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")
    assert "TASK-DISPATCH-DRY-001" in orders


def test_dispatch_include_pending_switch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-003"] = {
        "task_id": "TASK-DISPATCH-003",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "pending",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-003.md",
    }
    _write_state(workspace, payload)

    result_without_pending = _run_dispatch(workspace, "--dry-run")
    assert result_without_pending.returncode == 0, result_without_pending.stderr
    report_without = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report_without["candidate_count"] == 0

    result_with_pending = _run_dispatch(workspace, "--dry-run", "--include-pending")
    assert result_with_pending.returncode == 0, result_with_pending.stderr
    report_with = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report_with["candidate_count"] == 1
    assert report_with["dispatched_count"] == 1


def test_dispatch_redispatch_reopened_implementing_task_with_existing_record(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-004"] = {
        "task_id": "TASK-DISPATCH-004",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "implementing",
        "updated_at": "2026-03-03T14:05:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-004.md",
        "notes": [
            "[2026-03-03T14:04:00+08:00] codex review rejected: previous result invalid",
            "[2026-03-03T14:04:30+08:00] Reopened by codex: rerun original acceptance commands",
        ],
    }
    _write_state(workspace, payload)

    dispatch_state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-DISPATCH-004": {
                        "task_id": "TASK-DISPATCH-004",
                        "assignee": "claude_code",
                        "status": "pending",
                        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-004.md",
                        "updated_at": "2026-03-03T14:00:00+08:00",
                        "dispatched_at": "2026-03-03T14:00:30+08:00",
                        "dispatch_count": 1,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _run_dispatch(workspace, "--dry-run", "--redispatch")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0
    assert report["candidate_tasks"][0]["status"] == "implementing"

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")
    assert "TASK-DISPATCH-004" in orders
    assert "返工重派说明（必须先读）" in orders
    assert "禁止因为 result_file 已存在或任务曾到过 testing 就回复 noop。" in orders
    assert "Reopened by codex" in orders


def test_dispatch_redispatch_does_not_include_new_implementing_task_without_record(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-005"] = {
        "task_id": "TASK-DISPATCH-005",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "implementing",
        "updated_at": "2026-03-03T14:05:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-005.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace, "--dry-run", "--redispatch")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 0
    assert report["dispatched_count"] == 0


def test_dispatch_honors_custom_orders_path(tmp_path):
    """`--orders` 必须真的决定输出路径。

    回归：实现曾把文件名写死成 AGENT_DISPATCH_ORDERS_test.md，导致
    `cli trigger` 按配置去读 AGENT_DISPATCH_ORDERS_latest.md 时报
    "派单指令包不存在"，整条派单→触发链路断掉。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-006"] = {
        "task_id": "TASK-DISPATCH-006",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-006.md",
    }
    _write_state(workspace, payload)

    custom = "collaboration/monitoring/AGENT_DISPATCH_ORDERS_custom.md"
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--report",
        "logs/task_dispatch_report.json",
        "--history",
        "logs/task_dispatch_history.jsonl",
        "--state",
        "logs/agent_dispatch_state.json",
        "--orders",
        custom,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert (workspace / custom).exists()
    assert "TASK-DISPATCH-006" in (workspace / custom).read_text(encoding="utf-8")


def test_dispatch_orders_carry_assignee_section_headings(tmp_path):
    """指令包必须带 `## 发送给 `Name` (`assignee`)` 标题。

    回归：`split_orders_by_assignee` 靠这个标题切分指令包，缺了就切不出
    任何执行方，payload 会退化成"当前无待派发任务"。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-007"] = {
        "task_id": "TASK-DISPATCH-007",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-007.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")
    assert "## 发送给 `CodeArts` (`codearts_agent`)" in orders

    from ai_collab.dispatch_trigger import split_orders_by_assignee

    sections = split_orders_by_assignee(orders)
    assert "codearts_agent" in sections
    assert "TASK-DISPATCH-007" in sections["codearts_agent"]


def test_dispatch_orders_carry_task_contract(tmp_path):
    """指令包的任务块必须带契约：描述 / 涉及文件 / 结果文件 / change_id / 角色。

    回归（2026-10-22 真机实测）：payload 之前只有「任务 ID + 改状态命令 +
    验收命令」，接收方拿不到「要做什么、交什么」，只能自己翻仓库反推。
    CodeArts 收到这种 payload 后探索了 5 分钟，一个文件也没产出。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-CONTRACT-001"] = {
        "task_id": "TASK-CONTRACT-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "assignee_role": "AGENT_EXEC",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "description": "把 consensus_engine 移植到 Hermes 并把覆盖率提到 80%",
        "files": ["hermes_target/hermes_agent/engines/consensus_engine.py"],
        "change_id": "migrate-parallel-architecture-to-hermes",
        "acceptance_commands": ["pytest -q hermes_target/hermes_agent/tests/unit/"],
        "result_file": "hermes_target/RESULT-TASK-CONTRACT-001.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")

    assert "**任务描述**: 把 consensus_engine 移植到 Hermes 并把覆盖率提到 80%" in orders
    assert "`hermes_target/hermes_agent/engines/consensus_engine.py`" in orders
    assert "`hermes_target/RESULT-TASK-CONTRACT-001.md`" in orders
    assert "`migrate-parallel-architecture-to-hermes`" in orders
    assert "`AGENT_EXEC`" in orders
    assert "#### 执行步骤" in orders


def test_dispatch_orders_contract_survives_trigger_payload(tmp_path):
    """契约段必须一路活到最终交给对方的 trigger payload 里。

    回归：`build_handoff_payload` 原样拼接指令包分节，若分节时丢内容，
    接收方拿到的仍然是一份没有任务描述的 payload。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-CONTRACT-002"] = {
        "task_id": "TASK-CONTRACT-002",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "assignee_role": "AGENT_EXEC",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "description": "把 coverage 门禁接到 CI 上",
        "files": ["ai_collab/pack/schema_validator.py"],
        "result_file": "collaboration/results/RESULT-TASK-CONTRACT-002.md",
        "acceptance_commands": ["pytest -q tests/unit/test_pack_schema_validator.py"],
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")

    from ai_collab.dispatch_trigger import build_handoff_payload, split_orders_by_assignee

    sections = split_orders_by_assignee(orders)
    trigger_payload = build_handoff_payload(
        assignee="codearts_agent",
        trigger_phrase="2X DISPATCH CodeArts",
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_test.md",
        section_markdown=sections["codearts_agent"],
    )

    assert "把 coverage 门禁接到 CI 上" in trigger_payload
    assert "`collaboration/results/RESULT-TASK-CONTRACT-002.md`" in trigger_payload
    assert "#### 执行步骤" in trigger_payload


def test_dispatch_orders_include_codearts_tool_constraints(tmp_path):
    """CodeArts 的指令包必须写明工具约束：不要用 write/edit、不要派生子代理。

    回归（2026-10-22 真机实测）：两个 CodeArts 会话都死在工具调用上——
    `ses_e9be3df` 的 `write` 调用永久挂起（状态停在 running，文件没落盘），
    `ses_e9c15` 的 `task`（子代理）调用报 MessageAbortedError。
    同期的 bash / read / todowrite 全部正常完成。
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-TOOLS-001"] = {
        "task_id": "TASK-TOOLS-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "assignee_role": "AGENT_EXEC",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "description": "补 consensus_engine 单元测试",
        "files": ["hermes_target/hermes_agent/tests/unit/test_consensus_engine.py"],
        "result_file": "hermes_target/RESULT-TASK-TOOLS-001.md",
        "acceptance_commands": ["pytest -q hermes_target/hermes_agent/tests/unit/"],
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")

    assert "#### 执行环境约束（真机实测，必须遵守）" in orders
    assert "cat > path/to/file.py <<'EOF'" in orders
    assert "不要用" in orders
    assert "`task`（派生子代理）" in orders


def test_dispatch_orders_skip_tool_constraints_for_other_assignees(tmp_path):
    """工具约束只对已知会卡死的 provider 渲染，别家执行方不该看到。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-TOOLS-002"] = {
        "task_id": "TASK-TOOLS-002",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "assignee_role": "AGENT_ARCH",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "description": "评审派单链路",
        "acceptance_commands": ["pytest -q tests/unit/test_agent_dispatch_bridge.py"],
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")

    assert "#### 执行环境约束（真机实测，必须遵守）" not in orders
    assert "评审派单链路" in orders


def test_tool_constraints_survive_trigger_payload(tmp_path):
    """工具约束必须一路活到最终交给 CodeArts 的 trigger payload 里。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-TOOLS-003"] = {
        "task_id": "TASK-TOOLS-003",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "assignee_role": "AGENT_EXEC",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "description": "补 consensus_engine 单元测试",
        "result_file": "hermes_target/RESULT-TASK-TOOLS-003.md",
        "acceptance_commands": ["pytest -q hermes_target/hermes_agent/tests/unit/"],
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")

    from ai_collab.dispatch_trigger import build_handoff_payload, split_orders_by_assignee

    sections = split_orders_by_assignee(orders)
    trigger_payload = build_handoff_payload(
        assignee="codearts_agent",
        trigger_phrase="2X DISPATCH CodeArts",
        orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_test.md",
        section_markdown=sections["codearts_agent"],
    )

    assert "#### 执行环境约束（真机实测，必须遵守）" in trigger_payload
    assert "cat > path/to/file.py <<'EOF'" in trigger_payload

