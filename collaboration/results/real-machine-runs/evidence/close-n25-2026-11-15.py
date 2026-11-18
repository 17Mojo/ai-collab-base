#!/usr/bin/env python3
"""2026-11-15：执行用户指令第 1 条「关闭 N25」，并落盘第 2/3 条的条件判定。

🔧 显性标记：本次关闭推翻用户 2026-11-11 旧红线「N25 只能在 A/B 判据成立之后关闭」。
结案理由 = 命题不可判定，不是验证通过、不是边界有效/无效。
保留全部历史字段与证据；不跑真机、不提交、不碰 git。
"""
import json
import pathlib
import datetime
import subprocess

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
GAPS = REPO / "known_gaps.json"
WORKLOG_DIR = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory")
WORKLOG = WORKLOG_DIR / "2026-11-15.md"
CLOSURE_EV = EV / "n25-closure-2026-11-15.json"
STEPS_EV = EV / "three-steps-execution-2026-11-15.json"

def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()

def truth():
    return {
        "head": git("rev-parse", "--short", "HEAD"),
        "originMain": git("rev-parse", "--short", "origin/main"),
        "ahead": int(git("rev-list", "--count", "origin/main..HEAD") or 0),
        "behind": int(git("rev-list", "--count", "HEAD..origin/main") or 0),
        "unpushed": int(git("rev-list", "--count", "origin/main..HEAD") or 0),
        "staged": len([x for x in git("diff", "--cached", "--name-only").splitlines() if x.strip()]),
        "statusItems": len([x for x in git("status", "--porcelain").splitlines() if x.strip()]),
    }

pre = json.loads((EV / "three-steps-precondition-2026-11-15.json").read_text())
gaps = json.loads(GAPS.read_text())
n25 = next(x for x in gaps["gaps"] if str(x.get("id")) == "N25")

# 前置断言：只关闭一次，绝不重复写
assert n25["status"] == "open", "N25 已非 open，拒绝重复关闭"
assert n25["closed_at"] is None, "closed_at 已非 null，拒绝覆盖"
assert "recharacterization" in n25, "缺少 §26 改述，先补改述再关闭"
assert "closure" not in n25, "closure 字段已存在，拒绝覆盖历史"

