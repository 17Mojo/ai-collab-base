"""md 工单事实源同步的守护用例。

核心断言不是「同步能跑」，而是三条不可退让的边界：
1. 只写 md 已声明的事实，缺失字段一律留空（不推导、不编造）；
2. created_at 取自 md，不能用同步时刻替代（否则历史工单被误判 missing）；
3. 同步单向，不回写 md，重复跑不制造新事实。
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from ai_collab.state_manager import StateManager

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """临时工作区；禁止写全局状态文件与备份，避免污染本机。"""
    monkeypatch.setattr(StateManager, "_sync_to_global", lambda self: None)
    monkeypatch.setattr(StateManager, "_backup_state", lambda self: None)
    return tmp_path


def _write_task(
    workspace: Path,
    task_id: str,
    *,
    session_id: str | None = None,
    model_id: str | None = None,
    created_at: str = "2026-10-24T10:00:00+08:00",
) -> Path:
    tasks_dir = workspace / "collaboration" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"task_id: {task_id}",
        "change_id: bugfix/no-spec",
        "status: completed",
        f"created_at: {created_at}",
    ]
    if session_id is not None:
        lines.append(f"session_id: {session_id}")
    if model_id is not None:
        lines.append(f"model_id: {model_id}")
    lines += ["---", "", f"# {task_id}", ""]
    path = tasks_dir / f"{task_id}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _state(workspace: Path) -> StateManager:
    return StateManager(workspace_path=str(workspace))


def _tasks_hash(workspace: Path) -> str:
    data = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    payload = json.dumps(data.get("tasks", {}), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class TestCoverage:
    def test_empty_ledger_syncs_every_md(self, workspace):
        for name in ("TASK-ALPHA-001", "TASK-BETA-002", "TASK-GAMMA-003"):
            _write_task(workspace, name)

        report = _state(workspace).sync_tasks_from_md(workspace / "collaboration" / "tasks")

        assert report["source_files"] == 3
        assert report["created"] == 3
        assert _state(workspace).audit_task_identity()["total"] == 3

    def test_dry_run_does_not_write(self, workspace):
        _write_task(workspace, "TASK-ALPHA-001")
        state = _state(workspace)

        report = state.sync_tasks_from_md(workspace / "collaboration" / "tasks", dry_run=True)

        assert report["dry_run"] is True
        assert report["created"] == 1
        assert state.audit_task_identity()["total"] == 0
        assert (workspace / "logs" / "collaboration_state.json").exists() is False

    def test_ledger_entry_without_md_is_not_deleted(self, workspace):
        _write_task(workspace, "TASK-ALPHA-001")
        state = _state(workspace)
        state.register_task(
            task_id="TASK-LOCAL-ONLY-001",
            ai_type="claude_code",
            description="本机注册，无 md",
            files=[],
        )

        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")

        tasks = state.audit_task_identity()["total"]
        assert tasks == 2, "同步只补 md，不删除没有 md 的本机条目"


class TestNoFabrication:
    def test_declared_and_legacy(self, workspace):
        _write_task(
            workspace,
            "TASK-NEW-001",
            session_id="sess-a-20261117",
            model_id="vendor/model-1",
            created_at="2026-11-17T10:00:00+08:00",
        )
        _write_task(workspace, "TASK-OLD-001", created_at="2026-10-24T10:00:00+08:00")

        state = _state(workspace)
        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")
        counts = state.audit_task_identity()["counts"]

        assert counts["declared"] == 1
        assert counts["legacy"] == 1
        assert counts["missing"] == 0
        assert counts["invalid"] == 0

    def test_partial_never_infers_model_id(self, workspace):
        _write_task(
            workspace,
            "TASK-PARTIAL-001",
            session_id="sess-a-20261117",
            created_at="2026-11-17T10:00:00+08:00",
        )

        state = _state(workspace)
        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")
        report = state.audit_task_identity()

        assert report["counts"]["partial"] == 1
        entry = next(d for d in report["details"] if d["task_id"] == "TASK-PARTIAL-001")
        assert entry["model_id"] == "", "md 没写 model_id，账本就必须为空"
        assert report["counts"]["invalid"] == 0

    def test_created_at_comes_from_md_not_sync_time(self, workspace):
        """回归：register_task 用当前时间建条目，会把切点前工单误判 missing。"""
        _write_task(workspace, "TASK-OLD-001", created_at="2026-10-24T10:00:00+08:00")

        state = _state(workspace)
        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")
        report = state.audit_task_identity()

        assert report["counts"]["legacy"] == 1
        assert report["counts"]["missing"] == 0
        entry = report["details"][0]
        assert entry["created_at"].startswith("2026-10-24")
        assert "2026-10-24" in str(state.state["tasks"]["TASK-OLD-001"]["created_at"])


class TestSourceDisclosure:
    def test_unsynced_state_is_explicit(self, workspace):
        _write_task(workspace, "TASK-OLD-001")
        state = _state(workspace)
        state.register_task("TASK-LOCAL-001", "claude_code", "本机条目", [])

        source = state.audit_task_identity()["input_source"]

        assert source["synced"] is False
        assert "未同步过 md" in source["text"]

    def test_synced_state_reports_count_and_time(self, workspace):
        _write_task(workspace, "TASK-OLD-001")
        state = _state(workspace)
        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")

        source = state.audit_task_identity()["input_source"]

        assert source["synced"] is True
        assert source["synced_count"] == 1
        assert source["synced_at"]


class TestOneWayAndIdempotent:
    def test_sync_is_idempotent_and_never_rewrites_md(self, workspace):
        path = _write_task(workspace, "TASK-OLD-001")
        md_before = hashlib.sha256(path.read_bytes()).hexdigest()
        state = _state(workspace)

        state.sync_tasks_from_md(workspace / "collaboration" / "tasks")
        first = _tasks_hash(workspace)
        second_report = state.sync_tasks_from_md(workspace / "collaboration" / "tasks")
        second = _tasks_hash(workspace)

        assert second_report["unchanged"] == 1
        assert second_report["created"] == 0
        assert first == second, "任务内容必须幂等"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == md_before
        assert "md_sync" in state.state, "synced_at 允许刷新，元数据仍在"


class TestRegistrationPath:
    def test_verify_script_passes_identity_at_both_call_sites(self):
        """静态守护：两个登记调用点必须传身份，否则补录完仍全 legacy。"""
        source = (REPO_ROOT / "scripts" / "verify_task_file_contracts.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"register_task", "update_task_contract"}
        ]
        assert len(calls) == 2, "应恰有两个登记调用点"
        for call in calls:
            keywords = {kw.arg for kw in call.keywords}
            assert {"session_id", "model_id"} <= keywords, f"{call.func.attr} 漏传身份字段"
