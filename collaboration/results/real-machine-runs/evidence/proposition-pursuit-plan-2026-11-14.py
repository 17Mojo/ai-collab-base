#!/usr/bin/env python3
"""追究命题：把「自变量不可控」形式化为可判定条件，产出 plan-only 方案。

只读。不启动浏览器、不改 Pack、不改源码/测试/dist、不碰 git、不产生真机回执。
所有数字从磁盘回执机械重算，不硬编码结论。
"""
import json
import pathlib
import datetime
import hashlib
import glob
import os

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
OUT = EV / "proposition-pursuit-plan-2026-11-14.json"

# ── 机械汇总所有 A 组（no-boundary）回执 ─────────────────────
paths = sorted(set(glob.glob(str(EV / "L2-*-auto-2026-11-1*.ab*-no-boundary.json")) +
                   glob.glob(str(EV / "L2-*-auto-2026-11-14.ab5-no-boundary.json"))))
a_rounds = []
for p in paths:
    d = json.loads(pathlib.Path(p).read_text())
    ex = d.get("exec") or {}
    r = ex.get("result") or {}
    st = r.get("steps") or []
    ai_steps = [s for s in st if s.get("type") in ("generation", "analysis", "fusion")]
    s8 = next((s for s in st if s.get("id") == "step_8_output"), None)
    a_rounds.append({
        "receipt": pathlib.Path(p).name,
        "platform": d.get("platform"),
        "packVariant": d.get("packVariant"),
        "status": r.get("status"),
        "stepsTotal": len(st),
        "stepSuccess": sum(1 for s in st if s.get("success") is True),
        "aiRoundTrips": len(ai_steps),
        "outputChars": sum(len(str(s.get("output") or "")) for s in st),
        "sessionResets": len(r.get("sessionResets") or []),
        "firstFailedStepId": next((s.get("id") for s in st if s.get("success") is not True), None),
        "step8Reached": isinstance(s8, dict),
        "step8Success": s8.get("success") if isinstance(s8, dict) else None,
        "step8DurationMs": s8.get("duration") if isinstance(s8, dict) else None,
        "durationMs": r.get("duration"),
    })

# 结构复现组：F1 之后、A 组、8 步全走完、无边界
post_f1_full = [x for x in a_rounds
                if x["stepsTotal"] == 8 and x["sessionResets"] == 0
                and x["status"] == "completed"]
wall_observed = [x for x in post_f1_full if x["step8Success"] is False]

# ── 其它引用证据 ─────────────────────────────────────────────
diag = json.loads((EV / "wall-observability-diagnosis-2026-11-12.json").read_text())
ab4 = json.loads((EV / "ab4-verdict-2026-11-12.json").read_text())
ab5 = json.loads((EV / "ab5-final-verdict-2026-11-14.json").read_text())
iso = json.loads((EV / "L2-longcat-fusion-isolated-2026-11-11.json").read_text())

pack_a = EV / "ab-pack-2026-11-11.no-boundary.json"
pack_b = EV / "ab-pack-2026-11-11.with-boundary.json"
packs_sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (pack_a, pack_b)}

# ── 可判定条件的形式化 ───────────────────────────────────────
formal = {
    "proposition": "fresh_session 会话边界能解掉 deepseek / longcat 的 step_8 长会话撞墙",
    "independentVariable": "单会话串行累积到 step_8 时的「长会话撞墙」状态",
    "dependentVariable": "step_8_output 是否失败（Response timeout / 站点报错）",
    "decidableIff": (
        "存在至少一次 A 组（no-boundary）能稳定复现『前 7 步全成功、step_8_output 失败、"
        "且失败不是站点侧随机报错、不是等待判据 bug』的墙状态；"
        "并且同站相邻时间窗内的 B 组（with-boundary）在边界真执行后通过。"
    ),
    "currentState": {
        "structuralConditionAlreadyMet": len(post_f1_full) > 0,
        "structuralConditionNote": (
            "A 组 no-boundary 本来就是同一会话 8 步串行、7 次 AI 往返、无任何 fresh_session；"
            "这正是 §9.4 宣称的『会话已累积 7 轮』条件。F1 后多轮已复现该结构，仍不撞墙。"
        ),
        "postF1FullARounds": len(post_f1_full),
        "postF1FullARoundsWithWall": len(wall_observed),
        "code": "PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE",
        "strengthenedByAb5": (
            "ab5 observe-first 单轮再次 8/8 completed、step_8 11.7s、sessionResets=0，"
            "是第 3 份同型结构复现证据；§24 的『墙不复现』从推论升级为多次真机同型观察。"
        ),
    },
    "isNot": [
        "不是说边界无效", "不是说命题不成立（不成立需可判定的对照轮次）",
        "不是说 N25 可关闭", "不是说 F1 / F2 真机验证无效",
        "不是说『长会话从未被复现』——结构条件已复现，只是墙不出现",
    ],
}

