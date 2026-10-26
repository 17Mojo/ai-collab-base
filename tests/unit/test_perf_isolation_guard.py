"""性能基线隔离守护：基线必须与「运行者的机器历史」解耦。

2026-10-24 实测根因（复核发现 #2 的真实成因，与「阈值抖动」无关）：
`tests/perf/test_performance_baseline.py::test_state_update_performance` 测的
`update_task_status` 会经由 `StateManager._sync_to_global()` **重写全局状态文件**
`~/.vscode/ai-collab/collaboration_state.json`。该文件按 `workspace_path` 逐条累加、
**从不回收**——开发机上已累积 1581 条，其中 1578 条是 pytest 临时目录路径
（测试自身泄漏的产物），只有 3 条是真实工作区，体积 5.4MB。

于是「单次状态更新」每次都要把这份 5.4MB 重新序列化一遍：拿开发机真实全局文件
的**逐字节副本**做隔离复现，单次 update 稳定落在 0.098~0.103 秒——**死死贴着
0.1s 阈值**；而把 HOME 隔离到空目录后，同一用例只要 0.0011 秒（90 倍差距）。

换句话说，这条基线过去测的是**开发机的历史垃圾清理成本**，不是产品自身开销。
本守护把这个前提钉住：

1. **正向**：把 ambient HOME 污染成 5MB 的全局状态文件后跑性能套件，仍必须全绿，
   且 ambient 文件**一个字节都不能被改**（隔离确实生效）。
2. **对照**（2026-10-26 随产品修复翻转了方向，见下）。

对照用**倍率**而不是「是否越过 0.1s 阈值」来判定：污染态实测 0.098~0.103 秒，
本身就在阈值上下横跳，拿阈值当断言线会写出必然偶发的用例。

---
**2026-10-26：全局状态文件的死条目回收已修复**（见
`collaboration/results/RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md`），
产品现在会把「路径已不存在」的条目回收掉。因此：

- 原来的对照断言「污染态必须比隔离态慢一个量级」，在修复后**等于要求缺陷永远
  存在**——它必须跟着翻转，否则修复永远落不了地。
- 翻转后的对照是它的**反面**：污染态必须先被回收（体积掉下来），回收之后
  **稳态**耗时就不得再被机器历史主导。
- canary 的牙齿没变：回收逻辑一旦坏掉，被回收的体积不会掉、稳态耗时会重新被
  机器历史主导，本守护照样变红。
- 断言同时保留「污染在被回收之前确实主导了测量」这一条——它是旧对照想说的话，
  现在被表达成「第一次写入（顺带回收）比稳态慢一个量级」。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 与 tests/perf/test_performance_baseline.py::PERF_THRESHOLDS["state_update_single"] 同源。
STATE_UPDATE_THRESHOLD = 0.1

# 污染源的形状对着开发机真实全局文件的实际形状配（1581 条 / 3.9M 字符）。
POLLUTED_ENTRIES = 1500
POLLUTED_ENTRY_TASKS = 6
POLLUTED_TASK_DESCRIPTION_CHARS = 900

# 污染态（**尚未**被回收时）与隔离态的耗时要拉开多少倍，才算「污染真的影响了测量」。
# 实测：污染态 0.098~0.103s，隔离态 0.0011s → 倍率约 90。
MEASUREMENT_RATIO_FLOOR = 10

# 回收之后，污染态的稳态耗时就**不得**再被机器历史主导——倍率必须落在这个上限内。
# 回收逻辑坏掉时这个倍率会飙回 90 上下 ⇒ 守护变红。
MEASUREMENT_RATIO_CEILING = 10

# 第一次写入（顺带回收）相对稳态写入，至少要慢这么多倍，才算「污染在被回收之前
# 确实主导了测量」——这是旧对照想说的话，修复后依然成立。
RECLAIM_SPEEDUP_FLOOR = 5

# 量一次单次 update 耗时的探针。走真实写路径（含 _sync_to_global 全局同步）。
_UPDATE_LATENCY_PROBE = """
import tempfile
import time

from ai_collab.state_manager import StateManager, TaskStatus

