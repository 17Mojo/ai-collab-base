"""结果文件章节契约的绊线（台账 N41）。

守三件事：

1. **两份实现不许漂移** —— `ai_collab/result_file_contract.py` 是权威，
   `scripts/agent_receipt_bridge.py` 出于「可单独拷走执行」保留本地副本。
   两份的 `SECTION_GROUPS` 必须逐字一致，且在同一批文本上给出相同结论。
2. **判据形状不许退化回子串匹配** —— 编号标题要算数、合并标题要算数，
   而描述性标题（`### 关于回滚的说明`）不许顶替真正的 `## 回滚` 段。
3. **强制段不许再零执行** —— 缺 `## 回滚` 必须报错。这条正是 N41 的核心：
   修复前「回滚」只是「风险」的替代词，写了风险就不用写回滚。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from ai_collab.result_file_contract import (
    SECTION_GROUPS,
    describe_missing,
    iter_headings,
    missing_sections,
    satisfied_sections,
)
from ai_collab.state_manager import StateManager

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_BRIDGE = REPO_ROOT / "scripts" / "agent_receipt_bridge.py"


def _load_receipt_bridge():
    spec = importlib.util.spec_from_file_location("_arb_under_test", RECEIPT_BRIDGE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bridge():
    return _load_receipt_bridge()


# ---------------- 两份实现不许漂移 ----------------

def test_section_groups_are_identical_across_implementations(bridge):
    assert bridge.SECTION_GROUPS == SECTION_GROUPS, (
        "结果文件章节契约的两份实现已经不一致：\n"
        f"  ai_collab/result_file_contract.py -> {SECTION_GROUPS}\n"
        f"  scripts/agent_receipt_bridge.py   -> {bridge.SECTION_GROUPS}\n"
        "改一处必须同步改另一处（台账 N41）。"
    )


FIXTURES = {
    "四段齐全": "## 执行命令\nls\n\n## 验证结果\n### 测试结论\nok\n\n## 风险\n无\n\n## 回滚\ngit revert\n",
    "编号标题": "## 4. 执行命令\nls\n\n## 5. 测试结论\nok\n\n## 6. 风险与回滚\ngit revert\n",
    "缺回滚": "## 执行命令\nls\n\n## 验证结果\n### 测试结论\nok\n\n## 风险\n无\n",
    "缺验证结果": "## 执行命令\nls\n\n## 风险\n无\n\n## 回滚\ngit revert\n",
    "描述性标题顶替": "## 执行命令\nls\n\n## 验证结果\nok\n\n## 风险\n无\n\n### 关于回滚的说明\n正文\n",
    "正文提及不算": "## 执行命令\nls\n\n## 验证结果\nok\n\n## 风险\n本文件不含回滚段\n",
    "全缺": "# 只有标题\n正文\n",
}


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_implementations_agree_on_every_fixture(bridge, name):
    text = FIXTURES[name]
    assert missing_sections(text) == bridge.missing_result_sections(text), (
        f"两份实现在 {name!r} 上结论不同"
    )


def test_state_manager_compat_view_shares_the_same_groups():
    """`TASK_RESULT_REQUIRED_SECTION_GROUPS` 只是兼容视图，不得成为第二套判据。"""
    view = StateManager.TASK_RESULT_REQUIRED_SECTION_GROUPS
    assert len(view) == len(SECTION_GROUPS)
    for (label, *keywords), (expected_label, expected_keywords) in zip(view, SECTION_GROUPS):
        assert label == expected_label
        assert tuple(keywords) == expected_keywords


# ---------------- 判据形状 ----------------

def test_numbered_headings_count():
    """`## 4. 执行命令` 这种编号标题必须算数。

    修复前 `"## 执行命令" in text` 匹配不上它，
    于是四段齐全的 RESULT-P1-GOV-CONVERGE-001.md 被判缺段。
    """
    text = "## 4. 执行命令\nls\n\n## 5. 测试结论\nok\n\n## 6. 风险与回滚\ngit revert\n"
    assert missing_sections(text) == []
    assert satisfied_sections(text)["执行命令"] == "4. 执行命令"


def test_compound_heading_satisfies_both_groups():
    """`## 风险与回滚` 同时满足风险与回滚两组。"""
    got = satisfied_sections("## 风险与回滚\n内容\n")
    assert got["风险"] == "风险与回滚"
    assert got["回滚"] == "风险与回滚"


def test_descriptive_heading_does_not_substitute_real_section():
    """描述性小节标题含「回滚」二字，不许顶替真正的回滚段。

    这是本模块第一版真踩到的坑：`### F7〔门禁缺口〕`## 回滚` 是强制段…`
    按文档顺序先出现，于是一个说明性标题把自己的门禁骗过去了。
    """
    text = "## 执行命令\nls\n\n## 验证结果\nok\n\n## 风险\n无\n\n### F7 关于回滚的说明\n正文\n"
    assert missing_sections(text) == ["回滚"]


def test_body_mention_is_not_a_heading():
    text = "## 执行命令\nls\n\n## 验证结果\nok\n\n## 风险\n本文件不含回滚段\n"
    assert missing_sections(text) == ["回滚"]


def test_missing_rollback_is_reported():
    """N41 核心断言：缺 `## 回滚` 必须报错。

    修复前「回滚」是「风险」的替代词——写了 `## 风险` 就算满足，
    PROTOCOL §7.4 的第四段实质零执行。
    """
    assert missing_sections("## 执行命令\nls\n\n## 验证结果\nok\n\n## 风险\n无\n") == ["回滚"]


def test_test_conclusion_as_subsection_satisfies_verification_group():
    """`### 测试结论` 作为 `## 验证结果` 的小节，满足「验证结果」组。

    修复前回执桥要求字面 `## 测试结论`，这类合规文件被判 invalid（N41 的起点）。
    """
    assert missing_sections("## 执行命令\nls\n\n## 验证结果\n### 测试结论\nok\n\n## 风险\n无\n\n## 回滚\nr\n") == []


def test_verification_group_accepts_standalone_test_conclusion():
    """`## 测试结论` 独立成段也算满足「验证结果」组。"""
    text = "## 执行命令\nls\n\n## 测试结论\nok\n\n## 风险\n无\n\n## 回滚\nr\n"
    assert missing_sections(text) == []


def test_iter_headings_only_h2_to_h4():
    heads = iter_headings("# H1\n## H2\n### H3\n#### H4\n##### H5\n")
    levels = [lvl for lvl, _raw, _norm in heads]
    assert levels == [2, 3, 4]


def test_describe_missing_lists_accepted_synonyms():
    msg = describe_missing("# 空\n")
    assert "执行命令" in msg and "验证结果" in msg and "风险" in msg and "回滚" in msg


# ---------------- 真实语料回归 ----------------

def test_real_artifact_with_numbered_headings_passes():
    """真实历史交付物：四段齐全、但用编号标题与合并标题。

    它是修复前唯一被判缺段的在册任务结果文件，作为回归样本保留。
    """
    path = REPO_ROOT / "collaboration/results/RESULT-P1-GOV-CONVERGE-001.md"
    if not path.exists():  # pragma: no cover - 文件被移走时跳过而非误报
        pytest.skip(f"{path.name} 不存在")
    text = path.read_text(encoding="utf-8", errors="ignore")
    assert missing_sections(text) == []
