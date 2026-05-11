import json
from pathlib import Path

import pytest

import ai_collab.state_manager as state_manager


def _patch_state_paths(monkeypatch, workspace: Path):
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "get_project_config",
        lambda: {"stateFile": "./logs/collaboration_state.json"},
    )
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "update_vscode_output",
        lambda message, channel="AI Collab": None,
    )
    monkeypatch.setattr(
        state_manager.VSCodeStateManager,
        "get_global_state_file",
        lambda: str(workspace / "global_collaboration_state.json"),
    )


def _create_openspec_change(workspace: Path, change_id: str):
    change_dir = workspace / "openspec" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "proposal.md").write_text("## Why\nunit test change\n", encoding="utf-8")


def test_load_state_recovers_from_corrupted_json(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    state_file = tmp_path / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text('{"broken": ', encoding="utf-8")

    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    assert manager.state["tasks"] == {}
    assert manager.state["active_tasks"] == []
    assert manager.state["completed_tasks"] == []
    assert manager.state["workspace"] == str(tmp_path)


def test_save_state_uses_atomic_write_and_keeps_json_valid(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-ATOMIC-001",
        ai_type="codex",
        description="atomic write",
        files=["src/example.py"],
        vscode_context={"source": "unit-test"},
    )

    state_file = tmp_path / "logs" / "collaboration_state.json"
    payload = json.loads(state_file.read_text(encoding="utf-8"))

    assert "TASK-ATOMIC-001" in payload["tasks"]
    assert payload["tasks"]["TASK-ATOMIC-001"]["ai_type"] == "codex"
    assert payload["active_tasks"] == ["TASK-ATOMIC-001"]
    assert not list((tmp_path / "logs").glob(".state_tmp_*.json"))


def test_atomic_write_cleans_temp_file_when_replace_fails(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))
    target_file = tmp_path / "logs" / "failed-write.json"

    def _raise_replace(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(state_manager.os, "replace", _raise_replace)

    with pytest.raises(OSError, match="replace failed"):
        manager._atomic_write_json(str(target_file), {"ok": True})

    assert not list((tmp_path / "logs").glob(".state_tmp_*.json"))


def test_normalize_state_reconciles_active_and_completed_lists(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    state_file = tmp_path / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "workspace": str(tmp_path),
                "tasks": {
                    "TASK-DONE-001": {
                        "task_id": "TASK-DONE-001",
                        "ai_type": "claude_code",
                        "description": "done task",
                        "files": [],
                        "status": "completed",
                        "created_at": "2026-02-28T10:00:00",
                        "updated_at": "2026-02-28T10:10:00",
                        "completed_at": None,
                        "notes": [],
                        "vscode_context": {},
                    },
                    "TASK-ACTIVE-001": {
                        "task_id": "TASK-ACTIVE-001",
                        "ai_type": "codex",
                        "description": "active task",
                        "files": [],
                        "status": "planning",
                        "created_at": "2026-02-28T11:00:00",
                        "updated_at": "2026-02-28T11:10:00",
                        "completed_at": "2026-02-28T11:11:00",
                        "notes": [],
                        "vscode_context": {},
                    },
                },
                "active_tasks": ["TASK-DONE-001", "TASK-GHOST-001"],
                "completed_tasks": ["TASK-ACTIVE-001", "TASK-GHOST-002"],
                "conflicts": [],
                "file_status": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    assert manager.state["active_tasks"] == ["TASK-ACTIVE-001"]
    assert manager.state["completed_tasks"] == ["TASK-DONE-001"]
    assert manager.state["tasks"]["TASK-DONE-001"]["completed_at"] is not None
    assert manager.state["tasks"]["TASK-ACTIVE-001"]["completed_at"] is None


def test_normalize_state_maps_legacy_in_progress_and_keeps_blocked(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    state_file = tmp_path / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "workspace": str(tmp_path),
                "tasks": {
                    "TASK-LEGACY-001": {
                        "task_id": "TASK-LEGACY-001",
                        "ai_type": "codex",
                        "description": "legacy status",
                        "files": [],
                        "status": "in_progress",
                        "created_at": "2026-02-28T12:00:00",
                        "updated_at": "2026-02-28T12:01:00",
                        "completed_at": None,
                        "notes": [],
                        "vscode_context": {},
                    },
                    "TASK-BLOCKED-001": {
                        "task_id": "TASK-BLOCKED-001",
                        "ai_type": "claude_code",
                        "description": "blocked status",
                        "files": [],
                        "status": "blocked",
                        "created_at": "2026-02-28T12:00:00",
                        "updated_at": "2026-02-28T12:01:00",
                        "completed_at": None,
                        "notes": [],
                        "vscode_context": {},
                    },
                },
                "active_tasks": [],
                "completed_tasks": [],
                "conflicts": [],
                "file_status": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    assert manager.state["tasks"]["TASK-LEGACY-001"]["status"] == "implementing"
    assert manager.state["tasks"]["TASK-BLOCKED-001"]["status"] == "blocked"
    assert set(manager.state["active_tasks"]) >= {"TASK-LEGACY-001", "TASK-BLOCKED-001"}


def test_file_lock_timeout_when_lock_file_exists(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))
    target_file = tmp_path / "logs" / "locked.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("{}", encoding="utf-8")

    lock_file = Path(f"{target_file}.lock")
    lock_file.write_text("another-process", encoding="utf-8")

    with pytest.raises(TimeoutError, match="获取文件锁超时"):
        with manager._file_lock(str(target_file), timeout_sec=0.05, stale_sec=120.0, poll_interval=0.01):
            pass

    assert lock_file.exists()


def test_file_lock_removes_stale_lock(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))
    target_file = tmp_path / "logs" / "stale-locked.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("{}", encoding="utf-8")

    lock_file = Path(f"{target_file}.lock")
    lock_file.write_text("stale-lock", encoding="utf-8")

    # 将锁文件时间戳设置到过去，触发 stale 清理。
    old_ts = 1.0
    state_manager.os.utime(lock_file, (old_ts, old_ts))

    with manager._file_lock(str(target_file), timeout_sec=0.2, stale_sec=0.01, poll_interval=0.01):
        assert lock_file.exists()

    assert not lock_file.exists()


def test_file_lock_does_not_remove_replaced_lock_file(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))
    target_file = tmp_path / "logs" / "replaced-lock.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("{}", encoding="utf-8")
    lock_file = Path(f"{target_file}.lock")

    with manager._file_lock(str(target_file), timeout_sec=0.2, stale_sec=120.0, poll_interval=0.01):
        assert lock_file.exists()
        # 模拟锁文件被外部替换为“另一个持有者”的锁。
        lock_file.unlink()
        lock_file.write_text("other-token|999|2026-01-01T00:00:00\n", encoding="utf-8")

    assert lock_file.exists()
    assert lock_file.read_text(encoding="utf-8").startswith("other-token|")


