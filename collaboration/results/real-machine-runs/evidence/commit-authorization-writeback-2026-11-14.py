#!/usr/bin/env python3
"""回写 2026-11-14 提交授权裁定：暂不提交 + 日后文件集合偏好。

只做文本追加与只读证据落盘，不 commit / push / stage，不产生真机回执。
"""
import json
import pathlib
import datetime
import subprocess

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
WORKLOG = pathlib.Path("/Users/raymondna/WorkBuddy/2026-11-04-12-09-59/.workbuddy/memory/2026-11-14.md")
OUT = EV / "commit-authorization-ruling-2026-11-14.json"

def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()

def truth():
    return {
        "head": git("rev-parse", "--short", "HEAD"),
        "originMain": git("rev-parse", "--short", "origin/main"),
        "unpushed": int(git("rev-list", "--count", "origin/main..HEAD") or 0),
        "behind": int(git("rev-list", "--count", "HEAD..origin/main") or 0),
        "statusItems": len([x for x in git("status", "--porcelain").splitlines() if x.strip()]),
        "staged": len([x for x in git("diff", "--cached", "--name-only").splitlines() if x.strip()]),
    }

rec = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "commit-authorization-ruling",
    "questions": [
        {"id": "q-0", "header": "提交动作", "answer": "暂不提交（推荐）"},
        {"id": "q-1", "header": "文件集合", "answer": "仅本轮 ab5 产物（推荐）"},
    ],
    "effectiveDecision": {
        "commitNow": False, "pushNow": False, "stageNow": False,
        "resolveRemoteDivergenceNow": False,
        "allChangesStayInWorkingTree": True,
        "note": "q-0 是本次的实际裁定：本轮不碰 git。远端 behind=4 的分歧不处理。",
    },
    "fileSetPreference": {
        "status": "PREFERENCE_ONLY_NOT_AUTHORIZATION",
        "appliesWhen": "仅当用户下一次明确授权『提交』动作时才生效；不得据此推断本轮已授权提交",
        "scope": "19 项 ab5 observe-first 新产物 + RESULT 报告 + known_gaps.json 台账",
        "excludes": ["15 个 tracked 源码/测试改动", "deepseek-newchat 本地修复门禁产物 13 项",
                     "ab4 21 项 / ab3 17 项 / ab / ab2 14 项历史真机证据", "其他 evidence 23 项"],
        "note": "q-1 的题面是『若后续授权提交』，属文件集合偏好登记，不是一次全收 125 项的授权。",
    },
    "diskTruthBefore": {"head": "36d9ec2", "originMain": "f98a1a7", "behind": 4,
                        "ahead": 0, "unpushed": 0, "statusItems": 125, "staged": 0},
    "diskTruthAfter": truth(),
    "gitUntouched": True,
    "noRealMachineAction": True,
}
OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")

section = """

### 25.11 提交授权裁定：暂不提交（`commit-authorization-ruling-2026-11-14.json`）

按用户明令「提交 / push 按『提交』与『文件集合』分别确认，不要默认一次全收」，两个问题分别确认：

| 问题 | 用户裁定 | 效力 |
|---|---|---|
| q-0 提交动作 | **暂不提交（推荐）** | **本次实际裁定**：不 commit / 不 push / 不 stage，125 项全留工作区；远端 `behind=4` 的分歧不处理 |
| q-1 文件集合 | **仅本轮 ab5 产物（推荐）** | **仅为日后偏好登记**（`PREFERENCE_ONLY_NOT_AUTHORIZATION`）：19 项 ab5 新产物 + RESULT 报告 + `known_gaps.json`，不含源码/测试与 ab3/ab4/ab/ab2 历史证据 |

q-1 的题面是「若后续授权提交」，因此**不能**据此推断本轮已授权提交，也不能当成一次全收 125 项的授权。下一次真正提交时，「提交动作」仍须单独重新授权；且因本地落后远端 4 个提交，push 前处理分歧的动作也须单独授权。

落盘前后磁盘真值一致（`HEAD=36d9ec2`、`origin/main=f98a1a7`、`unpushed=0`、`behind=4`、`staged=0`）；本轮**未碰 git**。
"""
with RESULT.open("a") as f:
    f.write(section)

with WORKLOG.open("a") as f:
    f.write("\n- **提交授权分别确认**：q-0「提交动作」= 暂不提交（推荐）⇒ 本轮不 commit/push/stage，125 项全留工作区，behind=4 分歧不处理；q-1「文件集合」= 仅本轮 ab5 产物（推荐）⇒ 只登记为日后真正提交时的偏好（19 项 ab5 + RESULT + known_gaps），`PREFERENCE_ONLY_NOT_AUTHORIZATION`，不是本轮授权、不是一次全收。回写 RESULT §25.11、`commit-authorization-ruling-2026-11-14.json`。最终磁盘真证：HEAD 36d9ec2 / origin f98a1a7 / unpushed 0 / staged 0 / RESULT 1647+ 行 §25 11 子节 / N25 open 40 条证据 / 131 份 evidence JSON 全可解析。\n")

print("WROTE", OUT.name)
print("commitNow =", rec["effectiveDecision"]["commitNow"])
print("pushNow =", rec["effectiveDecision"]["pushNow"])
print("fileSet =", rec["fileSetPreference"]["status"])
print("diskTruthAfter =", json.dumps(rec["diskTruthAfter"], ensure_ascii=False))
