"""治理剩余缺口收口：可核验必读声明、会话级配置覆盖层、开发日志可入库。

对应 change `close-governance-gaps` 的三条 Requirement。三条都在验证同一件事：
门禁拿到的输入必须是**可核验的事实**，而不是一句自证，也不是一个永远拿不到的配置项。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_collab import governance
from ai_collab.governance import (
    GovernanceError,
    ack_required_reads,
    guard_input_report,
    preflight,
    verify_required_reads,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
READS = governance.REQUIRED_READS


def _workspace(tmp_path: Path, *, with_reads: bool = True) -> Path:
    ws = tmp_path / "ws"
    (ws / "logs").mkdir(parents=True)
    (ws / ".vscode").mkdir(parents=True)
    if with_reads:
        for rel in READS:
            target = ws / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {rel}\n版本 1\n", encoding="utf-8")
    return ws


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


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


# --------------------------------------------------------------------------
# 缺口 A：必读清单从裸自证改为可核验声明
# --------------------------------------------------------------------------
def test_ack_records_hashes_and_verifies(tmp_path: Path):
    ws = _workspace(tmp_path)
    record = ack_required_reads(ws, session_id="sess-1", acknowledged_by="claude_code")

    assert record["version"] == governance.SESSION_VERSION
    assert record["session_id"] == "sess-1"
    assert len(record["required_reads"]) == len(READS)
    for entry in record["required_reads"]:
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0

    report = verify_required_reads(ws)
    assert report["ok"] is True
    assert report["legacy"] is False
    assert report["verified"] == len(READS)
    assert report["stale"] == []
    assert report["missing"] == []


def test_modified_required_read_becomes_stale(tmp_path: Path):
    ws = _workspace(tmp_path)
    ack_required_reads(ws, session_id="sess-1")

    # 声明之后有人改了必读文档：路径名还在名单里，但内容已不是被读的那一版。
    target = ws / READS[2]
    target.write_text("# 改过的内容\n版本 2\n", encoding="utf-8")

    report = verify_required_reads(ws)
    assert report["ok"] is False
    assert report["stale"] == [READS[2]]
    assert READS[2] in report["detail"]


def test_legacy_session_format_is_rejected(tmp_path: Path):
    ws = _workspace(tmp_path)
    # 旧格式：只有路径名，证明不了任何东西。不得当作合法声明。
    (ws / governance.SESSION_REL).write_text(json.dumps({"required_reads_acknowledged": list(READS)}), encoding="utf-8")

    report = verify_required_reads(ws)
    assert report["ok"] is False
    assert report["legacy"] is True
    assert "旧格式" in report["detail"]


def test_missing_required_read_fails(tmp_path: Path):
    ws = _workspace(tmp_path)
    ack_required_reads(ws, session_id="sess-1")
    (ws / READS[0]).unlink()

    report = verify_required_reads(ws)
    assert report["ok"] is False
    assert READS[0] in report["missing"]


def test_ack_refuses_when_required_read_absent(tmp_path: Path):
    ws = _workspace(tmp_path, with_reads=False)
    with pytest.raises(GovernanceError) as exc:
        ack_required_reads(ws, session_id="sess-1")
    assert READS[0] in str(exc.value)


def test_no_session_file_fails(tmp_path: Path):
    ws = _workspace(tmp_path)
    report = verify_required_reads(ws)
    assert report["ok"] is False
    assert "无法核验" in report["detail"]


def test_cli_ack_reads_writes_session_file(tmp_path: Path):
    ws = _workspace(tmp_path)
    result = _run_cli(ws, "sessions", "ack-reads", "--session-id", "sess-cli", "--assignee", "claude_code")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "verify: PASS" in result.stdout

    payload = json.loads((ws / governance.SESSION_REL).read_text(encoding="utf-8"))
    assert payload["session_id"] == "sess-cli"
    assert len(payload["required_reads"]) == len(READS)


def test_cli_ack_reads_requires_session_id(tmp_path: Path):
    ws = _workspace(tmp_path)
    result = _run_cli(ws, "sessions", "ack-reads")
    assert result.returncode == 1
    assert "需要指定 --session-id" in result.stdout


# --------------------------------------------------------------------------
# 缺口 B：会话级配置覆盖层
# --------------------------------------------------------------------------
def _write_guard(path: Path, guard: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"concurrentGuard": guard}), encoding="utf-8")


def test_local_overlay_overrides_tracked_config(tmp_path: Path):
    ws = _workspace(tmp_path)
    _write_guard(ws / governance.TRACKED_CONFIG_REL, {})
    _write_guard(
        ws / governance.LOCAL_CONFIG_REL,
        {"expectedBranch": "feat/x", "baselineCommit": "abc1234", "watchPaths": ["ai_collab"]},
    )

    report = guard_input_report(ws)
    assert report["complete"] is True
    assert report["missing"] == []
    assert set(report["sources"].values()) == {governance.LOCAL_CONFIG_REL}


def test_partial_overlay_reports_sources(tmp_path: Path):
    ws = _workspace(tmp_path)
    _write_guard(
        ws / governance.TRACKED_CONFIG_REL,
        {"expectedBranch": "main", "baselineCommit": "abc1234"},
    )
    _write_guard(ws / governance.LOCAL_CONFIG_REL, {"watchPaths": ["ai_collab"]})

    report = guard_input_report(ws)
    assert report["complete"] is True
    assert report["sources"]["expectedBranch"] == governance.TRACKED_CONFIG_REL
    assert report["sources"]["baselineCommit"] == governance.TRACKED_CONFIG_REL
    assert report["sources"]["watchPaths"] == governance.LOCAL_CONFIG_REL
    # 覆盖层不得改写受跟踪文件本身。
    tracked = json.loads((ws / governance.TRACKED_CONFIG_REL).read_text(encoding="utf-8"))
    assert "watchPaths" not in tracked["concurrentGuard"]


def test_overlay_cannot_hide_tracked_values(tmp_path: Path):
    ws = _workspace(tmp_path)
    _write_guard(
        ws / governance.TRACKED_CONFIG_REL,
        {"expectedBranch": "main", "baselineCommit": "abc1234", "watchPaths": ["ai_collab"]},
    )
    _write_guard(ws / governance.LOCAL_CONFIG_REL, {"expectedBranch": "feat/y"})

    report = guard_input_report(ws)
    assert report["complete"] is True
    assert report["sources"]["expectedBranch"] == governance.LOCAL_CONFIG_REL
    assert report["sources"]["baselineCommit"] == governance.TRACKED_CONFIG_REL


# --------------------------------------------------------------------------
# 缺口 C：忽略规则的正反两侧
# --------------------------------------------------------------------------
def test_gitignore_allows_dev_logs_only(tmp_path: Path):
    """在本仓真实 .gitignore 上判定：开发日志放行，其他 logs/ 内容继续忽略。"""
    cases = {
        "logs/claude-code/2026-11/example.md": False,
        "logs/claude-code/2026-11/nested/deeper.md": False,
        "logs/collaboration_state.json": True,
        "logs/governance_coverage_observe.jsonl": True,
        "logs/workspace_forensics/report.json": True,
        "logs/handoff/HANDOFF.md": True,
        governance.LOCAL_CONFIG_REL: True,
        governance.SESSION_REL: True,
    }
    for rel, should_ignore in cases.items():
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", rel],
            capture_output=True,
            text=True,
        )
        ignored = proc.returncode == 0
        assert ignored is should_ignore, f"{rel}: 期望 ignored={should_ignore}，实际 {ignored}"


def test_dev_log_really_addable(tmp_path: Path):
    """反向证明：不是「check-ignore 说没忽略」就算，而是真能 add 进索引。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "g@example.com")
    _git(repo, "config", "user.name", "g")
    (repo / ".gitignore").write_text((REPO_ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    log = repo / "logs" / "claude-code" / "2026-11" / "day.md"
    log.parent.mkdir(parents=True)
    log.write_text("dev log\n", encoding="utf-8")
    state = repo / "logs" / "collaboration_state.json"
    state.write_text("{}", encoding="utf-8")

    _git(repo, "add", "logs/claude-code/2026-11/day.md")
    tracked = _git(repo, "diff", "--cached", "--name-only").splitlines()
    assert "logs/claude-code/2026-11/day.md" in tracked

    with pytest.raises(AssertionError):
        _git(repo, "add", "logs/collaboration_state.json")


# --------------------------------------------------------------------------
# 三条缺口同时收口后：preflight 才有机会全绿
# --------------------------------------------------------------------------
def _equip_all(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "g@example.com")
    _git(repo, "config", "user.name", "g")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    for rel in READS:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {rel}\n", encoding="utf-8")

    (repo / "logs").mkdir(exist_ok=True)
    (repo / "logs" / "collaboration_state.json").write_text(
        json.dumps({"last_updated": "2026-11-16T00:00:00", "tasks": {}, "patches": {}}), encoding="utf-8"
    )
    boundary = _git(repo, "rev-parse", "HEAD")
    ledger = repo / governance.LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps({"kind": "enforcement", "commit_sha": boundary, "reason": "验收用生效边界声明"}) + "\n",
        encoding="utf-8",
    )
    (repo / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps({"version": "1.0.0", "items": {"TASK-X": {"task_id": "TASK-X", "source": "cli-ack"}}}),
        encoding="utf-8",
    )
    _write_guard(
        repo / governance.LOCAL_CONFIG_REL,
        {"expectedBranch": "main", "baselineCommit": boundary, "watchPaths": ["ai_collab"]},
    )
    ack_required_reads(repo, session_id="sess-e2e")
    return repo


def test_preflight_passes_with_all_five_equipped(tmp_path: Path):
    repo = _equip_all(tmp_path)
    result = _run_cli(repo, "governance", "preflight")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight: PASS" in result.stdout
    assert "必读清单声明" in result.stdout
    assert "核验通过 4/4" in result.stdout


def test_preflight_fails_when_required_read_changes_after_ack(tmp_path: Path):
    repo = _equip_all(tmp_path)
    (repo / READS[1]).write_text("# 变了\n", encoding="utf-8")

    report = preflight(repo)
    reads = next(item for item in report["checks"] if item["name"] == "必读清单声明")
    assert reads["pass"] is False
    assert READS[1] in reads["stale"]
    assert report["pass"] is False
