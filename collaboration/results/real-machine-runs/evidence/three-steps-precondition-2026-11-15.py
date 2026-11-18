#!/usr/bin/env python3
"""2026-11-15：三条「后续步骤（均未授权，按依赖顺序）」的只读授权前提判定。

不关闭 N25、不跑真机、不提交、不碰 git。只把每条的机器可判定前提落盘。
"""
import json
import pathlib
import datetime
import subprocess

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
GAPS = REPO / "known_gaps.json"
OUT = EV / "three-steps-precondition-2026-11-15.json"
DIVERGENCE = EV / "remote-divergence-2026-11-15.json"

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

gaps = json.loads(GAPS.read_text())
n25 = next(x for x in gaps["gaps"] if str(x.get("id")) == "N25")
plan = json.loads((EV / "proposition-pursuit-plan-2026-11-14.json").read_text())
ab5 = json.loads((EV / "ab5-final-verdict-2026-11-14.json").read_text())

# ── 远端分歧变化（回溯补记 §25.10）────────────────────────────
commits = [x for x in git("log", "--oneline", "f98a1a7..origin/main").splitlines() if x.strip()]
files = [x for x in git("diff", "--name-only", "f98a1a7..origin/main").splitlines() if x.strip()]
touched = [f for f in files if any(k in f for k in (
    "chrome-extension/dist", "ab-pack", "real-machine-runs/evidence",
    "known_gaps", "RESULT", "chrome-extension/src", "chrome-extension/tests"))]
div = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "remote-divergence-readonly-2026-11-15",
    "previousSnapshot": {"originMain": "f98a1a7", "behind": 4, "at": "2026-11-14"},
    "currentSnapshot": truth(),
    "newCommitsCount": len(commits),
    "newCommits": commits,
    "changedFiles": files,
    "ourInputsTouched": touched,
    "source": "git reflog origin/main 多次 fetch origin main --quiet: fast-forward（外部推进，非本会话操作）",
    "impactOnAb5AndS26": "none：27 个新提交只改 7 个 .github/workflows/*.yml，未触碰 dist / 变体 Pack / evidence / 台账 / 报告 / 源码 / 测试",
    "correction": "§25.10 与上一轮裁定里写的 behind=4 是 2026-11-14 快照；2026-11-15 真值是 behind=31。原文不删，本条为回溯补记。",
    "implicationForPush": "若日后授权 push，须先单独授权处理 behind=31 的分歧（merge / rebase / pull），代价较 behind=4 大幅上升",
    "localAction": "本会话未 fetch / pull / merge / rebase / commit / push；本地 HEAD 未移动",
    "gitUntouched": True,
}
DIVERGENCE.write_text(json.dumps(div, ensure_ascii=False, indent=2) + "\n")

# ── 三条指令的机器前提判定 ───────────────────────────────────
step1 = {
    "instruction": "1、关闭 N25",
    "userLabeledUnauthorized": True,
    "currentN25": {"status": n25["status"], "closed_at": n25["closed_at"],
                   "evidenceCount": len(n25["appended_evidence"]),
                   "recharacterized": "recharacterization" in n25},
    "conflict": {
        "oldRedLine": "用户 2026-11-11 明令：N25 只能在 A/B 跑完且判据成立之后关闭；在此之前保持 open",
        "criteriaNeverMet": True,
        "evidence": "ab3/ab4/ab5 三份裁定均 propositionSupported=false；ab5 code=ABORT_NO_WALL",
        "newBasis": "§26 只读诊断：自变量结构条件已满足但墙不出现，命题不可判定",
    },
    "machineVerdict": "REQUIRES_EXPLICIT_USER_RULING",
    "reason": "用户本条自带「均未授权」标注，且关闭会推翻自己设的旧红线并改写交付口径；不得凭清单本身推断已授权",
    "recommendation": {
        "action": "按『命题不可判定而结案』关闭，status=closed、写 closed_at",
        "mandatoryWording": [
            "结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定",
            "不得写『验证通过』『边界有效』『边界无效』『长会话撞墙已根治』",
            "显性标记：本次关闭是用户 2026-11-15 显式推翻 2026-11-11『判据成立才关闭』旧红线",
            "保留 title / detail / fix / reader / where / recharacterization 与全部 42 条证据，不删不改",
        ],
    },
}