ws = tempfile.mkdtemp(prefix="perf-guard-probe-")
state = StateManager(workspace_path=ws)
state.register_task(
    task_id="PERF-GUARD-001",
    ai_type="codearts_agent",
    description="Performance guard task",
    files=["test.py"],
    change_id="bugfix/no-spec",
    assignee="codearts_agent",
    reviewer="claude_code",
    primary_skill="performance-expert",
    support_skills=["devops-architect"],
    acceptance_commands=["python3 -m pytest -q tests/perf/"],
    result_file="collaboration/results/RESULT_PERF-GUARD-001.md",
)
start = time.perf_counter()
state.update_task_status("PERF-GUARD-001", TaskStatus.IMPLEMENTING, note="guard")
print(time.perf_counter() - start)
"""


def _build_polluted_global_state(fake_home: Path) -> Path:
    """造一份「被测试自身泄漏撑大」的全局状态文件。

    条目的 key 必须是**系统临时目录**下的路径——这正是实测到的泄漏形态
    （pytest 临时工作区），也是产品回收规则里「立即回收」的那一档。
    写死 `/tmp/...` 会让判定随平台漂移：macOS 的 `tempfile.gettempdir()` 是
    `/var/folders/...`（不在 `/tmp` 下面），Linux 才是 `/tmp`。
    """
    global_dir = fake_home / ".vscode" / "ai-collab"
    global_dir.mkdir(parents=True, exist_ok=True)
    global_file = global_dir / "collaboration_state.json"

    temp_root = tempfile.gettempdir()
    description = "x" * POLLUTED_TASK_DESCRIPTION_CHARS
    doc = {
        f"{temp_root}/pytest-of-user/pytest-{i}/test_leak{i}/ws": {
            "last_sync": "2026-10-24T00:00:00",
            "tasks": {
                f"PERF-LEAK-{i}-{j}": {
                    "task_id": f"PERF-LEAK-{i}-{j}",
                    "ai_type": "codearts_agent",
                    "description": description,
                    "files": ["test.py"],
                    "status": "completed",
                }
                for j in range(POLLUTED_ENTRY_TASKS)
            },
            "patches": {},
            "active_tasks": [],
            "conflicts": [],
        }
        for i in range(POLLUTED_ENTRIES)
    }
    global_file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return global_file


# 量一次**首次写入**耗时的探针。首次写入 = 读一遍现有全局文件 + 回收死条目 +
# 写回。稳态探针（`_UPDATE_LATENCY_PROBE`）量的 `update_task_status` 发生在
# `register_task` 之后——那时回收已经做完了，量不到「机器历史」的那一次成本。
_FIRST_WRITE_LATENCY_PROBE = """
import tempfile
import time

from ai_collab.state_manager import StateManager

