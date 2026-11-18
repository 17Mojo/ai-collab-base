#!/usr/bin/env python3
"""跨时段只读前置对账（2026-11-15 第 2 次）：git / behind / N25 / evidence。

对应 Task #77。只读，不改 git、不改源码/测试/dist/Pack、不碰冻结站。
刻意不对 porcelain 输出做 .strip()：前导空格是 XY 状态码的一部分。
"""
import json
import pathlib
import subprocess
import datetime

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EVID = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return r.stdout.rstrip("\n")


def porcelain_lines():
    out = git("status", "--porcelain=v1")
    return [l for l in out.split("\n") if l]


lines = porcelain_lines()
staged = [l for l in lines if l[0] not in (" ", "?")]
modified_tracked = [l for l in lines if l[0] == " " and l[1] != " "]
untracked = [l for l in lines if l[0] == "?"]

head = git("rev-parse", "--short", "HEAD")
origin = git("rev-parse", "--short", "origin/main")
lr = git("rev-list", "--left-right", "--count", "origin/main...HEAD").split()
behind, ahead = int(lr[0]), int(lr[1])
unpushed = len(git("log", "--oneline", "origin/main..HEAD").split("\n")) if git("log", "--oneline", "origin/main..HEAD") else 0

# 远端增量：19635c6 -> 915c350
new_commits = git("log", "--oneline", "--no-decorate", "19635c6..origin/main").split("\n")
new_files = [l.split("\t", 1)[1] for l in git("diff", "--name-status", "19635c6..origin/main").split("\n") if "\t" in l]
cum_files = [l for l in git("diff", "--name-only", "36d9ec2..origin/main").split("\n") if l]
our_inputs = [p for p in cum_files if p.startswith("chrome-extension/src/") or p.startswith("chrome-extension/dist/")
              or "known_gaps" in p or "RESULT-" in p or "real-machine-runs/evidence" in p or "ab-pack" in p]

kg = json.loads((REPO / "known_gaps.json").read_text())
gaps = kg.get("gaps") or kg.get("items") or []
n25 = next(x for x in gaps if x.get("id") == "N25")
status_counts = {s: sum(1 for x in gaps if x.get("status") == s) for s in ("open", "closed", "wontfix")}

ev_json = sorted(EVID.glob("*.json"))
parse_failures = []
for p in ev_json:
    try:
        json.loads(p.read_text())
    except Exception as e:
        parse_failures.append({"file": p.name, "error": str(e)})

rtext = RESULT.read_text()
import re
sections = re.findall(r"^## §(\d+)", rtext, flags=re.M)
s27 = re.findall(r"^### 27\.(\d+)", rtext, flags=re.M)

# 两条数据缺陷：本轮首个对账脚本的 .strip() 假阳性 + 上一轮清单首字符被切
old_scope = json.loads((EVID / "commit-scope-2026-11-14.json").read_text())
bad_path = old_scope["modifiedTracked"]["files"][0]