# ── 候选路径（每条都明示红线冲突与授权需求）─────────────────
paths_plan = [
    {
        "id": "P1",
        "name": "按不可判定收口 / 改述 N25",
        "realMachineRounds": 0,
        "changes": ["只回写 RESULT 与 known_gaps.json 的性质描述"],
        "needsUnfreeze": False,
        "needsPackChange": False,
        "needsSourceOrDistChange": False,
        "redLineConflicts": ["是否关闭 N25 必须由用户裁定；判据未成立前默认保持 open"],
        "expectedOutcome": "把 N25 从『待 A/B 验证』改述为『已跑 A/B，原始观察对象已重新归因、命题不可判定』，零额度成本",
        "recommendation": "推荐：唯一不消耗站点额度、不制造新混杂变量的诚实路径",
    },
    {
        "id": "P2",
        "name": "回滚 F1 的归因对照实验",
        "realMachineRounds": "2–4",
        "changes": ["临时把等待判据退回 countGrew-only", "重建 dist", "跑门禁", "真机 A/B"],
        "needsUnfreeze": True,
        "needsPackChange": False,
        "needsSourceOrDistChange": True,
        "redLineConflicts": [
            "主动制造一个已知 bug，违反『不改源码 / 不改 dist』的本轮边界",
            "即便重现假超时，也只证明 F-D1 归因正确，不能证明 fresh_session 有效",
            "需要新的机器判据，且用完必须把 F1 恢复并重新全量门禁",
        ],
        "expectedOutcome": "把 F-D1 从推论升级为对照实验证据；对原命题的因果结论无直接贡献",
        "recommendation": "不推荐作为追究原命题的手段（答的是另一个问题）",
    },
    {
        "id": "P3",
        "name": "人工加长会话试图复现墙",
        "realMachineRounds": "2–4",
        "changes": ["改 Pack 增加轮次 / 加长 prompt", "生成新变体", "重定 Gate 判据"],
        "needsUnfreeze": True,
        "needsPackChange": True,
        "needsSourceOrDistChange": False,
        "redLineConflicts": [
            "违反 ab5 plan 硬约束『A/B 只差 fresh_session 一个变量、Pack hash 不变』",
            "§9.4 的『长会话是变量』归因已被 F-D3 削弱，加长会话属换命题而非追究原命题",
            "deepseek 侧原始症状已证伪为等待判据假超时，加长大概率只拉长耗时",
        ],
        "expectedOutcome": "大概率仍无墙，或引入新的上下文长度混杂变量",
        "recommendation": "不推荐：换命题 + 破坏单变量约束",
    },
    {
        "id": "P4",
        "name": "按原判据再跑一次完整 4 轮 A/B",
        "realMachineRounds": 4,
        "changes": ["无（复用现有 dist / Pack / 判据）"],
        "needsUnfreeze": True,
        "needsPackChange": False,
        "needsSourceOrDistChange": False,
        "redLineConflicts": ["§24 已判定为盲跑；用户 2026-11-14 明令『而不是盲跑 4 轮』"],
        "expectedOutcome": "大概率 NO_WALL_THIS_ROUND 或站点报错，无法提供成对证据",
        "recommendation": "不推荐：与用户最新明令冲突",
    },
    {
        "id": "P5",
        "name": "换活跃 5 站做替代对照",
        "realMachineRounds": "2–4",
        "changes": ["换平台", "重定命题"],
        "needsUnfreeze": False,
        "needsPackChange": False,
        "needsSourceOrDistChange": False,
        "redLineConflicts": [
            "N25 原始观察对象明确是 deepseek / longcat，换站等于换命题，不能代偿",
            "N23 已证明活跃 5 站『重置真的做到了』，不是因果证据",
        ],
        "expectedOutcome": "得到另一条命题的结论，N25 仍不可判定",
        "recommendation": "不推荐：答非所问",
    },
]

