"""CLI 层 `pack trending` 行为门禁（契约 TASK-P1-TRENDING-CLI-001 R5）。

本文件只守护 CLI 这一层：参数透传、正数校验、口径标注。
排序/窗口边界逻辑属 store 层（`tests/unit/test_pack_store.py`），此处不重复守护。
"""

import sys
from types import SimpleNamespace

import pytest

import ai_collab.cli as cli
import ai_collab.prompt_pack.store as store_mod


def _make_pack(name="demo-pack", version="1.0.0", rating=4.5, downloads=100):
    return SimpleNamespace(
        name=name,
        version=version,
        rating=rating,
        downloads=downloads,
    )


def _run_trending(monkeypatch, capsys, *, days, limit=10, packs=None):
    """调用 CLI 的 pack trending 分支，返回 (退出码, stdout, store 调用捕获)。"""
    captured = {}

    class FakeEngine:
        def get_trending_packs(self, days=7, limit=10):
            captured["days"] = days
            captured["limit"] = limit
            return list(packs or [])

    monkeypatch.setattr(store_mod, "create_pack_store", lambda *a, **k: FakeEngine())

    args = SimpleNamespace(store_subcommand="trending", days=days, limit=limit)
    code = cli._handle_store_command(args, "packs")
    return code, capsys.readouterr().out, captured


def test_default_days_7_passed_to_store(monkeypatch, capsys):
    code, out, captured = _run_trending(monkeypatch, capsys, days=7)
    assert code == 0
    assert captured["days"] == 7
    assert "7天内" in out


@pytest.mark.parametrize("days", [1, 30])
def test_days_passed_through(monkeypatch, capsys, days):
    code, _out, captured = _run_trending(monkeypatch, capsys, days=days)
    assert code == 0
    assert captured["days"] == days


@pytest.mark.parametrize("days", [0, -1])
def test_non_positive_days_rejected_before_store_call(monkeypatch, capsys, days):
    code, out, captured = _run_trending(monkeypatch, capsys, days=days)
    assert code == 1
    assert "必须为正整数" in out
    assert out.count("\n") <= 1
    assert "days" not in captured


def test_limit_zero_returns_empty_with_exit_zero(monkeypatch, capsys):
    code, out, captured = _run_trending(monkeypatch, capsys, days=7, limit=0, packs=[])
    assert code == 0
    assert captured["limit"] == 0
    assert "  1. " not in out


def test_title_reflects_actual_days(monkeypatch, capsys):
    _code, out, _captured = _run_trending(monkeypatch, capsys, days=30)
    assert "30天内" in out
    assert "7天内" not in out


def test_row_marks_downloads_as_cumulative(monkeypatch, capsys):
    _code, out, _captured = _run_trending(
        monkeypatch, capsys, days=7, packs=[_make_pack(downloads=42)]
    )
    assert "累计 42 下载" in out


@pytest.mark.parametrize(
    ("argv", "expected_days"),
    [
        (["ai-collab", "pack", "trending"], 7),
        (["ai-collab", "pack", "trending", "--days", "30"], 30),
    ],
)
def test_parser_exposes_days(monkeypatch, capsys, argv, expected_days):
    """argparse 层：`--days` 可解析且默认 7（保持既有默认行为）。"""
    captured = {}

    class FakeEngine:
        def get_trending_packs(self, days=7, limit=10):
            captured["days"] = days
            captured["limit"] = limit
            return []

    monkeypatch.setattr(store_mod, "create_pack_store", lambda *a, **k: FakeEngine())
    monkeypatch.setattr(sys, "argv", argv)

    assert cli.main() == 0
    assert captured["days"] == expected_days
    assert f"{expected_days}天内" in capsys.readouterr().out
