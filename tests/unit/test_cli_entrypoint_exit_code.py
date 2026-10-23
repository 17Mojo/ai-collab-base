"""TASK-P1-CLI-EXITCODE-001 回归测试。

守护点：两个模块入口的**进程退出码**必须如实反映 main() 的返回值。

- ``python3 -m ai_collab.cli`` -> ``ai_collab/cli/__main__.py``
- ``python3 -m ai_collab``     -> ``ai_collab/__main__.py``

必须用 subprocess 跑真实进程：直接调用 ``main()`` 测不到「入口没有把返回值
交给 sys.exit」这个缺陷 —— 这正是上一轮工单的漏网之处。
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, module: str = "ai_collab.cli", workspace: str | None = None):
    cmd = [sys.executable, "-m", module]
    if workspace:
        cmd += ["-w", workspace]
    cmd += list(args)
    return subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )


def test_cli_entry_invalid_days_exits_nonzero():
    """用例 1：--days 0 是函数级友好报错，进程退出码必须非 0。"""
    proc = _run("pack", "trending", "--days", "0")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "必须为正整数" in proc.stdout, proc.stdout
    assert "Traceback" not in proc.stderr, proc.stderr


def test_cli_entry_negative_days_exits_nonzero():
    """用例 2：--days -1 同样必须非 0 退出。"""
    proc = _run("pack", "trending", "--days", "-1")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr, proc.stderr


def test_cli_entry_success_path_returns_zero():
    """用例 3：--days 7 --limit 0 成功路径的退出码保持 0。"""
    proc = _run("pack", "trending", "--days", "7", "--limit", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_cli_entry_limit_zero_returns_zero():
    """用例 4：--limit 0 成功路径的退出码保持 0。"""
    proc = _run("pack", "trending", "--limit", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_package_entry_invalid_days_exits_nonzero():
    """用例 5：python3 -m ai_collab 入口同样必须传播非 0 退出码。"""
    proc = _run("pack", "trending", "--days", "0", module="ai_collab")
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "必须为正整数" in proc.stdout, proc.stdout
    assert "Traceback" not in proc.stderr, proc.stderr


def test_ack_success_path_still_emits_ack_line(tmp_path):
    """用例 6：ACK 协议命令的成功路径没被改坏（退出码 0 且输出 ACK 行）。

    ack 会读写 ACK 桥接状态，因此必须用 tmp_path 隔离工作区。
    """
    proc = _run("ack", "--task-id", "none", "--status", "ok", workspace=str(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ".ACK|" in proc.stdout, proc.stdout


def test_ack_missing_task_id_exits_nonzero():
    """用例 7：缺 --task-id 时 argparse 报错，退出码非 0。"""
    proc = _run("ack")
    assert proc.returncode != 0, proc.stdout + proc.stderr
