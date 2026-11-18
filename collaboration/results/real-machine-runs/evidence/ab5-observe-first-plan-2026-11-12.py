#!/usr/bin/env python3
"""生成 plan-only 的「观测先行」A/B 方案（ab5），不执行任何真机动作。

为什么不是「再盲跑 4 轮」：wall-observability-diagnosis-2026-11-12.json 证明
命题的自变量（长会话撞墙）在 F1 修复后不可控、不复现。盲跑 4 轮大概率仍是
NO_WALL_THIS_ROUND 或站点随机报错，白耗约 30 分钟与 32 步额度。

改成观测先行：先只跑 A 组单轮做 gate，机器判「A 真的在 step_8_output 撞墙」
才允许跑同站 B；否则立刻停，把「本轮墙不存在」记成证据，不跑 B。

本脚本只写一份 JSON 计划，带硬性自检；status 恒为 plan-only / NOT-EXECUTED。
"""
import json
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "ab5-observe-first-plan-2026-11-12.json"
DIAG = HERE / "wall-observability-diagnosis-2026-11-12.json"
DIST_EV = HERE / "dist-consistency-2026-11-12.deepseek-newchat.json"
AB4_VERDICT = HERE / "ab4-verdict-2026-11-12.json"

PACK_A = "ab-pack-2026-11-11.no-boundary.json"
PACK_B = "ab-pack-2026-11-11.with-boundary.json"
PACK_A_SHA = "89b197cf99f2fcac835bc78269f89315a9740bfe57222da207d5851796692d03"
PACK_B_SHA = "0e1b4b9816545e52e74abaee117d96fba3b449cfa5a71c5370a0e22b2516f46f"

plan = {
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mode": "ab5-observe-first-plan",
    "status": "plan-only / NOT-EXECUTED",
    "proposition": "fresh_session 会话边界能解掉 deepseek / longcat 的 step_8 长会话撞墙",
    "whyNotBlindRerun": {
        "diagnosis": "wall-observability-diagnosis-2026-11-12.json",
        "code": "PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE",
        "summary": "F1 修复后 deepseek 4 轮 step_8 全在 12.3–13.6s 成功；longcat 失败步在 step_3/4/6/8 漂移且截图同型站点报错 ⇒ 墙不复现、自变量不可控。",
        "costSaved": "gateA 不通过时只跑 1 轮而不是 4 轮（约省 3/4 的站点额度与时间）",
    },
    "gateA": {
        "description": "先只跑 A 组（no-boundary）单轮，机器判『A 真的在 step_8_output 撞墙』",
        "machineCriteria": {
            "stepsTotal": "== 8",
            "stepSuccess": "== 7",
            "firstFailedStepId": "== 'step_8_output'",
            "failedStepError": "包含 'Response timeout'",
            "earlierStepsAllSucceeded": "前 7 步全部 success===true（排除站点提前挂掉）",
            "noBoundaryDeclared": "A 组 sessionResets 必须为空；非空说明变体用错",
        },
        "visualGate": {
            "required": True,
            "note": "截图人工视觉判读必须确认末条 AI 回复不是『服务出错啦，请稍后再试。』；这是 nonMachineObservation，不参与机器布尔推导，但 gate 放行必须由人确认。",
        },
        "onFalse": {
            "code": "ABORT_NO_WALL",
            "action": "不跑 B，落盘『本轮墙不存在』证据，N25 保持 open；不得说边界有效/无效。",
        },
        "onTrue": {
            "action": "立即跑同站 B 组（with-boundary），A/B 间隔目标 ≤ 5 分钟并如实记录实际秒数。",
        },
    },
    "bCriteria": {
        "hard": "sessionResets[0].available===true && messageCountAfter<messageCountBefore",
        "passed": "hard 成立 && 8/8 steps success && exec.success===true && status==='completed'",
        "onHardFalse": "该轮作废 / 本轮不可评估；不得包装成「边界无效」",
        "onBoundaryNotAttempted": "sessionResets 为空 ⇒ 本轮不可评估",
    },
    "verdictRule": {
        "supportsProposition": "gateA.passed && gateA.visualConfirmed && bCriteria.passed",
        "onlyThen": "只有「A 撞墙且 B 通过」才支持命题；A/B 都通过 ⇒ 本轮墙不存在；A 在 step_8 之前失败 ⇒ 有混杂变量、不可评估。",
        "n25": "判据成立前保持 open；成立也只是具备关闭条件，关闭由用户裁定。",
    },
    "hardConstraints": [
        "不得改 Pack：A/B 只允许差 fresh_session 一个变量，两个变体 Pack 的 sha256 必须保持不变。",
        "A/B 同 dist、同账号态、同 prompt、相邻时间窗；dist hash 必须与 dist-consistency-2026-11-12.deepseek-newchat.json 一致。",
        "冻结白名单代码不得改；每条命令逐次 ALLOW_FROZEN=1，放行写进回执 platformPolicy 留痕；用完仍是冻结。",
        "预检 PRECHECK=1 也要显式 ALLOW_FROZEN=1 与 CANDIDATES=deepseek,longcat。",
        "stdout 全程 tee -a；每轮 start / node-exit / verify 即时写 append-only JSONL；回执由驱动自身即时落盘。",
        "不设置 CODEBUDDY_SAFE_DELETE_ENABLED=0 绕过 safe-delete shim；若被拦，单轮独立补跑并留痕。",
        "OUT 用新的 *.ab5-* 前缀，前置检查 .json/.png 全空，不覆盖任何既有证据。",
        "runner 结尾必须逐份核 ALL_RECEIPTS_PRESENT，RUNNER_FINISHED 不等于四轮都跑完。",
        "提交 / push 单独授权，按提交与文件集合分清。",
    ],
    "preconditions": [
        "用户给出明确解冻指令（点名 deepseek / longcat + 允许范围）——当前未满足",
        "PRECHECK=1 两站 composerVisible=true / looksLikeLogin=false",
        "dist 产物 sha256 与 DIST_EV 一致；两个变体 Pack sha256 与计划一致",
        "SW 缓存三个目录条目数低于 shim 阈值（否则单轮补跑）",
        "目标 OUT 路径（.json/.png）全部为空",
    ],
    "packs": [
        {"variant": "no-boundary", "file": PACK_A, "sha256": PACK_A_SHA},
        {"variant": "with-boundary", "file": PACK_B, "sha256": PACK_B_SHA},
    ],
    "evidence": {
        "diagnosis": "wall-observability-diagnosis-2026-11-12.json",
        "previousVerdict": "ab4-verdict-2026-11-12.json",
        "distConsistency": "dist-consistency-2026-11-12.deepseek-newchat.json",
        "offlineScriptVerify": "offline-verify-ab4-round4-fix-2026-11-12.json",
    },
    "attributionBoundaries": [
        "不能说会话边界解掉 step_8 撞墙，也没有依据说边界无效。",
        "不能把 A/B 都通过归功边界；不能把 F1 / F2 真机成功挪用为因果证据。",
        "不能说重置免费或把耗时差异归因给重置；不能说长会话撞墙已根治。",
        "站点侧报错是外部混杂变量，必须单独标注，不得与「墙」合并归因。",
    ],
    "noRealMachineAction": True,
    "gitUnchanged": True,
    "note": "本文件是计划，不是回执。任何真机执行都必须先取得用户明确解冻授权。",
}

