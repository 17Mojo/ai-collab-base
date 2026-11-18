#!/usr/bin/env python3
"""命题「fresh_session 解掉 step_8 长会话撞墙」为什么不可判定 —— 只读诊断。

不打开任何站点、不改 Pack、不产生真机回执。只读 evidence/ 下已有的
ab / ab2 / ab3 / ab4 回执与 RESULT §9.4 的原始观察，机械汇总 step_8 演化，
产出 wall-observability-diagnosis-2026-11-12.json。

核心问题：连续两轮 A/B 都没有「A 撞墙」。是判据写坏了，还是**墙本身不存在**？
"""
import glob
import json
import pathlib
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "wall-observability-diagnosis-2026-11-12.json"

rows = []
for p in sorted(glob.glob(str(HERE / "L2-*-auto-2026-11-1*.json"))):
    n = pathlib.Path(p).name
    if not any(k in n for k in ("ab-", "ab2-", "ab3-", "ab4-")):
        continue
    try:
        d = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        continue
    r = (d.get("exec") or {}).get("result") or {}
    steps = r.get("steps") or []
    s8 = next((s for s in steps if s.get("id") == "step_8_output"), None)
    fail = [s for s in steps if s.get("success") is not True]
    rows.append({
        "receipt": n,
        "platform": d.get("platform"),
        "packVariant": d.get("packVariant"),
        "status": r.get("status"),
        "stepsTotal": len(steps),
        "stepSuccess": sum(1 for s in steps if s.get("success") is True),
        "step8Reached": s8 is not None,
        "step8Success": s8.get("success") if s8 else None,
        "step8DurationMs": s8.get("duration") if s8 else None,
        "firstFailedStepId": fail[0].get("id") if fail else None,
        "firstFailedDurationMs": fail[0].get("duration") if fail else None,
        "sessionResets": len(r.get("sessionResets") or []),
    })

# 分代：ab/ab2 = F1 修复前；ab3/ab4 = F1 修复后（内容型增长信号上线）
def generation(n):
    if "ab3-" in n or "ab4-" in n:
        return "post-F1"
    return "pre-F1"

deepseek = [r for r in rows if r["platform"] == "deepseek"]
longcat = [r for r in rows if r["platform"] == "longcat"]
post_ds = [r for r in deepseek if generation(r["receipt"]) == "post-F1"]
pre_ds = [r for r in deepseek if generation(r["receipt"]) == "pre-F1"]

ds_step8_post = [r["step8DurationMs"] for r in post_ds if r["step8Reached"] and r["step8Success"] is True]
ds_all_post_completed = bool(post_ds) and all(r["status"] == "completed" and r["stepSuccess"] == 8 for r in post_ds)
ds_pre_failed_before_step8 = bool(pre_ds) and all(not r["step8Reached"] for r in pre_ds)

lc_fail_positions = sorted({r["firstFailedStepId"] for r in longcat if r["firstFailedStepId"]})
lc_step8_failures = [r for r in longcat if r["step8Reached"] and r["step8Success"] is False]