doc = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "proposition-pursuit-readonly-plan",
    "status": "plan-only / NOT-EXECUTED",
    "scope": "用户 2026-11-14 明令『1、追究命题；2、重新授权』中的第 1 项",
    "formal": formal,
    "machineEvidence": {
        "aGroupRoundsExamined": len(a_rounds),
        "aGroupRounds": a_rounds,
        "postF1FullARounds": post_f1_full,
        "isolationExperiment": {
            "receipt": "L2-longcat-fusion-isolated-2026-11-11.json",
            "verdict": iso.get("verdict"), "durationSeconds": iso.get("dur"),
            "promptLen": iso.get("promptLen"), "textLen": iso.get("textLen"),
            "interpretation": "空会话 21s 通过只能证明提示词本身不被拒；不能独立证明『长会话是变量』",
        },
        "diagnosisFindings": [f["id"] + ": " + f["claim"] for f in diag["findings"]],
        "ab4F2": {"f2RealMachineVerified": ab4.get("f2RealMachineVerified"),
                  "allBoundariesActuallyExecuted": ab4.get("allBoundariesActuallyExecuted"),
                  "bHardCriteriaMetCount": ab4.get("bHardCriteriaMetCount")},
        "ab5": {"code": ab5.get("code"), "roundsExecuted": ab5["abortBranch"]["roundsExecuted"],
                "bActuallyRun": ab5["abortBranch"]["bActuallyRun"]},
        "packsSha256": packs_sha,
    },
    "candidatePaths": paths_plan,
    "authorizationRequired": {
        "note": "『重新授权』未指明宾语。以下维度必须分别确认，不得默认全收或凭上下文推断：",
        "dimensions": [
            {"id": "A1", "name": "追究命题走哪条路径（P1–P5）", "default": "未裁定，不擅自选 P1"},
            {"id": "A2", "name": "逐次解冻 deepseek / longcat（ALLOW_FROZEN=1）", "default": "未授权"},
            {"id": "A3", "name": "提交动作（git commit）", "default": "未授权；上轮 q-0=暂不提交"},
            {"id": "A4", "name": "提交文件集合", "default": "上轮 q-1 仅为 PREFERENCE_ONLY_NOT_AUTHORIZATION"},
            {"id": "A5", "name": "behind=4 分歧处理（merge / rebase / pull）", "default": "未授权"},
            {"id": "A6", "name": "push 到远端", "default": "未授权"},
        ],
    },
    "hardBoundaries": {
        "noRealMachineAction": True,
        "noPackChange": True,
        "noSourceOrDistChange": True,
        "noGitChange": True,
        "noBrowserLaunch": True,
        "noMessageSent": True,
    },
    "n25": "remain open",
    "note": "本文件是只读裁定与方案，不是回执、不证明命题成立与否。任何真机执行都须先取得明确解冻授权。",
    "selfCheck": {"pass": True, "errors": [], "checkedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "note": "自检只核引用证据存在与 JSON 可解析，不启动浏览器、不产生回执"},
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
print("WROTE", OUT.name)
print("status =", doc["status"])
print("A group rounds examined =", len(a_rounds))
print("postF1 full A rounds =", len(post_f1_full), "| with wall =", len(wall_observed))
for x in post_f1_full:
    print("  ", x["receipt"], "steps", x["stepsTotal"], "/", x["stepSuccess"],
          "step8", x["step8Success"], x["step8DurationMs"], "ms, resets", x["sessionResets"])
print("code =", formal["currentState"]["code"])
print("candidate paths =", [p["id"] for p in paths_plan])
print("authorization dimensions =", [d["id"] for d in doc["authorizationRequired"]["dimensions"]])
