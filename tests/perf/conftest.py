"""性能基线用例的隔离装置：基线必须与「运行者的机器历史」解耦。

2026-10-24 实测根因（复核发现 #2 的真实成因，与「阈值抖动」无关）：
`test_state_update_performance` 测的 `update_task_status` 会经由
`StateManager._sync_to_global()` **重写全局状态文件**
`~/.vscode/ai-collab/collaboration_state.json`。该文件按 `workspace_path`
逐条累加、从不回收——开发机上已累积 1581 条，其中 1578 条是 pytest 临时目录
路径（测试自身泄漏的产物），只有 3 条是真实工作区，体积 5.4MB。

于是「单次状态更新」每次都要把这份 5.4MB 重新序列化一遍：真实 HOME 下
40 次采样有 36 次越过 0.1s 阈值，而隔离环境下同一用例只要 0.0011s——75 倍差距。
换句话说，这条基线过去测的是**开发机的历史垃圾清理成本**，不是产品自身开销。

因此这里把 `HOME` / `USERPROFILE` 指向临时目录：全局状态文件随之落到临时目录
（`os.path.expanduser` 跟随 `HOME`），基线才测产品本身。子进程（`python3 -m
ai_collab.cli`）继承同一环境，隔离对它们同样成立。

**边界**：本装置只隔离**测量环境**。全局状态文件无上限增长、死条目从不回收
本身是产品的独立缺陷，另行跟踪，不在性能基线的修复范围内。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把 HOME / USERPROFILE 指向临时目录，隔离全局状态文件。

    `os.path.expanduser` 在 POSIX 上跟随 `HOME`、在 Windows 上跟随
    `USERPROFILE`，两者都要设——CI runner 是 Ubuntu、开发机是 macOS，
    但同一份用例在两端跑，漏掉一个就会在另一端失效。
    """
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    return fake_home
