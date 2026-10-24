---
name: CI 隔离陷阱——「本地绿、CI 红」的用例依赖本机 HOME 状态
description: 2026-10-24 实测——tests/unit/test_codearts_bridge_deliver.py 有 7 条用例依赖开发机上真实安装的 CodeArts Doer kernel 与凭据文件，开发机全绿而 CI runner 全红；本仓已加空 HOME 隔离守护
type: project
from: Agent
---

## 事实（2026-10-24，PR #2 首次触发 CI 时暴露）

`tests/unit/test_codearts_bridge_deliver.py` 有 7 条用例依赖**开发机上的本机状态**：

- `~/.codeartsdoer/Visual_Studio_Code/Vscode_*/server_config.properties`（CodeArts Doer kernel）
- `~/.codeartsdoer/kernel-bridge.env`（kernel 凭据）

bridge 的 `KERNEL_CONFIG_ROOT` / `CREDENTIAL_FILE` / `CRON_STORE_PATH` 都是
`Path.home()` 下的全局常量，而 `main()` 在进入 dry-run 分支**之前**就先
`_discover_kernel()`。于是：

- 开发机（有 kernel、有凭据）→ 7 条全绿
- CI runner（两者都没有）→ 7 条全红，报「找不到 CodeArts Doer kernel 的
  server_config.properties，查找路径：/home/runner/.codeartsdoer/Visual_Studio_Code」

**为什么一直没暴露**：本仓 feature 分支推送**不触发 CI**（lint.yml / test.yml 只在
push 到 main 或 PR 到 main 时跑），所以本仓历史上第一次 PR 才第一次真正跑 CI——
「本地全绿」与「CI 全红」之间的差距可以潜伏整整 118 个提交。

## 修法与已有守护

1. 该测试文件加 **autouse fixture**，把 `KERNEL_CONFIG_ROOT` 钉到 tmp 内的假 kernel
   （pid 用 `os.getpid()`，保证 `_pid_alive` 判定为存活）。
2. `test_purge_residue_cli_flag_runs_purge` 补 `resolve_credentials` 打桩。
3. **`tests/unit/test_ci_isolation_guard.py`（新增）**：把 `HOME` 指到空目录，
   子进程重跑所有「涉及本机主目录状态」的用例文件，rc 必须为 0。
   已做反向验证——撤掉打桩后守护立即失败。

## How to apply

1. 新增/修改用例时，凡是碰到 `Path.home()`、凭据文件、本机服务端口的，
   **一律用 tmp fixture 打桩**，别依赖开发机状态。相关源文件见
   `scripts/codearts_bridge_deliver.py`、`ai_collab/codex_integration.py`
   （`~/.claude/settings.json`）、`scripts/sync_agent_memory.py`
   （`~/.codeartsdoer/memory/<slug>/`）。
2. 往 `tests/unit/test_ci_isolation_guard.py` 的 `HOME_DEPENDENT_MODULES` 登记新文件，
   否则守护覆盖不到。
3. **开 PR 前的自检**：本地「全绿」不等于 CI 会绿。凡是涉及本机环境的分支，
   先用空 HOME 跑一遍再推。
4. 推 feature 分支**不会**跑门禁——想触发门禁只能开 PR 到 main。

**相关**：[[project_openspec_cli_wiring]]、[[feedback_verification_static_vs_behavioral]]
