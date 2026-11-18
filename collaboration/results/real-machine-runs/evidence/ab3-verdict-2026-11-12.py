#!/usr/bin/env python3
"""
ab3 四轮 A/B 机器裁定生成器（2026-11-12）

只读 4 份真机回执，按 session-wall-ab-plan-2026-11-11.json 的验收判据
机械计算，产出 evidence/ab3-verdict-2026-11-12.json。

判据（用户 2026-11-11 明确，计划文件 acceptance 字段）：
  packCompleted        : exec.success===true && status===completed && 8/8
  resetActuallyHappened: B 组 sessionResets[0].available===true
                          && messageCountAfter < messageCountBefore
  verdictRule          : 只有「A 撞墙且 B 通过」才支持命题
                         A/B 都通过 ⇒ 本轮墙不存在，不能归功边界
                         A/B 都撞墙 ⇒ 另找根因，不能包装成「边界无效」
  补充裁定（用户 2026-11-12）：
    B 组边界压根没执行 / available:false ⇒ 明写「本轮不可评估 / 该轮作废」

不做任何人工判断：所有布尔值直接从回执字段推导；回执缺失即 exists=false。
"""
import hashlib
import json
import pathlib
import datetime

E = pathlib.Path(__file__).resolve().parent
REPO = E.parents[3]

ROUNDS = {
    "deepseek": {
        "A": "L2-deepseek-auto-2026-11-12.ab3-no-boundary.json",
        "B": "L2-deepseek-auto-2026-11-12.ab3-with-boundary.json",
    },
    "longcat": {
        "A": "L2-longcat-auto-2026-11-12.ab3-no-boundary.json",
        "B": "L2-longcat-auto-2026-11-12.ab3-with-boundary.json",
    },
}


def read_round(path):
    p = E / path
    rec = {
        "file": path,
        "exists": p.exists(),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
        "generatedAt": None,
        "variant": None,
        "unfrozenBy": None,
        "execSuccess": None,
        "resultStatus": None,
        "stepsTotal": 0,
        "stepsPassed": 0,
        "duration": None,
        "failedAt": [],
        "failedStepDuration": [],
        "failedStepErrors": [],
        "sessionResets": [],
        "boundaryStepReached": False,
    }
    if not p.exists():
        return rec
    d = json.loads(p.read_text())
    ex = d.get("exec") or {}
    r = ex.get("result") or {}
    steps = r.get("steps") or []
    pp = d.get("platformPolicy")
    rec.update({
        "generatedAt": d.get("generatedAt"),
        "variant": d.get("packVariant"),
        "unfrozenBy": pp.get("unfrozenBy") if isinstance(pp, dict) else None,
        "execSuccess": ex.get("success"),
        "resultStatus": r.get("status"),
        "stepsTotal": len(steps),
        "stepsPassed": sum(1 for s in steps if s.get("success") is True),
        "duration": r.get("duration"),
        "failedAt": [s.get("id") for s in steps if s.get("success") is not True],
        "failedStepDuration": [s.get("duration") for s in steps if s.get("success") is not True],
        "failedStepErrors": [s.get("error") for s in steps if s.get("success") is not True],
        "sessionResets": r.get("sessionResets") or [],
        # step_8_output 是边界声明所在步；出现在 steps 里才算「到达」
        "boundaryStepReached": any(s.get("id") == "step_8_output" for s in steps),
    })
    return rec


def completed_8of8(rec):
    return (
        rec["exists"]
        and rec["execSuccess"] is True
        and rec["resultStatus"] == "completed"
        and rec["stepsTotal"] == 8
        and rec["stepsPassed"] == 8
    )


def reset_happened(rec):
    rs = rec["sessionResets"]
    if not rs:
        return False
    r0 = rs[0]
    before = r0.get("messageCountBefore")
    after = r0.get("messageCountAfter")
    return (
        r0.get("available") is True
        and isinstance(before, int)
        and isinstance(after, int)
        and after < before
    )


