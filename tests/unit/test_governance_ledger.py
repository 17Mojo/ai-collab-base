"""治理账本统一写入入口：一致性扫描、跨进程互斥、原子替换、运行时守卫。

覆盖 openspec/changes/restore-governance-enforcement/specs/governance-coverage/spec.md
的「治理账本写入互斥与原子性」四个 Scenario，以及 1.4 的一致性校验硬门禁。
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_collab import ack_protocol, governance
from ai_collab.governance import (
    COVERAGE_IN_DECISION,
    GovernanceError,
    append_jsonl,
    check_direct_writes,
    evaluate_coverage,
    file_lock,
    find_direct_state_writes,
    guard_input_report,
    input_contract_complete,
    is_managed_ledger,
    lock_path_for,
    locked_json_update,
    merge_state_write,
    preflight,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCRIPT = REPO_ROOT / "scripts" / "agent_receipt_bridge.py"

# 两个独立进程同时写同一账本；用 go 文件做发令枪，避免依赖 multiprocessing 的
# spawn/pickle 差异。mutate 内短暂 sleep 放大临界区，裸写必然丢一条记录。
_CONCURRENT_WORKER = r"""
import os
import pathlib
import sys
import time

sys.path.insert(0, os.environ["GOV_REPO_ROOT"])
from ai_collab.governance import locked_json_update

target = pathlib.Path(os.environ["GOV_TARGET"])
go = pathlib.Path(os.environ["GOV_GO"])
key = os.environ["GOV_KEY"]
deadline = time.time() + 15
while not go.exists() and time.time() < deadline:
    time.sleep(0.005)

def mutate(payload):
    items = payload.setdefault("items", {})
    time.sleep(0.05)
    items[key] = {"owner": key}
    return key

