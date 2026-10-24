---
name: 体检工具链加固工单背景（密钥扫描器误报、check_git 假绿）
description: 2026-10-24 派单 TASK-P1-HEALTHCHECK-TOOL-HARDEN-001 的背景问题——密钥扫描器误报 237 条需降到 0、check_git() 缺 origin/main 存在性判断造成体检假绿、check_health_rules() 对长期经验条数统计不准
type: project
from: Agent
---

2026-10-24，CodeArts 收到派单工单 **TASK-P1-HEALTHCHECK-TOOL-HARDEN-001**，目标是把项目体检工具链加固，消除三类已知问题：

1. **密钥扫描器噪声**：既有密钥/PII 扫描器在真实工作区产生 **237 条误报**，需要通过目录排除 + 两段式密码规则 + 值级占位符判定 + 白名单文件把它压到 **0 条**。
2. **体检假绿（false green）**：`check_git()` 只看本地状态、不判断 **origin/main 是否存在**，导致「体检通过」并不代表真的能对比远端主线——这是「假绿」的典型来源。
3. **长期经验条数统计不准**：`check_health_rules()` 对长期经验条数的统计口径不精确，需要精确统计。

**Why:** 体检工具的输出要作为协作控制面的门禁依据，误报会让门禁失去可执行性，假绿与统计不准会让「体检通过」被误当作真实健康度——这比直接失败更危险。

**How to apply:**
- 后续任何体检/门禁类改动，都要区分「真的健康」与「工具认为健康」；涉及 git 状态时记得显式判断远端分支是否存在。
- 涉及密钥扫描时，判定要以「0 误报」为口径，而不是把噪声当信号放宽规则。
- 修复结果以 `collaboration/results/RESULT-P1-HEALTHCHECK-TOOL-HARDEN-2026-10-24.md`（按 PROTOCOL §7.3 四段契约）与工单终态为准；本条仅记录背景问题，不预设实现细节。
