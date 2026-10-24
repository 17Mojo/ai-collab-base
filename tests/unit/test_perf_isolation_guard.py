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
2. **对照**：同一份污染在场时，**隔离**与**不隔离**的单次 update 耗时要拉开一个
   量级以上的差距。没有这条，正向断言可能因为「污染得不够狠」或「问题其实不存在」
   而假绿——守护就测不出「基线依赖机器历史」这个真问题。

对照用**倍率**而不是「是否越过 0.1s 阈值」来判定：污染态实测 0.098~0.103 秒，
本身就在阈值上下横跳，拿阈值当断言线会写出必然偶发的用例。

本守护只隔离**测量环境**。全局状态文件无上限增长、死条目从不回收本身是产品的
独立缺陷，另行跟踪，不在性能基线的修复范围内。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 与 tests/perf/test_performance_baseline.py::PERF_THRESHOLDS["state_update_single"] 同源。
STATE_UPDATE_THRESHOLD = 0.1

# 污染源的形状对着开发机真实全局文件的实际形状配（1581 条 / 3.9M 字符）。
POLLUTED_ENTRIES = 1500
POLLUTED_ENTRY_TASKS = 6
POLLUTED_TASK_DESCRIPTION_CHARS = 900

# 隔离 / 不隔离的耗时要拉开多少倍才算「污染真的影响了测量」。
# 实测：污染态 0.098~0.103s，隔离态 0.0011s → 倍率约 90。
MEASUREMENT_RATIO_FLOOR = 10

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
    """造一份「被测试自身泄漏撑大」的全局状态文件。"""
    global_dir = fake_home / ".vscode" / "ai-collab"
    global_dir.mkdir(parents=True, exist_ok=True)
    global_file = global_dir / "collaboration_state.json"

    description = "x" * POLLUTED_TASK_DESCRIPTION_CHARS
    doc = {
        f"/tmp/pytest-of-user/pytest-{i}/test_leak{i}/ws": {
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
    result = subprocess.run(
        [sys.executable, "-c", _UPDATE_LATENCY_PROBE],
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


def test_polluted_global_state_dominates_unisolated_measurement(tmp_path: Path):
    """对照：污染态与隔离态的耗时要拉开一个量级——否则上面那条守护可能假绿。

    断言用**倍率**而非「是否越过 0.1s 阈值」：污染态实测 0.098~0.103 秒，
    本身就在阈值上下横跳，拿阈值当断言线会写出必然偶发的用例。
    """
    polluted_home = tmp_path / "polluted-home"
    polluted_home.mkdir()
    _build_polluted_global_state(polluted_home)

    isolated_home = tmp_path / "isolated-home"
    isolated_home.mkdir()

    polluted_elapsed = _measure_update_latency(polluted_home)
    isolated_elapsed = _measure_update_latency(isolated_home)

    ratio = polluted_elapsed / max(isolated_elapsed, 1e-6)
    assert ratio >= MEASUREMENT_RATIO_FLOOR, (
        f"污染态 {polluted_elapsed:.4f}s vs 隔离态 {isolated_elapsed:.4f}s，"
        f"倍率仅 {ratio:.1f}（门槛 {MEASUREMENT_RATIO_FLOOR}）——"
        "污染没能主导测量，说明这份守护测不出「基线依赖机器历史」这个真问题"
    )
    assert isolated_elapsed < STATE_UPDATE_THRESHOLD, (
        f"隔离态单次 update 花了 {isolated_elapsed:.4f}s（阈值 {STATE_UPDATE_THRESHOLD}s）"
        "——隔离后基线仍不达标，隔离没把测量对象与机器历史解耦"
    )
