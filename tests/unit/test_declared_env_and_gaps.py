"""声明式配置的一致性守门

两类「文档说了但可能不是真的」的东西：
1. pyproject.toml 的 requires-python / classifiers / ruff target-version 三家口径
2. known_gaps.json 的台账格式——写下来却没人看的台账等于没写

这些检查故意不 import 第三方库：它们要在任何 Python 版本上都能跑。
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
KNOWN_GAPS = REPO_ROOT / "known_gaps.json"


def _read_pyproject_text() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


# ---------------- pyproject 口径一致 ----------------


def _requires_python_tuple() -> tuple[int, int]:
    text = _read_pyproject_text()
    m = re.search(r'^requires-python\s*=\s*"[><=~!]*\s*(\d+)\.(\d+)"', text, re.MULTILINE)
    assert m, "pyproject.toml 里没找到 requires-python"
    return int(m.group(1)), int(m.group(2))


def test_requires_python_is_not_below_310():
    """代码用了 PEP 604（X | None），运行时至少要 3.10。

    历史：这里曾长期写 >=3.8，而 ai_collab/ 里有数百处 `str | None` 注解。
    py3.8/3.9 根本不认，装上去直接 syntax/TypeError——声明是假的。
    """
    major, minor = _requires_python_tuple()
    assert (major, minor) >= (3, 10), (
        f"requires-python 声明为 >={major}.{minor}，但代码使用 PEP 604 联合类型，需 >=3.10"
    )


def test_classifiers_do_not_claim_versions_below_requires_python():
    """classifiers 不许声称支持比 requires-python 更老的版本。"""
    text = _read_pyproject_text()
    major, minor = _requires_python_tuple()

    claimed = [
        (int(a), int(b))
        for a, b in re.findall(
            r'"Programming Language :: Python :: (\d+)\.(\d+)"', text
        )
    ]
    assert claimed, "pyproject.toml 未声明任何具体 Python 版本 classifier"

    too_old = [f"{a}.{b}" for a, b in claimed if (a, b) < (major, minor)]
    assert not too_old, (
        f"classifiers 声称支持 {too_old}，低于 requires-python >={major}.{minor}"
    )


def test_ruff_target_version_matches_requires_python():
    """ruff 的 target-version 应与 requires-python 对齐，否则 lint 放行/拦截口径不一致。"""
    text = _read_pyproject_text()
    major, minor = _requires_python_tuple()
    m = re.search(r'^target-version\s*=\s*"py(\d)(\d+)"', text, re.MULTILINE)
    assert m, "pyproject.toml 里没找到 ruff 的 target-version"
    assert (int(m.group(1)), int(m.group(2))) == (major, minor), (
        f"ruff target-version=py{m.group(1)}{m.group(2)} 与 requires-python "
        f">={major}.{minor} 不一致"
    )


# ---------------- known_gaps 台账格式 ----------------

REQUIRED_KEYS = {"id", "priority", "status", "title", "reader", "where", "detail", "fix"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_STATUSES = {"open", "closed", "wontfix"}


@pytest.fixture(scope="module")
def gaps_doc():
    assert KNOWN_GAPS.exists(), f"缺少缺陷台账: {KNOWN_GAPS}"
    return json.loads(KNOWN_GAPS.read_text(encoding="utf-8"))


def test_known_gaps_has_conventions(gaps_doc):
    """台账必须自带命名口径，否则下一个人不知道该按什么规则加条目。"""
    assert gaps_doc.get("schema_version") == 1
    conventions = gaps_doc.get("conventions")
    assert isinstance(conventions, dict)
    for key in ("id", "priority", "reader", "where", "status"):
        assert key in conventions, f"conventions 缺 {key} 的说明"


def test_known_gaps_entries_are_well_formed(gaps_doc):
    gaps = gaps_doc.get("gaps")
    assert isinstance(gaps, list) and gaps, "gaps 必须是非空数组"

    problems = []
    for gap in gaps:
        missing = REQUIRED_KEYS - set(gap)
        if missing:
            problems.append(f"{gap.get('id', '?')} 缺字段 {sorted(missing)}")
            continue
        if gap["priority"] not in VALID_PRIORITIES:
            problems.append(f"{gap['id']} 优先级非法: {gap['priority']}")
        if gap["status"] not in VALID_STATUSES:
            problems.append(f"{gap['id']} 状态非法: {gap['status']}")
        if not isinstance(gap["where"], list) or not gap["where"]:
            problems.append(f"{gap['id']} where 必须是非空数组")
        if not str(gap["reader"]).strip():
            problems.append(f"{gap['id']} 未声明 reader")
        if gap["status"] == "closed" and not gap.get("closed_at"):
            problems.append(f"{gap['id']} 已关闭但没写 closed_at")

    assert not problems, "known_gaps.json 格式问题: " + "; ".join(problems)


def test_known_gaps_ids_are_unique(gaps_doc):
    ids = [g["id"] for g in gaps_doc["gaps"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"known_gaps.json 编号重复: {sorted(dupes)}"
