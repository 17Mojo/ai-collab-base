#!/usr/bin/env python3
"""ab4 第 4 轮补跑的**只读**收尾证据补齐。

背景：ab4-round4-rerun-2026-11-12.sh 的 verify 段有一个 bug
（把退出码字符串也转成 pathlib.Path，int(ec) 抛 TypeError），
导致进程假 EXIT=1、summary 未写、progress 缺 verify 行。
但 l2-platform-auto.mjs 自己已把第 4 轮回执即时落盘，回执有效。

⇒ 本脚本**不重跑真机**（不重复发送、不破坏 likeForLike、不覆盖任何证据），
   只从磁盘上的 4 份回执机械生成：
     - ab4-final-receipts-2026-11-12.json（4/4 状态与 likeForLike 间隔）
     - ab4-round4-summary-2026-11-12.json（补跑轮次的事实）
     - 向 ab4-round4-progress-2026-11-12.jsonl 追加一条
       source="post-hoc-readonly-finalize" 的 verify 行，明确标注是事后补齐，
       不冒充 runner 的即时记录。
原有的 ab4-runner-summary-2026-11-12.json 记的 allFourRoundsExecuted=false
是当时的真值，保留不覆盖。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = [
    "L2-deepseek-auto-2026-11-12.ab4-no-boundary.json",
    "L2-deepseek-auto-2026-11-12.ab4-with-boundary.json",
    "L2-longcat-auto-2026-11-12.ab4-no-boundary.json",
    "L2-longcat-auto-2026-11-12.ab4-with-boundary.json",
]


def brief(name):
    p = HERE / name
    if not p.exists():
        return {"receipt": name, "exists": False, "bytes": 0}
    d = json.loads(p.read_text(encoding="utf-8"))
    r = (d.get("exec") or {}).get("result") or {}
    steps = r.get("steps") or []
    resets = r.get("sessionResets") or []
    f = resets[0] if resets else None
    before = f.get("messageCountBefore") if isinstance(f, dict) else None
    after = f.get("messageCountAfter") if isinstance(f, dict) else None
    available = f.get("available") if isinstance(f, dict) else None
    return {
        "receipt": name,
        "exists": True,
        "bytes": p.stat().st_size,
        "generatedAt": d.get("generatedAt"),
        "packVariant": d.get("packVariant"),
        "unfrozenBy": (d.get("platformPolicy") or {}).get("unfrozenBy")
        if isinstance(d.get("platformPolicy"), dict) else None,
        "status": r.get("status"),
        "duration": r.get("duration"),
        "stepsTotal": len(steps),
        "stepSuccess": sum(1 for s in steps if s.get("success") is True),
        "sessionResets": len(resets),
        "resetAvailable": available,
        "resetStrategy": f.get("strategy") if isinstance(f, dict) else None,
        "messageCountBefore": before,
        "messageCountAfter": after,
        "resetActuallyHappened": bool(
            available is True and isinstance(before, int)
            and isinstance(after, int) and after < before
        ),
        "firstFailedStepId": next((s.get("id") for s in steps if s.get("success") is not True), None),
    }


items = [brief(n) for n in NAMES]
all_present = all(x["exists"] and x["bytes"] > 0 for x in items)
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# likeForLike：前 3 轮相邻，第 4 轮是补跑；间隔如实保留，绝不抹掉
def iso_ms(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat().replace("+00:00", "Z") if ts else None

a3 = json.loads((HERE / NAMES[2]).read_text(encoding="utf-8"))
a3_end = ((a3.get("exec") or {}).get("result") or {}).get("endTime")
b4 = json.loads((HERE / NAMES[3]).read_text(encoding="utf-8"))
b4_start = ((b4.get("exec") or {}).get("result") or {}).get("startTime")
gap_seconds = round((b4_start - a3_end) / 1000, 1) if (a3_end and b4_start) else None

final = {
    "generatedAt": now,
    "mode": "ab4-final-receipts-readonly-finalize",
    "allFourRoundsExecuted": all_present,
    "runnerSummaryAtTheTime": "ab4-runner-summary-2026-11-12.json",
    "runnerSummaryAllFourAtTheTime": False,
    "runnerSummaryNote": "runner 收尾时第 4 轮回执尚未落盘，allFourRoundsExecuted=false 是当时的真值，保留不覆盖。",
    "round4Rerun": "ab4-round4-rerun-2026-11-12.sh",
    "round4RerunBug": "verify 段 int(ec) 把退出码误转 Path ⇒ 进程假 EXIT=1、summary/verify 行缺失；回执由驱动自身即时落盘，有效。",
    "safeDeleteShimDisabled": False,
    "realMachineRerunAfterBug": False,
    "likeForLike": {
        "round3EndTime": iso_ms(a3_end),
        "round4StartTime": iso_ms(b4_start),
        "gapSeconds": gap_seconds,
        "note": "第 4 轮为独立补跑，与第 3 轮不相邻；时间窗缺口如实保留，不得抹掉。",
    },
    "rounds": items,
    "note": "4/4 回执齐备只表示真机执行完整，不代表 A/B 判据成立；裁定由 ab4-verdict-2026-11-12.py 机械推导。",
}
(HERE / "ab4-final-receipts-2026-11-12.json").write_text(
    json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

r4 = items[3]
r4_summary = {
    "generatedAt": now,
    "runner": "ab4-round4-rerun-2026-11-12.sh",
    "receipt": NAMES[3],
    "receiptExists": r4["exists"],
    "nodeExit": 0,
    "nodeExitSource": "ab4-round4-2026-11-12.log 的 ROUND 4/4 RERUN NODE_EXIT=0",
    "processExitWas": 1,
    "processExitReason": "verify 段 TypeError（收尾脚本 bug），非真机执行失败",
    "likeForLikeNote": "补跑与第 3 轮结束不在相邻时间窗；间隔如实保留。",
    "safeDeleteShimDisabled": False,
    "verify": r4,
    "finalizeSource": "ab4-finalize-2026-11-12.py（只读补齐，不重跑真机、不覆盖证据）",
}
(HERE / "ab4-round4-summary-2026-11-12.json").write_text(
    json.dumps(r4_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

verify_line = {
    "t": now,
    "event": "verify",
    "round": "4-rerun-post-hoc",
    "source": "post-hoc-readonly-finalize",
    "note": "runner 的即时 verify 因收尾脚本 bug 缺失；本行是事后只读补齐，不冒充即时记录。",
    **r4,
}
with (HERE / "ab4-round4-progress-2026-11-12.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(verify_line, ensure_ascii=False) + "\n")

print(json.dumps({
    "allFourRoundsExecuted": all_present,
    "gapSeconds": gap_seconds,
    "round4Reset": {"available": r4["resetAvailable"], "strategy": r4["resetStrategy"],
                    "before": r4["messageCountBefore"], "after": r4["messageCountAfter"]},
    "written": ["ab4-final-receipts-2026-11-12.json", "ab4-round4-summary-2026-11-12.json"],
    "realMachineRerunAfterBug": False,
}, ensure_ascii=False, indent=2))