step2 = {
    "instruction": "2、跑真机：须逐次明确解冻，并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据",
    "userSetPreconditions": ["逐次明确解冻 deepseek / longcat", "说明本次改变了哪个自变量"],
    "actual": {
        "explicitUnfreezeGiven": False,
        "independentVariableSpecified": False,
        "allowFrozenFlagInThisTurn": False,
        "platformPolicyUnfrozenBy": None,
    },
    "diskEvidence": {
        "ab5": ab5["code"],
        "planCode": plan["formal"]["currentState"]["code"],
        "postF1FullARounds": len(plan["machineEvidence"]["postF1FullARounds"]),
        "postF1WallCount": 0,
        "candidatePathsChangingIndependentVariable": [
            p["id"] + " " + p["name"] for p in plan["candidatePaths"]
            if p["needsPackChange"] or p["needsSourceOrDistChange"]
        ],
        "note": "P2 需改源码/dist、P3 需改 Pack，均违反本轮硬约束；P1/P4/P5 不改变自变量",
    },
    "machineVerdict": "NOT_EXECUTED_PRECONDITION_UNMET",
    "reason": "用户自设的两个前提都没给；§26 已证不存在可控自变量，按用户自己的条件此条自动不成立",
    "actionsTaken": {"browserLaunched": False, "frozenSiteOpened": False,
                     "messageSent": False, "receiptCreated": False},
}

step3 = {
    "instruction": "3、提交：按「提交动作」与「文件集合」分别重新授权；若 push，还须单独授权先处理 behind=4 分歧",
    "userSetPreconditions": ["提交动作单独授权", "文件集合单独授权",
                            "若 push：单独授权先处理分歧"],
    "actual": {
        "commitAuthorized": False, "fileSetAuthorized": False,
        "pushAuthorized": False, "divergenceHandlingAuthorized": False,
        "behindAtPreviousTurn": 4, "behindNow": truth()["behind"],
    },
    "staleFact": "用户指令里写 behind=4，磁盘真值已是 behind=31；按 disk-truth 以 31 为准并回溯补记",
    "machineVerdict": "NOT_AUTHORIZED_NO_ACTION",
    "reason": "两项授权都没给，且 push 的前置分歧处理也没授权；不 commit / 不 push / 不 stage / 不 merge / 不 rebase",
    "previousRulingStillEffective": {
        "q0": "暂不提交", "q3": "仅本轮产物（PREFERENCE_ONLY_NOT_AUTHORIZATION）",
        "file": "commit-authorization-ruling-2026-11-14.json",
    },
}

doc = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "localTime": "2026-11-15 06:02 GMT+8",
    "mode": "three-steps-precondition-readonly",
    "userMandate": "后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机… 3、提交…",
    "interpretation": "用户明确标注『均未授权』，因此本文件只做机器前提判定，不把清单本身当作授权",
    "steps": [step1, step2, step3],
    "dependencyOrderRespected": True,
    "executionSummary": {
        "step1": "待用户显式裁定（推荐按命题不可判定结案，显性标记推翻旧红线）",
        "step2": "前提未满足 → 不跑",
        "step3": "未授权 → 不提交",
    },
    "remoteDivergence": {"previous": "f98a1a7 / behind 4", "current": truth()["originMain"] + " / behind " + str(truth()["behind"]),
                         "evidence": DIVERGENCE.name},
    "hardBoundaries": {
        "noRealMachineAction": True, "noGitChange": True,
        "noPackChange": True, "noSourceOrDistChange": True,
        "n25StatusChanged": False,
    },
    "diskTruth": truth(),
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")

print("WROTE", OUT.name, "/", DIVERGENCE.name)
print("step1 =", step1["machineVerdict"])
print("step2 =", step2["machineVerdict"])
print("step3 =", step3["machineVerdict"])
print("behind:", 4, "->", truth()["behind"], "| new commits:", len(commits),
      "| files:", len(files), "| ourInputsTouched:", touched)
print("git =", json.dumps(truth(), ensure_ascii=False))