# ── 硬性自检：计划不许冒充回执，判据不许与既有裁定冲突 ──────────
errors = []
if plan["status"] != "plan-only / NOT-EXECUTED":
    errors.append("status 必须是 plan-only")
if plan["noRealMachineAction"] is not True:
    errors.append("noRealMachineAction 必须为 true")
for p in [PACK_A, PACK_B]:
    if not (HERE / p).exists():
        errors.append("变体 Pack 不存在: " + p)
for f in [DIAG, DIST_EV, AB4_VERDICT]:
    if not f.exists():
        errors.append("引用证据不存在: " + f.name)
else:
    if DIST_EV.exists():
        d = json.loads(DIST_EV.read_text(encoding="utf-8"))
        if not (d.get("allPass") and d.get("idempotent")):
            errors.append("dist 一致性证据未通过")
    if AB4_VERDICT.exists():
        v = json.loads(AB4_VERDICT.read_text(encoding="utf-8"))
        if v.get("propositionSupported") is not False:
            errors.append("与 ab4 裁定冲突：命题当前仍不支持")
        if "sessionResets[0].available===true" not in v.get("bHardCriteria", ""):
            errors.append("B 组硬判据与既有裁定不一致")
import hashlib
for item in plan["packs"]:
    h = hashlib.sha256((HERE / item["file"]).read_bytes()).hexdigest() if (HERE / item["file"]).exists() else None
    if h != item["sha256"]:
        errors.append("Pack hash 不符: " + item["variant"])

plan["selfCheck"] = {
    "pass": len(errors) == 0,
    "errors": errors,
    "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "note": "自检只核计划内部一致性与引用证据存在，不启动浏览器、不产生回执。",
}
OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "written": str(OUT),
    "status": plan["status"],
    "selfCheckPass": plan["selfCheck"]["pass"],
    "errors": errors,
    "noRealMachineAction": True,
}, ensure_ascii=False, indent=2))
sys.exit(0 if plan["selfCheck"]["pass"] else 1)