locked_json_update(target, {"items": {}}, mutate)
print("ok")
"""


def _load_receipt_module():
    spec = importlib.util.spec_from_file_location("_receipt_bridge_under_test", RECEIPT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "logs").mkdir(parents=True)
    (ws / ".vscode").mkdir(parents=True)
    return ws


# --------------------------------------------------------------------------
# 一致性扫描：先证明扫描器本身不是假绿
# --------------------------------------------------------------------------
def test_scanner_detects_injected_direct_write(tmp_path: Path):
    ws = tmp_path / "scan"
    (ws / "ai_collab").mkdir(parents=True)
    (ws / "ai_collab" / "bad_writer.py").write_text(
        "from pathlib import Path\n\n"
        "def bad(workspace):\n"
        '    state_file = workspace / "logs" / "collaboration_state.json"\n'
        '    state_file.write_text("{}", encoding="utf-8")\n',
        encoding="utf-8",
    )
    hits = find_direct_state_writes(ws)
    assert len(hits) == 1
    assert hits[0].startswith("ai_collab/bad_writer.py:")
    assert hits[0].endswith("write_text()")

    report = check_direct_writes(ws)
    assert report["pass"] is False
    assert report["checked"] == 1
    assert report["hits"] == hits


def test_scanner_accepts_unified_entry_and_non_ledger_reports(tmp_path: Path):
    ws = tmp_path / "scan"
    (ws / "scripts").mkdir(parents=True)
    (ws / "scripts" / "good_writer.py").write_text(
        "from ai_collab.governance import locked_json_update\n\n"
        "def good(workspace):\n"
        '    locked_json_update(workspace / "logs" / "collaboration_state.json", {}, lambda p: None)\n'
        '    report = workspace / "logs" / "some_report.json"\n'
        '    report.write_text("{}", encoding="utf-8")\n',
        encoding="utf-8",
    )
    assert find_direct_state_writes(ws) == []
    assert check_direct_writes(ws)["pass"] is True


def test_scanner_isolates_same_local_name_across_functions(tmp_path: Path):
    """同名局部变量在读函数里指向账本，在写函数里指向别的文件，不得误报。"""
    ws = tmp_path / "scan"
    (ws / "scripts").mkdir(parents=True)
    (ws / "scripts" / "bridge.py").write_text(
        "def reader(workspace):\n"
        '    state_file = workspace / "logs" / "collaboration_state.json"\n'
        "    return state_file.read_text()\n\n"
        "def writer(workspace):\n"
        '    state_file = workspace / "logs" / "agent_dispatch_state.json"\n'
        '    state_file.write_text("{}", encoding="utf-8")\n',
        encoding="utf-8",
    )
    assert find_direct_state_writes(ws) == []


def test_repository_has_no_direct_state_writes():
    """真实仓库：所有受管账本写入都必须已收口到统一入口。"""
    assert find_direct_state_writes(REPO_ROOT) == []
    assert check_direct_writes(REPO_ROOT)["pass"] is True


def test_receipt_bridge_guard_table_matches_governance():
    """脚本可单独拷走执行，兜底表必须与治理模块常量逐项一致。"""
    module = _load_receipt_module()
    assert tuple(module._MANAGED_LEDGER_FILENAMES) == governance.LEDGER_FILENAMES


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("logs/collaboration_state.json", True),
        ("logs/agent_ack_bridge_state.json", True),
        ("logs/agent_receipt_state.json", True),
        ("logs/agent_dispatch_state.json", False),
        ("logs/session_registry_state.json", False),
        ("logs/some_report.json", False),
    ],
)
def test_is_managed_ledger(path: str, expected: bool):
    assert is_managed_ledger(path) is expected


# --------------------------------------------------------------------------
# 跨进程互斥 / 原子替换 / fail-loud
# --------------------------------------------------------------------------
def test_two_processes_concurrent_registration(tmp_path: Path):
    """Scenario: 两个执行主体并发登记 → 两条都在、文件合法、无丢失。"""
    target = tmp_path / "logs" / "collaboration_state.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"items": {}}), encoding="utf-8")
    go = tmp_path / "go"
    base_env = dict(os.environ)
    base_env.update(
        {
            "GOV_REPO_ROOT": str(REPO_ROOT),
            "GOV_TARGET": str(target),
            "GOV_GO": str(go),
        }
    )
    procs = []
    for key in ("A", "B"):
        env = dict(base_env)
        env["GOV_KEY"] = key
        procs.append(
            subprocess.Popen(
                [sys.executable, "-c", _CONCURRENT_WORKER],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    go.touch()
    for proc in procs:
        _, err = proc.communicate(timeout=30)
        assert proc.returncode == 0, err

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert set(payload["items"]) == {"A", "B"}
    assert payload["items"]["A"] == {"owner": "A"}
    assert payload["items"]["B"] == {"owner": "B"}


def test_atomic_write_interrupted_keeps_previous_content(tmp_path: Path, monkeypatch):
    """Scenario: 替换前中断 → 目标保持完整内容，不留被当账本读取的半截文件。"""
    target = tmp_path / "logs" / "agent_ack_bridge_state.json"
    target.parent.mkdir(parents=True)
    before = json.dumps({"items": {"A": 1}}, indent=2)
    target.write_text(before, encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("simulated interruption before os.replace")

    monkeypatch.setattr(governance.os, "replace", boom)
    with pytest.raises(OSError):
        locked_json_update(target, {}, lambda payload: payload["items"].update({"B": 2}))

    monkeypatch.undo()
    assert target.read_text(encoding="utf-8") == before
    assert json.loads(target.read_text(encoding="utf-8"))["items"] == {"A": 1}
    assert list(target.parent.glob(".gov_tmp_*")) == []


def test_lock_contention_timeout_is_explicit(tmp_path: Path):
    """Scenario: 锁争用超过阈值 → 明确超时，不静默放弃写入。"""
    target = tmp_path / "logs" / "collaboration_state.json"
    target.parent.mkdir(parents=True)
    lock = lock_path_for(target)
    lock.write_text("other|99999|2026-11-15T00:00:00\n", encoding="utf-8")
    try:
        with pytest.raises(TimeoutError):
            with file_lock(target, timeout_sec=0.2, poll_interval=0.02):
                pass
    finally:
        lock.unlink(missing_ok=True)


def test_corrupted_ledger_fails_loud(tmp_path: Path):
    """半截账本不能被静默当成空账本重置后覆盖。"""
    target = tmp_path / "logs" / "collaboration_state.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"items": {"A":', encoding="utf-8")
    with pytest.raises(GovernanceError, match="账本内容损坏"):
        locked_json_update(target, {}, lambda payload: None)
    assert target.read_text(encoding="utf-8") == '{"items": {"A":'


def test_locked_json_update_reads_latest_inside_lock(tmp_path: Path):
    target = tmp_path / "logs" / "agent_receipt_state.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"items": {"A": 1}}), encoding="utf-8")

    def mutate(payload):
        assert payload["items"] == {"A": 1}
        payload["items"]["B"] = 2
        return len(payload["items"])

    payload, result = locked_json_update(target, {}, mutate)
    assert result == 2
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_merge_state_write_preserves_concurrent_keys(tmp_path: Path):
    target = tmp_path / "logs" / "collaboration_state.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"tasks": {"OTHER": {"status": "pending"}}}), encoding="utf-8")
    merge_state_write(target, {"tasks": {"MINE": {"status": "completed"}}})
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert set(payload["tasks"]) == {"OTHER", "MINE"}
    assert payload["tasks"]["OTHER"]["status"] == "pending"


def test_append_jsonl_is_line_oriented(tmp_path: Path):
    path = tmp_path / "logs" / "governance-ledger.jsonl"
    append_jsonl(path, {"kind": "commit", "n": 1})
    append_jsonl(path, {"kind": "commit", "n": 2})
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["n"] for row in rows] == [1, 2]


# --------------------------------------------------------------------------
# 运行时守卫：动态路径也拦得住
# --------------------------------------------------------------------------
def test_ack_protocol_write_json_guards_managed_ledger(tmp_path: Path):
    ledger = tmp_path / "logs" / "collaboration_state.json"
    ledger.parent.mkdir(parents=True)
    with pytest.raises(GovernanceError, match="禁止直接覆写"):
        ack_protocol.write_json(ledger, {"tasks": {}})
    assert not ledger.exists()

    report = tmp_path / "logs" / "report.json"
    ack_protocol.write_json(report, {"ok": True})
    assert json.loads(report.read_text(encoding="utf-8")) == {"ok": True}


def test_receipt_bridge_write_json_guards_managed_ledger(tmp_path: Path):
    module = _load_receipt_module()
    ledger = tmp_path / "logs" / "agent_receipt_state.json"
    ledger.parent.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="禁止直接覆写"):
        module.write_json(ledger, {"items": {}})
    assert not ledger.exists()


def test_record_ack_bridge_writes_through_unified_entry(tmp_path: Path):
    """改造后单进程可观测行为不变，且落盘走统一入口。"""
    ws = _workspace(tmp_path)
    record = ack_protocol.record_ack_bridge(
        workspace=ws,
        task_id="TASK-GOV-001",
        assignee="claude_code",
        result_file="collaboration/results/RESULT_TASK-GOV-001.md",
        completed_at="2026-11-15T10:00:00",
        source="cli-ack",
        bridged_at="2026-11-15T10:00:00",
    )
    assert record["ack_line"].startswith("C.ACK|task=TASK-GOV-001|status=ok")
    state = json.loads((ws / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8"))
    assert state["items"]["TASK-GOV-001"]["source"] == "cli-ack"
    assert state["version"] == "1.0.0"


def test_record_ack_bridge_dry_run_does_not_write(tmp_path: Path):
    ws = _workspace(tmp_path)
    record = ack_protocol.record_ack_bridge(
        workspace=ws,
        task_id="TASK-GOV-002",
        assignee="claude_code",
        result_file="collaboration/results/R.md",
        completed_at="2026-11-15T10:00:00",
        source="cli-ack",
        bridged_at="2026-11-15T10:00:00",
        dry_run=True,
    )
    assert record["task_id"] == "TASK-GOV-002"
    assert not (ws / "logs" / "agent_ack_bridge_state.json").exists()


# --------------------------------------------------------------------------
# 门禁输入契约 / 观测期决策冻结（Phase 3、Phase 4 前置）
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("branch", "baseline", "watch", "expected"),
    [
        ("main", "abc1234", ["ai_collab"], True),
        ("main", "abc1234", [], False),
        ("main", None, ["ai_collab"], False),
        (None, "abc1234", ["ai_collab"], False),
        (None, None, [], False),
    ],
)
def test_input_contract_complete(branch, baseline, watch, expected):
    assert input_contract_complete(branch, baseline, watch) is expected


def test_guard_input_report_names_missing_inputs(tmp_path: Path):
    ws = _workspace(tmp_path)
    (ws / ".vscode" / "ai-collab.json").write_text(json.dumps({"concurrentGuard": {}}), encoding="utf-8")
    report = guard_input_report(ws)
    assert report["complete"] is False
    assert report["missing"] == ["expectedBranch", "baselineCommit", "watchPaths"]

    (ws / ".vscode" / "ai-collab.json").write_text(
        json.dumps(
            {
                "concurrentGuard": {
                    "expectedBranch": "main",
                    "baselineCommit": "abc1234",
                    "watchPaths": ["ai_collab"],
                }
            }
        ),
        encoding="utf-8",
    )
    assert guard_input_report(ws) == {"complete": True, "missing": []}


def test_preflight_fails_when_guard_not_equipped(tmp_path: Path):
    ws = _workspace(tmp_path)
    (ws / ".vscode" / "ai-collab.json").write_text(json.dumps({"concurrentGuard": {}}), encoding="utf-8")
    (ws / "logs" / "collaboration_state.json").write_text(
        json.dumps({"last_updated": "2026-11-15T00:00:00"}), encoding="utf-8"
    )
    report = preflight(ws)
    checks = {item["name"]: item for item in report["checks"]}
    assert report["pass"] is False
    assert checks["状态机时效"]["pass"] is True
    assert checks["门禁输入完整性"]["pass"] is False
    assert "expectedBranch" in checks["门禁输入完整性"]["detail"]
    assert checks["HEAD 治理登记"]["pass"] is False


def test_coverage_gate_enabled_after_phase4_flip(tmp_path: Path):
    """Phase 4 已翻闸：事实源不可用时必须引红，不得静默放过。"""
    assert COVERAGE_IN_DECISION is True
    ws = _workspace(tmp_path)
    report = evaluate_coverage(ws, {"invalid_count": 0, "valid": True})
    assert report["observe"]["decision_enabled"] is True
    assert report["observe"]["applied"] is True
    assert report["observe"]["coverage_available"] is False
    observe_file = ws / "logs" / governance.OBSERVE_REL.split("/", 1)[1]
    assert observe_file.exists()
    rows = [json.loads(line) for line in observe_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["would_fail"] is True
    assert rows[0]["applied"] is True


# --------------------------------------------------------------------------
# CLI 级证据：1.4「检出即非零退出并点名文件」
# --------------------------------------------------------------------------
def _run_cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "ai_collab.cli", "--workspace", str(workspace), "governance", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_check_writes_passes_on_clean_workspace():
    result = _run_cli(REPO_ROOT, "check-writes")
    assert result.returncode == 0, result.stderr
    assert "一致性校验通过" in result.stdout


def test_cli_check_writes_fails_and_names_violation(tmp_path: Path):
    ws = tmp_path / "scan"
    (ws / "ai_collab").mkdir(parents=True)
    (ws / "ai_collab" / "bad.py").write_text(
        "def bad(workspace):\n"
        '    state_file = workspace / "logs" / "collaboration_state.json"\n'
        '    state_file.write_text("{}", encoding="utf-8")\n',
        encoding="utf-8",
    )
    result = _run_cli(ws, "check-writes")
    assert result.returncode == 1
    assert "ai_collab/bad.py:" in result.stderr
    assert "write_text()" in result.stderr
    assert "不得声明多执行主体模式可启用" in result.stderr


def test_cli_preflight_fails_when_guard_not_equipped(tmp_path: Path):
    ws = _workspace(tmp_path)
    (ws / ".vscode" / "ai-collab.json").write_text(json.dumps({"concurrentGuard": {}}), encoding="utf-8")
    result = _run_cli(ws, "preflight")
    assert result.returncode == 1
    assert "[FAIL] 门禁输入完整性" in result.stdout
    assert "expectedBranch" in result.stdout
    assert "preflight: FAIL" in result.stdout


# --------------------------------------------------------------------------
# Phase 2/3：观测期决策冻结、输入完整性独立信号、既有结论零改变
# --------------------------------------------------------------------------
def _run_tasks_cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "ai_collab.cli", "--workspace", str(workspace), "tasks", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_concurrent_guard_adds_input_contract_without_changing_risk(tmp_path: Path, monkeypatch):
    from ai_collab import concurrent_guard

    baseline_assessment = {
        "risk_level": "low",
        "allowed": True,
        "git_context": {},
        "signals": {},
        "violations": [],
        "warnings": [],
    }
    monkeypatch.setattr(concurrent_guard, "assess_concurrent_risk", lambda *a, **k: dict(baseline_assessment))

    empty = concurrent_guard.run_concurrent_guard(workspace=tmp_path)
    full = concurrent_guard.run_concurrent_guard(
        workspace=tmp_path,
        expected_branch="main",
        baseline_commit="abc1234",
        watch_paths=["ai_collab"],
    )
    assert empty["input_contract_complete"] is False
    assert full["input_contract_complete"] is True
    for key in ("risk_level", "allowed", "violations", "warnings"):
        assert empty[key] == baseline_assessment[key]
        assert full[key] == baseline_assessment[key]

    # 反向测试：移除新增信号字段后，既有报告逐位一致（仅时间戳为动态值）。
    def strip_signal(report):
        return {k: v for k, v in report.items() if k not in {"generated_at", "input_contract_complete"}}

    assert strip_signal(empty) == strip_signal(full)


def test_coverage_signal_can_be_disabled_and_restored(tmp_path: Path, monkeypatch):
    """反向测试：总闸可关闭、可恢复，且判定值与关闭前一致。"""
    ws = _workspace(tmp_path)
    enabled = evaluate_coverage(ws, {"invalid_count": 0, "valid": True})
    assert enabled["observe"]["decision_enabled"] is True
    assert enabled["observe"]["applied"] is True

    monkeypatch.setattr(governance, "COVERAGE_IN_DECISION", False)
    frozen = evaluate_coverage(ws, {"invalid_count": 0, "valid": True})
    assert frozen["observe"]["applied"] is False
    assert frozen["observe"]["would_fail"] == enabled["observe"]["would_fail"]

    monkeypatch.undo()
    restored = evaluate_coverage(ws, {"invalid_count": 0, "valid": True})
    assert restored["observe"]["applied"] == enabled["observe"]["applied"]


def test_observation_record_is_reviewable_and_append_only(tmp_path: Path):
    ws = _workspace(tmp_path)
    evaluate_coverage(ws, {"invalid_count": 2, "valid": False})
    evaluate_coverage(ws, {"invalid_count": 0, "valid": True})
    observe_file = ws / "logs" / governance.OBSERVE_REL.split("/", 1)[1]
    rows = [json.loads(line) for line in observe_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    for row in rows:
        for key in ("input_summary", "current_conclusion", "hypothetical_conclusion", "differs"):
            assert key in row
    assert rows[0]["input_summary"]["invalid_count"] == 2
    assert rows[1]["input_summary"]["invalid_count"] == 0


# --------------------------------------------------------------------------
# Phase 4 验收场景 A1-A6（4.2-4.7）
# --------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _prepare_workspace(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "gov@example.com")
    _git(repo, "config", "user.name", "gov")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    (repo / "logs").mkdir(exist_ok=True)
    (repo / "logs" / "collaboration_state.json").write_text(
        json.dumps({"last_updated": "2026-11-15T00:00:00", "tasks": {}, "patches": {}}),
        encoding="utf-8",
    )
    return repo


def _add_merge(repo: Path, name: str) -> str:
    _git(repo, "checkout", "-q", "-b", f"feat/{name}")
    (repo / f"{name}.txt").write_text(name, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", name)
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-q", f"feat/{name}", "-m", f"merge {name}")
    return _git(repo, "rev-parse", "HEAD")


def _enforcement(boundary: str) -> dict:
    return {
        "kind": "enforcement",
        "commit_sha": boundary,
        "reason": "启用覆盖率判定的生效边界",
        "declared_at": "2026-11-15T00:00:00",
        "declared_by": "test",
    }


def _write_ledger(repo: Path, rows: list[dict]) -> Path:
    path = repo / governance.LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    return path


def test_acceptance_a1_undeclared_merge_fails_strict(tmp_path: Path):
    repo = _prepare_workspace(tmp_path)
    boundary = _git(repo, "rev-parse", "HEAD")
    merge = _add_merge(repo, "one")
    _write_ledger(repo, [_enforcement(boundary)])

    result = _run_tasks_cli(repo, "validate-contract", "--scope", "active", "--strict")
    assert result.returncode == 1
    assert merge in result.stderr
    assert "未登记合并提交" in result.stderr
    assert "契约校验结果" in result.stdout


def test_acceptance_a2_declared_merge_passes(tmp_path: Path):
    repo = _prepare_workspace(tmp_path)
    boundary = _git(repo, "rev-parse", "HEAD")
    merge = _add_merge(repo, "one")
    _write_ledger(repo, [_enforcement(boundary)])

    decl = _run_cli(
        repo,
        "declare-commit",
        "--commit-sha",
        merge,
        "--change-id",
        "restore-governance-enforcement",
        "--reason",
        "该合并属于本次治理恢复 change 的实施提交",
    )
    assert decl.returncode == 0, decl.stderr

    result = _run_tasks_cli(repo, "validate-contract", "--scope", "active", "--strict")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "gap_count=0" in result.stdout


def test_acceptance_a3_merges_before_boundary_not_flagged(tmp_path: Path):
    repo = _prepare_workspace(tmp_path)
    early = _add_merge(repo, "early")
    boundary = _git(repo, "rev-parse", "HEAD")
    late = _add_merge(repo, "late")
    _write_ledger(repo, [_enforcement(boundary)])

    coverage = governance.compute_coverage(repo)
    assert coverage["available"] is True
    assert coverage["gaps"] == [late]
    assert early not in coverage["gaps"]

    result = _run_tasks_cli(repo, "validate-contract", "--scope", "active", "--strict")
    assert result.returncode == 1
    assert late in result.stderr
    assert early not in result.stderr


def test_acceptance_a4_missing_or_corrupt_ledger_fails(tmp_path: Path):
    repo = _prepare_workspace(tmp_path)
    _add_merge(repo, "one")

    missing = _run_tasks_cli(repo, "validate-contract", "--scope", "active", "--strict")
    assert missing.returncode == 1
    assert "登记表缺失" in missing.stderr

    path = repo / governance.LEDGER_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json\n", encoding="utf-8")
    corrupt = _run_tasks_cli(repo, "validate-contract", "--scope", "active", "--strict")
    assert corrupt.returncode == 1
    assert "无法解析" in corrupt.stderr


def test_acceptance_a5_guard_not_equipped_fails_preflight_but_keeps_risk(tmp_path: Path, monkeypatch):
    from ai_collab import concurrent_guard

    baseline_assessment = {
        "risk_level": "low",
        "allowed": True,
        "git_context": {},
        "signals": {},
        "violations": [],
        "warnings": [],
    }
    monkeypatch.setattr(concurrent_guard, "assess_concurrent_risk", lambda *a, **k: dict(baseline_assessment))
    ws = _workspace(tmp_path)
    (ws / ".vscode" / "ai-collab.json").write_text(json.dumps({"concurrentGuard": {}}), encoding="utf-8")

    report = concurrent_guard.run_concurrent_guard(workspace=ws)
    assert report["input_contract_complete"] is False
    assert report["risk_level"] == "low"
    assert report["allowed"] is True

    result = _run_cli(ws, "preflight")
    assert result.returncode == 1
    assert "preflight: FAIL" in result.stdout
    assert "未装备" in result.stdout


def test_acceptance_a6_preflight_passes_with_all_inputs(tmp_path: Path):
    repo = _prepare_workspace(tmp_path)
    boundary = _git(repo, "rev-parse", "HEAD")
    _write_ledger(repo, [_enforcement(boundary)])
    (repo / ".ai_collab_session.json").write_text(
        json.dumps({"required_reads_acknowledged": list(governance.REQUIRED_READS)}), encoding="utf-8"
    )
    (repo / ".vscode").mkdir(exist_ok=True)
    (repo / ".vscode" / "ai-collab.json").write_text(
        json.dumps(
            {
                "concurrentGuard": {
                    "expectedBranch": "main",
                    "baselineCommit": boundary,
                    "watchPaths": ["ai_collab"],
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {"TASK-GOV-RESTORE-001": {"task_id": "TASK-GOV-RESTORE-001", "source": "cli-ack"}},
            }
        ),
        encoding="utf-8",
    )

    result = _run_cli(repo, "preflight")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight: PASS" in result.stdout