ws = tempfile.mkdtemp(prefix="perf-guard-probe-")
state = StateManager(workspace_path=ws)
start = time.perf_counter()
state.register_task(
    task_id="PERF-GUARD-001",
    ai_type="codearts_agent",
    description="Performance guard task",
    files=["test.py"],
    change_id="bugfix/no-spec",
    assignee="codearts_agent",
    reviewer="claude_code",
    primary_skill="performance-expert",
    support_skills=["devops-architect"],
    acceptance_commands=["python3 -m pytest -q tests/perf/"],
    result_file="collaboration/results/RESULT_PERF-GUARD-001.md",
)
print(time.perf_counter() - start)
"""


def _digest(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _env_with_home(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    return env


def _measure_update_latency(home: Path) -> float:
    """在给定 HOME 下量一次单次 update 耗时。"""
    return _run_probe(_UPDATE_LATENCY_PROBE, home)


def _measure_first_write_latency(home: Path) -> float:
    """在给定 HOME 下量一次**首次写入**耗时（含读旧文件 + 回收 + 写回）。"""
    return _run_probe(_FIRST_WRITE_LATENCY_PROBE, home)


def _run_probe(probe: str, home: Path) -> float:
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(PROJECT_ROOT),
        env=_env_with_home(home),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"探针执行失败：\n{result.stderr[-2000:]}"
    return float(result.stdout.strip().splitlines()[-1])


def test_perf_suite_ignores_polluted_ambient_global_state(tmp_path: Path):
    """被污染的 ambient HOME 不得影响性能基线的结果，也不得被写。"""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    polluted = _build_polluted_global_state(fake_home)
    polluted_size = polluted.stat().st_size
    before = _digest(polluted)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/perf/",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(PROJECT_ROOT),
        env=_env_with_home(fake_home),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "性能套件在「被污染的 ambient HOME」下失败——说明基线仍在依赖运行者的机器历史：\n"
        f"{result.stdout[-3000:]}\n{result.stderr[-2000:]}"
    )
    assert _digest(polluted) == before, (
        f"ambient 全局状态文件被改写（原 {polluted_size} 字节）——"
        "说明性能用例仍写向运行者的真实全局文件，隔离没有生效"
    )


def test_polluted_global_state_is_reclaimed_and_stops_dominating_measurement(
    tmp_path: Path,
):
    """对照（修复后）：污染态必须先被回收，之后**稳态**耗时不被机器历史主导。

    方向说明：这条断言在 2026-10-26 随产品修复翻转了。原来的对照要求
    「污染态必须比隔离态慢一个量级」——那是**缺陷存在**的证据（全局状态文件
    从不回收死条目，1500 条垃圾每次都要整份重新序列化）。缺陷修好后，同一个
    断言等于要求缺陷永远存在，修复就永远落不了地。

    翻转后守护的是同一件事的**修复后形态**：机器历史不得再主导测量。
    canary 的牙齿没变——回收逻辑坏掉时：
      - 体积掉不下来（第一条断言红）
      - 稳态耗时被机器历史重新主导（第二条断言红）

    并且「污染在被回收之前确实主导了测量」这条旧结论仍然被钉住：
    首次写入（读 9.7MB + 回收 + 写回）必须显著慢于隔离态的首次写入。
    """
    polluted_home = tmp_path / "polluted-home"
    polluted_home.mkdir()
    polluted = _build_polluted_global_state(polluted_home)
    polluted_size_before = polluted.stat().st_size

    isolated_home = tmp_path / "isolated-home"
    isolated_home.mkdir()

    # 首次写入：读一遍 9.7MB 的旧文件 + 回收死条目 + 写回（机器历史在这一刻要付钱）
    first_elapsed = _measure_first_write_latency(polluted_home)
    polluted_size_after = polluted.stat().st_size
    isolated_first_elapsed = _measure_first_write_latency(isolated_home)

    # 稳态：回收之后，文件已经很小
    polluted_elapsed = _measure_update_latency(polluted_home)
    isolated_elapsed = _measure_update_latency(isolated_home)

    assert polluted_size_after < polluted_size_before * 0.1, (
        f"死条目没有被回收：{polluted_size_before} → {polluted_size_after} 字节。"
        "全局状态文件的无上限增长这个缺陷还在"
    )

    first_ratio = first_elapsed / max(isolated_first_elapsed, 1e-6)
    assert first_ratio >= RECLAIM_SPEEDUP_FLOOR, (
        f"污染态首次写入 {first_elapsed:.4f}s vs 隔离态首次写入 "
        f"{isolated_first_elapsed:.4f}s，倍率仅 {first_ratio:.1f}"
        f"（门槛 {RECLAIM_SPEEDUP_FLOOR}）——"
        "说明这份污染当初根本没主导过测量，对照就成了空转"
    )

    ratio = polluted_elapsed / max(isolated_elapsed, 1e-6)
    assert ratio <= MEASUREMENT_RATIO_CEILING, (
        f"回收之后污染态 {polluted_elapsed:.4f}s 仍显著慢于隔离态 "
        f"{isolated_elapsed:.4f}s（倍率 {ratio:.1f}，上限 {MEASUREMENT_RATIO_CEILING}）"
        "——机器历史仍在主导测量，回收逻辑多半没生效"
    )
    assert isolated_elapsed < STATE_UPDATE_THRESHOLD, (
        f"隔离态单次 update 花了 {isolated_elapsed:.4f}s（阈值 {STATE_UPDATE_THRESHOLD}s）"
        "——隔离后基线仍不达标，隔离没把测量对象与机器历史解耦"
    )


def test_polluted_global_state_would_dominate_without_reclamation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """反证：回收逻辑坏掉时，污染态会重新主导测量——证明上面那条对照有牙齿。

    这里不靠改产品代码，而是**直接构造**「产品没能回收」的状态：把死条目的 key
    换成仍然存在的目录（产品按设计不会回收路径还在的条目），并把容量兜底关掉
    （关掉才等价于「修复前」的行为）。此时这份大文件会一直留在那里，每次写入
    都要整份重写——机器历史重新主导测量。
    """
    monkeypatch.setenv("AI_COLLAB_GLOBAL_STATE_MAX_ENTRIES", "100000")
    monkeypatch.setenv("AI_COLLAB_GLOBAL_STATE_MAX_BYTES", str(512 * 1024 * 1024))

    polluted_home = tmp_path / "polluted-home"
    polluted_home.mkdir()
    polluted = _build_polluted_global_state(polluted_home)

    doc = json.loads(polluted.read_text(encoding="utf-8"))
    survivors = tmp_path / "survivors"
    survivors.mkdir()
    rebuilt: dict[str, object] = {}
    for index, value in enumerate(doc.values()):
        holder = survivors / f"ws-{index}"
        holder.mkdir()
        rebuilt[str(holder)] = value
    polluted.write_text(json.dumps(rebuilt, ensure_ascii=False), encoding="utf-8")

    elapsed = _measure_update_latency(polluted_home)

    isolated_home = tmp_path / "isolated-home"
    isolated_home.mkdir()
    isolated_elapsed = _measure_update_latency(isolated_home)

    ratio = elapsed / max(isolated_elapsed, 1e-6)
    assert ratio >= MEASUREMENT_RATIO_FLOOR, (
        f"存活路径的污染态 {elapsed:.4f}s vs 隔离态 {isolated_elapsed:.4f}s，"
        f"倍率仅 {ratio:.1f}（门槛 {MEASUREMENT_RATIO_FLOOR}）——"
        "污染没能主导测量，这份反证就证明不了上面那条对照有牙齿"
    )
