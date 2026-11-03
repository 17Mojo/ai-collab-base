---
name: 历史 Prompt Pack 是空壳（2026-11-03 考古结论）
description: 16 个历史包共 62 个 AI 步骤、0 个有 prompt_template，Chrome 侧 `step.prompt_template || ""` 空串直送 AI；唯一有提示词的是 external-user-smoke.json（2026-10-25 新建，单步冒烟自检）；老包是 5 月遗留骨架，外部用户排演因此没有可跑的业务包
type: project
from: Agent
---

2026-11-03 规划前的考古结论：**仓里的 16 个历史包是空壳**。

```
16 个历史包 = 62 个 AI 步骤，其中 0 个有 prompt_template
```

- Chrome 侧 `_buildPrompt` 里是 `step.prompt_template || ""` ⇒ **空串直接送 AI**。实测确认：即使补上类型让步骤能跑，发出的仍是空提示。
- 唯一有提示词的是 `packs/examples/external-user-smoke.json`（**2026-10-25 新建**），但它只是**单步冒烟自检**，做不了业务演示。2026-11-03 阶段一补了 `xiaohongshu_knowledge_creator.json`（7 条 `prompt_template`），阶段三把 15 个空壳移入 `packs/templates/`，`packs/examples/` 现只剩 2 个能跑的包。
- 其余老包是 **5 月遗留骨架**，不是"内容没写完"这么简单。

**由此推出的两件事：**
1. "只补 `quality_metrics.metrics.*.name` 一个字段，10/16 立即通过"虽然实测成立、成本极低，但那是**让空壳过体检** —— 校验器变绿、产品行为一点没变，跑起来仍是"成功完成、产物为空"。故该条被用户否决，不单做。
2. **真正的阻塞不是校验不过**，而是 `EXTERNAL_USER_SESSION_RUNBOOK.md:29` 待发送的 Pack 写着「具体 Pack：**TBD，会前定**」—— 仓里没有一个能跑的业务包可发。**W-D1 外部用户排演因此无法启动**，而它背后是路线 A/B 决策门禁。

**Why:** 这决定了"提效型小修复"与"真阻塞"的分野：把通过率从 6/16 拉到 16/16 很容易，但对外部用户排演毫无帮助。

**How to apply:**
- 谈 Pack 修复成本时，先说清"能过校验"与"能真跑出产物"是两件事，别拿通过率当成果。
- 规划外部用户排演 / 真机演示前，先确认有**至少一个带 prompt_template 的业务包**；否则排演无法启动。
- 阶段三是做减法：空壳包移到 `packs/templates/`，`packs/examples/` 只留能跑的 —— 目录名要诚实。