def classify(a, b):
    """返回 (roundStatus, why, machineChecks, reasons)。机械推导，不写死结论。"""
    a_pass = completed_8of8(a)
    b_pass = completed_8of8(b)
    a_wall = a["exists"] and not a_pass  # A 没跑完即视为「撞墙」候选
    a_wall_at_boundary = (
        a_wall and "step_8_output" in a["failedAt"]
    )
    b_reset = reset_happened(b)
    b_boundary_attempted = b["exists"] and len(b["sessionResets"]) > 0
    checks = {
        "aExists": a["exists"],
        "bExists": b["exists"],
        "aPassed8of8": a_pass,
        "bPassed8of8": b_pass,
        "aHitWall": a_wall,
        "aHitWallAtBoundaryStep": a_wall_at_boundary,
        "aBoundaryStepReached": a["boundaryStepReached"],
        "bBoundaryStepReached": b["boundaryStepReached"],
        "bBoundaryAttempted": b_boundary_attempted,
        "bResetActuallyHappened": b_reset,
        "bRoundUsable": b_pass and b_reset,
        "supportsProposition": a_wall and b_pass and b_reset,
        "bothPassed": a_pass and b_pass,
    }
    if not b["exists"]:
        why = "B 组回执不存在：本轮未执行，不可评估"
        return "ROUND_NOT_EXECUTED", why, checks, [why]
    if not a["exists"]:
        why = "A 组回执不存在：本轮未执行，不可评估"
        return "ROUND_NOT_EXECUTED", why, checks, [why]
    reasons = []
    if a_pass and b_pass:
        reasons.append("A/B 都 8/8 通过 ⇒ 本轮墙不存在，不能把 B 的通过归功于会话边界")
    if not b_boundary_attempted:
        reasons.append("B 组 sessionResets 为空：边界步骤从未到达或未尝试，本轮不可评估，不能归功边界，也不能说边界无效")
    elif not b_reset:
        r0 = b["sessionResets"][0]
        reasons.append(
            "B 组 sessionResets[0].available=%r / strategy=%r / %r→%r，"
            "按判据该轮作废（prefer 降级照发不等于开了新会话）"
            % (
                r0.get("available"), r0.get("strategy"),
                r0.get("messageCountBefore"), r0.get("messageCountAfter"),
            )
        )
    if not a_pass and not b_pass:
        reasons.append("A/B 都没跑完，不能把「都失败」包装成「边界无效」")

    # 主状态取最根本的一条：A/B 都通过时，「本轮墙不存在」优先于边界是否执行。
    if a_pass and b_pass:
        status = "NO_WALL_THIS_ROUND"
    elif not b_boundary_attempted:
        status = "BOUNDARY_NEVER_ATTEMPTED"
    elif not b_reset:
        status = "INVALID_ROUND_RESET_UNAVAILABLE"
    elif checks["supportsProposition"]:
        status = "SUPPORTS"
    else:
        status = "NOT_SUPPORTS"
    return status, "；".join(reasons) if reasons else "判据未成立", checks, reasons


