#!/usr/bin/env python3
"""回写 2026-11-14 追究命题只读诊断：RESULT §26 / N25 / 工作日志。

只追加文本与台账，不改源码/测试/dist/Pack，不跑真机，不碰 git。
路径裁定与授权维度仍标 PENDING，等用户明确后再补 §26.x。
"""
import json
import pathlib

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
GAPS = REPO / "known_gaps.json"
WORKLOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-14.md")

plan = json.loads((EV / "proposition-pursuit-plan-2026-11-14.json").read_text())
full = plan["machineEvidence"]["postF1FullARounds"]
rows = "\n".join(
    "| `{}` | {}/{} | {} | {} ms | 0 |".format(
        x["receipt"], x["stepsTotal"], x["stepSuccess"], x["step8Success"], x["step8DurationMs"])
    for x in full
)
path_rows = "\n".join(
    "| {} | {} | {} | {} | {} |".format(
        p["id"], p["name"], p["realMachineRounds"],
        "是" if p["needsUnfreeze"] else "否", p["recommendation"])
    for p in plan["candidatePaths"]
)

section = """

---

## §26 追究命题：可判定性的只读诊断（2026-11-14，路径待裁定）

用户明令「处理后续步骤：1、追究命题；2、重新授权」。本节只完成第 1 项的**只读诊断**；第 2 项授权宾语未指明，按维度分别确认，不擅自执行。开工前核磁盘真值：`HEAD=36d9ec2` / `origin/main=f98a1a7`，behind 4 / ahead 0 / unpushed 0 / staged 0，127 项全在工作区；N25 `open` 40 证据；ab5 仍 `ABORT_NO_WALL`；132 份 evidence JSON 全可解析；`ab6` 目标路径为空。

### 26.1 命题与可判定条件的形式化

| 项 | 定义 |
|---|---|
| 命题 | `fresh_session` 会话边界能解掉 deepseek / longcat 的 `step_8` 长会话撞墙 |
| 自变量 | 单会话串行累积到 `step_8` 时的「长会话撞墙」状态 |
| 因变量 | `step_8_output` 是否失败（`Response timeout` / 站点报错） |
| 可判定 iff | 存在至少一次 A 组能稳定复现「前 7 步全成功、`step_8_output` 失败、且失败**不是**站点侧随机报错、**不是**等待判据 bug」；且同站相邻时间窗的 B 组在边界真执行后通过 |

### 26.2 机械证据：8 份 A 组回执，结构条件已满足但墙不出现

变体 Pack 的唯一差异经复核确认：B 组只在 `workflow.steps[7]` 多一个 `fresh_session: "prefer"`，A 组递归删掉该键，**其余 8 步的 `prompt_template` / `input_fields` / `config` 逐字节一致**。因此 A 组 `no-boundary` 本来就是**同一会话 8 步串行、7 次 AI 往返、无任何会话边界**——这正是 §9.4 原文宣称的自变量条件「会话已累积 7 轮、约 5–6k 字」。

`proposition-pursuit-plan-2026-11-14.py` 机械汇总 8 份 A 组回执，F1 之后走满 8 步的有 3 份：

| 回执 | steps | step_8 成功 | step_8 耗时 | sessionResets |
|---|---|---|---|---|
""" + rows + """

**3 份全部 8/8 completed，撞墙 0 次**。加上 ab5 observe-first 单轮（8/8、11.7s、`sessionResets=0`），这是第 3 份同型结构复现证据。

### 26.3 回溯修正 §24：不是「没复现长会话」，而是「条件满足、因变量不出现」

§24 写「自变量不可控、不复现」。更准确的机械表述是：**长会话的结构条件已经复现**（同一会话 7 次 AI 往返），但 `step_8` 没有失败。原始观察的两种症状已被分别重新归因 —— deepseek 是 F1 已根治的虚拟列表 `countGrew` 假超时，longcat 是站点侧随机报错（外部混杂变量）。因此「墙」不是被漏掉，而是**作为可复现的自变量并不存在**。§24 的 `PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE` 结论不变，但论据由「推论」升级为「多次真机同型观察」。

隔离实验 `L2-longcat-fusion-isolated-2026-11-11.json`（2437 字、空会话、21s、1481 字）只能证明「提示词本身不被平台拒绝」，不能独立证明「长会话是变量」，F-D3 的削弱依然有效。

### 26.4 五条候选路径（`proposition-pursuit-plan-2026-11-14.json`）

| ID | 路径 | 真机轮次 | 需解冻 | 建议 |
|---|---|---|---|---|
""" + path_rows + """

- **P1**：零真机成本、不制造新混杂变量；但「是否关闭 N25」仍须用户裁定，判据未成立前默认保持 `open`，只改述性质为「已跑 A/B，原始观察对象已重新归因、命题不可判定」。
- **P2**：临时回滚 F1 属主动制造已知 bug，违反本轮「不改源码 / 不改 dist」边界；即便重现假超时，只验证 F-D1 归因，**对原命题的因果结论无直接贡献**。
- **P3**：改 Pack 违反 ab5 plan 硬约束「A/B 只差 `fresh_session` 一个变量、Pack hash 不变」；加长会话等于换命题。
- **P4**：与用户 2026-11-14 明令「而不是盲跑 4 轮」直接冲突。
- **P5**：N25 原始观察对象明确是 deepseek / longcat，换活跃 5 站等于换命题，N23 的「重置真的做到了」不能代偿。

### 26.5 「重新授权」的授权维度拆分（宾语未指明）

用户只说「重新授权」，未指明授权什么。按既有红线「提交 / push 按提交与文件集合分别确认、不要默认一次全收」，拆解为 6 个**互相独立**的维度，当前全部为未授权：A1 追究路径（P1–P5）、A2 逐次解冻 deepseek / longcat、A3 `git commit`、A4 提交文件集合、A5 behind=4 分歧处理（merge / rebase / pull）、A6 push 到远端。上一轮 q-0 = 暂不提交、q-1 = 仅本轮 ab5 产物且状态为 `PREFERENCE_ONLY_NOT_AUTHORIZATION`，**不因本轮「重新授权」四个字自动升级为授权**。

### 26.6 状态

方案 `status = plan-only / NOT-EXECUTED`；硬边界全 false（未启动浏览器、未改 Pack、未改源码/dist、未碰 git、未发消息、未产生真机回执）；`n25 = remain open`。本节路径裁定与授权结果待用户明确后补 §26.x。
"""

