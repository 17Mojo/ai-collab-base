---
name: CLI 退出码传递缺陷与 R6 禁止修改清单
description: 2026-10-23 TASK-P1-TRENDING-CLI-001 验收发现 ai_collab/cli/__main__.py 丢弃 main() 返回值，子命令 return 1 到不了进程退出码（browse 分支同理）；该文件属 R6 禁改清单，故只报告未修
type: project
from: Agent
---

## 事实

- **遗留缺陷（2026-10-23 验收发现）**：`ai_collab/cli/__main__.py` 调用 `main()` 但**丢弃其返回值**，因此 CLI 子命令内部的 `return 1`（例如 `--days 0` 这类非法入参）**传不到进程退出码**，进程仍以 0 退出；`browse` 分支同样如此。属**既有缺陷**，非本次改动引入。
- **治理约束**：该工单契约的 **R6「禁止修改清单」把 `ai_collab/cli/__main__.py` 列入禁改文件**，故发现缺陷只能**报告、不得擅自修改**——已写入结果文件「风险」段交复核方裁决。
- **关联交付（2026-10-23）**：`TASK-P1-TRENDING-CLI-001`（新增 pack trending CLI 子命令）验收全绿——新增 `test_cli_pack_trending.py` 10 passed、既有 `test_pack_store.py` 30 passed（零改动）、**全量 2890 passed / 6 skipped / 0 failed**、`ruff check ai_collab/` All checks passed、`tasks validate-contract` 无问题。结果文件 `collaboration/results/RESULT-P1-TRENDING-CLI-2026-10-23.md`，ACK 前缀 `A.ACK`（格式 `A.ACK|task=<TASK_ID>|status=ok|result=<路径>`）。

**Why**: 该项目的派单工单带「禁止修改清单」条款，触碰清单内文件等于越权变更公共入口；而 CLI 退出码这条缺陷一旦被"顺手修掉"就会破坏契约校验，所以正确动作是**报告 + 交裁决**，而不是修复。

**How to apply**:
1. 任何 CLI 退出码/返回值相关需求，先确认是否已获准改 `ai_collab/cli/__main__.py`；未获准时按「只报告、不修改」处理，并写进结果文件的「风险」段。
2. 新增 CLI 子命令时，验收需同时覆盖三层：顶层 parser 是否暴露该子命令、子命令参数转发路径是否完整（如 `days` 透传到转发函数）、以及内部 handler 的返回值语义；只测 handler 会漏掉前两层。
3. 引用测试基线时用最新口径：**2890 passed / 6 skipped / 0 failed（2026-10-23）**，旧的 2686/2350/2660 数字已过期。
