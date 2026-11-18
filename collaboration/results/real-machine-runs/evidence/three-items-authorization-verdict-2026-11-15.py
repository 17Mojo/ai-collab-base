#!/usr/bin/env python3
"""①②③ 授权闭合度机器裁定（2026-11-15）。只读、机械推导，不默认打包。"""
import json
import pathlib
import datetime

EVID = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/collaboration/results/real-machine-runs/evidence")
pre = json.loads((EVID / "three-items-precondition-2026-11-15.json").read_text())
plan = json.loads((EVID / "proposition-pursuit-plan-2026-11-14.json").read_text())
ab5 = json.loads((EVID / "ab5-final-verdict-2026-11-14.json").read_text())
ab4 = json.loads((EVID / "ab4-verdict-2026-11-12.json").read_text())

paths = plan.get("candidatePaths") or []
# plan 真实字段是 needsPackChange / needsSourceOrDistChange，没有 changesIndependentVariable。
# 只有改动 Pack 或源码/dist 的路径才可能改变自变量；P1/P4/P5 不满足。
changes_iv = [
    p for p in paths
    if isinstance(p, dict) and (p.get("needsPackChange") is True or p.get("needsSourceOrDistChange") is True)
]

verdict = {
    "mode": "three-items-authorization-closure-verdict-2026-11-15",
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source": [
        "three-items-precondition-2026-11-15.json",
        "proposition-pursuit-plan-2026-11-14.json",
        "ab5-final-verdict-2026-11-14.json",
        "ab4-verdict-2026-11-12.json",
        "RESULT §26 / §27",
    ],
    "principle": "三条指令各自独立判定，不默认打包：② 的意图不构成 ③ 的授权；① 的前提缺失不构成 ② 的自动放行；任何一条都不得靠复述清单升级为授权。",
    "derivationCorrection": {
        "what": "首次推导按不存在的字段 changesIndependentVariable 过滤 candidatePaths，得到空列表",
        "detectedBy": "回读 proposition-pursuit-plan-2026-11-14.json 顶层真实结构",
        "realFields": ["needsPackChange", "needsSourceOrDistChange"],
        "ruling": "以 P2（needsSourceOrDistChange）/ P3（needsPackChange）为改变自变量的路径重算；P1/P4/P5 不改变自变量。原有判定文字不变，本字段留痕。",
    },
    "items": [
        {
            "id": "①",
            "intent": "要跑真机",
            "intentExpressed": True,
            "dimensions": {
                "explicitUnfreezeGiven": False,
                "allowFrozenFlagInThisTurn": False,
                "platformsNamed": [],
                "independentVariableSpecified": False,
                "newCriterionSpecified": False,
                "platformPolicyStillFrozen": True,
            },
            "userSetPreconditions": [
                "用户 2026-11-15 上一轮第 2 条：须逐次明确解冻",
                "用户 2026-11-15 上一轮第 2 条：并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据",
            ],
            "diskEvidence": {
                "ab5Code": ab5.get("code"),
                "ab5RoundsExecuted": ab5.get("roundsExecuted"),
                "ab4Code": ab4.get("code"),
                "ab6Receipts": pre["evidence"]["ab6Targets"],
                "postF1FullARounds": 3,
                "postF1WallCount": 0,
                "planCode": plan.get("code"),
                "pathsChangingIndependentVariable": [p.get("id") or p.get("name") for p in changes_iv],
            },
            "whyIndependentVariableMatters": "§26 已证 A 组 no-boundary 本来就是同一会话 8 步串行 / 7 次 AI 往返，自变量结构条件已满足而墙不出现；F1 修复后 3 份完整 A 组回执 8/8、撞墙 0 次。不改变自变量的重跑只能重复 ABORT_NO_WALL。",
            "costOfRealChange": "P2（回滚 F1 归因对照）需改源码/dist；P3（人工加长会话）需改 Pack。两者都会使既有 dist hash / 变体 Pack sha256 证据链断代，必须重建 dist + 全量 npm test + 全量变异 + dist 一致性并登记新基线。",
            "code": "NOT_EXECUTED_PRECONDITION_UNMET",
            "actionsTaken": {
                "browserLaunched": False,
                "frozenSiteOpened": False,
                "messageSent": False,
                "receiptCreated": False,
            },
        },
        {
            "id": "②",
            "intent": "要提交",
            "intentExpressed": True,
            "dimensions": {
                "commitActionExplicitlyStated": True,
                "commitActionSeparatelyConfirmed": False,
                "fileSetAuthorized": False,
                "scopeSnapshotFresh": False,
                "staged": pre["diskTruth"]["staged"],
            },
            "userSetPreconditions": [
                "用户 2026-11-15 上一轮第 3 条：提交按「提交动作」与「文件集合」分别重新授权",
                "用户 2026-11-14 明令：不要默认一次全收",
            ],
            "diskEvidence": {
                "oldScopeTotal": 122,
                "oldScopeOriginMain": "f98a1a7",
                "oldScopeBehind": 4,
                "oldScopeDefect": "modifiedTracked.files[0] = 'hrome-extension/src/background/pack-executor.js'（首字符 c 被切）",
                "currentStatusItems": pre["diskTruth"]["statusItems"],
                "currentBehind": pre["diskTruth"]["behind"],
            },
            "code": "COMMIT_ACTION_EXPRESSED_BUT_FILE_SET_NOT_AUTHORIZED",
            "reason": "动作意图有，但文件集合这一维未给，且旧清单已过期并含路径缺陷。staged=0，任何 commit 都必须先显式 git add 指定集合；禁止 git add -A / git commit -a。",
            "actionsTaken": {"commit": False, "stage": False, "addAll": False},
        },
        {
            "id": "③",
            "intent": "要 push",
            "intentExpressed": True,
            "dimensions": {
                "userSelfMarkedNeedsSeparateAuthorization": True,
                "divergenceHandlingAuthorized": False,
                "pushAuthorized": False,
                "behindInUserInstruction": 31,
                "behindDiskTruth": pre["diskTruth"]["behind"],
                "unpushed": pre["diskTruth"]["unpushed"],
            },
            "code": "NOT_AUTHORIZED_NO_ACTION",
            "reason": "用户自己写明『另需单独授权先处理 behind 31 分歧』，该授权未给；且分歧真值已由外部 fetch 推进到 33。即便 ② 授权完成，push 也须再单独授权分歧处理方式（merge / rebase / 先 pull）并完成集成门禁。",
            "actionsTaken": {"push": False, "fetch": False, "pull": False, "merge": False, "rebase": False},
        },
    ],
    "overall": {
        "code": "PARTIAL_INTENT_ONLY_NO_EXECUTABLE_AUTHORIZATION",
        "executableItemCount": 0,
        "noBundling": True,
        "n25StatusChanged": False,
        "gitUntouched": True,
        "realMachineRounds": 0,
        "awaiting": [
            "① 逐次解冻指令 + 本次改变的自变量（或明确裁定不跑）",
            "② 提交动作与文件集合分别确认",
            "③ 单独授权处理 behind=33 分歧后才可 push",
        ],
    },
    "note": "本文件是机器裁定，不是用户授权；后续如用户通过选项补齐，须另写 ruling 文件，不回改本文件。",
}

out = EVID / "three-items-authorization-closure-verdict-2026-11-15.json"
out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({
    "overall": verdict["overall"],
    "items": [{"id": i["id"], "code": i["code"]} for i in verdict["items"]],
    "pathsChangingIV": [p.get("id") or p.get("name") for p in changes_iv],
}, ensure_ascii=False, indent=2))