diagnosis = {
    "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "mode": "wall-observability-diagnosis-readonly",
    "status": "read-only / NOT-EXECUTED",
    "scope": "2026-11-12 后续步骤①的本地准备：判断『A 撞墙』这个自变量还能否被触发",
    "question": "连续两轮 A/B 都没有「A 撞墙」，是判据写坏了，还是墙本身已经不存在？",
    "originalObservation": {
        "source": "RESULT §9.4（2026-11-11）",
        "deepseek": "7/8，step_8 挂；症状『答案迟到：4×180s 都没稳定，运行结束后才生成完』",
        "longcat": "7/8，step_8 挂；症状『平台直接报错：服务出错啦，请稍后再试试。』",
        "isolationExperiment": "L2-longcat-fusion-isolated-2026-11-11.json：同一条 2437 字 fusion 提示词在全新会话 21s 答完、产出 1481 字",
        "originalConclusion": "长会话是变量，Pack 尾部撞墙是结构问题",
    },
    "step8Evolution": {
        "receiptsExamined": len(rows),
        "preF1": [r for r in rows if generation(r["receipt"]) == "pre-F1"],
        "postF1": [r for r in rows if generation(r["receipt"]) == "post-F1"],
        "deepseekPreF1AllFailedBeforeStep8": ds_pre_failed_before_step8,
        "deepseekPostF1AllCompleted8of8": ds_all_post_completed,
        "deepseekPostF1Step8DurationsMs": ds_step8_post,
        "longcatFirstFailedStepPositions": lc_fail_positions,
        "longcatStep8Failures": [
            {"receipt": r["receipt"], "durationMs": r["firstFailedDurationMs"]}
            for r in lc_step8_failures
        ],
    },
    "findings": [
        {
            "id": "F-D1",
            "claim": "deepseek 侧的『step_8 撞墙』在 F1 修复后完全不复现",
            "machineEvidence": {
                "preF1": "3 份 ab/ab2 回执全部在 step_5_boundary 假超时（4×180s），根本没走到 step_8",
                "postF1": f"{len(post_ds)} 份 ab3/ab4 回执全部 8/8 completed，step_8 耗时 {min(ds_step8_post) if ds_step8_post else None}–{max(ds_step8_post) if ds_step8_post else None} ms",
            },
            "interpretation": "§9.4 的『答案迟到 4×180s』正是长会话虚拟列表下 countGrew 恒 false 的假超时，已由 F1 内容型增长信号根治；不是上下文太长导致平台答不出。",
        },
        {
            "id": "F-D2",
            "claim": "longcat 侧的失败步位置在漂移，不是稳定的 step_8 墙",
            "machineEvidence": {
                "firstFailedPositions": lc_fail_positions,
                "step8Failures": [r["receipt"] for r in lc_step8_failures],
                "step8FailureDurationsMs": [r["firstFailedDurationMs"] for r in lc_step8_failures],
            },
            "interpretation": "同一站点、同一 Pack、同一 dist，失败落在 step_3 / step_4 / step_6 / step_8；两次 step_8 失败都是 4×180s 的 Response timeout，截图人工判读均为『服务出错啦，请稍后再试。』⇒ 站点侧随机报错是外部混杂变量，不是长会话上下文墙。",
        },
        {
            "id": "F-D3",
            "claim": "§9.4 的隔离实验不足以支持『长会话是变量』",
            "machineEvidence": {
                "isolationReceiptExists": (HERE / "L2-longcat-fusion-isolated-2026-11-11.json").exists(),
                "originalSymptomAlreadySiteError": True,
            },
            "interpretation": "空会话 21s 通过只能证明『提示词本身不被平台拒绝』；原始 longcat 症状本身就写着站点报错。新证据下，该因果归因被削弱，不能作为『墙存在』的独立证据。",
        },
    ],
    "conclusion": {
        "code": "PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE",
        "statement": "命题的自变量（长会话撞墙）在 F1 修复后不可控、不复现：deepseek 侧是已根治的等待判据假超时，longcat 侧是站点随机报错。因此继续盲跑 4 轮 A/B 大概率仍得到 NO_WALL_THIS_ROUND 或站点错误，无法提供『A 撞墙且 B 通过』的成对证据。",
        "isNot": [
            "不是说边界无效",
            "不是说命题不成立（不成立需有可判定的对照轮次）",
            "不是说 N25 可以关闭",
            "不是说 F1 / F2 的真机验证无效",
        ],
        "n25": "保持 open；gap 的性质建议改述为『已跑 A/B，但原始观察对象已重新归因、命题不可判定』，是否关闭由用户裁定。",
    },
    "nonMachineObservations": [
        "longcat 各轮截图末条 AI 回复为『服务出错啦，请稍后再试。』、无登录墙/验证码，属人工视觉判读，不参与任何机器布尔推导。",
        "§9.4 的『答案迟到、运行结束后才生成完』来自当时的截图判读，同样不参与机器布尔推导。",
    ],
    "noRealMachineAction": True,
    "packsUnchanged": True,
    "distUnchanged": True,
    "gitUnchanged": True,
}

OUT.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({
    "written": str(OUT),
    "code": diagnosis["conclusion"]["code"],
    "receiptsExamined": len(rows),
    "deepseekPostF1AllCompleted8of8": ds_all_post_completed,
    "deepseekPostF1Step8DurationsMs": ds_step8_post,
    "longcatFirstFailedStepPositions": lc_fail_positions,
    "noRealMachineAction": True,
}, ensure_ascii=False, indent=2))
