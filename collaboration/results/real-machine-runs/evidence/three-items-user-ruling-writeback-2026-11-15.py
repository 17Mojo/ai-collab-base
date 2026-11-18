#!/usr/bin/env python3
"""用户四项裁定写回（2026-11-15）：①不跑真机 ②暂不提交 ③暂不 push ④不重开 N25。

只回写证据与报告，不执行任何被否定的动作。
"""
import json
import pathlib
import datetime

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EVID = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
LOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-15.md")

ruling = {
    "mode": "three-items-user-ruling-2026-11-15",
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "source": "AskUserQuestion 2026-11-15 四问四答",
    "answers": {
        "q0_realMachine": "不跑真机（推荐）",
        "q1_commit": "暂不提交（推荐）",
        "q2_push": "暂不 push（推荐）",
        "q3_reopenN25": "不重开（推荐）",
    },
    "effectiveRulings": [
        {
            "item": "① 要跑真机",
            "code": "NO_REAL_MACHINE_THIS_TURN",
            "detail": "冻结站 deepseek / longcat 保持冻结；本轮不解冻、不预检、不打开冻结站、不发消息、不产生真机回执；realMachineRounds=0；ALLOW_FROZEN=1 未出现在本轮任何命令中。",
        },
        {
            "item": "② 要提交",
            "code": "NO_COMMIT_NO_STAGE",
            "detail": "提交动作与文件集合均未授权；145 项全留工作区；不 commit / 不 stage / 不 add；staged 保持 0。",
        },
        {
            "item": "③ 要 push",
            "code": "NO_PUSH_NO_DIVERGENCE_HANDLING",
            "detail": "不 fetch / 不 pull / 不 merge / 不 rebase / 不 push；behind=33 保持不动；origin/main=915c350 的外部推进只做只读登记。",
        },
        {
            "item": "N25 重开",
            "code": "N25_REMAINS_CLOSED",
            "detail": "保持 status=closed / closed_at=2026-11-15 / 43 条证据 / closure 原样保留；不新增 reopen 字段，不改台账。",
        },
    ],
    "scope": {
        "thisTurnOnly": True,
        "notAuthorizationForFutureTurns": True,
        "note": "四项裁定只对本轮生效；后续如需真机 / 提交 / push / 重开，须重新逐项显式授权。",
    },
    "unchanged": {
        "git": True,
        "sourceOrTests": True,
        "dist": True,
        "variantPacks": True,
        "knownGaps": True,
        "n25": True,
        "frozenPlatforms": True,
    },
    "stillValid": [
        "只有『A 撞墙且 B 通过』才支持命题",
        "B 组 available===true && messageCountAfter<Before；边界未执行或 available:false ⇒ 该轮作废 / 本轮不可评估",
        "observe-first Gate A 判无墙即 ABORT_NO_WALL",
        "机器裁定 + 磁盘真证；人工视觉判读单列",
        "提交 / push 按『提交动作』与『文件集合』分别确认；push 另需单独授权分歧处理",
    ],
}
(EVID / "three-items-user-ruling-2026-11-15.json").write_text(
    json.dumps(ruling, ensure_ascii=False, indent=2) + "\n")

section = """
### 28.10 用户四项裁定（`three-items-user-ruling-2026-11-15.json`）

`AskUserQuestion` 四问四答：q-0 **不跑真机**、q-1 **暂不提交**、q-2 **暂不 push**、q-3 **不重开 N25**。据此：

| 条目 | 裁定码 | 实际动作 |
|---|---|---|
| ① 真机 | `NO_REAL_MACHINE_THIS_TURN` | 不解冻、不预检、不打开冻结站、不发消息；`realMachineRounds=0`，本轮任何命令都未出现 `ALLOW_FROZEN=1` |
| ② 提交 | `NO_COMMIT_NO_STAGE` | 145 项全留工作区，`staged` 保持 0；不 commit / stage / add |
| ③ push | `NO_PUSH_NO_DIVERGENCE_HANDLING` | 不 fetch / pull / merge / rebase / push；`behind=33` 保持不动 |
| N25 重开 | `N25_REMAINS_CLOSED` | 保持 `closed` / `closed_at=2026-11-15` / 43 条证据 / `closure` 原样；不新增 `reopen` 字段 |

四项裁定**只对本轮生效，不构成对后续轮次的授权**；后续如需真机 / 提交 / push / 重开，须重新逐项显式授权。判据继承不变：只有「A 撞墙且 B 通过」才支持命题；B 组 `available===true && messageCountAfter<Before`；边界未执行或 `available:false` ⇒ 该轮作废 / 本轮不可评估；observe-first Gate A 判无墙即 `ABORT_NO_WALL`；机器裁定 + 磁盘真证，人工视觉判读单列。

本轮未改 git / 源码 / 测试 / dist / 变体 Pack / known_gaps.json / N25，未碰冻结平台。新增产物为 `three-items-user-ruling-2026-11-15.json` 与本节回写脚本。
"""

with RESULT.open("a", encoding="utf-8") as f:
    f.write(section)

with LOG.open("a", encoding="utf-8") as f:
    f.write("\n- 用户四项裁定：① 不跑真机、② 暂不提交、③ 暂不 push、④ 不重开 N25（`three-items-user-ruling-2026-11-15.json` + RESULT §28.10）。四项只对本轮生效，不构成后续授权；未改 git / 源码 / dist / Pack / 台账，冻结站保持冻结。\n")

print(json.dumps({
    "ruling": ruling["answers"],
    "resultLinesAfter": len(RESULT.read_text().splitlines()),
    "section28SubsectionsTotal": RESULT.read_text().count("\n### 28."),
}, ensure_ascii=False, indent=2))
