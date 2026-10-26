"""全局状态文件的回收守护。

2026-10-24 实测到的缺陷：`~/.vscode/ai-collab/collaboration_state.json` 按
`workspace_path` 逐条累加、**从不回收**——开发机上 1589 条里 1587 条是 pytest
临时目录（测试自身泄漏的产物），只有 2 条真实工作区，体积 5.4MB。后果是每次
状态更新都要把整份重新序列化一遍（单次 update 0.098~0.103s，贴着 0.1s 阈值）。

全局文件是**镜像**，不是事实源：每个工作区自己的 `logs/collaboration_state.json`
才是事实源，全局文件只承担「跨工作区索引」职责。所以回收条目不会丢用户可见的
状态——该工作区下次同步时会被重新写回。

本文件钉住回收策略的**行为契约**：

  ① 临时目录下的死条目立即回收（实测泄漏全是这一类）
  ② 非临时目录下的死条目有宽限期（保护「盘临时未挂载」的真实工作区）
  ③ 真实工作区条目不被误删
  ④ 当前正在写的条目永不被回收
  ⑤ 判不出来的 key（`unknown` 之类）不被误删
  ⑥ 条目 schema 不变（`last_sync` / `tasks` / `patches` / `active_tasks` / `conflicts`）
  ⑦ 容量兜底按 `last_sync` 淘汰最旧的，且永不动当前条目
  ⑧ **反向可验证**：把回收逻辑改坏（退化成 no-op），守护用例必须变红

第 ⑧ 条是这套守护的元守护：没有它，「守护用例全绿」可能只是因为断言写空了。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from ai_collab import state_manager
from ai_collab.state_manager import StateManager, VSCodeStateManager

ENTRY_SCHEMA_KEYS = {"last_sync", "tasks", "patches", "active_tasks", "conflicts"}


# --------------------------------------------------------------------------- #
# 夹具与工具
# --------------------------------------------------------------------------- #


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _sync(workspace: str, task_id: str = "T-1") -> StateManager:
    """在指定工作区跑一次真实的状态同步（`register_task` → `_save_state` → `_sync_to_global`）。"""
    manager = StateManager(workspace_path=workspace)
    manager.register_task(
        task_id=task_id,
        ai_type="claude_code",
        description="global sync guard",
        files=[],
    )
    return manager


def _seed_entry(path: Path, key: str, last_sync: str, description_chars: int = 0) -> None:
    """直接往全局文件里塞一条条目。

    用来模拟「别的进程/别的机器写进来的条目」——产品自己写不进去的路径
    （比如未挂载的磁盘），只能这样构造。
    """
    doc = _read(path)
    doc[key] = {
        "last_sync": last_sync,
        "tasks": {
            f"SEED-{i}": {
                "task_id": f"SEED-{i}",
                "ai_type": "claude_code",
                "description": "x" * description_chars,
                "files": [],
                "status": "completed",
            }
            for i in range(3)
        },
        "patches": {},
        "active_tasks": [],
        "conflicts": [],
    }
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _now_iso(days_ago: float = 0.0) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat()


# --------------------------------------------------------------------------- #
# ① 临时目录下的死条目立即回收
# --------------------------------------------------------------------------- #


def _exercise_temp_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, break_reclamation: bool = False
) -> dict[str, Any]:
    """写一个临时工作区 → 把它删掉 → 再同步一次，返回最终的全局状态。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))
    if break_reclamation:
        # 模拟「缺陷复发」：回收逻辑退化成 no-op
        monkeypatch.setattr(
            StateManager, "_reclaim_dead_global_entries", lambda self, gs, key: []
        )

    leaked = tmp_path / "ws-leaked"
    leaked.mkdir()
    _sync(str(leaked), "T-1")
    shutil.rmtree(leaked)

    survivor = tmp_path / "ws-alive"
    survivor.mkdir()
    _sync(str(survivor), "T-2")
    return _read(global_file)


def _assert_leak_reclaimed(state: dict[str, Any], leaked: str, survivor: str) -> None:
    assert leaked not in state, "已消失的临时工作区必须被回收"
    assert survivor in state, "存活的工作区必须保留"


def test_temp_workspace_entries_are_reclaimed_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """① 临时工作区消失后，下一次同步就该被回收。"""
    assert StateManager._is_under_temp_dir(str(tmp_path)), (
        "测试前提失效：tmp_path 必须位于系统临时目录下，"
        "否则「临时目录死条目立即回收」这条规则不适用"
    )
    state = _exercise_temp_leak(tmp_path, monkeypatch)
    _assert_leak_reclaimed(state, str(tmp_path / "ws-leaked"), str(tmp_path / "ws-alive"))


