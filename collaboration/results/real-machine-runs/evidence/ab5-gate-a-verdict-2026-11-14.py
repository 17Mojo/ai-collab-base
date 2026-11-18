#!/usr/bin/env python3
"""ab5 Gate A 机器裁定：只读 A 单轮回执，机械判 6 条判据。

不启动浏览器、不发送消息、不跑 B、不写 L2 回执、不碰 git。
visualGate（截图末条 AI 回复是否为站点报错）属 nonMachineObservation，
本脚本只标记「需要人确认」，绝不把它折进机器布尔推导。
"""
import json
import pathlib
import hashlib
import datetime
import sys

EV = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/collaboration/results/real-machine-runs/evidence")
RECEIPT = EV / "L2-deepseek-auto-2026-11-14.ab5-no-boundary.json"
SHOT = EV / "L2-deepseek-auto-2026-11-14.ab5-no-boundary.png"
PLAN = EV / "ab5-observe-first-plan-2026-11-12.json"
RULING = EV / "ab5-gate-a-platform-ruling-2026-11-14.json"
PRECHECK = EV / "L2-precheck-2026-11-14.ab5.deepseek-longcat.json"
VERIFY = EV / "ab5-observe-first-verify-2026-11-14.json"
PROGRESS = EV / "ab5-observe-first-progress-2026-11-14.jsonl"
OUT = EV / "ab5-gate-a-verdict-2026-11-14.json"

if not RECEIPT.exists():
    print("RECEIPT_MISSING", RECEIPT.name)
    print("Gate A 不可判定：A 单轮回执尚未落盘，不得据此裁定或跑 B。")
    sys.exit(2)

raw = RECEIPT.read_bytes()
d = json.loads(raw)
ex = d.get("exec") or {}
r = ex.get("result") or {}
steps = r.get("steps") or []
resets = r.get("sessionResets") or []
pp = d.get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None

failed = [s for s in steps if s.get("success") is not True]
first_failed = failed[0] if failed else None
first_failed_id = first_failed.get("id") if isinstance(first_failed, dict) else None
first_failed_error = first_failed.get("error") if isinstance(first_failed, dict) else None

criteria = {
    "C1_stepsTotal_eq_8": len(steps) == 8,
    "C2_stepSuccess_eq_7": sum(1 for s in steps if s.get("success") is True) == 7,
    "C3_firstFailedStepId_eq_step_8_output": first_failed_id == "step_8_output",
    "C4_failedErrorContainsResponseTimeout": isinstance(first_failed_error, str) and "Response timeout" in first_failed_error,
    "C5_earlierStepsAllSucceeded": len(steps) >= 7 and all(s.get("success") is True for s in steps[:7]),
    "C6_A_hasNoSessionResets": len(resets) == 0,
}
machine_pass = all(criteria.values())

# 机器判据不成立 ⇒ 墙不存在（或站点提前挂掉），一律 ABORT_NO_WALL，不跑 B。
if machine_pass:
    code = "GATE_A_MACHINE_CRITERIA_MET_PENDING_VISUAL_CONFIRMATION"
    decision = "仅机器判据成立；visualGate 必须由人确认截图末条 AI 回复不是『服务出错啦，请稍后再试。』后才可跑同站 B"
    b_should_run = None  # 待人工裁定，脚本不擅自置 true
else:
    code = "ABORT_NO_WALL"
    decision = "判『墙不存在 / 本轮不构成 A 撞墙』：停机，不跑 B、不跑 longcat；N25 保持 open"
    b_should_run = False

# 附加事实（不构成判据，只供复核）
wall_step = next((s for s in steps if s.get("id") == "step_8_output"), None)
step_summary = [{"id": s.get("id"), "success": s.get("success"),
                 "duration": s.get("duration")} for s in steps]

verdict = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "ab5-gate-a-machine-verdict",
    "sourceReceipt": RECEIPT.name,
    "sourceReceiptSha256": hashlib.sha256(raw).hexdigest(),
    "sourceReceiptGeneratedAt": d.get("generatedAt"),
    "platform": d.get("platform"),
    "packVariant": d.get("packVariant"),
    "policyUnfrozenBy": unfrozen,
    "gateA": {
        "description": "A 组（no-boundary）单轮是否真的在 step_8_output 撞墙",
        "machineCriteria": criteria,
        "machinePass": machine_pass,
        "visualGate": {
            "required": True,
            "kind": "nonMachineObservation",
            "participatesInMachineBoolean": False,
            "status": "NOT_EVALUATED_BY_MACHINE",
            "note": "截图人工视觉判读：末条 AI 回复不得是『服务出错啦，请稍后再试。』；放行必须由人确认。",
            "screenshot": SHOT.name,
            "screenshotExists": SHOT.exists(),
        },
    },
    "observed": {
        "execSuccess": ex.get("success"),
        "status": r.get("status"),
        "durationMs": r.get("duration"),
        "stepsTotal": len(steps),
        "stepSuccess": sum(1 for s in steps if s.get("success") is True),
        "firstFailedStepId": first_failed_id,
        "firstFailedStepError": first_failed_error,
        "sessionResets": len(resets),
        "wallStep": {"id": wall_step.get("id"), "success": wall_step.get("success"),
                     "durationMs": wall_step.get("duration")} if isinstance(wall_step, dict) else None,
        "steps": step_summary,
    },
    "code": code,
    "decision": decision,
    "bShouldRun": b_should_run,
    "bActuallyRun": False,
    "longcatActuallyRun": False,
    "propositionSupported": False,
    "n25": "remain open",
    "attributionBoundaries": [
        "不得说会话边界有效，也不得说边界无效",
        "不得把 A/B 都通过归功边界；本轮未跑 B，无成对证据",
        "不得把 F1 / F2 真机验证挪用为因果证据",
        "站点侧报错属外部混杂变量，不得与『墙』合并归因",
    ],
    "evidence": {
        "plan": PLAN.name,
        "ruling": RULING.name,
        "precheck": PRECHECK.name,
        "precondition": "ab5-precondition-2026-11-14.json",
        "runnerVerify": VERIFY.name if VERIFY.exists() else None,
        "progress": PROGRESS.name if PROGRESS.exists() else None,
    },
    "noRealMachineAction": True,
    "gitUnchanged": True,
    "note": "本文件是只读裁定，不是回执。machinePass 只表示 6 条机器判据成立与否；命题成立还需 B 组硬判据 + 人工视觉闸。",
}
OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
print("WROTE", OUT.name)
print("code =", code)
print("machinePass =", machine_pass)
print(json.dumps(criteria, ensure_ascii=False, indent=2))
print("status =", r.get("status"), "| steps =", len(steps),
      "| success =", sum(1 for s in steps if s.get("success") is True),
      "| duration =", r.get("duration"))
print("firstFailed =", first_failed_id, "| sessionResets =", len(resets))
print("bShouldRun =", b_should_run, "| bActuallyRun =", False)