data = {
    "mode": "three-items-precondition-readonly-2026-11-15",
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "userMandate": "1、① 要跑真机 ② 要提交 ③ 要 push：另需单独授权先处理 behind 31 分歧；2、解释下 N25 若需重开",
    "interpretation": "① ② 是动作意图表述，③ 用户自己标注『另需单独授权』。本文件只做机器前提判定，不把意图表述自动升级为完整授权。",
    "diskTruth": {
        "head": head,
        "originMain": origin,
        "ahead": ahead,
        "behind": behind,
        "unpushed": unpushed,
        "staged": len(staged),
        "stagedFiles": staged,
        "modifiedTracked": len(modified_tracked),
        "untracked": len(untracked),
        "statusItems": len(lines),
    },
    "remoteDivergence": {
        "previous": "19635c6 / behind 31",
        "current": f"{origin} / behind {behind}",
        "behindDelta": behind - 31,
        "newCommits": new_commits,
        "newCommitCount": len(new_commits),
        "changedFilesInDelta": new_files,
        "cumulativeChangedFiles": cum_files,
        "cumulativeFileCount": len(cum_files),
        "ourInputsTouched": our_inputs,
        "byExternalFetch": True,
        "thisSessionGitOps": {"fetch": False, "pull": False, "merge": False, "rebase": False, "commit": False, "push": False, "stage": False},
        "staleFact": "用户指令写 behind 31；磁盘真值已是 behind 33。按 disk-truth 以 33 为准并回溯补记。",
        "evidence": "remote-divergence-2026-11-15.2.json",
    },
    "n25": {
        "status": n25.get("status"),
        "closed_at": n25.get("closed_at"),
        "evidenceCount": len(n25.get("appended_evidence", [])),
        "closureType": (n25.get("closure") or {}).get("type"),
        "recharacterized": bool(n25.get("recharacterization")),
        "ledgerTotal": len(gaps),
        "statusCounts": status_counts,
    },
    "evidence": {
        "jsonCount": len(ev_json),
        "parseFailures": parse_failures,
        "ab6Targets": len(list(EVID.glob("L2-*.ab6-*.json"))),
        "resultLines": len(rtext.splitlines()),
        "resultSectionsTail": sections[-3:],
        "resultSection27Subsections": len(s27),
    },
    "dataDefects": [
        {
            "id": "D-1",
            "kind": "FALSE_POSITIVE_IN_THIS_TURN_PROBE",
            "symptom": "本轮第一个只读对账脚本报 staged=1（chrome-extension/src/background/pack-executor.js）",
            "rootCause": "对 git status --porcelain 的整段 stdout 调用了 .strip()，吃掉了首行前导空格，' M path' 被误解析为 'M path'",
            "recheck": [
                "git status --porcelain=v1 首行确为 ' M chrome-extension/src/background/pack-executor.js'",
                "git diff --cached --stat 与 --raw 均为空",
                "git ls-files -s 的 index blob f151615 == HEAD blob f151615",
                "worktree blob cfc4fa2 与 index 不同 ⇒ 是未暂存的 worktree 修改",
            ],
            "ruling": "staged=0；不得把假差异写进提交范围或据此执行 unstage",
        },
        {
            "id": "D-2",
            "kind": "REAL_DEFECT_IN_PREVIOUS_INVENTORY",
            "symptom": f"commit-scope-2026-11-14.json 的 modifiedTracked.files[0] = '{bad_path}'，首字符 c 被切掉",
            "rootCause": "同一 .strip() 使首行长度少 1，再按 [3:] 取路径时吃掉路径首字符；仅首行受影响",
            "impact": "若照该清单逐条 git add，会漏 add 或报 pathspec 错",
            "ruling": "本轮新盘点用 rstrip('\\n') 保留状态码列并修正该路径；旧清单作为历史证据保留不覆盖",
        },
    ],
    "stepsPrecheck": [
        {
            "item": "① 要跑真机",
            "machineVerdict": "NOT_EXECUTED_PRECONDITION_UNMET",
            "missing": ["逐次明确解冻 deepseek / longcat 及 ALLOW_FROZEN=1 留痕", "说明本次改变了哪个自变量"],
            "note": "用户上一轮自设前提；§26 已证未改自变量的盲跑不产生新证据",
        },
        {
            "item": "② 要提交",
            "machineVerdict": "COMMIT_ACTION_EXPRESSED_BUT_FILE_SET_NOT_AUTHORIZED",
            "missing": ["文件集合单独授权"],
            "note": "commit-scope-2026-11-14.json 已过期（122 项 / origin f98a1a7 / behind 4），真值 139 项 / behind 33",
        },
        {
            "item": "③ 要 push",
            "machineVerdict": "NOT_AUTHORIZED_NO_ACTION",
            "missing": ["单独授权先处理 behind 分歧"],
            "note": "用户自己写明『另需单独授权』；且分歧真值是 33 而非 31",
        },
    ],
    "hardBoundaries": {
        "noRealMachineAction": True,
        "noGitChange": True,
        "noPackChange": True,
        "noSourceOrDistChange": True,
        "n25StatusChanged": False,
    },
}

out = EVID / "three-items-precondition-2026-11-15.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

div = {
    "mode": "remote-divergence-readonly-2026-11-15.2",
    "generatedAt": data["generatedAt"],
    "head": head,
    "originMain": origin,
    "ahead": ahead,
    "behind": behind,
    "previousSnapshot": {"originMain": "19635c6", "behind": 31, "evidence": "remote-divergence-2026-11-15.json"},
    "newCommits": new_commits,
    "changedFilesInDelta": new_files,
    "cumulativeChangedFiles": cum_files,
    "ourInputsTouched": our_inputs,
    "note": "外部 fetch 推进，非本会话操作。若授权 push，须先单独授权处理 behind=33 分歧。",
}
(EVID / "remote-divergence-2026-11-15.2.json").write_text(json.dumps(div, ensure_ascii=False, indent=2) + "\n")

print(json.dumps({
    "head": head, "origin": origin, "behind": behind, "ahead": ahead,
    "staged": len(staged), "statusItems": len(lines),
    "n25": data["n25"], "evidenceJson": len(ev_json), "parseFailures": len(parse_failures),
    "resultLines": data["evidence"]["resultLines"], "section27Subsections": len(s27),
    "newCommits": len(new_commits), "deltaFiles": new_files,
    "ourInputsTouched": our_inputs,
}, ensure_ascii=False, indent=2))
