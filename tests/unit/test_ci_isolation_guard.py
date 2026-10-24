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

**只隔离 HOME 是不够的**（2026-10-24 复核补正）：CodeArts 会话由 kernel
进程派生，继承了 kernel 的凭据环境变量（`OPENCODE_SERVER_PASSWORD` 等）。
守护若原样透传 `os.environ`，被守护的用例在开发机上仍能靠**环境变量**
拿到凭据 → 本该「CI 上会红」的用例在本地照样绿 → 守护形同虚设。

所以这里必须**同时**做两件事：
1. `HOME` / `USERPROFILE` 指向空目录（隔离主目录状态）；
2. 显式**剔除凭据类环境变量**（隔离进程环境里的凭据）。

两者缺一，守护就不成立。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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

# 凭据类环境变量：CI runner 上没有，开发机（装了 CodeArts kernel）上可能有。
#
# `resolve_credentials()` 的取值顺序是「环境变量优先于凭据文件」
# （scripts/codearts_bridge_deliver.py），所以只要这些变量还在环境里，
# 被守护的用例就能绕过凭据文件路径直接拿到真凭据 —— 守护失去意义。
#
# 清单来自全仓实际读取点：`grep -rho 'environ\.get("[A-Z_]*"' ai_collab/ scripts/`
CREDENTIAL_ENV_VARS = [
    "OPENCODE_SERVER_PASSWORD",
    "OPENCODE_SERVER_USERNAME",
    "CODEARTS_KERNEL_PASSWORD",
]


def _build_isolated_env(fake_home: Path) -> dict[str, str]:
    """构造被守护子进程的环境：空 HOME + 无凭据变量。"""
    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    for name in CREDENTIAL_ENV_VARS:
        env.pop(name, None)
    return env


def test_home_dependent_tests_pass_with_empty_home(tmp_path: Path):
    """空 HOME 下必须仍然全绿——不得依赖开发机上的任何本机状态。"""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()

    env = _build_isolated_env(fake_home)

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


def test_isolated_env_drops_credential_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """被守护子进程的环境里**不得**残留凭据变量。

    这条守护本身：只要凭据变量透传，被守护的用例就能绕过「无凭据」这一
    CI 前提，守护就再也测不出「本地绿、CI 红」的那类依赖。
    """
    for name in CREDENTIAL_ENV_VARS:
        monkeypatch.setenv(name, "should-not-reach-child")

    env = _build_isolated_env(tmp_path / "fake-home")

    for name in CREDENTIAL_ENV_VARS:
        assert name not in env, f"凭据变量 {name} 透传进了被守护子进程的环境"


def test_credential_vars_are_really_read_by_the_bridge():
    """守住「凭据环境变量确实会被读」这个前提。

    若哪天 `resolve_credentials()` 不再读环境变量，本文件上两条用例就
    变成空转——那时可以撤掉 CREDENTIAL_ENV_VARS，但必须**先**改这里。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_ci_isolation_bridge", PROJECT_ROOT / "scripts" / "codearts_bridge_deliver.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = (PROJECT_ROOT / "scripts" / "codearts_bridge_deliver.py").read_text(
        encoding="utf-8"
    )
    for name in CREDENTIAL_ENV_VARS:
        if name == "OPENCODE_SERVER_USERNAME":
            continue
        assert name in source, f"{name} 已不再被 bridge 读取，CREDENTIAL_ENV_VARS 需要复核"
    assert module is not None
