#!/usr/bin/env python3
"""ab4 四轮真机 A/B 的机器裁定（只读回执，机械推导，不手写结论）。

判据（用户 2026-11-12 明确下达，逐条落成布尔）：
  1. 4 份回执都必须落盘；缺一份就 code != 完整裁定。
  2. B 组 sessionResets[0].available===true && messageCountAfter<messageCountBefore
     才算「边界真的执行了」；否则该轮作废 / 本轮不可评估。
  3. 边界步骤压根没被触发（sessionResets 为空）⇒ 本轮不可评估。
     ⚠️ 以上两种都不得写成「边界无效」——本生成器永不产出该结论。
  4. 只有「A 撞墙且 B 通过」才支持命题。
     A 8/8 ⇒ NO_WALL_THIS_ROUND（本轮墙不存在，不能归功边界）。
     A 在 step_8 之前失败 ⇒ 有混杂变量，本轮不可评估。
  5. N25：判据成立前保持 open；判据成立也只是「具备关闭条件」，
     是否关闭由用户裁定（机器不擅自 close）。

人工视觉判读（截图）单列 nonMachineObservations，不参与任何机器布尔推导。

用法：python3 ab4-verdict-2026-11-12.py [--regenerate]
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ab4-verdict-2026-11-12.json"
REGENERATE = "--regenerate" in sys.argv

RECEIPTS = {
    ("deepseek", "A"): "L2-deepseek-auto-2026-11-12.ab4-no-boundary.json",
    ("deepseek", "B"): "L2-deepseek-auto-2026-11-12.ab4-with-boundary.json",
    ("longcat", "A"): "L2-longcat-auto-2026-11-12.ab4-no-boundary.json",
    ("longcat", "B"): "L2-longcat-auto-2026-11-12.ab4-with-boundary.json",
}


def load(name):
    p = HERE / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def view(d):
    ex = (d or {}).get("exec") or {}
    res = ex.get("result") or {}
    steps = res.get("steps") or []
    resets = res.get("sessionResets") or []
    failed = [s for s in steps if s.get("success") is not True]
    first_failed = failed[0] if failed else None
    first_reset = resets[0] if resets else None
    before = first_reset.get("messageCountBefore") if isinstance(first_reset, dict) else None
    after = first_reset.get("messageCountAfter") if isinstance(first_reset, dict) else None
    available = first_reset.get("available") if isinstance(first_reset, dict) else None
    reset_ok = bool(
        available is True
        and isinstance(before, int)
        and isinstance(after, int)
        and after < before
    )
    err = (first_failed or {}).get("error") or ""
    return {
        "exists": d is not None,
        "receipt": None,
        "generatedAt": (d or {}).get("generatedAt"),
        "platform": (d or {}).get("platform"),
        "packVariant": (d or {}).get("packVariant"),
        "unfrozenBy": ((d or {}).get("platformPolicy") or {}).get("unfrozenBy")
        if isinstance((d or {}).get("platformPolicy"), dict)
        else None,
        "execSuccess": ex.get("success"),
        "status": res.get("status"),
        "duration": res.get("duration"),
        "stepsTotal": len(steps),
        "stepSuccess": sum(1 for s in steps if s.get("success") is True),
        "completed8of8": bool(
            ex.get("success") is True
            and res.get("status") == "completed"
            and len(steps) == 8
            and all(s.get("success") is True for s in steps)
        ),
        "firstFailedStepId": (first_failed or {}).get("id"),
        "firstFailedError": err,
        "firstFailedDuration": (first_failed or {}).get("duration"),
        "responseTimeout": "Response timeout" in err,
        "sessionResets": len(resets),
        "boundaryAttempted": len(resets) > 0,
        "resetAvailable": available,
        "resetStrategy": first_reset.get("strategy") if isinstance(first_reset, dict) else None,
        "resetReason": first_reset.get("reason") if isinstance(first_reset, dict) else None,
        "messageCountBefore": before,
        "messageCountAfter": after,
        "resetActuallyHappened": reset_ok,
    }


rounds = {}
for key, name in RECEIPTS.items():
    v = view(load(name))
    v["receipt"] = name
    v["group"] = key[1]
    rounds[f"{key[0]}_{key[1]}"] = v

all_four = all(v["exists"] for v in rounds.values())
all_boundaries = all(rounds[f"{p}_B"]["resetActuallyHappened"] for p in ("deepseek", "longcat"))
b_hard_count = sum(1 for p in ("deepseek", "longcat") if rounds[f"{p}_B"]["resetActuallyHappened"])

pairs = {}
for p in ("deepseek", "longcat"):
    a = rounds[f"{p}_A"]
    b = rounds[f"{p}_B"]
    a_wall = bool(
        (not a["completed8of8"])
        and a["firstFailedStepId"] == "step_8_output"
        and a["responseTimeout"]
    )
    a_failed_before_wall = bool(
        (not a["completed8of8"])
        and a["firstFailedStepId"] is not None
        and a["firstFailedStepId"] != "step_8_output"
    )
    b_usable = bool(b["boundaryAttempted"] and b["resetActuallyHappened"])
    b_passed = bool(b_usable and b["completed8of8"])
    no_wall = bool(a["completed8of8"] and b["completed8of8"])

    if not b["boundaryAttempted"]:
        status = "BOUNDARY_NEVER_ATTEMPTED"
        reason = "B 组 sessionResets 为空：边界步骤压根没执行 ⇒ 本轮不可评估，不得说边界有效或无效"
        usable = False
    elif not b["resetActuallyHappened"]:
        status = "INVALID_ROUND_RESET_UNAVAILABLE"
        reason = "B 组边界执行了但 available=false 或消息数没下降 ⇒ 该轮作废，不得包装成边界无效"
        usable = False
    elif a["completed8of8"] and b["completed8of8"]:
        status = "NO_WALL_THIS_ROUND"
        reason = "A/B 都 8/8 ⇒ 本轮墙不存在，不能把 B 的通过归功于边界"
        usable = True
    elif a_failed_before_wall:
        status = "A_FAILED_BEFORE_WALL_STEP"
        reason = f"A 组在 {a['firstFailedStepId']} 就失败（边界声明在 step_8_output）⇒ 有混杂变量，本轮不可评估"
        usable = False
    elif a_wall and b_passed:
        status = "SUPPORTS_PROPOSITION"
        reason = "A 在 step_8_output 撞墙且 B 组边界真执行后 8/8 ⇒ 成对证据成立"
        usable = True
    elif a_wall and not b_passed:
        status = "A_WALL_B_NOT_PASSED"
        reason = "A 撞墙但 B 未 8/8 ⇒ 命题不成立，且不能反推边界无效"
        usable = True
    else:
        status = "UNCLASSIFIED_MIXED"
        reason = "A/B 结果不构成可归因的成对证据 ⇒ 本轮不可评估"
        usable = False

    pairs[p] = {
        "platform": p,
        "status": status,
        "reason": reason,
        "roundUsable": usable,
        "aCompleted8of8": a["completed8of8"],
        "aWallObserved": a_wall,
        "aFailedBeforeWallStep": a_failed_before_wall,
        "aFirstFailedStepId": a["firstFailedStepId"],
        "bBoundaryAttempted": b["boundaryAttempted"],
        "bResetActuallyHappened": b["resetActuallyHappened"],
        "bCompleted8of8": b["completed8of8"],
        "bPassed": b_passed,
        "bothPassed": no_wall,
        "supportsProposition": bool(a_wall and b_passed and usable),
        "boundaryIneffectiveClaimed": False,
    }

supports = any(x["supportsProposition"] for x in pairs.values())
all_usable = all(x["roundUsable"] for x in pairs.values())

# 本轮最有价值的新事实：两个 adapter 的新会话入口都在真机上真的生效了。
# 这验证的是「会话边界能被打开」（F2），不是「边界解掉了长会话撞墙」（命题）。
f2_real_machine_verified = all_boundaries and all_four

# longcat B：边界 6→0 真执行之后，step_8_output 仍 Response timeout。
# 这是一条与命题方向相反的观察，必须显式列出，但**不许**据此宣称「边界无效」：
# A 组在 step_4 就挂了（站点错误），没有成对对照，且站点报错是混杂变量。
b_failed_at_wall_step_after_reset = bool(
    rounds["longcat_B"]["resetActuallyHappened"]
    and rounds["longcat_B"]["firstFailedStepId"] == "step_8_output"
    and rounds["longcat_B"]["responseTimeout"]
)
final_receipts = HERE / "ab4-final-receipts-2026-11-12.json"
like_for_like_gap = None
if final_receipts.exists():
    try:
        like_for_like_gap = json.loads(final_receipts.read_text(encoding="utf-8")).get("likeForLike", {}).get("gapSeconds")
    except Exception:
        pass

if not all_four:
    code = "INCOMPLETE_RECEIPTS_CANNOT_VERDICT"
elif not all_usable and not supports:
    code = "PROPOSITION_NOT_SUPPORTED_ROUNDS_UNUSABLE"
elif supports:
    code = "PROPOSITION_SUPPORTED_BY_MACHINE_PAIR_PENDING_VISUAL_REVIEW"
else:
    code = "PROPOSITION_NOT_SUPPORTED"

verdict = {
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mode": "ab4-four-round-ab-verdict",
    "scope": "2026-11-12 用户明确解冻后，新 dist（deepseek 精确文案逃生口）的 4 轮真机 A/B",
    "authorization": {
        "unfrozenBy": "user 2026-11-12 explicit instruction",
        "perRoundFlag": "ALLOW_FROZEN=1",
        "whitelistChanged": False,
        "commitOrPush": False,
    },
    "code": code,
    "allFourRoundsExecuted": all_four,
    "allBoundariesActuallyExecuted": all_boundaries,
    "bHardCriteriaMetCount": b_hard_count,
    "bHardCriteria": "sessionResets[0].available===true && messageCountAfter<messageCountBefore",
    "f2RealMachineVerified": f2_real_machine_verified,
    "f2Scope": "只证明两个 adapter 的新会话入口在真机上真的打开了会话（3→0 / 6→0）；不证明边界解掉长会话撞墙。",
    "bFailedAtWallStepAfterSuccessfulReset": b_failed_at_wall_step_after_reset,
    "bFailedAtWallStepNote": (
        "longcat B 在边界 6→0 真执行之后 step_8_output 仍 Response timeout；"
        "这是与命题方向相反的观察，但 A 组在 step_4 就失败、站点报错是混杂变量，"
        "没有成对判据 ⇒ 不得包装成「边界无效」，也不得说命题成立。"
    ),
    "likeForLikeGapSeconds": like_for_like_gap,
    "likeForLikeNote": "第 3→4 轮为独立补跑，间隔如实保留；Pack 与 dist hash 经前置复核一致。",
    "propositionSupported": supports,
    "n25": {
        "status": "open",
        "decision": "remain open",
        "eligibleToClose": supports,
        "reason": (
            "判据成立的成对证据已出现，但 N25 关闭由用户裁定，机器不擅自 close"
            if supports
            else "只有「A 撞墙且 B 通过」才支持命题；判据未成立前 N25 保持 open"
        ),
    },
    "rounds": rounds,
    "pairs": pairs,
    "nonMachineObservations": [
        "截图里是否出现「服务出错啦，请稍后再试。」等站点侧错误，属人工视觉判读，不参与任何机器布尔推导。",
        "A 组在 step_8_output 的 Response timeout 是否确为长会话撞墙（而非站点报错）需人工核截图；机器只判回执层事实。",
        "若机器判据成立，仍需在报告中显式写明视觉复核结论后才能关闭 N25。",
    ],
    "attributionBoundaries": [
        "不得把边界未执行或 available:false 的轮次包装成「边界无效」。",
        "不得把 A/B 都通过的轮次归功于边界（本轮墙不存在）。",
        "不得把 A 在 step_8 之前失败归给边界（边界声明在 step_8_output）。",
        "不得把 deepseek 的 8/8 归功于边界；不得说重置免费或把耗时差异归因给重置。",
        "不得把 F1 公共等待判据的真机成功挪用为 fresh_session 的因果证据。",
    ],
    "evidence": {
        "receipts": list(RECEIPTS.values()),
        "runner": "ab4-runner-2026-11-12.sh",
        "runnerLog": "ab4-rerun-2026-11-12.log",
        "runnerProgress": "ab4-rerun-progress-2026-11-12.jsonl",
        "runnerSummary": "ab4-runner-summary-2026-11-12.json",
        "precheck": "L2-precheck-2026-11-12.ab4.deepseek-longcat.json",
        "distConsistency": "dist-consistency-2026-11-12.deepseek-newchat.json",
    },
}
if REGENERATE and OUT.exists():
    try:
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        verdict["regeneratedFrom"] = {
            "file": OUT.name,
            "previousCode": prev.get("code"),
            "previousGeneratedAt": prev.get("generatedAt"),
            "note": "显式 --regenerate 重生成；产物内留痕，最终 code 以本次机械推导为准。",
        }
    except Exception:
        pass

OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "written": str(OUT), "code": code,
    "allFourRoundsExecuted": all_four,
    "allBoundariesActuallyExecuted": all_boundaries,
    "bHardCriteriaMetCount": b_hard_count,
    "propositionSupported": supports,
    "n25": verdict["n25"]["decision"],
    "pairs": {k: v["status"] for k, v in pairs.items()},
}, ensure_ascii=False, indent=2))