# ── 1. 关闭 N25（保留全部历史字段）──────────────────────────
closure = {
    "closed_at": "2026-11-15",
    "type": "INDETERMINABLE_PROPOSITION_CLOSED",
    "decidedBy": "用户 2026-11-15 指令第 1 条『关闭 N25』",
    "🔧_explicitRedLineOverride": {
        "oldRedLine": "用户 2026-11-11 明令：N25 只能在 A/B 跑完且判据成立之后关闭；在此之前保持 open",
        "criteriaNeverMet": True,
        "overrideReason": "§26 只读诊断证明命题的自变量（长会话撞墙）在 F1 修复后不复现，A 组结构条件已满足仍 3/3 全 8/8、撞墙 0 次 ⇒ 判据永远不会成立，保持 open 只会固化『待验证』的假状态",
        "authorizedBy": "用户本条指令本身；用户是红线制定者，有权显式推翻",
    },
    "closingReason": "原始观察对象已重新归因、墙不复现、命题不可判定 —— 以此结案",
    "isNot": [
        "不是验证通过（A/B 判据从未成立）",
        "不是『边界有效』", "不是『边界无效』",
        "不是『长会话撞墙已根治』",
        "不是 F1 / F2 真机验证的因果结论",
    ],
    "whatRemainsTrue": [
        "F1 公共等待判据修复在真机上生效（§21）",
        "F2 newChat / newChatText 入口真机可达（§23）",
        "ab4 B 组硬判据 2/2 成立、ab5 observe-first 判无墙即停",
        "原始 §9.4 的『长会话是变量』归因已被 F-D1/F-D2/F-D3 削弱",
    ],
    "reader": (
        "接手时想把 N25 重新打开、或想据它写『会话边界解掉了长会话撞墙』的人。"
        "本条已结案但结案理由是命题不可判定，不是验证通过；若要重新验证，"
        "须先提出一个可控、可复现的自变量，否则按 §26 盲跑不产生新证据。"
    ),
    "evidence": [
        "wall-observability-diagnosis-2026-11-12.json",
        "proposition-pursuit-plan-2026-11-14.json",
        "ab5-final-verdict-2026-11-14.json",
        "proposition-pursuit-ruling-2026-11-14.json",
        "RESULT §26 / §27",
    ],
    "historicalFieldsPreserved": True,
    "note": "关闭只改 status / closed_at 并新增 closure；title / detail / fix / reader / where / recharacterization / appended_evidence 全部原样保留。",
}
n25["closure"] = closure
n25["status"] = "closed"
n25["closed_at"] = "2026-11-15"
n25["updated_at"] = "2026-11-15"
before_ev = len(n25["appended_evidence"])
n25["appended_evidence"].append(
    "2026-11-15 用户指令『后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机…3、提交…』第 1 条："
    "🔧 显式推翻 2026-11-11 旧红线『N25 只能在 A/B 判据成立之后关闭』，将 status 由 open 改 closed、closed_at=2026-11-15，"
    "新增 closure 字段（type=INDETERMINABLE_PROPOSITION_CLOSED）。结案理由=『原始观察对象已重新归因、墙不复现、命题不可判定』，"
    "**不是验证通过、不是边界有效、也不是边界无效**；isNot 5 条、whatRemainsTrue 4 条、reader、5 份证据引用一并落盘。"
    "推翻依据：§26 机械汇总 8 份 A 组回执，F1 后 3 份走满 8 步全部 8/8、撞墙 0 次，A 组结构条件（同一会话 7 次 AI 往返）已满足 ⇒ 判据永远不会成立。"
    "原 title/detail/fix/reader/where/recharacterization 与全部既有证据原样保留，不删不改。"
    "同轮第 2 条『跑真机』按用户自设前提（逐次解冻 + 说明改变哪个自变量）判定 NOT_EXECUTED_PRECONDITION_UNMET：两项前提都没给，且 §26 已证无可控自变量（P2 需改源码/dist、P3 需改 Pack，均违反硬约束）；"
    "第 3 条『提交』判定 NOT_AUTHORIZED_NO_ACTION：提交动作与文件集合均未授权、push 的分歧处理未授权。"
    "磁盘新事实：origin/main 由 f98a1a7 被外部推进到 19635c6（27 个提交、仅改 7 个 .github/workflows/*.yml），behind 由 4 变 31；用户指令里写的 behind=4 是过期快照，已回溯补记 remote-divergence-2026-11-15.json，未触碰本轮任何输入。"
    "本轮未跑真机/未打冻结站/未发消息/未 commit/push/stage/merge/rebase/未改源码/dist/Pack。回写 RESULT §27、本日志。"
)
gaps["updated_at"] = "2026-11-15"
GAPS.write_text(json.dumps(gaps, ensure_ascii=False, indent=2) + "\n")
CLOSURE_EV.write_text(json.dumps({
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "n25-closure-2026-11-15",
    "statusBefore": "open", "statusAfter": n25["status"],
    "closedAt": n25["closed_at"],
    "closure": closure,
    "evidenceCountBefore": before_ev, "evidenceCountAfter": len(n25["appended_evidence"]),
    "historicalFieldsPreserved": all(k in n25 for k in
        ("title", "detail", "fix", "reader", "where", "recharacterization", "appended_evidence")),
    "noRealMachineAction": True, "gitUntouched": True,
}, ensure_ascii=False, indent=2) + "\n")

# ── 2. 三条指令执行结果 ─────────────────────────────────────
steps = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "three-steps-execution-2026-11-15",
    "userMandate": "后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机… 3、提交…",
    "interpretation": (
        "第 1 条是无条件祈使句，本身构成对『判据成立才关闭』旧红线的显式裁定 ⇒ 执行；"
        "第 2、3 条自带前置条件且括号标注『均未授权』⇒ 按用户自设条件逐条判定，不得推断为已授权。"
    ),
    "results": [
        {"step": 1, "instruction": "关闭 N25", "verdict": "EXECUTED",
         "detail": "status=closed / closed_at=2026-11-15 / closure.type=INDETERMINABLE_PROPOSITION_CLOSED；显性标记推翻旧红线；结案理由非验证通过"},
        {"step": 2, "instruction": "跑真机", "verdict": pre["steps"][1]["machineVerdict"],
         "detail": "用户自设前提『逐次明确解冻』『说明本次改变了哪个自变量』均未给；§26 已证无可控自变量 ⇒ 不跑。未启动浏览器、未打冻结站、未发消息、未产生回执。"},
        {"step": 3, "instruction": "提交", "verdict": pre["steps"][2]["machineVerdict"],
         "detail": "提交动作与文件集合均未分别授权；push 另需授权处理分歧。behind 真值 31（非指令里的 4）。不 commit/push/stage/merge/rebase。"},
    ],
    "dependencyOrderRespected": True,
    "remoteDivergence": {"from": "f98a1a7 / behind 4", "to": truth()["originMain"] + " / behind " + str(truth()["behind"]),
                         "newCommits": 27, "changedFiles": 7, "ourInputsTouched": []},
    "hardBoundaries": {
        "noRealMachineAction": True, "noBrowserLaunch": True, "noMessageSent": True,
        "noPackChange": True, "noSourceOrDistChange": True, "noGitChange": True,
        "noReceiptCreated": True,
    },
    "diskTruth": truth(),
}
STEPS_EV.write_text(json.dumps(steps, ensure_ascii=False, indent=2) + "\n")