def _measure_leak_growth(
    root: Path, monkeypatch: pytest.MonkeyPatch, *, break_reclamation: bool = False
) -> tuple[int, int, int, int]:
    """连续写入 4 次 + 8 次泄漏，返回 (4 次后的条目数/字节, 12 次后的条目数/字节)。"""
    root.mkdir(parents=True, exist_ok=True)
    global_file = root / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))
    if break_reclamation:
        monkeypatch.setattr(
            StateManager, "_reclaim_dead_global_entries", lambda self, gs, key: []
        )

    def write_leaks(count: int, offset: int) -> None:
        for i in range(offset, offset + count):
            ws = root / f"leak-{i}"
            ws.mkdir()
            _sync(str(ws), f"T-{i}")
            shutil.rmtree(ws)

    write_leaks(4, 0)
    after_four = len(_read(global_file))
    size_after_four = global_file.stat().st_size
    write_leaks(8, 4)
    after_twelve = len(_read(global_file))
    size_after_twelve = global_file.stat().st_size
    return after_four, after_twelve, size_after_four, size_after_twelve


def test_entry_count_does_not_grow_with_repeated_leaked_workspaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """工单验收：连续写入 N 个已消失的临时 workspace，条目数/体积不随之无上限增长。"""
    after_four, after_twelve, size_after_four, size_after_twelve = _measure_leak_growth(
        tmp_path / "healthy", monkeypatch
    )

    assert after_twelve <= after_four, (
        f"条目数随泄漏次数增长：4 次后 {after_four} 条，12 次后 {after_twelve} 条"
    )
    # 体积不随泄漏次数**成比例**增长（条目内容本身有 id 长度等零星差异，
    # 所以按比例判定，不按绝对字节相等判定）
    assert size_after_twelve <= size_after_four * 1.5, (
        f"文件体积随泄漏次数成比例增长：4 次后 {size_after_four} 字节，"
        f"12 次后 {size_after_twelve} 字节"
    )
    assert after_twelve <= 2, f"泄漏的工作区没有被回收，仍剩 {after_twelve} 条"

    # 反证：把回收逻辑改坏，同样的写入次数就会让条目数线性增长——
    # 证明上面那两条断言真的对「回收逻辑」敏感，而不是恒真。
    broken_four, broken_twelve, _, _ = _measure_leak_growth(
        tmp_path / "broken", monkeypatch, break_reclamation=True
    )
    assert broken_twelve > broken_four, (
        "反证失败：回收逻辑坏掉后条目数竟然没增长，说明上面的断言可能恒真"
    )


# --------------------------------------------------------------------------- #
# ②③ 真实工作区不被误删（含「盘临时未挂载」这一档）
# --------------------------------------------------------------------------- #


def test_live_workspace_entries_are_never_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """③ 真实工作区条目不被误删。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))

    live = []
    for i in range(3):
        ws = tmp_path / f"live-{i}"
        ws.mkdir()
        live.append(str(ws))
        _sync(str(ws), f"T-{i}")

    # 再同步一次，触发一轮回收
    _sync(live[0], "T-again")
    state = _read(global_file)
    for key in live:
        assert key in state, f"存活的工作区被误删：{key}"


def test_dead_non_temp_workspace_is_kept_during_grace_period(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """② 非临时目录下的死条目有宽限期——保护「盘临时未挂载」的真实工作区。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))

    unmounted = "/Volumes/external-disk/projects/team-repo"
    _seed_entry(global_file, unmounted, last_sync=_now_iso())

    alive = tmp_path / "alive"
    alive.mkdir()
    _sync(str(alive), "T-1")

    assert unmounted in _read(global_file), (
        "宽限期内不得回收非临时目录的死条目——那可能只是磁盘临时没挂上"
    )


