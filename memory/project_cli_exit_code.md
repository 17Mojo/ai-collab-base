---
name: CLI 退出码传递与 R6 禁止修改清单
description: 2026-10-23 曾发现 ai_collab/cli/__main__.py 丢弃 main() 返回值，同日已由 commit a938cd8 正式修复（TASK-P1-CLI-EXITCODE-001）；2026-10-24 进程级复验通过——该缺陷已不存在，「因禁改清单而未修」的记忆不得再当作现状引用
type: project
from: Agent
---

## 事实

- **缺陷已修复（2026-10-23 当日）**：本条目原记录「`ai_collab/cli/__main__.py` 调用
  `main()` 但丢弃返回值，子命令内部的 `return 1` 传不到进程退出码，`browse` 分支同样如此」
  ——**该描述已不再成立**。修复 commit：`a938cd8`
  `fix(cli): 让模块入口的进程退出码如实反映命令结果（TASK-P1-CLI-EXITCODE-001）`。
  修复后 `ai_collab/cli/__main__.py:20` 为 `sys.exit(main())`。
- **2026-10-24 进程级复验**（跑命令看 `$?`，不是读源码推断）：

  | 命令 | 退出码 | 含义 |
  |---|---|---|
  | `python3 -m ai_collab.cli tasks list` | 0 | 正常路径 |
  | `python3 -m ai_collab.cli ack --task-id NOPE-XXX`（缺参数） | 1 | 子命令 `return 1` **已**传到进程退出码 |
  | `python3 -m ai_collab.cli tasks show --task-id NOPE`（argparse 报错） | 2 | argparse 标准退出码 |
  | `python3 -m ai_collab.cli pack browse --category <不存在的分类>` | 2 | `browse` 分支同样**已**透传 |

- **治理纪律仍然有效**：那份工单契约的 **R6「禁止修改清单」把
  `ai_collab/cli/__main__.py` 列入禁改文件**，当时发现缺陷只能**报告、不得擅自修改**
  —— 这个原则本身没错，它只是导致缺陷挂了一个「已知未修」的尾巴，随后由独立工单
  `TASK-P1-CLI-EXITCODE-001` 正式修掉。
  **「因禁改清单而未修」≠「缺陷现在还在」**——引用本条前必须重新验证。
- **CLI 验收的三层检查（仍然有效的经验）**：新增 CLI 子命令时，验收要覆盖三层——
  ① 顶层 parser 是否暴露该子命令；② 子命令参数转发路径是否完整（如 `days` 是否透传到
  转发函数）；③ 内部 handler 的返回值语义是否一路传到进程退出码。
  **只测 handler 会漏掉前两层**；返回值语义必须在**进程级**验证
  （`python3 -m ai_collab.cli <子命令>; echo $?`）——**测函数返回值是假绿**。

## 生命周期教训（本条被修订的真正原因）

记忆条目记录的是**当时的事实**，不是永久状态。这条曾把「2026-10-23 验收时的未修缺陷」
写成了长期结论，后续一旦照着它行动，就会去「修」一个早已修好的东西，或据此误判
CLI 退出码至今是坏的。**缺陷存在 → 被独立工单修复 → 记忆过期**，这条生命周期
本身就是本条最值得记住的部分。

## How to apply

1. 引用本条前先做**进程级复验**（`python3 -m ai_collab.cli <子命令>; echo $?`），
   不要凭条目正文判断缺陷是否还在。
2. 记忆里凡是写「发现但未修」的缺陷，都要标明**是否已有后续修复工单/commit**；
   有的话以工单与 commit 为准，条目本身应被修订而不是继续沿用。
3. **测试基线用最新口径**：**3008 passed / 6 skipped / 0 failed**（2026-10-24，
   Python 3.14.6）。旧的 2890 / 2686 / 2350 等数字均已过期。