def main():
    rounds = {
        plat: {arm: read_round(fn) for arm, fn in arms.items()}
        for plat, arms in ROUNDS.items()
    }
    out_platforms = {}
    for plat, arms in rounds.items():
        status, why, checks, reasons = classify(arms["A"], arms["B"])
        out_platforms[plat] = {**arms, "machineChecks": checks,
                               "roundStatus": status, "why": why,
                               "reasons": reasons}

    any_supports = any(
        p["machineChecks"]["supportsProposition"] for p in out_platforms.values()
    )
    all_rounds_executed = all(
        r["exists"] for p in rounds.values() for r in p.values()
    )
    all_boundaries_executed = all(
        reset_happened(p["B"]) for p in rounds.values()
    )

    # F1 修复是否在真机上生效：旧指纹是 4×180s=720s 级假超时；
    # 新 dist 下只要出现 8/8 completed 或 AI 步骤在 <60s 内连续成功即算有证据。
    f1_evidence = []
    for plat, arms in rounds.items():
        for arm, r in arms.items():
            if not r["exists"]:
                continue
            ai_steps = [
                s for s in (r["failedStepDuration"] or []) if isinstance(s, int)
            ]
            if completed_8of8(r):
                f1_evidence.append(f"{plat}/{arm}: 8/8 completed，duration={r['duration']}ms")
            elif r["stepsPassed"] >= 4:
                f1_evidence.append(
                    f"{plat}/{arm}: 前 {r['stepsPassed']} 步成功，失败于 "
                    f"{r['failedAt']}，失败步骤耗时 {ai_steps}ms"
                )
    f1_real_machine_verified = any(
        "8/8 completed" in x for x in f1_evidence
    )

    code = (
        "PROPOSITION_SUPPORTED" if any_supports
        else "PROPOSITION_NOT_SUPPORTED"
    )
    must_not_claim = [
        "不能说会话边界解掉了 step_8 撞墙（没有「A 撞墙且 B 通过」的成对证据）",
        "不能说边界无效（B 组边界多次未真正执行，不可用「都失败」反推无效）",
        "不能把 B 组「prefer 降级照发」当成「开了新会话」",
        "不能说重置免费，也不能把耗时差异归因给重置（§14.4 继续有效）",
        "不能把 F1 等待判据修复在真机上的成功归因给会话边界（两者是不同变量）",
    ]

    verdict = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "machine-verdict",
        "subject": "N25 A/B 会话墙验证 / ab3 四轮（修复后 dist）",
        "evidenceSet": "ab3 / 2026-11-12",
        "acceptance": {
            "packCompleted": "exec.success===true && status===completed && 8/8",
            "resetActuallyHappened": "B 组 sessionResets[0].available===true && messageCountAfter<messageCountBefore",
            "verdictRule": "只有 A 撞墙且 B 通过才支持命题；A/B 都通过=本轮墙不存在不能归功边界；A/B 都撞墙=另找根因",
            "unusableRule": "B 组边界未执行 / available:false ⇒ 明写本轮不可评估或该轮作废",
        },
        "platforms": out_platforms,
        "crossRound": {
            "allFourRoundsExecuted": all_rounds_executed,
            "allBoundariesActuallyExecuted": all_boundaries_executed,
            "f1WaitPolicyFixRealMachineEvidence": f1_evidence,
            "f1RealMachineVerified": f1_real_machine_verified,
            "note": "f1RealMachineVerified 只说明公共等待判据修复在真机上生效，"
                    "与「会话边界解掉撞墙」是两条独立命题，不得互相替代",
        },
        # 明确标注为「非机器判定」：截图需人工视觉判读，不参与上面任何布尔推导。
        "nonMachineObservations": {
            "label": "人工视觉巡检，仅供归因参考，不参与机器裁定",
            "items": [
                "longcat A 截图 L2-longcat-auto-2026-11-12.ab3-no-boundary.png："
                "最后一条 AI 回复为「服务出错啦，请稍后再试。」，非长会话回答，"
                "无登录墙/验证码；输入框可用。⇒ step_6 失败属站点侧错误，"
                "不是 step_8 长会话撞墙，也不是等待判据假超时。",
                "longcat B 截图 L2-longcat-auto-2026-11-12.ab3-with-boundary.png："
                "同一句「服务出错啦，请稍后再试。」，左栏「开启新对话」入口可见。"
                "⇒ step_4 失败同属站点侧错误；F2 的 newChat 选择器本轮仍未被触发验证。",
            ],
        },
        "verdict": {
            "code": code,
            "propositionSupported": any_supports,
            "n25": "remain open" if not any_supports else "eligible to close after review",
            "mustNotClaim": must_not_claim,
        },
    }

    target = E / "ab3-verdict-2026-11-12.json"
    if target.exists():
        # N22 教训：默认绝不静默覆盖。只有显式 --regenerate 才允许，
        # 且把「为什么重生成」写进产物，避免两份裁定看起来像不同结论。
        import sys
        if "--regenerate" not in sys.argv:
            raise SystemExit("裁定文件已存在，拒绝覆盖（如需重生成请显式 --regenerate）: " + str(target))
        old = json.loads(target.read_text())
        if old.get("mode") != "machine-verdict":
            raise SystemExit("已有文件不是机器裁定，拒绝覆盖: " + str(target))
        verdict["regeneratedFrom"] = {
            "previousGeneratedAt": old.get("generatedAt"),
            "previousVerdictCode": (old.get("verdict") or {}).get("code"),
            "reason": "初版 classify() 把 deepseek 标成 INVALID_ROUND_RESET_UNAVAILABLE，"
                      "埋没了更根本的 A/B 都 8/8 通过（本轮墙不存在）；"
                      "改为并列 reasons + 主状态 NO_WALL_THIS_ROUND。"
                      "底层布尔判据与最终 code 均未改变，仍是 PROPOSITION_NOT_SUPPORTED。",
        }
    target.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
    print("VERDICT_WRITTEN", target.name)
    print("code =", code)
    for plat, p in out_platforms.items():
        print(" ", plat, p["roundStatus"], "|", p["why"])
        print("    A:", p["A"]["exists"], p["A"]["stepsPassed"], "/", p["A"]["stepsTotal"],
              "B:", p["B"]["exists"], p["B"]["stepsPassed"], "/", p["B"]["stepsTotal"],
              "reset:", p["B"]["sessionResets"][:1])
    print("allFourRoundsExecuted =", all_rounds_executed)
    print("f1RealMachineVerified =", f1_real_machine_verified)


if __name__ == "__main__":
    main()