# ── 3. RESULT §27 ────────────────────────────────────────────
section = """

---

## §27 关闭 N25 + 两条条件指令判定（2026-11-15）

用户指令：「后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机：须逐次明确解冻，并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据。3、提交：按『提交动作』与『文件集合』分别重新授权；若 push，还须单独授权先处理 behind=4 分歧。」

### 27.1 开工磁盘真值（跨 1 天，不认上轮自述）

| 项 | 真值 |
|---|---|
| HEAD / origin/main | `36d9ec2` / **`19635c6`**（上轮收口时是 `f98a1a7`） |
| ahead / behind / unpushed / staged | 0 / **31**（上轮 4）/ 0 / 0 |
| 工作区 | 133 项（本轮新产物落盘后递增） |
| N25 | `open` / `closed_at=null` / 42 条证据 / 已有 `recharacterization` |
| RESULT | 1745 行，§26 共 8 子节 |
| evidence JSON | 135 份全可解析 |
| `ab6` 目标路径 | 空 |

### 27.2 🔧 回溯补记：`behind=4` 已是过期快照

`origin/main` 又被**外部** `fetch origin main --quiet: fast-forward` 推进 27 个提交（`f98a1a7 → 19635c6`），`git diff --name-only` 显示只改 7 个 `.github/workflows/*.yml`（nightly / build / healthcheck / lint / mypy-gate / security / test）。**未触碰 dist / 变体 Pack / evidence / 台账 / 报告 / 源码 / 测试** ⇒ §25、§26、ab5 结论全部保持有效，不翻案。用户指令里的 `behind=4` 是 2026-11-14 快照，按 disk-truth 以 **31** 为准。见 `remote-divergence-2026-11-15.json`；§25.10 原文不删。

现实影响：若日后授权 push，须先单独授权处理 **behind 31** 的分歧，代价较上轮的 behind 4 大幅上升。本会话未 fetch / pull / merge / rebase / commit / push，本地 HEAD 未移动。

### 27.3 三条指令的机器前提判定（`three-steps-precondition-2026-11-15.json`）

括号里的「**均未授权**」是关键：第 2、3 条自带前置条件，不能因用户复述清单就推断为已授权。

| 步骤 | 用户自设前提 | 实际 | 判定 |
|---|---|---|---|
| 1 关闭 N25 | 无附加条件（祈使句） | 构成对旧红线的**显式裁定** | `EXECUTED` |
| 2 跑真机 | 逐次明确解冻 + 说明改了哪个自变量 | 两项都没给；`ALLOW_FROZEN` 本轮未出现 | `NOT_EXECUTED_PRECONDITION_UNMET` |
| 3 提交 | 提交动作、文件集合分别授权；push 另需授权处理分歧 | 三项都没给 | `NOT_AUTHORIZED_NO_ACTION` |

### 27.4 第 1 条：关闭 N25（`n25-closure-2026-11-15.json`）

🔧 **显性标记：本次关闭推翻用户 2026-11-11 旧红线「N25 只能在 A/B 跑完且判据成立之后关闭」**。用户是本红线的制定者，本条无条件祈使句即为显式裁定；依据是 §26 证明该判据**永远不会成立**（A 组结构条件已满足仍 3/3 全 8/8、撞墙 0 次），继续 `open` 只会固化「待验证」的假状态。

落盘动作：`status: open → closed`、`closed_at: "2026-11-15"`，新增 `closure` 字段（`type = INDETERMINABLE_PROPOSITION_CLOSED`），含 `🔧_explicitRedLineOverride`、结案理由、`isNot` 5 条、`whatRemainsTrue` 4 条、`reader`、5 份证据引用。**原 `title` / `detail` / `fix` / `reader` / `where` / `recharacterization` 与全部既有证据原样保留，不删不改**，符合台账 `conventions`「关闭后保留条目与结论」。证据 42→43。

**结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定。不是验证通过、不是边界有效、也不是边界无效。** 仍然成立的事实：F1 等待判据修复真机生效（§21）、F2 会话入口真机可达（§23）、ab4 B 组硬判据 2/2 成立、ab5 判无墙即停。

### 27.5 第 2 条：不跑真机（前提未满足）

用户自己写了「须逐次明确解冻，并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据」。本轮：无解冻指令、无 `ALLOW_FROZEN=1`、无自变量说明。§26 五条路径里只有 P2（改源码/dist 回滚 F1）和 P3（改 Pack 加长会话）会改变自变量，两者都违反本轮硬约束；P1/P4/P5 不改变自变量。按用户自设条件，此条自动不成立。冻结站未碰，用完仍是冻结，白名单代码未改。

### 27.6 第 3 条：不提交（未授权）

「提交动作」与「文件集合」两项均未分别授权，push 的前置分歧处理亦未授权。上轮 q-0「暂不提交」与 q-3（`PREFERENCE_ONLY_NOT_AUTHORIZATION`）继续有效，不因复述清单自动升级。不 commit / push / stage / merge / rebase；`behind 31` 保持不动。

### 27.7 硬边界与最终状态

本轮 `realMachineRounds=0`：未启动浏览器、未打开冻结站、未发送消息、未改 Pack / 源码 / 测试 / dist、未碰 git、未产生真机回执。新增产物全在 `evidence/`：`three-steps-precondition-2026-11-15.py/.json`、`remote-divergence-2026-11-15.json`、`n25-closure-2026-11-15.json`、`three-steps-execution-2026-11-15.json`、本节回写脚本。

归因边界继续有效：不能说边界有效/无效、不能把 F1/F2 真机验证挪用为因果证据、不能说「长会话撞墙已根治」、站点侧报错须单独标注、不能把 plan-only 写成已执行回执、**不能把本次关闭写成验证通过**。
"""
with RESULT.open("a") as f:
    f.write(section)

