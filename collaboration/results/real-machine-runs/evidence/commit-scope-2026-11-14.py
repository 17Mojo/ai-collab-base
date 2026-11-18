#!/usr/bin/env python3
"""2026-11-14 最终磁盘真证对账 + 提交范围只读盘点（按文件集合分类）。

不产生任何 git 变更，不 commit、不 push、不 stage。
"""
import json
import pathlib
import subprocess
import datetime
import collections

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EV = REPO / "collaboration/results/real-machine-runs/evidence"
RESULT = REPO / "collaboration/results/RESULT-L2-MULTIPLATFORM-2026-11-10.md"
GAPS = REPO / "known_gaps.json"
OUT = EV / "commit-scope-2026-11-14.json"

def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()

head = git("rev-parse", "--short", "HEAD")
origin = git("rev-parse", "--short", "origin/main")
unpushed = int(git("rev-list", "--count", "origin/main..HEAD") or 0)
porcelain = [x for x in git("status", "--porcelain").splitlines() if x.strip()]

modified, untracked = [], []
for line in porcelain:
    code, path = line[:2], line[3:]
    if "?" in code:
        untracked.append(path)
    else:
        modified.append(path)

def bucket(path):
    n = pathlib.Path(path).name
    if "ab5-" in n or ".ab5-" in n:
        return "B_ab5_observe_first_2026-11-14"
    if n.startswith("ab4-") or ".ab4-" in n:
        return "E_ab4_2026-11-12"
    if n.startswith("ab3-") or ".ab3-" in n:
        return "F_ab3_2026-11-12"
    if n.startswith("ab2-") or ".ab2-" in n or n.startswith("ab-") or ".ab-" in n:
        return "G_ab_ab2_2026-11-11"
    if "deepseek-newchat" in n or "deepseek-new-session" in n or "gates-deepseek" in n:
        return "D_deepseek_newchat_local_fix_2026-11-12"
    if path.startswith("chrome-extension/"):
        return "A_source_and_tests"
    if path.startswith("evidence/") or "real-machine-runs/evidence/" in path:
        return "H_other_evidence"
    if path.startswith("collaboration/results/"):
        return "C_report"
    if n == "known_gaps.json":
        return "B_gap_ledger"
    return "H_other_evidence"

by_bucket = collections.Counter(bucket(p) for p in untracked)
by_ext = collections.Counter(pathlib.Path(p).suffix or "(none)" for p in untracked)

# evidence JSON 可解析性
ej = sorted((EV).glob("*.json"))
bad = []
for p in ej:
    try:
        json.loads(p.read_text())
    except Exception as e:
        bad.append({"file": p.name, "error": str(e)})

# 关键证据存在性 / 内容
gaps = json.loads(GAPS.read_text())
n25 = next(x for x in gaps["gaps"] if str(x.get("id")) == "N25")
final = json.loads((EV / "ab5-final-verdict-2026-11-14.json").read_text())
gatea = json.loads((EV / "ab5-gate-a-verdict-2026-11-14.json").read_text())
result_text = RESULT.read_text()
s25_count = sum(1 for line in result_text.splitlines() if line.startswith("### 25."))

doc = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "commit-scope-inventory-readonly-2026-11-14",
    "head": head, "originMain": origin, "unpushed": unpushed,
    "authorization": "用户 2026-11-14 明令：提交 / push 按「提交」与「文件集合」分别确认，不要默认一次全收 ⇒ 本轮未 commit、未 push、未 stage；本清单仅供按集合授权时核对。",
    "total": len(porcelain),
    "modifiedTracked": {"count": len(modified), "files": modified},
    "untracked": {
        "count": len(untracked),
        "byBucket": dict(sorted(by_bucket.items())),
        "byExtension": dict(sorted(by_ext.items())),
        "files": sorted(untracked),
    },
    "bucketGuide": {
        "A_source_and_tests": "源码 / 测试 / 变异锚（F1、F2、deepseek newChat 等本地修复链）",
        "B_gap_ledger": "known_gaps.json 台账",
        "C_report": "RESULT 报告",
        "B_ab5_observe_first_2026-11-14": "本轮 observe-first 全部新产物（runner / 回执 / 截图 / 裁定 / 前置 / 预检 / 日志 / JSONL / 写回脚本）",
        "D_deepseek_newchat_local_fix_2026-11-12": "§22 deepseek newChat 本地修复门禁产物",
        "E_ab4_2026-11-12": "ab4 四轮 A/B 证据",
        "F_ab3_2026-11-12": "ab3 四轮 A/B 证据",
        "G_ab_ab2_2026-11-11": "ab / ab2 早期 A/B 证据",
        "H_other_evidence": "其他既有 evidence 产物",
    },
    "diskTruth": {
        "evidenceJsonTotal": len(ej),
        "evidenceJsonParseFailures": len(bad),
        "evidenceJsonFailures": bad,
        "knownGapsCount": len(gaps["gaps"]),
        "n25Status": n25["status"],
        "n25EvidenceCount": len(n25["appended_evidence"]),
        "n25ClosedAt": n25["closed_at"],
        "resultTotalLines": len(result_text.splitlines()),
        "resultSection25Subsections": s25_count,
        "ab5FinalCode": final["code"],
        "ab5RoundsExecuted": final["abortBranch"]["roundsExecuted"],
        "ab5BActuallyRun": final["abortBranch"]["bActuallyRun"],
        "ab5LongcatActuallyRun": final["abortBranch"]["longcatActuallyRun"],
        "gateAMachinePass": gatea["gateA"]["machinePass"],
        "propositionSupported": final["propositionSupported"],
        "boundaryIneffectiveClaimed": final["boundaryIneffectiveClaimed"],
    },
    "gitUntouched": {"commit": False, "push": False, "stage": False},
    "note": "只读盘点，清单自身落盘后 status_items 会 +1。授权必须按「是否提交」与「提交哪个文件集合」分别确认，禁止一次性默认全收。",
}
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
print("WROTE", OUT.name)
print("head/origin/unpushed =", head, origin, unpushed)
print("status_items =", len(porcelain), "| tracked =", len(modified), "| untracked =", len(untracked))
print("byBucket =", json.dumps(dict(sorted(by_bucket.items())), ensure_ascii=False))
print("byExtension =", json.dumps(dict(sorted(by_ext.items())), ensure_ascii=False))
print("evidence json =", len(ej), "parse failures =", len(bad))
print("RESULT lines =", len(result_text.splitlines()), "§25 subsections =", s25_count)
print("N25 =", n25["status"], "/", len(n25["appended_evidence"]), "evidence / closed_at =", n25["closed_at"])
print("ab5 code =", final["code"], "rounds =", final["abortBranch"]["roundsExecuted"],
      "B =", final["abortBranch"]["bActuallyRun"], "longcat =", final["abortBranch"]["longcatActuallyRun"])
