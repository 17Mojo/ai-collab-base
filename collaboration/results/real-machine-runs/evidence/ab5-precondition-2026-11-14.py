#!/usr/bin/env python3
"""ab5 observe-first：跨 2 天只读前置对账 + 逐次解冻授权留痕。

不启动浏览器、不打开冻结站、不发送消息、不写任何 L2 回执、不碰 git。
只把 2026-11-14 当时的磁盘真值机械重算一遍，落盘成可复核证据。
"""
import hashlib
import json
import pathlib
import subprocess
import datetime

REPO = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base")
EXT = REPO / "chrome-extension"
EV = REPO / "collaboration/results/real-machine-runs/evidence"
PROFILE = pathlib.Path.home() / "Library/Application Support/rm-qianwen-l2-profile"
OUT = EV / "ab5-precondition-2026-11-14.json"

DIST_EV = EV / "dist-consistency-2026-11-12.deepseek-newchat.json"
PLAN = EV / "ab5-observe-first-plan-2026-11-12.json"
SCOPE = EV / "commit-scope-2026-11-12.json"

PACKS = {
    "no-boundary": EV / "ab-pack-2026-11-11.no-boundary.json",
    "with-boundary": EV / "ab-pack-2026-11-11.with-boundary.json",
}
OUT_NAMES = [
    "L2-deepseek-auto-2026-11-14.ab5-no-boundary",
    "L2-deepseek-auto-2026-11-14.ab5-with-boundary",
    "L2-longcat-auto-2026-11-14.ab5-no-boundary",
    "L2-longcat-auto-2026-11-14.ab5-with-boundary",
]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()

errors = []
checks = {}

# ── 1. git 真值 ──────────────────────────────────────────────
head = git("rev-parse", "--short", "HEAD")
origin = git("rev-parse", "--short", "origin/main")
unpushed = int(git("rev-list", "--count", "origin/main..HEAD") or 0)
status_items = len([x for x in git("status", "--porcelain").splitlines() if x.strip()])
checks["git"] = {
    "head": head, "originMain": origin, "unpushed": unpushed,
    "statusItems": status_items,
}
if head != origin or unpushed != 0:
    errors.append("HEAD/origin 不一致或存在未推送提交")

# ── 2. dist 产物 hash 与一致性证据 ──────────────────────────
d = json.loads(DIST_EV.read_text())
dist_files = []
for item in d["files"]:
    actual = sha(EXT / item["path"])
    ok = actual == item["sha256"]
    dist_files.append({"path": item["path"], "expected": item["sha256"],
                       "actual": actual, "pass": ok})
    if not ok:
        errors.append("dist 产物 hash 不符: " + item["path"])
checks["dist"] = {
    "evidence": DIST_EV.name,
    "allPass": d.get("allPass"), "idempotent": d.get("idempotent"),
    "files": dist_files,
}
if not (d.get("allPass") and d.get("idempotent")):
    errors.append("dist 一致性证据本身未通过")

# ── 3. 两个变体 Pack sha256 ─────────────────────────────────
plan = json.loads(PLAN.read_text())
expected_packs = {p["variant"]: p["sha256"] for p in plan["packs"]}
pack_check = []
for variant, p in PACKS.items():
    actual = sha(p)
    ok = actual == expected_packs.get(variant)
    pack_check.append({"variant": variant, "file": p.name,
                       "expected": expected_packs.get(variant),
                       "actual": actual, "pass": ok})
    if not ok:
        errors.append("变体 Pack hash 不符: " + variant)
checks["packs"] = pack_check

# ── 4. ab5 目标 OUT 路径全空（不覆盖既有证据）──────────────
targets = []
for name in OUT_NAMES:
    for suffix in (".json", ".png", ".dom-samples.json"):
        p = EV / (name + suffix) if suffix != ".dom-samples.json" else EV / (name + suffix)
        targets.append({"file": p.name, "exists": p.exists()})
        if p.exists():
            errors.append("目标路径已存在，拒绝覆盖: " + p.name)
checks["targetPaths"] = {"checked": len(targets), "occupied": sum(1 for t in targets if t["exists"])}

# ── 5. SW 缓存三目录条目数（safe-delete shim 阈值 50）───────
sw = {}
for label in ("Service Worker", "Code Cache", "Extension Scripts"):
    p = PROFILE / "Default" / label
    sw[label] = {"exists": p.is_dir(),
                 "fileCount": len(list(p.rglob("*"))) and sum(1 for x in p.rglob("*") if x.is_file()) if p.is_dir() else 0}