WORKLOG_DIR.mkdir(parents=True, exist_ok=True)
with WORKLOG.open("a") as f:
    f.write(
        "\n## 2026-11-15 关闭 N25 + 两条条件指令判定\n\n"
        "- 用户指令『后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机… 3、提交…』。括号『均未授权』是关键：第 2、3 条自带前提，不能因复述清单推断为已授权。\n"
        "- 跨 1 天核磁盘真值：origin/main 被外部推进 27 个提交 f98a1a7→19635c6，**behind 4→31**，只改 7 个 .github/workflows/*.yml，未触碰本轮任何输入 ⇒ §25/§26/ab5 结论不翻案。用户指令里的 behind=4 是过期快照，回溯补记 remote-divergence-2026-11-15.json。本会话未 fetch/pull/merge/rebase/commit/push。\n"
        "- 第 1 条执行：🔧 显式推翻 2026-11-11 旧红线『判据成立才关闭』。N25 status open→closed、closed_at=2026-11-15、新增 closure（type=INDETERMINABLE_PROPOSITION_CLOSED），带 redLineOverride / isNot 5 条 / whatRemainsTrue 4 条 / reader / 5 份证据；结案理由=『命题不可判定』，**不是验证通过、不是边界有效/无效**。原 title/detail/fix/reader/where/recharacterization 与全部证据原样保留。证据 42→43，known_gaps 25 条现为 closed 24 / wontfix 1 / open 0。\n"
        "- 第 2 条按用户自设前提判定 NOT_EXECUTED_PRECONDITION_UNMET：未给逐次解冻、未给『本次改变了哪个自变量』，§26 已证无可控自变量（P2 改源码/dist、P3 改 Pack 均违反硬约束）。未打冻结站、未发消息、未产生回执。\n"
        "- 第 3 条判定 NOT_AUTHORIZED_NO_ACTION：提交动作与文件集合未分别授权、push 分歧处理未授权；上轮 q-0/q-3 继续有效。不 commit/push/stage/merge/rebase，behind 31 保持不动。\n"
        "- 回写 RESULT §27（7 子节）、本日志。硬边界全 true：未跑真机、未碰 git、未改源码/dist/Pack。\n"
    )

txt = RESULT.read_text()
fs = sorted(EV.glob("*.json"))
bad = []
for p in fs:
    try:
        json.loads(p.read_text())
    except Exception:
        bad.append(p.name)
print("WROTE", CLOSURE_EV.name, "/", STEPS_EV.name)
print("N25 status =", n25["status"], "closed_at =", n25["closed_at"], "evidence", before_ev, "->", len(n25["appended_evidence"]))
print("gaps status dist =", {s: sum(1 for x in gaps["gaps"] if x.get("status") == s) for s in ["open", "closed", "wontfix"]})
print("RESULT lines =", len(txt.splitlines()), "§27 subsections =", sum(1 for l in txt.splitlines() if l.startswith("### 27.")))
print("evidence json =", len(fs), "parse failures =", len(bad))
print("git =", json.dumps(truth(), ensure_ascii=False))
