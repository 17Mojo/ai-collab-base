"""结果文件章节契约 —— PROTOCOL §7.4 的唯一实现（台账 N41）。

**为什么有这个模块**：这条契约此前有两份互相矛盾的实现。

- 写入门禁 `state_manager`：三组替代词，且把「回滚」当成「风险」的替代词
  （写了「风险」就算满足，`## 回滚` 零强制）。
- 回执门禁 `scripts/agent_receipt_bridge.py`：要求字面 `## 测试结论`，无替代词。

后果（2026-11-18 端到端实跑抓到）：按 PROTOCOL §7.4 写出的合规结果文件
——四段齐全、但「测试结论」是 `## 验证结果` 下的小节——**被回执桥判 invalid**，
卡在链路最后一步；而缺强制段 `## 回滚` 的文件**两处门禁都放行**。方向正好相反。

**判据形状**（关键：不是子串匹配，是标题语义匹配）：

1. 必须在 **H2–H4 标题**里出现。正文里提到「风险」不算，正文提到也不算数。
   旧实现用 `"## 执行命令" in text`，于是 `## 4. 执行命令` 这种编号标题
   反而匹配不上——`RESULT-P1-GOV-CONVERGE-001.md` 四段齐全却因此被判缺段。
2. 标题**允许前导编号**：`## 4. 执行命令` / `## 2.3 风险` / `## 六、回滚` 均算。
3. 标题**允许合并**：`## 风险与回滚` 同时满足「风险」与「回滚」两组。
   契约的目的是「读者能找到回滚说明」，合并标题做得到，就不强制拆开。
4. 每组接受若干同义词，见 `SECTION_GROUPS`。

**一致性**：`scripts/agent_receipt_bridge.py` 出于「可被单独拷走执行」的设计，
保留了本地副本而非 import 本模块；`tests/unit/test_result_file_contract.py`
强制两侧逐字一致（沿用 `_MANAGED_LEDGER_FILENAMES` 的既有模式）。改这里必须同步改那边。
"""

from __future__ import annotations

import re

# (组名, 同义词元组)。组名用于错误信息，不要随意改（有测试与文档引用）。
SECTION_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("执行命令", ("执行命令", "命令清单", "acceptance_commands", "verification commands", "commands")),
    ("验证结果", ("验证结果", "测试结论", "验证", "test result", "test conclusion", "verification")),
    ("风险", ("风险", "risk")),
    ("回滚", ("回滚", "rollback")),
)

# `(?!#)` 必不可少：没有它，`##### H5` 会被贪婪的 `#{2,4}` 吃掉四个 `#`，
# 剩下的 `# H5` 当成标题文字，于是 5 级标题被误判成 4 级。
_HEADING_RE = re.compile(r"^(#{2,4})(?!#)[ \t]*(.+?)[ \t]*$", re.MULTILINE)

# 前导编号：`1.` `2.3` `六、` `(1)` `第3节` 等。只剥一层，不动正文。
_NUMBERING_RE = re.compile(
    r"^[ \t]*(?:"
    r"第?[0-9０-９一二三四五六七八九十百]+(?:[.．、)）]|[ \t])"
    r"|[（(][0-9０-９一二三四五六七八九十百]+[）)]"
    r"|[0-9０-９]+(?:[.．][0-9０-９]+)+[.．、]?"
    r")[ \t]*"
)

# 复合标题的分隔符：`## 风险与回滚` 拆成 [风险, 回滚]。
_COMPOUND_SEP_RE = re.compile(r"[与和及、/／,，;；]+")


def _matches(heading_normalized: str, keywords: tuple[str, ...]) -> bool:
    """标题是否**作为章节名**表达该概念。

    只接受「某一段以关键词开头」，不接受「标题里随便提到」。

    这修掉了一个真实误命中：`### F7〔门禁缺口〕``## 回滚`` 是强制段，但零执行`
    这种**描述性小节标题**含「回滚」二字，旧实现（子串匹配、首个命中优先）
    会让它顶替真正的 `## 回滚` 段——等于自己写的一段说明把自己的门禁骗过去了。
    """
    parts = [p.strip() for p in _COMPOUND_SEP_RE.split(heading_normalized) if p.strip()]
    if not parts:
        return False
    for part in parts:
        low = part.lower()
        for kw in keywords:
            k = str(kw).lower()
            if low.startswith(k):
                return True
    return False


def iter_headings(text: str) -> list[tuple[int, str, str]]:
    """返回 [(级别, 原始标题文字, 去编号后的标题文字)]。"""
    out: list[tuple[int, str, str]] = []
    for m in _HEADING_RE.finditer(text or ""):
        level = len(m.group(1))
        raw = m.group(2).strip()
        out.append((level, raw, _NUMBERING_RE.sub("", raw).strip()))
    return out


def satisfied_sections(text: str) -> dict[str, str | None]:
    """每个必填组命中的标题原文；未命中为 None。"""
    headings = iter_headings(text)
    result: dict[str, str | None] = {}
    for label, keywords in SECTION_GROUPS:
        hit = None
        for _level, raw, normalized in headings:
            if _matches(normalized, keywords):
                hit = raw
                break
        result[label] = hit
    return result


def missing_sections(text: str) -> list[str]:
    """返回缺失的组名列表（空列表表示齐备）。"""
    got = satisfied_sections(text)
    return [label for label, hit in got.items() if not hit]


def describe_missing(text: str) -> str:
    """给错误信息用的一句话，含每组接受的同义词，便于执行者一次改对。"""
    got = satisfied_sections(text)
    parts = []
    for label, keywords in SECTION_GROUPS:
        if got[label]:
            parts.append(f"{label}✓")
        else:
            parts.append(f"{label}✗（可用：{'/'.join(keywords[:3])}）")
    return "，".join(parts)
