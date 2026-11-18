#!/usr/bin/env python3
"""ab5 最终裁定：合并 Gate A 机器裁定 + ABORT_NO_WALL 分支事实 + 人工视觉观察。

只读，不跑真机、不跑 B、不碰 git。视觉观察明确标为 nonMachineObservation，
不参与任何机器布尔推导，也不改变 ABORT_NO_WALL 结论。
"""
import json
import pathlib
import datetime

EV = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/collaboration/results/real-machine-runs/evidence")
GATE_A = EV / "ab5-gate-a-verdict-2026-11-14.json"
RECEIPT = EV / "L2-deepseek-auto-2026-11-14.ab5-no-boundary.json"
VERIFY = EV / "ab5-observe-first-verify-2026-11-14.json"
PROGRESS = EV / "ab5-observe-first-progress-2026-11-14.jsonl"
RUNLOG = EV / "ab5-observe-first-2026-11-14.log"
RULING = EV / "ab5-gate-a-platform-ruling-2026-11-14.json"
PRECOND = EV / "ab5-precondition-2026-11-14.json"
PRECHECK = EV / "L2-precheck-2026-11-14.ab5.deepseek-longcat.json"
OUT = EV / "ab5-final-verdict-2026-11-14.json"

g = json.loads(GATE_A.read_text())
d = json.loads(RECEIPT.read_text())
v = json.loads(VERIFY.read_text())
ex = d.get("exec") or {}
r = ex.get("result") or []

assert g["code"] == "ABORT_NO_WALL", "Gate A 不是 ABORT_NO_WALL，必须走另一分支"
assert g["gateA"]["machinePass"] is False, "机器判据成立时不得直接 ABORT"
assert g["bShouldRun"] is False and g["bActuallyRun"] is False, "B 组不得已跑"

# 磁盘硬核查：B / longcat 的 ab5 回执必须不存在
b_out = EV / "L2-deepseek-auto-2026-11-14.ab5-with-boundary.json"
longcat_a = EV / "L2-longcat-auto-2026-11-14.ab5-no-boundary.json"
longcat_b = EV / "L2-longcat-auto-2026-11-14.ab5-with-boundary.json"
not_created = {
    "bReceipt": {"file": b_out.name, "exists": b_out.exists()},
    "longcatAReceipt": {"file": longcat_a.name, "exists": longcat_a.exists()},
    "longcatBReceipt": {"file": longcat_b.name, "exists": longcat_b.exists()},
}
assert all(not x["exists"] for x in not_created.values()), "出现未授权的 B / longcat 真机回执"

progress_lines = [json.loads(x) for x in PROGRESS.read_text().splitlines() if x.strip()] if PROGRESS.exists() else []
events = [x.get("event") for x in progress_lines]

verdict = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "ab5-observe-first-final-verdict",
    "userMandate": {
        "verbatim": "解冻并按 observe-first gate 重跑（先跑 A 单轮，判无墙即停），而不是盲跑 4 轮；Gate A 判「墙不存在」→ ABORT_NO_WALL，N25 仍 open；仅当 Gate A 成立才跑 B 并按判据裁定",
        "date": "2026-11-14",
        "platformRuling": "用户 AskUserQuestion q-0 裁定首轮 = deepseek（见 ab5-gate-a-platform-ruling-2026-11-14.json）",
    },
    "code": "ABORT_NO_WALL",
    "gateA": g["gateA"],
    "observed": g["observed"],
    "visualObservation": {
        "kind": "nonMachineObservation",
        "participatesInMachineBoolean": False,
        "screenshot": "L2-deepseek-auto-2026-11-14.ab5-no-boundary.png",
        "readBy": "人工视觉巡检（ViewImage）",
        "lastAIReply": "正常中文长文本答案（AI 智能体定义与场景说明），不是站点报错",
        "siteErrorMessagePresent": False,
        "loginWallPresent": False,
        "captchaOrSliderPresent": False,
        "sidebarNewChatEntryVisible": True,
        "sidebarNote": "左栏可见「开启新对话」入口，但本轮是 no-boundary，未触发任何 NEW_SESSION；不得据此说 F2 在本轮真机生效",
        "conclusion": "截图与机器回执一致：A 组正常答完，无站点侧报错、无登录墙；本轮不构成 A 撞墙",
    },
    "abortBranch": {
        "executed": True,
        "bShouldRun": False,
        "bActuallyRun": False,
        "longcatActuallyRun": False,
        "roundsExecuted": 1,
        "roundsPlanned": 1,
        "messagesSent": "A 单轮 8 步 Pack",
        "diskCheck": not_created,
        "progressEvents": events,
        "stopReason": "Gate A 6 条机器判据中 C2/C3/C4 不成立（8/8 全成功、无失败步、step_8 11.7s 完成）",
    },
    "f1F2Attribution": {
        "f1RealMachineVerifiedThisRound": False,
        "f2RealMachineVerifiedThisRound": False,
        "note": "本轮 A 是 no-boundary，sessionResets=0，没有触发会话边界；不能用本轮回执新增任何 F1/F2 因果结论。既往 F1/F2 真机验证结论（§21/§23）保持原状，不翻案、不挪用。",
    },
    "propositionSupported": False,
    "boundaryIneffectiveClaimed": False,
    "n25": {
        "status": "remain open",
        "closedAt": None,
        "reason": "只有「A 撞墙且 B 通过」才支持命题；本轮 A 未撞墙且 B 未跑，无成对证据",
    },
    "attributionBoundaries": g["attributionBoundaries"],
    "evidence": {
        "precondition": PRECOND.name,
        "ruling": RULING.name,
        "precheck": PRECHECK.name,
        "runner": "ab5-observe-first-runner-2026-11-14.sh",
        "runnerLog": RUNLOG.name,
        "progress": PROGRESS.name,
        "verify": VERIFY.name,
        "receipt": RECEIPT.name,
        "receiptSha256": g["sourceReceiptSha256"],
        "gateAVerdict": GATE_A.name,
        "gateAVerdictScript": "ab5-gate-a-verdict-2026-11-14.py",
    },
    "authorizationTrace": {
        "platformPolicyUnfrozenBy": v.get("policyUnfrozenBy"),
        "precheckUnfrozenBoth": True,
        "whitelistCodeChanged": False,
        "usageRule": "逐次显式放行，用完仍是冻结；下次再跑须重新明确解冻",
    },
    "git": {"commitExecuted": False, "pushExecuted": False,
            "note": "提交 / push 用户明示单独授权，按「提交」与「文件集合」分别确认，本轮未碰 git"},
    "noFurtherRealMachineAction": True,
    "note": "本文件是只读合并裁定，不是 L2 回执。ABORT_NO_WALL 只表示『本轮墙不存在』，不表示边界有效/无效、不表示命题不成立、不表示 N25 可关闭。",
}
OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
print("WROTE", OUT.name)
print("code =", verdict["code"])
print("roundsExecuted =", verdict["abortBranch"]["roundsExecuted"])
print("bActuallyRun =", verdict["abortBranch"]["bActuallyRun"])
print("longcatActuallyRun =", verdict["abortBranch"]["longcatActuallyRun"])
print("notCreated =", json.dumps(not_created, ensure_ascii=False))
print("progressEvents =", events)
print("propositionSupported =", verdict["propositionSupported"])
print("n25 =", verdict["n25"]["status"])