def test_stale_managers_do_not_lose_tasks_on_save(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager1 = state_manager.StateManager(workspace_path=str(tmp_path))
    manager2 = state_manager.StateManager(workspace_path=str(tmp_path))

    manager1.register_task(
        task_id="TASK-MERGE-001",
        ai_type="claude_code",
        description="first writer",
        files=[],
        vscode_context={"source": "unit-test"},
    )
    manager2.register_task(
        task_id="TASK-MERGE-002",
        ai_type="codex",
        description="stale writer",
        files=[],
        vscode_context={"source": "unit-test"},
    )

    state_file = tmp_path / "logs" / "collaboration_state.json"
    payload = json.loads(state_file.read_text(encoding="utf-8"))

    assert "TASK-MERGE-001" in payload["tasks"]
    assert "TASK-MERGE-002" in payload["tasks"]
    assert set(payload["active_tasks"]) >= {"TASK-MERGE-001", "TASK-MERGE-002"}


def test_record_conflict_uses_uuid_id_and_persists_valid_json(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CONFLICT-UUID-001",
        ai_type="claude_code",
        description="conflict source",
        files=["src/a.py"],
        vscode_context={"source": "unit-test"},
    )

    manager._record_conflict("TASK-CONFLICT-UUID-001", "codex", ["src/a.py"], "command")
    manager._record_conflict("TASK-CONFLICT-UUID-001", "copilot", ["src/a.py"], "command")

    issues_file = tmp_path / "logs" / "collaboration_issues.json"
    payload = json.loads(issues_file.read_text(encoding="utf-8"))
    issues = payload.get("issues", [])

    assert len(issues) == 2
    assert issues[0]["conflict_id"].startswith("CONFLICT-")
    assert issues[1]["conflict_id"].startswith("CONFLICT-")
    assert issues[0]["conflict_id"] != issues[1]["conflict_id"]
    assert len(issues[0]["conflict_id"].split("CONFLICT-")[1]) == 32


def test_record_conflict_recovers_from_corrupted_issues_file(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CONFLICT-RECOVER-001",
        ai_type="claude_code",
        description="conflict source",
        files=["src/b.py"],
        vscode_context={"source": "unit-test"},
    )

    issues_file = tmp_path / "logs" / "collaboration_issues.json"
    issues_file.parent.mkdir(parents=True, exist_ok=True)
    issues_file.write_text("{broken", encoding="utf-8")

    manager._record_conflict("TASK-CONFLICT-RECOVER-001", "codex", ["src/b.py"], "on_save")

    payload = json.loads(issues_file.read_text(encoding="utf-8"))
    issues = payload.get("issues", [])
    assert len(issues) == 1
    assert issues[0]["ai_type_2"] == "codex"


def test_patch_register_update_and_ops_log(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_patch(
        patch_id="PATCH-001",
        task_id="TASK-001",
        title="add index",
        files=["local-backend/app/models/pack.py"],
        assignee="codex",
        actor="codex",
        source="unit-test",
        reason="create patch",
    )
    manager.update_patch_status(
        patch_id="PATCH-001",
        status=state_manager.PatchStatus.COMPLETED,
        note="done",
        actor="codex",
        source="unit-test",
        reason="complete patch",
    )

    patch = manager.get_patch("PATCH-001")
    assert patch is not None
    assert patch["status"] == "completed"
    assert patch["completed_at"] is not None

    ops_file = tmp_path / "logs" / "patch_ops.jsonl"
    lines = [line for line in ops_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["patch_id"] == "PATCH-001"
    assert second["new_status"] == "completed"


def test_list_patches_supports_filters(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_patch(
        patch_id="PATCH-001",
        task_id="TASK-A",
        title="patch a",
        files=["a.py"],
    )
    manager.register_patch(
        patch_id="PATCH-002",
        task_id="TASK-B",
        title="patch b",
        files=["b.py"],
        status=state_manager.PatchStatus.IN_PROGRESS,
    )

    pending = manager.list_patches(status_filter="pending")
    in_progress = manager.list_patches(status_filter="in_progress")
    task_a = manager.list_patches(task_id="TASK-A")

    assert len(pending) == 1
    assert pending[0]["patch_id"] == "PATCH-001"
    assert len(in_progress) == 1
    assert in_progress[0]["patch_id"] == "PATCH-002"
    assert len(task_a) == 1
    assert task_a[0]["patch_id"] == "PATCH-001"


def test_load_handoffs_falls_back_to_legacy_file(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    legacy_file = tmp_path / "handoff_status.json"
    legacy_file.write_text(
        json.dumps(
            {
                "HANDOFF-LEGACY-001": {
                    "handoff_id": "HANDOFF-LEGACY-001",
                    "from_ai": "copilot",
                    "to_ai": "claude_code",
                    "status": "PENDING",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    handoff = manager.get_handoff("HANDOFF-LEGACY-001")
    assert handoff is not None
    assert handoff["from_ai"] == "copilot"
    assert handoff["status"] == "PENDING"


def test_create_handoff_writes_primary_and_mirrors_legacy(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    legacy_file = tmp_path / "handoff_status.json"
    legacy_file.write_text("{}", encoding="utf-8")

    handoff = manager.create_handoff(
        from_ai="claude_code",
        to_ai="codex",
        task_description="handoff test",
        files=["src/example.py"],
        context={"source": "unit-test"},
    )

    primary_file = tmp_path / "logs" / "handoff_status.json"
    assert primary_file.exists()
    assert legacy_file.exists()

    primary_payload = json.loads(primary_file.read_text(encoding="utf-8"))
    legacy_payload = json.loads(legacy_file.read_text(encoding="utf-8"))
    handoff_id = handoff["handoff_id"]

    assert handoff_id in primary_payload
    assert handoff_id in legacy_payload
    assert primary_payload[handoff_id]["to_ai"] == "codex"
    assert legacy_payload[handoff_id]["to_ai"] == "codex"


def test_task_contract_blocks_implementing_when_required_fields_missing(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CONTRACT-MISS-001",
        ai_type="claude_code",
        description="missing contract",
        files=["ai_collab/cli.py"],
        vscode_context={"source": "unit-test"},
        contract_required=True,
    )

    with pytest.raises(ValueError, match="任务契约校验失败"):
        manager.update_task_status(
            task_id="TASK-CONTRACT-MISS-001",
            status=state_manager.TaskStatus.IMPLEMENTING,
            note="move to implementing",
        )


def test_task_contract_allows_implementing_when_required_fields_complete(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    _create_openspec_change(tmp_path, "add-task-contract-gatekeeper")
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CONTRACT-OK-001",
        ai_type="claude_code",
        description="complete contract",
        files=["ai_collab/cli.py"],
        vscode_context={"source": "unit-test"},
        change_id="add-task-contract-gatekeeper",
        assignee="claude_code",
        reviewer="codex",
        primary_skill="backend-architect",
        support_skills=["planning-with-files"],
        acceptance_commands=["pytest -q tests/unit/test_cli.py"],
        result_file="collaboration/results/RESULT_TASK-CONTRACT-OK-001.md",
        contract_required=True,
    )

    manager.update_task_status(
        task_id="TASK-CONTRACT-OK-001",
        status=state_manager.TaskStatus.IMPLEMENTING,
        note="move to implementing",
    )
    assert manager.state["tasks"]["TASK-CONTRACT-OK-001"]["status"] == "implementing"


def test_takeover_task_locks_owner_and_reassigns_assignee(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-LOCK-001",
        ai_type="codearts_agent",
        description="ownership lock",
        files=["ai_collab/state_manager.py"],
        assignee="codearts_agent",
        contract_required=False,
    )

    result = manager.takeover_task(
        task_id="TASK-LOCK-001",
        owner="codex",
        actor="codex",
        note="take over for close-loop",
        reason="prevent concurrent late updates",
    )

    task = manager.get_task("TASK-LOCK-001")
    assert result["owner"] == "codex"
    assert task is not None
    assert task["assignee"] == "codex"
    assert task["ownership"]["lock_active"] is True
    assert task["ownership"]["owner"] == "codex"
    assert task["ownership"]["previous_owner"] == "codearts_agent"


def test_repair_task_assignee_updates_metadata_and_audit_log(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))
    result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-REPAIR-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "pytest -q tests/unit/test_state_manager.py",
                "## 测试结论",
                "all green",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )

    manager.register_task(
        task_id="TASK-REPAIR-001",
        ai_type="codearts_agent",
        description="repair task assignee",
        files=["ai_collab/state_manager.py"],
        assignee="codex",
        acceptance_commands=["pytest -q tests/unit/test_state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-REPAIR-001.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-REPAIR-001",
        status=state_manager.TaskStatus.COMPLETED,
        note="complete before metadata repair",
        actor="codex",
    )

    before_updated_at = manager.get_task("TASK-REPAIR-001")["updated_at"]
    result = manager.repair_task_assignee(
        task_id="TASK-REPAIR-001",
        assignee="codearts_agent",
        actor="codex",
        reason="explicit ACK closeout residual",
        note="restore controller assignee",
        source="unit-test",
    )

    task = manager.get_task("TASK-REPAIR-001")
    assert result["old_assignee"] == "codex"
    assert result["new_assignee"] == "codearts_agent"
    assert task is not None
    assert task["assignee"] == "codearts_agent"
    assert task["status"] == "completed"
    assert task["updated_at"] != before_updated_at
    assert "TASK-REPAIR-001" in manager.state["completed_tasks"]
    assert "TASK-REPAIR-001" not in manager.state["active_tasks"]
    assert any("[assignee-repair]" in note for note in task.get("notes", []))

    ops_file = tmp_path / "logs" / "task_ops.jsonl"
    lines = [line for line in ops_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["task_id"] == "TASK-REPAIR-001"
    assert payload["op_type"] == "repair_assignee"
    assert payload["old_assignee"] == "codex"
    assert payload["new_assignee"] == "codearts_agent"


def test_repair_task_assignee_rejects_empty_assignee(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    with pytest.raises(ValueError, match="assignee 不能为空"):
        manager.repair_task_assignee(
            task_id="TASK-REPAIR-EMPTY",
            assignee="",
            actor="codex",
        )


def test_repair_task_assignee_rejects_missing_task(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    with pytest.raises(ValueError, match="任务不存在"):
        manager.repair_task_assignee(
            task_id="TASK-MISSING-001",
            assignee="codearts_agent",
            actor="codex",
        )


def test_takeover_lock_rejects_previous_assignee_status_update(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-LOCK-002",
        ai_type="codearts_agent",
        description="reject stale agent write",
        files=["ai_collab/state_manager.py"],
        assignee="codearts_agent",
        contract_required=False,
    )
    manager.takeover_task(
        task_id="TASK-LOCK-002",
        owner="codex",
        actor="codex",
        reason="manual takeover",
    )

    with pytest.raises(ValueError, match="任务接管防并发拦截"):
        manager.update_task_status(
            task_id="TASK-LOCK-002",
            status=state_manager.TaskStatus.TESTING,
            note="late agent update",
            actor="codearts_agent",
        )


def test_takeover_lock_allows_locked_owner_update(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-LOCK-003",
        ai_type="codearts_agent",
        description="allow new owner update",
        files=["ai_collab/state_manager.py"],
        assignee="codearts_agent",
        contract_required=False,
    )
    manager.takeover_task(
        task_id="TASK-LOCK-003",
        owner="codex",
        actor="codex",
        reason="manual takeover",
    )

    manager.update_task_status(
        task_id="TASK-LOCK-003",
        status=state_manager.TaskStatus.BLOCKED,
        note="codex now owns this task",
        actor="codex",
    )

    task = manager.get_task("TASK-LOCK-003")
    assert task is not None
    assert task["status"] == "blocked"


def test_takeover_lock_blocks_stale_manager_late_update(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager1 = state_manager.StateManager(workspace_path=str(tmp_path))
    manager2 = state_manager.StateManager(workspace_path=str(tmp_path))

    manager1.register_task(
        task_id="TASK-LOCK-004",
        ai_type="codearts_agent",
        description="stale manager race",
        files=["ai_collab/state_manager.py"],
        assignee="codearts_agent",
        contract_required=False,
    )

    manager1.takeover_task(
        task_id="TASK-LOCK-004",
        owner="codex",
        actor="codex",
        reason="prevent concurrent update",
    )

    with pytest.raises(ValueError, match="任务接管防并发拦截"):
        manager2.update_task_status(
            task_id="TASK-LOCK-004",
            status=state_manager.TaskStatus.TESTING,
            note="late write from stale manager",
            actor="codearts_agent",
        )

    fresh = state_manager.StateManager(workspace_path=str(tmp_path))
    task = fresh.get_task("TASK-LOCK-004")
    assert task is not None
    assert task["assignee"] == "codex"
    assert task["ownership"]["lock_active"] is True


def test_validate_task_contracts_reports_invalid_issues(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    _create_openspec_change(tmp_path, "add-prompt-pack-lifecycle-baseline")
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CONTRACT-INVALID-001",
        ai_type="codearts_agent",
        description="invalid contract",
        files=["collaboration/PROTOCOL.md"],
        vscode_context={"source": "unit-test"},
        change_id="add-prompt-pack-lifecycle-baseline",
        assignee="codearts_agent",
        reviewer="codex",
        # primary_skill intentionally missing
        support_skills=[],
        acceptance_commands=[],
        result_file="",
        contract_required=True,
    )

    report = manager.validate_task_contracts(scope="active")
    assert report["checked_tasks"] >= 1
    assert report["invalid_count"] == 1
    assert report["issues"][0]["task_id"] == "TASK-CONTRACT-INVALID-001"


def test_validate_task_contract_does_not_skip_legacy_task(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-LEGACY-VALIDATE-001",
        ai_type="copilot",
        description="legacy validate",
        files=[],
        contract_required=False,
    )

    check = manager.validate_task_contract("TASK-LEGACY-VALIDATE-001")
    assert check["skipped"] is False
    assert check["valid"] is False
    assert "change_id" in check["missing_fields"]


def test_migrate_task_contracts_upgrades_legacy_tasks(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-MIGRATE-LEGACY-001",
        ai_type="copilot",
        description="legacy task",
        files=["collaboration/tasks/TASK-MIGRATE-LEGACY-001.md"],
        contract_required=False,
    )

    report = manager.migrate_task_contracts(scope="all", dry_run=False)

    assert report["migrated_count"] == 1
    assert report["remaining_legacy"] == 0
    assert report["legacy_branch_eliminated"] is True

    task = manager.get_task("TASK-MIGRATE-LEGACY-001")
    assert task is not None
    assert task["contract_required"] is True
    assert task["change_id"] == "legacy/task-contract-migration"
    assert task["assignee"] == "copilot"
    assert task["reviewer"] == "codex"
    assert task["primary_skill"] == "api-test-pro"
    assert task["support_skills"] == ["legacy-contract-migration"]
    assert task["acceptance_commands"] == [
        "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
    ]
    assert task["result_file"] == "collaboration/results/RESULT_TASK-MIGRATE-LEGACY-001.md"


def test_migrate_task_contracts_dry_run_keeps_state_unchanged(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-MIGRATE-DRYRUN-001",
        ai_type="claude_code",
        description="legacy dry-run",
        files=["ai_collab/state_manager.py"],
        contract_required=False,
    )

    report = manager.migrate_task_contracts(scope="all", dry_run=True)
    task = manager.get_task("TASK-MIGRATE-DRYRUN-001")

    assert report["dry_run"] is True
    assert report["migrated_count"] == 1
    assert task is not None
    assert task["contract_required"] is False
    assert task.get("change_id") is None


def test_validate_task_contract_rejects_unknown_change_id(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-CHANGE-ID-INVALID-001",
        ai_type="codex",
        description="invalid change id",
        files=["ai_collab/cli.py"],
        change_id="add-non-existent-change",
        assignee="codex",
        reviewer="codex",
        primary_skill="duoai-coordinator",
        support_skills=["planning-with-files"],
        acceptance_commands=["pytest -q tests/unit/test_state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-CHANGE-ID-INVALID-001.md",
        contract_required=True,
    )

    check = manager.validate_task_contract("TASK-CHANGE-ID-INVALID-001")
    assert check["valid"] is False
    assert "change_id" in check["invalid_fields"]


def test_task_completion_blocks_when_result_file_missing(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    manager.register_task(
        task_id="TASK-COMPLETE-MISS-001",
        ai_type="claude_code",
        description="missing result file",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-COMPLETE-MISS-001.md",
        contract_required=False,
    )

    with pytest.raises(ValueError, match="result_file not found"):
        manager.update_task_status(
            task_id="TASK-COMPLETE-MISS-001",
            status=state_manager.TaskStatus.COMPLETED,
            note="try complete",
        )


def test_task_completion_blocks_when_result_file_missing_required_sections(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-COMPLETE-SECTIONS-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text("# 结果\n仅有结论，没有风险\n", encoding="utf-8")

    manager.register_task(
        task_id="TASK-COMPLETE-SECTIONS-001",
        ai_type="codex",
        description="result file missing sections",
        files=["ai_collab/state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-COMPLETE-SECTIONS-001.md",
        contract_required=False,
    )

    with pytest.raises(ValueError, match="missing sections"):
        manager.update_task_status(
            task_id="TASK-COMPLETE-SECTIONS-001",
            status=state_manager.TaskStatus.COMPLETED,
            note="try complete",
        )


def test_task_completion_allows_when_result_file_has_required_sections(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-COMPLETE-OK-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "pytest -q tests/unit/test_state_manager.py",
                "## 测试结论",
                "all green",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )

    manager.register_task(
        task_id="TASK-COMPLETE-OK-001",
        ai_type="claude_code",
        description="result file complete",
        files=["ai_collab/state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-COMPLETE-OK-001.md",
        contract_required=False,
    )

    manager.update_task_status(
        task_id="TASK-COMPLETE-OK-001",
        status=state_manager.TaskStatus.COMPLETED,
        note="complete with evidence",
    )
    assert manager.state["tasks"]["TASK-COMPLETE-OK-001"]["status"] == "completed"


def test_task_completion_blocks_when_result_file_misses_acceptance_command(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-COMPLETE-CMD-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "pytest -q tests/unit/test_cli.py",
                "## 测试结论",
                "all green",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )

    manager.register_task(
        task_id="TASK-COMPLETE-CMD-001",
        ai_type="claude_code",
        description="result file command mismatch",
        files=["ai_collab/state_manager.py"],
        acceptance_commands=["pytest -q tests/unit/test_state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-COMPLETE-CMD-001.md",
        contract_required=False,
    )

    with pytest.raises(ValueError, match="missing acceptance_commands"):
        manager.update_task_status(
            task_id="TASK-COMPLETE-CMD-001",
            status=state_manager.TaskStatus.COMPLETED,
            note="complete with wrong command evidence",
        )


def test_task_completion_blocks_when_result_file_contains_negative_signal(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    result_file = tmp_path / "collaboration" / "results" / "RESULT_TASK-COMPLETE-NEG-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "rg -n 'Generate Playwright failure summary|Upload Playwright failure summary' .github/workflows/ci.yml .github/workflows/nightly.yml",
                "## 测试结论",
                "- [ ] 在 CI workflow 中添加 `Generate Playwright failure summary` 步骤",
                "当前仍未集成，需要返工。",
                "## 风险与回滚",
                "需要继续修改 workflow。",
            ]
        ),
        encoding="utf-8",
    )

    manager.register_task(
        task_id="TASK-COMPLETE-NEG-001",
        ai_type="codearts_agent",
        description="result file negative signal",
        files=[".github/workflows/ci.yml"],
        acceptance_commands=[
            "rg -n 'Generate Playwright failure summary|Upload Playwright failure summary' .github/workflows/ci.yml .github/workflows/nightly.yml"
        ],
        result_file="collaboration/results/RESULT_TASK-COMPLETE-NEG-001.md",
        contract_required=False,
    )

    with pytest.raises(ValueError, match="contains_negative_signals"):
        manager.update_task_status(
            task_id="TASK-COMPLETE-NEG-001",
            status=state_manager.TaskStatus.COMPLETED,
            note="complete with negative signal evidence",
        )
