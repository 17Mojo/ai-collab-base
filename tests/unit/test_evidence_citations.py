"""被报告引用的证据文件，必须真的在 git 里（证据链完整性）。

## 为什么要有这条

2026-11-18 核查发现：`collaboration/results/real-machine-runs/evidence/` 下已跟踪 203 个文件、
另有 135 个**从未 `git add`**；其中 92 个被受跟踪的报告正文引用
（主要是 `RESULT-L2-MULTIPLATFORM-2026-11-10.md`）。

`.gitignore:50` 有一条明确的反例放行规则：

    # 真机回归证据日志属交付物（RESULT 报告以其为最终判定依据），例外放行
    !collaboration/results/real-machine-runs/evidence/*.log

也就是说「证据属交付物」是本仓的既定口径，不是我的推断。那么漏 `add` 就不是「少提交几个文件」，
而是**报告引用的证据在干净检出上不存在** —— 结论照旧写着，复核路径断掉，
「结论可复现」这条基本口径在这份仓库的 clone 上不成立。

这条测试守的正是这个缺口：**磁盘上有 → 文档引用了 → 那它就必须在 git 里。**

## 判据为什么只看「磁盘上存在的」

反向情况（文档引用了但磁盘上也没有）不属于本条的守护范围：那里面混着大量
生成物（playwright 截图、被 .gitignore 覆盖的 test-results）与历史占位名，
2026-11-18 实测有 176 个。把它们拉进来会让这条测试一出生就红，然后被当成噪音关掉
—— 那比没有更糟。真缺失的引用清查是另一件事，要单独定口径。
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_REL = "collaboration/results/real-machine-runs/evidence"
EVIDENCE_DIR = REPO_ROOT / EVIDENCE_REL

#: 证据文件常见扩展名。只认这些，避免把散文里的 `xxx.py` 之类误当证据。
EVIDENCE_SUFFIXES = (".json", ".jsonl", ".png", ".log", ".py", ".sh", ".md")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout


def _tracked_files() -> set[str]:
    return {line for line in _git("ls-files").split("\n") if line}


def _cited_names() -> dict[str, set[str]]:
    """从**受跟踪的** markdown 里抽出被提到的文件名 → 引用它的文档集合。"""
    pattern = re.compile(r"([A-Za-z0-9][A-Za-z0-9._\-]*\.[A-Za-z0-9]+)")
    cites: dict[str, set[str]] = {}
    for rel in _tracked_files():
        if not rel.endswith(".md"):
            continue
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in pattern.finditer(text):
            name = match.group(1)
            if name.endswith(EVIDENCE_SUFFIXES):
                cites.setdefault(name, set()).add(rel)
    return cites


def test_cited_evidence_files_are_tracked():
    """磁盘上存在、且被受跟踪文档引用的证据文件，必须出现在 git 索引里。"""
    assert EVIDENCE_DIR.is_dir(), f"证据目录不存在：{EVIDENCE_REL}"

    tracked = _tracked_files()
    tracked_evidence = {p for p in tracked if p.startswith(EVIDENCE_REL + "/")}
    cites = _cited_names()

    violations = []
    for path in sorted(EVIDENCE_DIR.iterdir()):
        if not path.is_file() or not path.name.endswith(EVIDENCE_SUFFIXES):
            continue
        rel = f"{EVIDENCE_REL}/{path.name}"
        if rel in tracked_evidence:
            continue
        if path.name in cites:
            violations.append(f"{path.name}  ← 被引用：{', '.join(sorted(cites[path.name]))}")

    assert not violations, (
        "以下证据文件在磁盘上存在、被报告引用，但**没有进 git**：\n  "
        + "\n  ".join(violations)
        + "\n\n干净检出里这些引用会全部悬空。请 `git add` 它们；"
        "若确实不该入库，就删掉文件并同步改引用它的文档（别只改一半）。"
    )


def test_evidence_dir_has_tracked_files():
    """反向保险：证据目录不能整体变成未跟踪（否则上面那条会因为「没引用」而空跑）。"""
    tracked = _tracked_files()
    tracked_evidence = [p for p in tracked if p.startswith(EVIDENCE_REL + "/")]
    assert len(tracked_evidence) > 100, (
        f"{EVIDENCE_REL} 下只有 {len(tracked_evidence)} 个受跟踪文件，"
        "与历史规模（200+）严重不符——证据链可能被整体移出仓库了。"
    )
