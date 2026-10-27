"""守护「外部用户会话操作手册」不会悄悄失效。

## 为什么需要这个守护

W-D1 排演查出的 6 个断点里，有一类是**材料自身失效**造成的：
说明书里写的东西在真实交付物里不存在（扩展没构建、页面路径 404、
Pack 文件选不中）。手册自己也可能重蹈覆辙——
它引用的脚本改了名、参数改了名、链接指向的文件被删了，
而**没人会读到一半才发现**。

所以这里把「手册引用的东西还在不在」变成可执行的断言。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = REPO_ROOT / "docs" / "EXTERNAL_USER_SESSION_RUNBOOK.md"
ONBOARDING = REPO_ROOT / "docs" / "EXTERNAL_USER_ONBOARDING.md"

# 手册里被**点名**的交付物：路径写错一个字符，这一层就红。
REQUIRED_PATHS = [
    "docs/EXTERNAL_USER_ONBOARDING.md",
    "docs/REAL_MACHINE_REGRESSION.md",
    "collaboration/results/external-user/README.md",
    "collaboration/results/external-user/TEMPLATE.md",
    "collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md",
    "packs/examples/external-user-smoke.json",
    "chrome-extension/tests/real-machine/l2-send-observer.mjs",
    "chrome-extension/tests/real-machine/dom-contract-probe.mjs",
    "scripts/real_machine_regression.py",
]

# 手册里的命令 ↔ 参数解析器所在的源文件。
# 手册教人敲的命令，参数名必须**真的**被源码认。
COMMAND_SOURCES = {
    "l2-send-observer.mjs": [
        "chrome-extension/tests/real-machine/l2-send-observer.mjs",
        "chrome-extension/tests/real-machine/l2-model.mjs",
    ],
    "dom-contract-probe.mjs": ["chrome-extension/tests/real-machine/dom-contract-probe.mjs"],
    "real_machine_regression.py": ["scripts/real_machine_regression.py"],
}

FENCE_RE = re.compile(r"```(?:bash|sh)?\n(.*?)```", re.DOTALL)
FLAG_RE = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
LINK_RE = re.compile(r"\]\(([^)#\s]+)\)")


def _runbook_text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_exists_and_is_not_a_stub() -> None:
    assert RUNBOOK.exists(), f"手册不存在：{RUNBOOK}"
    text = _runbook_text()
    assert len(text) > 4000, "手册内容过短——可能只写了个骨架"
    for heading in (
        "## 0.",
        "## 3.",
        "## 4.",
        "## 5.",
        "## 7.",
        "## 8.",
    ):
        assert heading in text, f"手册缺少必需章节：{heading}"


def test_referenced_deliverables_exist() -> None:
    missing = [p for p in REQUIRED_PATHS if not (REPO_ROOT / p).exists()]
    assert not missing, f"手册引用了不存在的文件：{missing}"


def test_relative_markdown_links_resolve() -> None:
    """手册与说明书里的相对链接必须都指得到真实文件。"""
    broken: list[str] = []
    for doc in (RUNBOOK, ONBOARDING):
        text = doc.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if any(ch in raw for ch in "<>*"):
                continue
            target = (doc.parent / raw).resolve()
            if not target.exists():
                broken.append(f"{doc.name} -> {raw}")
    assert not broken, f"相对链接失效：{broken}"


def _recognized_flags(source_text: str) -> set[str]:
    """抽出源码**真正解析**的参数名。

    只在源码里「出现过」是不够的——注释里也写着 `--wait-for-login`，
    参数真被改名了，字符串照样在注释里，守护会假绿。

    所以这里只认两种形态：
      - `raw === "--flag"`        （JS 侧：无值开关）
      - `raw.startsWith("--flag=")`（JS 侧：带值参数）
      - `add_argument("--flag"`   （Python 侧：argparse）
    """
    flags: set[str] = set()
    for pattern in (
        r'raw\s*===\s*"(--[a-z][a-z0-9-]*)"',
        r'raw\.startsWith\("(--[a-z][a-z0-9-]*)="\)',
        r'add_argument\("(--[a-z][a-z0-9-]*)"',
    ):
        flags.update(re.findall(pattern, source_text))
    return flags


def test_command_flags_are_recognized_by_the_tool() -> None:
    """手册里教的命令，参数名必须真的被对应工具解析。"""
    problems: list[str] = []
    text = _runbook_text()
    for block in FENCE_RE.findall(text):
        for tool, sources in COMMAND_SOURCES.items():
            if tool not in block:
                continue
            recognized: set[str] = set()
            for src in sources:
                recognized |= _recognized_flags(
                    (REPO_ROOT / src).read_text(encoding="utf-8")
                )
            for flag in sorted(set(FLAG_RE.findall(block))):
                if flag not in recognized:
                    problems.append(f"{tool} 不认 {flag}")
    assert not problems, f"手册里的命令参数与工具对不上：{sorted(set(problems))}"


def test_runbook_keeps_the_red_lines() -> None:
    """红线是这份手册的核心价值，删掉它等于把手册变成鼓励人代劳的说明书。"""
    text = _runbook_text()
    for phrase in (
        "不代劳",
        "不提示",
        "不诱导",
        "不代写记录",
        "不碰他的账号",
        "不删证据",
    ):
        assert phrase in text, f"手册丢了红线：{phrase}"
    # 「探针永不发送」是本仓的红线，手册里不能出现「脚本替人发送」的写法。
    assert "绝不点发送" in text or "不点发送" in text, "手册没有写明「发送由人做」"