with RESULT.open("a") as f:
    f.write(section)

gaps = json.loads(GAPS.read_text())
n25 = next(x for x in gaps["gaps"] if str(x.get("id")) == "N25")
before = len(n25["appended_evidence"])
n25["appended_evidence"].append(
    "2026-11-14 追究命题的只读可判定性诊断 evidence/proposition-pursuit-plan-2026-11-14.py/.json（status=plan-only/NOT-EXECUTED、自检 pass）：把命题形式化为『自变量=单会话长会话撞墙状态，因变量=step_8_output 失败』，可判定 iff 需 A 组稳定复现『前 7 步全成功 + step_8 失败 + 非站点报错 + 非等待判据 bug』且同站相邻时间窗 B 组边界真执行后通过。机械汇总 8 份 A 组回执，F1 后走满 8 步的 3 份（ab3/ab4/ab5 no-boundary）全部 8/8 completed、step_8 依次 13333/12310/11736ms、sessionResets=0，撞墙 0 次。关键回溯修正：A 组 no-boundary 本来就是同一会话 8 步串行、7 次 AI 往返、无任何 fresh_session，即 §9.4 宣称的『会话已累积 7 轮』条件——不是没复现长会话，而是结构条件已满足、因变量不出现；§24 的 PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE 结论不变但论据由推论升级为多次真机同型观察。变体 Pack 唯一差异复核：B 组仅 workflow.steps[7] 多 fresh_session=prefer，其余 8 步 prompt_template/input_fields/config 逐字节一致。五条候选路径：P1 按不可判定收口/改述 N25（零真机、推荐，是否关闭仍由用户裁定）、P2 回滚 F1 归因对照（违反不改源码/dist，只验证 F-D1 对原命题无直接贡献）、P3 人工加长会话（改 Pack 破坏单变量约束、等于换命题）、P4 再跑完整 4 轮（与用户明令『不是盲跑 4 轮』冲突）、P5 换活跃 5 站（换命题，N23 不能代偿）。授权维度拆为 A1 路径/A2 逐次解冻/A3 commit/A4 文件集合/A5 behind=4 分歧处理/A6 push 六项，『重新授权』未指明宾语，全部保持未授权，上轮 q-0 暂不提交与 q-1 PREFERENCE_ONLY 不自动升级。硬边界全 false：未启动浏览器/未改 Pack/未改源码 dist/未碰 git/未发消息/未产生真机回执。回写 RESULT §26（6 子节）、本日志；N25 保持 open。"
)
n25["status"] = "open"
n25["closed_at"] = None
n25["updated_at"] = "2026-11-14"
GAPS.write_text(json.dumps(gaps, ensure_ascii=False, indent=2) + "\n")

with WORKLOG.open("a") as f:
    f.write("\n- **追究命题 / 重新授权（第 2 轮后续步骤）**：先核磁盘真值（HEAD 36d9ec2 / origin f98a1a7 / behind 4 / staged 0 / 127 项 / N25 open 40 证据 / ab5 仍 ABORT_NO_WALL / 132 JSON 全可解析）。只读诊断产出 `proposition-pursuit-plan-2026-11-14.py/.json`（plan-only）：机械汇总 8 份 A 组回执，F1 后 3 份走满 8 步全部 8/8、step_8 11.7–13.3s、撞墙 0 次；**回溯修正 §24**：A 组 no-boundary 本来就是同一会话 7 次 AI 往返，自变量条件已满足但墙不出现，不是『没复现长会话』。给出 P1–P5 五条路径与各自红线冲突，推荐 P1 按不可判定收口/改述 N25（零真机，是否关闭仍由用户裁定）。『重新授权』宾语未指明 ⇒ 拆成 A1 路径 / A2 逐次解冻 / A3 commit / A4 文件集合 / A5 behind=4 分歧处理 / A6 push 六维，全部保持未授权，不因四个字自动升级上轮 q-0/q-1。回写 RESULT §26（6 子节）、N25 证据 40→41、本日志。本轮未改源码/未重建 dist/未改 Pack/未跑真机/未碰 git。\n")

print("RESULT §26 appended, lines =", section.count("\n"))
print("N25 evidence", before, "->", len(n25["appended_evidence"]))
print("worklog appended")
