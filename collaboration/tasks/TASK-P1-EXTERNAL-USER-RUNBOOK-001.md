---
task_id: TASK-P1-EXTERNAL-USER-RUNBOOK-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-27T09:40:00+08:00
acceptance_commands:
  - "python3 -m pytest tests/unit/test_external_user_runbook.py -q"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 scripts/scan_secrets_pii.py --workspace ."
  - "python3 scripts/verify_task_file_contracts.py"
  - "bash scripts/verify_agent_config_sync.sh"
result_file: collaboration/results/RESULT-P1-EXTERNAL-USER-RUNBOOK-2026-10-27.md
---

# TASK-P1-EXTERNAL-USER-RUNBOOK-001：把 W-D1 排演材料变成一场可以照着跑完的真人外部用户会话

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：用户 2026-10-27 的指示——
> 「W-D2 真人外部用户 —— 排演只证明材料与代码自洽，证明不了真人会用；
> 路线 A/B 门禁仍开着。」⇒ **把模拟资料转化成操作指南**。

## 一、要解决什么

W-D1（2026-10-26 排演）攒下了一堆材料：一页说明书、记录格式、6 个已修断点、
L2 观测器。但**排演者能读源码**，所以排演只证明了「材料与代码自洽」，
**证明不了「一个真人读得懂、做得下去」**——而这正是路线 A/B 决策门禁缺的最后一环。

材料侧因此欠三样东西：

| 欠什么 | 后果 |
|---|---|
| **谁在什么时候做什么**（主持人视角的流程） | 材料是「散件」，不是「一场会话」 |
| **现场看什么** | 主持人凭印象记，抓不住「症状级」的失败 |
| **这一场和 L2 的关系** | W-D2 与 L2 第 1 轮**都要人**，分两场做要约两次人 |

## 二、修法（交付什么）

1. **新增 `docs/EXTERNAL_USER_SESSION_RUNBOOK.md`**（主持人用）：
   - §0 是什么 / 不是什么（为什么排演代替不了这一场）
   - §1 **同一场同时干两件事**：W-D2 的人证 + L2 第 1 轮的机证
   - §2 角色分工与铁律（主持人一开口帮倒忙，这场就作废）
   - §3 前置准备（选人 / 选平台 / 构建 / **L1 探针自检** / 打包交付物，**明确「不给什么」**）
   - §4 现场流程（开场白逐字稿 + 5 步旁观表 + 并行观测器 + 收尾三问）
   - §5 **静默观察清单 D0–D7**：把 6 个已修断点翻译成「外部用户身上会长什么样」，
     主持人**盯着看但不告诉试用者**
   - §6 记录怎么写 + 隐私红线
   - §7 判定口径与收口（登记命令、门禁怎么变、**不许提前关**）
   - §8 七条红线 / §9 一页纸速查 / §10 相关文件
2. **说明书适配两种交付形态**：`docs/EXTERNAL_USER_ONBOARDING.md` 原先假设试用者
   会自己 `npm run build`——真人外部用户大概率不会。现在**预构建交付包**是默认，
   自己编译是备选。
3. **手册里的命令与工具对账**：L1 自检命令补 `--profile-dir` / `--out`，
   L2 登记命令改用**已存在的 run**（`record` 要求 run 先存在，另起一份会让 `verify`
   报「缺 L1 记录」），并写清 `verify` 退出码 2 在「一场只覆盖一个平台」时是正常的。
4. **缺口台账与路线门禁段落同步**：`docs/REAL_MACHINE_REGRESSION.md` §4 / §6.2 #13 / §7
   指向新手册，口径统一为「**材料已备齐，缺的只是人**」。
5. **守护**：`tests/unit/test_external_user_runbook.py`（5 条）——
   手册引用的交付物还在不在、相对链接通不通、手册教的**参数名**工具认不认、
   七条红线有没有被删。**每条都做过变异验证**（见结果文件）。

## 三、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 四、回滚

本工单只动文档与测试：
`docs/EXTERNAL_USER_SESSION_RUNBOOK.md`（新增）、
`docs/EXTERNAL_USER_ONBOARDING.md`、`docs/REAL_MACHINE_REGRESSION.md`、
`collaboration/results/external-user/README.md`、
`tests/unit/test_external_user_runbook.py`（新增）、
`memory/`（CodeArts 记忆源同步生成的镜像）。
回滚 = 回退这些文件；**不涉及任何运行时代码**，无回滚副作用。
