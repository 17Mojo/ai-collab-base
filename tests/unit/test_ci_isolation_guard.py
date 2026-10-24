"""CI 隔离守护：依赖本机环境的用例会「本地绿、CI 红」。

2026-10-24 实测：`tests/unit/test_codearts_bridge_deliver.py` 有 7 条用例
依赖开发机上**真实安装**的 CodeArts Doer kernel——`~/.codeartsdoer/Visual_Studio_Code/`
下的 `server_config.properties`，以及 `~/.codeartsdoer/kernel-bridge.env` 里的凭据。
bridge 的 `main()` 在进入 dry-run 分支**之前**就先 `_discover_kernel()`，于是：

- 开发机（有 kernel、有凭据）→ 全绿
- CI runner（两者都没有）→ 7 条失败

这是最难查的一类假绿：**本地永远是绿的**，只有 CI 才暴露；而且它伪装成
「CI 环境有问题」，很容易被误判成 runner 的问题而放过真正的根因。

本守护把 CI 的运行条件搬到本地：把 `HOME` 指到一个空目录再跑一遍这些用例。
任何依赖开发机本机状态的写法都会在这里当场暴露。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 涉及本机主目录状态（CodeArts kernel / 凭据文件 / 用户配置 / 记忆源）的用例文件。
# 新增此类文件时一并登记进来，否则守护覆盖不到。
HOME_DEPENDENT_MODULES = [
    "tests/unit/test_codearts_bridge_deliver.py",
    "tests/unit/test_dev_logger.py",
    "tests/unit/test_state_manager_extra.py",
    "tests/unit/test_sync_agent_memory.py",
    "tests/unit/test_vscode_integration.py",
]


def test_home_dependent_tests_pass_with_empty_home(tmp_path: Path):
    """空 HOME 下必须仍然全绿——不得依赖开发机上的任何本机状态。"""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()

    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *HOME_DEPENDENT_MODULES,
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "以下用例在空 HOME 下失败，说明它们依赖开发机上的本机状态"
        "（CodeArts kernel / 凭据文件 / 用户配置）——本地会绿、CI 会红：\n"
        f"{result.stdout[-3000:]}\n{result.stderr[-2000:]}"
    )
