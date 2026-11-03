---
name: Python 侧与 Chrome 侧的协议取值域互不相交（2026-11-03 审计根因）
description: 校验器/Schema 白名单只认 local/analysis/generation/validation/fusion/tracking，Chrome 执行器只认 local/ai，交集只有 local；external-user-smoke.json 唯一 ERROR 是 Invalid step type: ai；统一路线属产品取舍待用户拍板
type: project
from: Agent
---

2026-11-03 架构审计的根因结论（此前"validator 收紧、示例包没回灌"的判断已被推翻）：**三套协议从来没对齐过**，不是某一方最近变严。

| 判定方 | 认可的 step type |
|---|---|
| Python Enum / 校验器白名单 | local, analysis, generation, validation, fusion, tracking（**没有 ai**） |
| Chrome 执行器 | local, ai（**没有 analysis 等**） |
| 交集 | **只有 local** |

- `packs/examples/external-user-smoke.json`（专为外部用户准备、被测试守护的那份）自校验的唯一 ERROR 是 `Invalid step type: ai`——被拒的恰好是 Chrome 唯一能用的类型。
- 真机端到端证实两者行为不同：`analysis` 步骤执行器直接抛 `Unknown step type`；`ai` 步骤能走过 switch 到通讯阶段（无接收端时报 `Could not establish connection`，属预期）。
- 统一路线有三条互斥选项（Chrome 补齐 4 种分支 / Schema 收编 `ai` / 显式分成 Python 档与 Chrome 档），**属产品取舍，等用户拍板**，Agent 不代选。

**Why:** 这是外部用户路径上"照做必失败"的根因之一（另一处是扩展加载目录指引错误）；修复成本与兼容性影响面大，且直接决定后续所有 Pack 材料的写法，不能由 Agent 单方决定。

**How to apply:**
- 谈 Pack/协议相关问题时先问清"这次以哪一侧为准"，不要默认 Python 侧是全集。
- 需要真证时用"执行器遇到某类型会怎样"做端到端实测，不要只看静态枚举。
- 该项在 `docs/ARCHAEOLOGY_AUDIT_2026-11-03.md` 有完整记录（新增 §9）。