def test_dead_non_temp_workspace_is_reclaimed_after_grace_period(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """② 超过宽限期后，非临时目录的死条目才被回收。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))

    unmounted = "/Volumes/external-disk/projects/team-repo"
    _seed_entry(global_file, unmounted, last_sync=_now_iso(days_ago=30))

    alive = tmp_path / "alive"
    alive.mkdir()
    _sync(str(alive), "T-1")

    assert unmounted not in _read(global_file), (
        "超过宽限期的死条目必须被回收——否则真实项目目录被删/被移走后会永久留垃圾"
    )


# --------------------------------------------------------------------------- #
# ④⑤ 当前条目与判不出来的 key
# --------------------------------------------------------------------------- #


def test_current_workspace_entry_is_never_reclaimed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """④ 当前正在写的条目永不被回收——哪怕它自己的路径已经不存在。

    关键：这条路径必须**本来就可回收**（在临时目录下、且确实不存在）。
    否则测到的「没被删」其实是宽限期在兜底，而不是当前条目保护在兜底——
    那样这条用例就证明不了任何事。
    """
    monkeypatch.setattr(
        VSCodeStateManager, "get_global_state_file", lambda: str(tmp_path / "g.json")
    )
    manager = StateManager(workspace_path=str(tmp_path / "alive"))

    ghost = str(tmp_path / "gone")
    other = str(tmp_path / "other-gone")
    assert not Path(ghost).exists()
    assert manager._global_entry_is_reclaimable(ghost, {"last_sync": _now_iso()}), (
        "测试前提失效：这条路径本来就可回收"
    )

    state = {
        ghost: {"last_sync": _now_iso(), "tasks": {}},
        other: {"last_sync": _now_iso(), "tasks": {}},
    }
    reclaimed = manager._reclaim_dead_global_entries(state, current_key=ghost)

    assert ghost in state, "当前正在写的条目被回收了"
    assert ghost not in reclaimed
    assert other not in state, "非当前的可回收条目应该照常被回收"
    assert reclaimed == [other]


def test_unknown_key_is_not_reclaimed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑤ 判不出是否为路径的 key（`unknown`）不被误删。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))

    _seed_entry(global_file, "unknown", last_sync=_now_iso())
    alive = tmp_path / "alive"
    alive.mkdir()
    _sync(str(alive), "T-1")

    assert "unknown" in _read(global_file), "判不出来的 key 被误删了"


# --------------------------------------------------------------------------- #
# ⑥ 条目 schema 不变（兼容性：读取方的数据形状不能被这次修复改掉）
# --------------------------------------------------------------------------- #


def test_entry_schema_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑥ 条目 schema 不变。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))

    ws = tmp_path / "ws"
    ws.mkdir()
    _sync(str(ws), "T-1")

    entry = _read(global_file)[str(ws)]
    assert set(entry) == ENTRY_SCHEMA_KEYS, f"条目 schema 变了：{sorted(entry)}"


# --------------------------------------------------------------------------- #
# ⑦ 容量兜底
# --------------------------------------------------------------------------- #


def test_entry_count_cap_evicts_oldest_and_keeps_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑦ 条目数超上限时按 last_sync 淘汰最旧的，且永不动当前条目。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))
    monkeypatch.setattr(state_manager, "GLOBAL_STATE_MAX_ENTRIES", 3)

    live = []
    for i in range(5):
        ws = tmp_path / f"live-{i}"
        ws.mkdir()
        live.append(str(ws))
        _seed_entry(global_file, str(ws), last_sync=_now_iso(days_ago=10 - i))
    current = tmp_path / "current"
    current.mkdir()
    _sync(str(current), "T-current")

    state = _read(global_file)
    assert len(state) <= 3, f"条目数没有收敛到上限：{len(state)}"
    assert str(current) in state, "当前条目被容量兜底淘汰了"
    assert live[-1] in state, "最新的条目不该被淘汰"
    assert live[0] not in state, "最旧的条目应该被淘汰"


def test_byte_cap_evicts_oldest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑦ 体积超上限时按 last_sync 淘汰最旧的。"""
    global_file = tmp_path / "global_state.json"
    monkeypatch.setattr(VSCodeStateManager, "get_global_state_file", lambda: str(global_file))
    monkeypatch.setattr(state_manager, "GLOBAL_STATE_MAX_BYTES", 8192)

    live = []
    for i in range(4):
        ws = tmp_path / f"big-{i}"
        ws.mkdir()
        live.append(str(ws))
        _seed_entry(global_file, str(ws), last_sync=_now_iso(days_ago=10 - i), description_chars=4000)
    current = tmp_path / "current"
    current.mkdir()
    _sync(str(current), "T-current")

    size = global_file.stat().st_size
    assert size <= state_manager.GLOBAL_STATE_MAX_BYTES, f"体积没有收敛到上限：{size}"
    assert str(current) in _read(global_file), "当前条目被容量兜底淘汰了"


# --------------------------------------------------------------------------- #
# ⑧ 反向可验证（这套守护的元守护）
# --------------------------------------------------------------------------- #


def test_reclamation_guard_is_reverse_verifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑧ 把回收逻辑改坏（退化成 no-op），守护用例必须变红。

    没有这一条，「守护用例全绿」可能只是因为断言写空了——这套守护就证明不了
    「回收逻辑一旦坏掉，用例会报警」。
    """
    with pytest.raises(AssertionError):
        state = _exercise_temp_leak(tmp_path, monkeypatch, break_reclamation=True)
        _assert_leak_reclaimed(
            state, str(tmp_path / "ws-leaked"), str(tmp_path / "ws-alive")
        )


def test_temp_dir_detection_uses_realpath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """⑧ 临时目录判定必须走 realpath。

    macOS 上 `/var/folders/...` 与 `/private/var/folders/...` 是同一个目录，
    pytest 写进全局文件的是后者——只比字符串会把临时目录判成「不是临时目录」。
    """
    temp_root = tempfile.gettempdir()
    assert StateManager._is_under_temp_dir(temp_root)
    assert StateManager._is_under_temp_dir(str(Path(temp_root) / "pytest-of-x" / "ws"))
    assert not StateManager._is_under_temp_dir("/Users/somebody/Documents/project")


# --------------------------------------------------------------------------- #
# ⑨ 测试套件不得写进开发机「真实」的全局状态文件
# --------------------------------------------------------------------------- #


def _digest_or_missing(path: Path) -> str:
    """文件不存在时返回一个固定标记，便于和「存在但没变」区分开。"""
    if not path.exists():
        return "<absent>"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_suite_does_not_write_the_ambient_global_state_file(
    tmp_path: Path, ambient_global_state_file: str
):
    """⑨ 跑一次真实的状态同步，开发机真实的全局文件必须一个字节都没变。

    回收逻辑是**止血**，不是**治本**：产品照写全局文件，只是现在会回收死条目。
    治本的那一半是「测试不该写进开发机的真实文件」——由 `tests/conftest.py`
    的 HOME 隔离装置负责。这条守护把那个装置钉住：
    隔离一旦失效，真实文件立刻被改写，本用例当场变红。

    「真实文件」= 用例启动时环境里的 HOME 指向的那个（root conftest 在**模块
    导入时**就把原样 HOME 捕获下来了，早于任何 fixture 生效）。
    """
    assert ambient_global_state_file, "没捕获到 ambient HOME——守护无从比对"
    ambient = Path(ambient_global_state_file)
    before = _digest_or_missing(ambient)

    # 走真实写路径：StateManager → register_task → _sync_to_global
    workspace = tmp_path / "ws-ambient"
    workspace.mkdir()
    _sync(str(workspace), "T-AMBIENT")

    after = _digest_or_missing(ambient)
    assert after == before, (
        f"测试套件改写了开发机真实的全局状态文件：{ambient}\n"
        f"  隔离前 {before[:16]}… → 隔离后 {after[:16]}…\n"
        "HOME 隔离装置失效了——测试正在往真实文件里写条目"
    )


def test_global_state_file_is_redirected_into_the_test_sandbox(
    tmp_path: Path, ambient_global_state_file: str
):
    """⑨ 反向：全局文件确实被**写**了，只是写在隔离目录里。

    没有这条，上面那条可能因为「产品压根不写全局文件」而恒真。
    """
    monkey_home = Path(os.environ["HOME"])
    # ambient 文件 = <HOME>/.vscode/ai-collab/collaboration_state.json
    # ⇒ parents[2] 就是原始 HOME
    ambient_home = Path(ambient_global_state_file).parents[2]
    assert monkey_home != ambient_home, (
        f"HOME 没被隔离到别处（仍是 {ambient_home}）——隔离装置本身没生效"
    )

    workspace = tmp_path / "ws-sandbox"
    workspace.mkdir()
    _sync(str(workspace), "T-SANDBOX")

    sandboxed = monkey_home / ".vscode" / "ai-collab" / "collaboration_state.json"
    assert sandboxed.exists(), f"全局状态文件没落在隔离目录里：{sandboxed}"
    assert str(workspace) in _read(sandboxed), "隔离目录里的全局文件没有本次写入的条目"
