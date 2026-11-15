"""执行主体身份：session_id + model_id 的规范化、契约判定与迁移审计。

对应 change `migrate-session-identity`。三条 Requirement 的共同点：
身份必须可声明、可核验、可追溯，且**不能靠厂商名冒充**。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_collab import session_registry, state_manager
from ai_collab.identity import (
    IDENTITY_REQUIRED_SINCE,
    derive_assignee_from_session,
    normalize_model_id,
    normalize_session_id,
    resolve_identity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _manager(tmp_path: Path, monkeypatch) -> state_manager.StateManager:
    # 与 test_state_manager.py 同一套隔离手法：把全局镜像与输出通道掐掉，
    # 否则测试会读写真实的 ~/.vscode/ai-collab 状态。
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
        lambda: str(tmp_path / "global_collaboration_state.json"),
    )
    return state_manager.StateManager(workspace_path=str(tmp_path))


def _full_task(**overrides) -> dict:
    task = {
        "task_id": "TASK-ID-001",
        "change_id": "bugfix/no-spec",
        "assignee": "claude_code",
        "assignee_role": "AGENT_EXEC",
        "reviewer": "codearts_agent",
        "primary_skill": "governance-engineering",
        "support_skills": ["testing"],
        "acceptance_commands": ["pytest -q"],
        "result_file": "collaboration/results/RESULT-ID.md",
        "created_at": "2026-11-16T05:00:00+08:00",
    }
    task.update(overrides)
    return task


def _run_cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "ai_collab.cli", "--workspace", str(workspace), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# --------------------------------------------------------------------------
# 规范化与三态判定
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("sess-abc", "sess-abc"),
        ("sess:2026.11-16", "sess:2026.11-16"),
        ("  sess-trim  ", "sess-trim"),
        ("ab", None),  # 太短
        ("has space", None),
        ("bad/slash", None),
        ("", None),
        (None, None),
        (123, None),
    ],
)
def test_normalize_session_id(value, expected):
    assert normalize_session_id(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("deepseek-v4.1-flash", "deepseek-v4.1-flash"),
        ("vendor/model-1.2+flash", "vendor/model-1.2+flash"),
        ("claude-opus-4.6", "claude-opus-4.6"),
        ("has space", None),
        ("-leading-dash", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_model_id(value, expected):
    assert normalize_model_id(value) == expected


def test_resolve_identity_declared():
    result = resolve_identity({"session_id": "sess-1", "model_id": "deepseek-v4", "created_at": "2026-11-16T00:00"})
    assert result["state"] == "declared"
    assert result["session_id"] == "sess-1"


def test_resolve_identity_legacy_before_cutoff():
    result = resolve_identity({"created_at": "2026-10-24T11:05:00+08:00"})
    assert result["state"] == "legacy"
    assert "历史工单" in result["reason"]


def test_resolve_identity_missing_after_cutoff():
    result = resolve_identity({"created_at": f"{IDENTITY_REQUIRED_SINCE}T00:00:00"})
    assert result["state"] == "missing"


def test_resolve_identity_missing_created_at_is_fail_closed():
    # 没有 created_at 时无法证明它是历史工单，按必填处理。
    assert resolve_identity({})["state"] == "missing"


def test_resolve_identity_invalid_format():
    result = resolve_identity({"session_id": "has space", "model_id": "deepseek-v4", "created_at": "2026-11-16"})
    assert result["state"] == "invalid"
    assert "格式非法" in result["reason"]


# --------------------------------------------------------------------------
# 契约判定
# --------------------------------------------------------------------------
def test_contract_rejects_new_task_without_identity(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    check = manager._evaluate_task_contract(_full_task())
    assert check["valid"] is False
    assert check["missing_fields"] == ["session_id", "model_id"]
    assert check["identity_state"] == "missing"


def test_contract_accepts_new_task_with_identity(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    check = manager._evaluate_task_contract(
        _full_task(session_id="sess-1", model_id="deepseek-v4.1-flash"),
    )
    assert check["valid"] is True
    assert check["legacy_identity"] is False


def test_contract_accepts_legacy_task_and_counts_it(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    legacy = _full_task(created_at="2026-10-24T11:05:00+08:00")
    check = manager._evaluate_task_contract(legacy)
    assert check["valid"] is True
    assert check["identity_state"] == "legacy"
    assert check["legacy_identity"] is True


def test_contract_distinguishes_invalid_format_from_missing(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    check = manager._evaluate_task_contract(_full_task(session_id="has space", model_id="deepseek-v4"))
    assert check["valid"] is False
    assert check["invalid_fields"] == ["session_id"]
    assert check["missing_fields"] == []


def test_validate_contracts_reports_legacy_count(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.register_task(
        task_id="TASK-LEGACY-001",
        ai_type="claude_code",
        description="legacy",
        files=[],
        change_id="bugfix/no-spec",
        assignee="claude_code",
        reviewer="codex",
        primary_skill="s",
        support_skills=["t"],
        acceptance_commands=["pytest -q"],
        result_file="collaboration/results/RESULT-L.md",
    )
    # 把它伪装成切点之前的历史工单：只有 created_at 能证明「历史」，否则按必填处理。
    manager.state["tasks"]["TASK-LEGACY-001"]["created_at"] = "2026-10-24T11:05:00+08:00"

    report = manager.validate_task_contracts(scope="all")
    assert report["legacy_identity"] == 1
    assert report["invalid_count"] == 0


def test_register_task_rejects_malformed_model_id(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    with pytest.raises(ValueError) as exc:
        manager.register_task(
            task_id="TASK-BAD-ID-001",
            ai_type="claude_code",
            description="bad",
            files=[],
            session_id="sess-ok-1",
            model_id="has space",
        )
    assert "model_id 格式非法" in str(exc.value)


# --------------------------------------------------------------------------
# 身份 → 路由：反查与审计
# --------------------------------------------------------------------------
def test_derive_assignee_from_session(tmp_path: Path, monkeypatch):
    # 不覆写路径：默认落点就是 <workspace>/logs/session_registry_state.json，
    # CLI 子进程与库调用因此看到同一份注册表，测试才有意义。
    session_registry.register_session(
        workspace=tmp_path,
        session_id="sess-known",
        assignee="codearts_agent",
        transport_mode="manual",
    )

    assert derive_assignee_from_session(tmp_path, "sess-known") == "codearts_agent"
    assert derive_assignee_from_session(tmp_path, "sess-unknown") is None
    assert derive_assignee_from_session(tmp_path, "bad id") is None


def test_audit_identity_is_read_only_by_default(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.register_task(
        task_id="TASK-AUDIT-001",
        ai_type="claude_code",
        description="audit",
        files=[],
        change_id="bugfix/no-spec",
        assignee="claude_code",
        reviewer="codex",
        primary_skill="s",
        support_skills=["t"],
        acceptance_commands=["pytest -q"],
        result_file="collaboration/results/RESULT-A.md",
    )
    before = json.dumps(manager.state["tasks"], sort_keys=True, default=str)

    report = manager.audit_task_identity(scope="all")
    after = json.dumps(manager.state["tasks"], sort_keys=True, default=str)

    assert report["apply"] is False
    assert report["applied"] == []
    assert report["counts"]["missing"] == 1
    assert before == after


def test_audit_apply_only_fills_route_from_registry(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    # 不覆写路径：默认落点就是 <workspace>/logs/session_registry_state.json，
    # CLI 子进程与库调用因此看到同一份注册表，测试才有意义。
    session_registry.register_session(
        workspace=tmp_path,
        session_id="sess-audit-known",
        assignee="codearts_agent",
        transport_mode="manual",
    )
    manager.register_task(
        task_id="TASK-AUDIT-002",
        ai_type="claude_code",
        description="audit apply",
        files=[],
        change_id="bugfix/no-spec",
        reviewer="codex",
        primary_skill="s",
        support_skills=["t"],
        acceptance_commands=["pytest -q"],
        result_file="collaboration/results/RESULT-A2.md",
        session_id="sess-audit-known",
        model_id="deepseek-v4.1-flash",
    )

    report = manager.audit_task_identity(scope="all", apply=True)
    assert report["route_fillable"] == [{"task_id": "TASK-AUDIT-002", "assignee": "codearts_agent"}]
    assert report["applied"] == ["TASK-AUDIT-002"]
    assert manager.get_task("TASK-AUDIT-002")["assignee"] == "codearts_agent"
    # 身份本身没被改动，也没有被覆盖成别的值。
    assert manager.get_task("TASK-AUDIT-002")["session_id"] == "sess-audit-known"


def test_audit_never_invents_identity_for_legacy(tmp_path: Path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    manager.register_task(
        task_id="TASK-AUDIT-003",
        ai_type="claude_code",
        description="legacy",
        files=[],
        change_id="bugfix/no-spec",
        assignee="claude_code",
        reviewer="codex",
        primary_skill="s",
        support_skills=["t"],
        acceptance_commands=["pytest -q"],
        result_file="collaboration/results/RESULT-A3.md",
    )
    manager.state["tasks"]["TASK-AUDIT-003"]["created_at"] = "2026-10-24T11:05:00+08:00"

    report = manager.audit_task_identity(scope="all", apply=True)
    task = manager.get_task("TASK-AUDIT-003")
    assert report["counts"]["legacy"] == 1
    assert report["applied"] == []
    assert "session_id" not in task  # 没有事实就不写


# --------------------------------------------------------------------------
# CLI 行为
# --------------------------------------------------------------------------
def test_cli_register_requires_registry_or_explicit_assignee(tmp_path: Path):
    result = _run_cli(
        tmp_path,
        "tasks",
        "register",
        "--task-id",
        "TASK-CLI-ID-001",
        "--ai",
        "claude_code",
        "--change-id",
        "bugfix/no-spec",
        "--session-id",
        "sess-not-registered",
        "--model-id",
        "deepseek-v4",
    )
    assert result.returncode == 1
    assert "无法反查路由键" in result.stdout


def test_cli_register_derives_route_from_registry(tmp_path: Path, monkeypatch):
    # 不覆写路径：默认落点就是 <workspace>/logs/session_registry_state.json，
    # CLI 子进程与库调用因此看到同一份注册表，测试才有意义。
    session_registry.register_session(
        workspace=tmp_path,
        session_id="sess-cli-known",
        assignee="codearts_agent",
        transport_mode="manual",
    )

    result = _run_cli(
        tmp_path,
        "tasks",
        "register",
        "--task-id",
        "TASK-CLI-ID-002",
        "--ai",
        "claude_code",
        "--change-id",
        "bugfix/no-spec",
        "--session-id",
        "sess-cli-known",
        "--model-id",
        "deepseek-v4.1-flash",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "路由键来源: registry" in result.stdout
    assert "assignee=codearts_agent" in result.stdout


def test_cli_migrate_identity_defaults_to_read_only(tmp_path: Path):
    result = _run_cli(tmp_path, "tasks", "migrate-identity", "--scope", "all")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "身份迁移审计" in result.stdout
    assert "只读审计" in result.stdout
