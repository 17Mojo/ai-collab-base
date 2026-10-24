"""Unit tests for scripts/real_machine_regression.py.

守护的是**诚实性规则**，不是业务功能：

- 没有证据文件的 ``pass`` 不得被接受；
- L1 探针证据写着未验证（登录墙/拦截）却记成 ``pass``，必须被抓出来；
- 没跑就记 ``not-run``，且必须写原因；
- L1 与 L2 **不可互替**：L2 记 pass 而 L1 没有 pass 记录，属于不一致；
- 路线 A/B 决策门禁**永远**不会被这份记录判为关闭。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "real_machine_regression.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("real_machine_regression", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mod = _load_module()


def _make_run(workspace: Path, run_id: str = "RMR-TEST-001", platforms=("gemini",), locales=("zh-CN",)):
    args = mod.build_parser().parse_args(
        [
            "--workspace",
            str(workspace),
            "init",
            "--run-id",
            run_id,
            "--platforms",
            ",".join(platforms),
            "--locales",
            ",".join(locales),
            "--operator",
            "pytest",
        ]
    )
    assert mod.cmd_init(args) == 0
    return mod.record_path(workspace, run_id)


def _write_probe_verdict(path: Path, platform: str, outcome: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "layer": "L1-real-machine-dom-contract",
                "platforms": [{"platform": platform, "outcome": outcome}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _record(workspace: Path, run_id: str, **kwargs):
    argv = [
        "--workspace",
        str(workspace),
        "record",
        "--run-id",
        run_id,
        "--layer",
        kwargs.get("layer", "L1"),
        "--platform",
        kwargs.get("platform", "gemini"),
        "--status",
        kwargs.get("status", "pass"),
    ]
    if kwargs.get("locale"):
        argv += ["--locale", kwargs["locale"]]
    for item in kwargs.get("evidence", []):
        argv += ["--evidence", item]
    for item in kwargs.get("evidence_file", []):
        argv += ["--evidence-file", item]
    if kwargs.get("reason"):
        argv += ["--reason", kwargs["reason"]]
    args = mod.build_parser().parse_args(argv)
    return mod.cmd_record(args)


def test_init_creates_run_record(tmp_path):
    path = _make_run(tmp_path)
    run = json.loads(path.read_text(encoding="utf-8"))
    assert run["run_id"] == "RMR-TEST-001"
    assert run["platforms"] == ["gemini"]
    assert run["records"] == []


def test_init_refuses_to_overwrite_without_force(tmp_path):
    _make_run(tmp_path)
    args = mod.build_parser().parse_args(
        [
            "--workspace",
            str(tmp_path),
            "init",
            "--run-id",
            "RMR-TEST-001",
            "--platforms",
            "gemini",
            "--locales",
            "zh-CN",
        ]
    )
    assert mod.cmd_init(args) == 1


def test_record_requires_evidence_for_pass(tmp_path):
    _make_run(tmp_path)
    assert _record(tmp_path, "RMR-TEST-001", status="pass", evidence=[], evidence_file=[]) == 1
    assert _record(tmp_path, "RMR-TEST-001", status="pass", evidence=["结论"], evidence_file=[]) == 1


def test_record_requires_reason_for_not_run(tmp_path):
    _make_run(tmp_path)
    assert _record(tmp_path, "RMR-TEST-001", status="not-run", reason="") == 1


def test_record_requires_locale_for_l1(tmp_path):
    _make_run(tmp_path)
    assert _record(tmp_path, "RMR-TEST-001", layer="L1", locale="") == 1


def test_record_updates_instead_of_duplicating(tmp_path):
    _make_run(tmp_path)
    evidence = _write_probe_verdict(tmp_path / "ev.json", "gemini", "pass")
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            status="pass",
            locale="zh-CN",
            evidence=["首轮"],
            evidence_file=[str(evidence)],
        )
        == 0
    )
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            status="unverified",
            locale="zh-CN",
            reason="改口径：探针命中登录墙",
        )
        == 0
    )
    run = json.loads((tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json").read_text(encoding="utf-8"))
    assert len(run["records"]) == 1
    assert run["records"][0]["status"] == "unverified"


def test_verify_flags_pass_without_evidence_file(tmp_path):
    _make_run(tmp_path)
    # 直接构造一条「有结论、无证据文件」的记录（绕过 CLI 的入口校验）
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run["records"] = [
        {
            "layer": "L1",
            "platform": "gemini",
            "status": "pass",
            "locale": "zh-CN",
            "checked_at": "2026-10-25T00:00:00+08:00",
            "evidence": ["自称通过"],
            "evidence_files": [],
            "reason": "",
            "notes": "",
        }
    ]
    path.write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")

    errors, verdict, complete = mod.verify_run(run, tmp_path)
    assert any("evidence_file" in e for e in errors)
    assert verdict == "l1-only"
    assert complete is False


def test_verify_flags_missing_evidence_file_on_disk(tmp_path):
    _make_run(tmp_path)
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run["records"] = [
        {
            "layer": "L1",
            "platform": "gemini",
            "status": "pass",
            "locale": "zh-CN",
            "checked_at": "2026-10-25T00:00:00+08:00",
            "evidence": ["结论"],
            "evidence_files": ["does-not-exist.json"],
            "reason": "",
            "notes": "",
        }
    ]
    errors, _verdict, _complete = mod.verify_run(run, tmp_path)
    assert any("证据文件不存在" in e for e in errors)


def test_verify_cross_checks_probe_evidence_against_claim(tmp_path):
    """探针证据写着 unverified，记录却写 pass —— 必须判为不一致。"""
    _make_run(tmp_path)
    evidence = _write_probe_verdict(tmp_path / "ev.json", "gemini", "login_wall")
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            status="pass",
            locale="zh-CN",
            evidence=["我以为通过了"],
            evidence_file=[str(evidence)],
        )
        == 0
    )
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    errors, _verdict, _complete = mod.verify_run(run, tmp_path)
    assert any("证据与结论不符" in e for e in errors)


def test_verify_requires_l2_record_for_every_platform(tmp_path):
    _make_run(tmp_path, platforms=("gemini", "claude"))
    evidence = _write_probe_verdict(tmp_path / "ev.json", "gemini", "pass")
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            layer="L1",
            platform="gemini",
            status="pass",
            locale="zh-CN",
            evidence=["通过"],
            evidence_file=[str(evidence)],
        )
        == 0
    )
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    errors, verdict, complete = mod.verify_run(run, tmp_path)
    assert any("缺 L1 记录" in e for e in errors)
    assert any("缺 L2 记录" in e for e in errors)
    assert verdict == "partial"
    assert complete is False


def test_verify_rejects_l2_pass_without_l1_pass(tmp_path):
    _make_run(tmp_path)
    evidence = _write_probe_verdict(tmp_path / "ev.json", "gemini", "pass")
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            layer="L1",
            platform="gemini",
            status="unverified",
            locale="zh-CN",
            reason="探针命中登录墙",
        )
        == 0
    )
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            layer="L2",
            platform="gemini",
            status="pass",
            locale="zh-CN",
            evidence=["人工发送成功"],
            evidence_file=[str(evidence)],
        )
        == 0
    )
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    errors, _verdict, _complete = mod.verify_run(run, tmp_path)
    assert any("L2 记为 pass，但 L1 没有 pass 的记录" in e for e in errors)


def test_verify_verdict_l1_only_when_l2_not_run(tmp_path):
    _make_run(tmp_path)
    evidence = _write_probe_verdict(tmp_path / "ev.json", "gemini", "pass")
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            layer="L1",
            platform="gemini",
            status="pass",
            locale="zh-CN",
            evidence=["通过"],
            evidence_file=[str(evidence)],
        )
        == 0
    )
    assert (
        _record(
            tmp_path,
            "RMR-TEST-001",
            layer="L2",
            platform="gemini",
            status="not-run",
            reason="无已登录 profile",
        )
        == 0
    )
    path = tmp_path / "collaboration" / "results" / "real-machine-runs" / "RMR-TEST-001.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    errors, verdict, complete = mod.verify_run(run, tmp_path)
    assert errors == []
    assert verdict == "l1-only"
    assert complete is False


def test_route_gate_note_never_claims_closure():
    assert "第一个外部用户" in mod.ROUTE_GATE_NOTE
    assert "不得据此拍板路线" in mod.ROUTE_GATE_NOTE


def test_list_skips_probe_evidence_files(tmp_path, capsys):
    """同目录下的 L1 探针证据 JSON 不是 run 记录，list 必须跳过而不是误报。"""
    _make_run(tmp_path)
    evidence = _write_probe_verdict(tmp_path / "evidence" / "L1-gemini.json", "gemini", "pass")
    args = mod.build_parser().parse_args(["--workspace", str(tmp_path), "list"])
    assert mod.cmd_list(args) == 0
    out = capsys.readouterr().out
    assert "RMR-TEST-001" in out
    assert "L1-gemini" not in out
    assert evidence.exists()


@pytest.mark.parametrize("status", ["pass", "fail", "unverified", "not-run"])
def test_status_vocabulary_is_fixed(status):
    assert status in mod.STATUSES