sw_total = sum(v["fileCount"] for v in sw.values())
checks["swCache"] = {"dirs": sw, "totalFiles": sw_total, "shimThreshold": 50,
                     "belowThreshold": sw_total < 50}
if sw_total >= 50:
    errors.append("SW 缓存条目达到 shim 阈值，需单轮独立补跑")

# ── 6. plan 状态与提交清单 ──────────────────────────────────
checks["plan"] = {
    "file": PLAN.name,
    "status": plan.get("status"),
    "noRealMachineAction": plan.get("noRealMachineAction"),
    "selfCheckPass": plan.get("selfCheck", {}).get("pass"),
}
if plan.get("status") != "plan-only / NOT-EXECUTED":
    errors.append("ab5 plan 状态已变，需重新核对是否被偷跑")
scope = json.loads(SCOPE.read_text())
checks["commitScope"] = {"file": SCOPE.name, "totalAtInventory": scope.get("total"),
                         "currentStatusItems": status_items,
                         "note": "本轮新增证据落盘后 status_items 会再增加，属预期"}

# ── 7. 授权留痕（用户最新明令 = 唯一解冻来源）──────────────
authorization = {
    "source": "用户 2026-11-14 明令（本轮 continue 之前的最后一条动作指令）",
    "verbatim": (
        "后续步骤：1、解冻并按 observe-first gate 重跑（先跑 A 单轮，判无墙即停），"
        "而不是盲跑 4 轮；逐次 ALLOW_FROZEN=1 留痕。"
        "2、Gate A 判「墙不存在」→ ABORT_NO_WALL，N25 仍 open；"
        "仅当 Gate A 成立才跑 B 并按判据裁定。"
        "3、提交 / push 按「提交」与「文件集合」分别确认；"
        "commit-scope-2026-11-12.json 已有分类清单，当前工作区 105 项，不要默认一次全收。"
    ),
    "unfrozenPlatforms": ["deepseek", "longcat"],
    "scope": "只跑 observe-first 的 A 单轮；Gate A 不成立即停机；B 组仅 Gate A 成立后才跑",
    "perCommandFlag": "ALLOW_FROZEN=1",
    "appliesToPrecheck": True,
    "whitelistCodeChanged": False,
    "receiptTrace": "回执 platformPolicy.unfrozenBy 必须逐轮可复核",
    "usageRule": "逐次显式放行，用完仍是冻结；下次再跑须重新明确解冻",
    "commitPush": "未授权；按「提交」与「文件集合」分别确认，禁止默认一次全收",
    "outboundSend": "仅 A 单轮（Gate A 成立时才追加同站 B 单轮），不跑 4 轮",
}

# ── 8. 判据留白：Gate A 首轮平台未在 plan 中钉死 ───────────
openCriterion = {
    "item": "Gate A 首轮平台",
    "planSays": "gateA.description = 「先只跑 A 组（no-boundary）单轮」，未指定 platform",
    "mustNotGuess": True,
    "candidates": {
        "deepseek": "§24 诊断：F1 修复后 4 轮 step_8 全在 12.3–13.6s 成功，墙最确定不复现，单轮即可得 ABORT_NO_WALL，最省额度",
        "longcat": "§24 诊断：失败步在 step_3/4/6/8 漂移，截图同型「服务出错啦，请稍后再试。」，属站点侧外部混杂变量",
    },
    "resolution": "PENDING_USER_CONFIRMATION",
    "note": "不暗猜判据。未确认前不启动任何真机轮次。",
}
checks["openCriterion"] = openCriterion

result = {
    "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "mode": "ab5-observe-first-precondition-readonly",
    "checkedAt": "2026-11-14",
    "daysSincePlan": 2,
    "checks": checks,
    "authorization": authorization,
    "errors": errors,
    "preconditionPass": len(errors) == 0,
    "noRealMachineAction": True,
    "gitUnchanged": True,
    "note": (
        "本文件只核磁盘真值与授权边界，不是回执、不证明 Gate A。"
        "preconditionPass=true 仅表示前置条件齐备，不代表真机已跑或命题成立。"
    ),
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print("WROTE", OUT.name)
print("preconditionPass =", result["preconditionPass"])
print("errors =", json.dumps(errors, ensure_ascii=False))
print("git", checks["git"])
print("dist", [(x["path"], x["pass"]) for x in dist_files])
print("packs", [(x["variant"], x["pass"]) for x in pack_check])
print("targets occupied =", checks["targetPaths"]["occupied"])
print("swCache total =", sw_total)
print("openCriterion =", openCriterion["resolution"])
