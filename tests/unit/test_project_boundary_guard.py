"""项目边界守护：pytest 收集边界（设计文档 §6.3 / OpenSpec Phase 4.1）。

2026-09-26 的事故根因是「仓库根目录下存放了外部项目副本」——pytest 收集到那些
目录里的测试文件，触发 `ModuleNotFoundError`，主套件整体不可用。

正解不是 `norecursedirs`（那是掩盖，不是解决），而是两条一起守：
1. `testpaths` 限定 `tests/`（收集面收窄）；
2. `tests/` 之外不存放任何 pytest 会收集的测试文件（根因消除）。

本文件是这两条的**防回归断言**。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests"

# 跳过与「本仓源码」无关的目录：版本控制/虚拟环境/构建产物/缓存/运行时日志。
# 其中 logs/ 是 gitignored 的运行时产物目录（门禁报告、开发日志都落在这里），
# 不属于版本库内容，不纳入边界断言。
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".eggs",
    ".tox",
    ".nox",
    "dist",
    "build",
    "htmlcov",
    "site-packages",
    "logs",
}

COLLECTABLE_TEST_PATTERNS = ("test_*.py", "*_test.py")


def _collectable_files_outside_tests() -> list[str]:
    """列出 `tests/` 之外所有 pytest 会收集的测试文件（相对仓库根）。"""
    hits: list[str] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(PROJECT_ROOT).parts):
            continue
        if path.parent == TESTS_DIR or TESTS_DIR in path.parents:
            continue
        if any(path.match(pattern) for pattern in COLLECTABLE_TEST_PATTERNS):
            hits.append(str(path.relative_to(PROJECT_ROOT)))
    return sorted(hits)


def test_testpaths_limited_to_tests(pytestconfig):
    """`testpaths` 必须包含 `tests`——由 pytest 自己解析出的生效值，不是文本匹配。"""
    testpaths = pytestconfig.getini("testpaths")

    assert testpaths, "pytest 未解析出 testpaths（pyproject.toml 的 [tool.pytest.ini_options] 段？）"
    assert "tests" in testpaths


def test_no_collectable_test_files_outside_tests():
    """仓库内不得存放外部项目副本——`tests/` 之外不得有 pytest 会收集的测试文件。"""
    hits = _collectable_files_outside_tests()

    assert hits == [], (
        "tests/ 之外发现 pytest 会收集的测试文件："
        f"{hits}。这正是 2026-09-26 事故的直接成因（外部项目副本被收集 → "
        "ModuleNotFoundError）。请删除该副本，不要用 norecursedirs 掩盖。"
    )


def test_no_stray_conftest_outside_tests():
    """`tests/` 之外不得有 conftest.py（仓库根允许——那是合法的顶层 conftest 约定）。"""
    stray = []
    for path in PROJECT_ROOT.rglob("conftest.py"):
        if not path.is_file():
            continue
        rel = path.relative_to(PROJECT_ROOT)
        if SKIP_DIRS & set(rel.parts):
            continue
        if rel.parent == TESTS_DIR or TESTS_DIR in path.parents:
            continue
        if rel.parent == PROJECT_ROOT:
            # 仓库根的 conftest.py 是合法约定，不算越界
            continue
        stray.append(str(rel))

    assert stray == [], f"tests/ 之外发现 conftest.py：{stray}（外部项目副本的典型特征）"


def test_unit_collection_has_no_error():
    """主套件收集必须无 error（收集失败会让整套 CI 变成 0-job 假绿/假红）。"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit", "--collect-only", "-q"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"pytest tests/unit --collect-only 退出码 {result.returncode}\n"
        f"stdout:\n{result.stdout[-2000:]}\nstderr:\n{result.stderr[-2000:]}"
    )
    # 收集失败时 pytest 的收尾行是 "N errors" 或 "!!! interrupted: N error during collection !!!"。
    # 不能用 `'error' not in stdout` 粗判——测试**名字**里就含 error（如 test_xxx_io_error）。
    lowered = result.stdout.lower()
    assert "error during collection" not in lowered
    assert "!!! interrupted" not in lowered
    tail = [line for line in result.stdout.splitlines() if line.strip()]
    summary = tail[-1] if tail else ""
    assert "error" not in summary.lower(), f"收集收尾行含 error：{summary}"


def test_this_guard_lives_under_tests():
    """自检：本守护用例自身必须位于 `tests/` 之下（防后人把守护写到仓库根）。"""
    this_file = Path(__file__).resolve()

    assert this_file.parent == TESTS_DIR or TESTS_DIR in this_file.parents
    assert "tests" in this_file.relative_to(PROJECT_ROOT).parts
