"""Root conftest.py - ensure project root is on sys.path for all tests.

同时承担**全局状态文件的测试隔离**（2026-10-26 新增）。

背景：`StateManager._sync_to_global()` 会把每个工作区的状态写进
`~/.vscode/ai-collab/collaboration_state.json`（`os.path.expanduser` 跟随
`HOME`）。测试套件里全是临时工作区，于是**每跑一次测试就往开发机的真实
全局文件里塞一条条目**——2026-10-24 实测到 1589 条里 1587 条是这类泄漏。

产品侧的回收逻辑已修好（见
`collaboration/results/RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md`），
但回收只是**止血**：写进去这件事本身就不该发生。所以这里把整个套件的
`HOME` / `USERPROFILE` 指到临时目录——写进去的条目落在临时目录里，
连同临时目录一起消失，开发机的真实全局文件不再被测试碰过。

`os.path.expanduser` 在 POSIX 上跟随 `HOME`、在 Windows 上跟随
`USERPROFILE`，两者都要设——CI runner 是 Ubuntu、开发机是 macOS，
但同一份用例在两端跑，漏掉一个就会在另一端失效。

**为什么每个用例一个独立 HOME**：全局状态文件是跨用例共享状态，
共用一个目录就会出现「上一个用例写进去的条目影响下一个用例」的顺序依赖。
每个用例一个独立目录 ⇒ 全局文件对每个用例都是空的 ⇒ 无顺序依赖。
"""

import os
import sys
from pathlib import Path

import pytest

# 把项目根目录加入 sys.path（在 src/ 前面）
# 这样可以加载完整的 ai_collab/ 包，而不是精简版的 src/ai_collab/
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 真实 HOME 在**模块导入时**捕获（早于任何 fixture 生效）。
# 守护用例需要它来证明「测试套件没碰过开发机的真实全局文件」。
# 此时 os.environ 还是开发机原样——fixture 尚未把它改掉。
REAL_HOME = os.environ.get("HOME") or os.environ.get("USERPROFILE") or ""
REAL_GLOBAL_STATE_FILE = (
    str(Path(REAL_HOME) / ".vscode" / "ai-collab" / "collaboration_state.json")
    if REAL_HOME
    else ""
)


@pytest.fixture
def ambient_global_state_file() -> str:
    """开发机**真实**的全局状态文件路径（未受隔离影响）。

    守护用例拿它来对比：套件跑完之后，这个文件必须一个字节都没变。
    """
    return REAL_GLOBAL_STATE_FILE


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把 HOME / USERPROFILE 指向临时目录，隔离全局状态文件。

    隔离的是**路径解析**，不是产品行为：产品照常往「全局文件」写，只是
    那个文件落在临时目录里。这样既止住了对开发机真实文件的污染，
    又没有把「产品会写全局文件」这件事从测试里拿掉。

    目录名故意带 `conftest-` 前缀：`tests/unit/test_perf_isolation_guard.py`
    和 `tests/unit/test_ci_isolation_guard.py` 自己会在 `tmp_path/` 下造
    隔离环境（`fake-home` / `isolated-home` / `polluted-home`），重名会让
    它们 `mkdir` 时撞上「已存在」。
    """
    fake_home = tmp_path / "conftest-isolated-home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home
