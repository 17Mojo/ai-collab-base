""".gitignore 里「反例放行」的落点，磁盘上的文件必须真的在 git 里。

## 为什么要有这条

`.gitignore` 里以 `!` 开头的行是**故意的例外**：它声明「这个路径虽然被上面的规则挡住，
但它是交付物，要跟踪」。本仓有三处这样的声明：

    !logs/claude-code/**                      # PROTOCOL §7.4 要求的开发日志
    !collaboration/.../evidence/*.log         # 真机回归证据属交付物
    !packs/exports/_archive/.gitkeep          # 占位
    !chrome-extension/tests/screenshots/.gitkeep

2026-11-18 核查发现其中两处**口径与实际脱节**：

* `logs/claude-code/` 受跟踪数 **0**，13 份 10-21~10-27 的开发日志一直躺在工作区；
* `evidence/` 有 **135** 个文件从未 `git add`，其中 92 个被报告正文引用（已登记 N40）。

两次都是同一个形态：**规则写了、动作漏了**。规则本身不会报错，`git status` 只显示
一个 `??` 目录，跑测试、preflight、变异检查全都看不见 —— 因为读的都是同一片磁盘。

所以这条测试的判据不是清单，而是**从 .gitignore 自己的声明里推导**：
你声明要跟踪什么，就检查那底下是不是真的跟踪了。这样新增一处 `!` 放行时自动进入检查范围，
不需要有人记得来改测试。

## 判据为什么只看目录型放行

`!xxx/.gitkeep` 这类单文件放行只放行一个字面路径，没有「目录里还有别的文件」的含义，
拿它推导整目录要求会误伤。故只处理以 `/` 或 `/**` 或 `/*` 结尾的目录型放行。
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = REPO_ROOT / ".gitignore"


def _tracked_files() -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    return {line for line in out.split("\n") if line}


def _negated_dirs() -> list[str]:
    """从 .gitignore 里取出「目录型反例放行」的目录前缀（不带通配符）。"""
    dirs: list[str] = []
    for raw in GITIGNORE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("!") or line.startswith("##"):
            continue
        pattern = line[1:].strip()
        # 只处理目录型：以 / 、/**、/* 结尾
        for suffix in ("/**", "/*", "/"):
            if pattern.endswith(suffix) and not pattern.endswith("//"):
                candidate = pattern[: -len(suffix)]
                if candidate and candidate not in dirs:
                    dirs.append(candidate)
                break
    return dirs


def test_files_under_negated_dirs_are_tracked():
    """凡 .gitignore 用 `!` 放行的目录，磁盘上的文件都必须在 git 索引里。"""
    dirs = _negated_dirs()
    assert dirs, ".gitignore 里没解析出任何目录型反例放行——解析逻辑大概率失效了，别静默通过"

    tracked = _tracked_files()
    violations: list[str] = []
    for rel_dir in dirs:
        base = REPO_ROOT / rel_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel not in tracked:
                violations.append(rel)

    assert not violations, (
        "以下文件所在目录被 .gitignore 以 `!` 显式放行（声明为要跟踪的交付物），"
        "但它们并不在 git 里：\n  "
        + "\n  ".join(violations[:40])
        + (f"\n  …… 共 {len(violations)} 个" if len(violations) > 40 else "")
        + "\n\n要么 `git add` 入库，要么把 .gitignore 那行反例删掉并说明为什么不跟踪。"
        "\n别只改一半——规则说跟踪、实际没跟踪，比没有规则更容易骗人。"
    )
