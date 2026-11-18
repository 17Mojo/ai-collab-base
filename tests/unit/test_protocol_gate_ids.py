"""门禁编号只认「定义过的」，不许按连惯性虚构（台账 N38）。

## 为什么要有这条

2026-11-18 的真实事故：两份真机 plan 写着「门禁从 1 到 10 都齐」，agent 据此推断存在十条，
凑出「第 7 条写入门」「第 10 条 worktree-vs-commit」，并以此为由挡住了一次合法提交。
实际 `collaboration/PROTOCOL.md` §14.5 只定义过 **五种** 信号，中间那一段编号从未存在。

危害不是「门禁不灵」——真实门禁照常工作；危害是**编号被当成了权威来源**。
所以这条测试守的不是代码，是「编号集合」：一旦文档里冒出未登记的编号，
说明又有人按连惯性编了一条，此时必须回 §14.5 登记或把编号删掉。

## 判据

从 PROTOCOL.md 抽出所有 `G<数字>` 形式的面值，必须**恰好**等于已定义的五个。
不是「包含」而是「相等」——少一个说明表被删了，多一个说明有人编了新的。
两种都要红。

**注意**：本条测试自身的注释里不要写空号的字面量（例如 5 到 10 那一段），
否则会把判据自己污染。同理，PROTOCOL 里提到空号时必须用「第 7 条」这种说法
而不是字面编号，§14.5 的注里已写明这个约定。
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = REPO_ROOT / "collaboration" / "PROTOCOL.md"

#: §14.5 定义过的门禁信号。**新增门禁必须先改这里并在 PROTOCOL 登记。**
DEFINED_GATE_IDS = {"G1", "G2", "G3", "G4", "G11"}


def _protocol_text() -> str:
    assert PROTOCOL.is_file(), f"找不到门禁定义文件：{PROTOCOL}"
    return PROTOCOL.read_text(encoding="utf-8")


def _referenced_gate_ids(text: str) -> set[str]:
    return set(re.findall(r"G\d+", text))


def test_protocol_only_references_defined_gate_ids():
    """PROTOCOL 里出现的门禁编号必须全部是 §14.5 定义过的。"""
    referenced = _referenced_gate_ids(_protocol_text())
    unknown = sorted(referenced - DEFINED_GATE_IDS)
    assert not unknown, (
        f"PROTOCOL.md 出现了未登记的门禁编号：{unknown}\n"
        f"已定义的只有：{sorted(DEFINED_GATE_IDS)}\n"
        "要么回 §14.5 补齐定义并同步本测试的 DEFINED_GATE_IDS，"
        "要么把编号删掉改用「第 N 条」这种不含字面编号的表述。"
    )


def test_every_defined_gate_is_still_referenced():
    """已定义的门禁不能从文档里消失——少一个说明表被删过。"""
    referenced = _referenced_gate_ids(_protocol_text())
    missing = sorted(DEFINED_GATE_IDS - referenced)
    assert not missing, (
        f"PROTOCOL.md 里找不到这些已定义门禁的引用：{missing}\n"
        "若确实已废弃，请同时从 DEFINED_GATE_IDS 与 §14.5 表中移除，"
        "并登记进 known_gaps.json（编号永不复用）。"
    )


def test_gate_section_carries_non_contiguous_note():
    """§14.5 必须显式声明「编号非连续」，让空号成为事实而非隐含假设。"""
    text = _protocol_text()
    assert "本表编号非连续" in text, (
        "§14.5 缺少「本表编号非连续」的注。这条注是 N38 的直接止血措施："
        "没有它，读者会按编号连惯性推断存在中间那几条门禁。"
    )
    # 核对命令本身也必须在文档里可复现，否则「应输出什么」无从验证
    assert "grep -o 'G[0-9]\\+'" in text, "§14.5 的注里应保留核对命令，让「编号集合是否正确」可当场复核。"
