#!/usr/bin/env python3
"""提交范围只读盘点（2026-11-15 刷新版）。只生成清单与 plan-only 方案，不执行任何 git 写操作。

修正 commit-scope-2026-11-14.json 的 D-2 缺陷：不对 porcelain stdout 做 .strip()。
"""
import json
import pathlib
import subprocess
import datetime
import collections

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EVID = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.rstrip("\n")


lines = [l for l in git("status", "--porcelain=v1").split("\n") if l]
# XY PATH：路径从 index 3 开始；前导空格必须保留
modified_tracked = [l[3:] for l in lines if l[0] == " " and l[1] != " "]
untracked = [l[3:] for l in lines if l[0] == "?"]
staged = [l[3:] for l in lines if l[0] not in (" ", "?")]

assert all(p.startswith("chrome-extension/") or p.startswith("collaboration/") or p.startswith("known_gaps")
           for p in modified_tracked), "porcelain 路径解析异常"
# 注意：不能用子串判断（"hrome-extension" 本就是 "chrome-extension" 的子串），必须按路径前缀。
assert not any(p.startswith("hrome-extension") for p in modified_tracked), "D-2 缺陷未修正"

head = git("rev-parse", "--short", "HEAD")
origin = git("rev-parse", "--short", "origin/main")
lr = git("rev-list", "--left-right", "--count", "origin/main...HEAD").split()
behind, ahead = int(lr[0]), int(lr[1])


def bucket(name):
    n = name.lower()
    if "ab5" in n:
        return "B_ab5_observe_first_2026-11-14"
    if "deepseek-newchat" in n or "deepseek-new-session" in n or "gates-deepseek" in n:
        return "D_deepseek_newchat_local_fix_2026-11-12"
    if "ab4" in n:
        return "E_ab4_2026-11-12"
    if "ab3" in n:
        return "F_ab3_2026-11-12"
    if "ab2" in n or ".ab-" in n or "ab-round1" in n:
        return "G_ab_ab2_2026-11-11"
    if any(k in n for k in ("three-items", "three-steps", "n25-closure", "n25-reopen", "proposition-",
                            "commit-scope", "commit-authorization", "remote-divergence",
                            "wall-observability", "offline-verify", "ab5-prep-gates", "ab5-observe-first-plan")):
        return "I_governance_and_verdicts_2026-11-14_15"
    return "H_other_evidence"


by_bucket = collections.Counter(bucket(p) for p in untracked)
by_ext = collections.Counter(pathlib.Path(p).suffix or "(none)" for p in untracked)

this_turn = [p for p in untracked if "2026-11-15" in p and any(k in p for k in
             ("three-items", "remote-divergence-2026-11-15.2", "commit-scope-2026-11-15", "n25-reopen"))]
source_and_tests = [p for p in modified_tracked if p.startswith("chrome-extension/")]
ledger_and_report = [p for p in modified_tracked if not p.startswith("chrome-extension/")]

kg = json.loads((REPO / "known_gaps.json").read_text())
gaps = kg.get("gaps") or kg.get("items") or []
n25 = next(x for x in gaps if x.get("id") == "N25")
ev_json = sorted(EVID.glob("*.json"))
bad = []
for p in ev_json:
    try:
        json.loads(p.read_text())
    except Exception as e:
        bad.append(p.name)

data = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "mode": "commit-scope-inventory-readonly-2026-11-15",
    "authorization": "用户 2026-11-15 指令『② 要提交』只表达动作意图，文件集合未单独授权。本清单只读，未 commit / push / stage / add。",
    "supersedes": "commit-scope-2026-11-14.json",
    "defectFixed": {
        "id": "D-2",
        "oldFirstPath": "hrome-extension/src/background/pack-executor.js",
        "newFirstPath": modified_tracked[0],
        "rootCause": "旧脚本对 porcelain stdout 调 .strip() 吃掉首行前导空格，再按 [3:] 取路径时切掉首字符",
        "fix": "改用 rstrip('\\n') 并断言路径不以 hrome-extension 开头",
        "oldFileKeptAsHistory": True,
    },
    "total": len(lines),
    "staged": {"count": len(staged), "files": staged,
               "note": "staged=0。任何 commit 都必须先显式 git add 指定集合；禁止 git add -A / git commit -a。"},
    "modifiedTracked": {"count": len(modified_tracked), "files": modified_tracked},
    "untracked": {
        "count": len(untracked),
        "byBucket": dict(sorted(by_bucket.items())),
        "byExtension": dict(sorted(by_ext.items())),
        "files": untracked,
    },
    "bucketGuide": {
        "A_source_and_tests": "modifiedTracked 里的 chrome-extension 源码 / 测试 / 变异锚（F1、F2、deepseek newChat 本地修复链）",
        "B_gap_ledger": "known_gaps.json",
        "C_report": "RESULT-L2-MULTIPLATFORM-2026-11-10.md",
        "B_ab5_observe_first_2026-11-14": "observe-first 单轮 A 的 runner / 回执 / 截图 / 裁定 / 前置 / 预检 / 日志 / JSONL",
        "D_deepseek_newchat_local_fix_2026-11-12": "§22 deepseek newChat 本地修复门禁产物",
        "E/F/G": "ab4 / ab3 / ab+ab2 真机 A/B 四轮证据",
        "I_governance_and_verdicts_2026-11-14_15": "§24–§28 的只读诊断、授权裁定、结案与重开机制产物",
        "H_other_evidence": "其他既有 evidence 产物",
    },
    "candidateSets": {
        "minimal_this_turn": {
            "count": len(this_turn),
            "files": this_turn,
            "note": "仅本轮 ①②③ 判定 + 远端分歧 + §28 重开机制产物",
        },
        "source_tests_ledger_report": {
            "count": len(source_and_tests) + len(ledger_and_report) + 1,
            "files": source_and_tests + ledger_and_report + ["chrome-extension/tests/deepseek-new-session.test.mjs"],
            "note": "源码/测试/台账/报告，不含任何真机证据与日志",
        },
        "everything": {
            "count": len(lines),
            "note": "全部工作区改动。用户明令『不要默认一次全收』，此集合仅登记，不作默认。",
        },
    },
    "executionPlan": {
        "status": "plan-only / NOT-EXECUTED",
        "steps": [
            "1. 用户分别确认『提交动作』与『文件集合』",
            "2. git add 仅指定集合内的路径（逐条或按目录显式列出），不 add -A",
            "3. git status 复核 staged 集合与授权集合一致",
            "4. git commit -m '<用户确认的 message>'（不 amend、不 skip hooks）",
            "5. 若 push：另需单独授权处理 behind=33 分歧（merge / rebase / 先 pull），完成集成门禁后再 push",
        ],
        "forbidden": ["git add -A", "git commit -a", "git commit --amend", "--no-verify", "force push", "自动处理分歧"],
    },
    "diskTruth": {
        "head": head,
        "originMain": origin,
        "ahead": ahead,
        "behind": behind,
        "unpushed": 0,
        "staged": len(staged),
        "statusItemsAtRead": len(lines),
        "evidenceJsonTotal": len(ev_json),
        "evidenceJsonParseFailures": bad,
        "knownGapsCount": len(gaps),
        "n25Status": n25.get("status"),
        "n25EvidenceCount": len(n25.get("appended_evidence", [])),
        "n25ClosedAt": n25.get("closed_at"),
        "resultTotalLines": len(RESULT.read_text().splitlines()),
    },
    "remoteDivergence": {
        "head": head,
        "originMain": origin,
        "behind": behind,
        "ahead": ahead,
        "evidence": "remote-divergence-2026-11-15.2.json",
        "note": "用户指令写 behind 31，真值 33；外部 fetch 推进，本会话未 fetch/pull/merge/rebase。",
    },
    "gitUntouched": {"commit": False, "push": False, "stage": False, "add": False},
    "note": "只读盘点：本脚本与清单自身落盘后 status_items 会 +2。授权必须按『是否提交』与『提交哪个文件集合』分别确认。",
}

out = EVID / "commit-scope-2026-11-15.json"
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({
    "total": data["total"], "staged": len(staged),
    "modifiedTracked": len(modified_tracked), "firstPath": modified_tracked[0],
    "untracked": len(untracked), "byBucket": data["untracked"]["byBucket"],
    "thisTurnSet": len(this_turn), "sourceSet": data["candidateSets"]["source_tests_ledger_report"]["count"],
    "behind": behind, "origin": origin,
}, ensure_ascii=False, indent=2))
