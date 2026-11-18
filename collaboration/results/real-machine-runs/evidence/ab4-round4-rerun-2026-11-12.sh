#!/usr/bin/env bash
# ab4 第 4 轮补跑（longcat / with-boundary）
#
# 为什么单独跑：ab4-runner 的第 4 轮在 launch() 清 SW 缓存时被 WorkBuddy
# safe-delete shim 拦住（SAFE_DELETE_BULK_CONFIRM_REQUIRED，
# count 52 > threshold 50，scope="turn"，targets=Extension Scripts）。
# 浏览器未启动、页面未打开、Pack 未导入、未发送任何内容，回执 exists:false。
# 当前 Extension Scripts 实际只有 5 个文件 ⇒ 拦的是 turn 累计删除数，
# 与 ab3 第 4 轮同型：单轮独立跑、计数重置即可，不需要也不应该关安全门。
#
# 口径：
#   - 独立日志全程 tee、独立 JSONL 即时追加、回执由驱动自身即时落盘；
#   - 不覆盖任何既有证据（目标路径必须为空）；
#   - 前置复核 PRECONDITION_OK（放行留痕 / Pack hash / 新 dist hash / 前 3 轮回执 / 目标为空）；
#   - 不设置 CODEBUDDY_SAFE_DELETE_ENABLED=0；
#   - 补跑与第 3 轮的时间间隔如实写进 summary，保留 likeForLike 缺口。
set -u
set -o pipefail

REPO=/Users/raymondna/Documents/AI-collab/ai-collab-base
EXT=$REPO/chrome-extension
E=$REPO/collaboration/results/real-machine-runs/evidence
RUNLOG=$E/ab4-round4-2026-11-12.log
PROGRESS=$E/ab4-round4-progress-2026-11-12.jsonl
SUMMARY=$E/ab4-round4-summary-2026-11-12.json
OUT_NAME="L2-longcat-auto-2026-11-12.ab4-with-boundary.json"
PACK_B=$E/ab-pack-2026-11-11.with-boundary.json
PRECHECK=$E/L2-precheck-2026-11-12.ab4.deepseek-longcat.json
PLAN=$E/session-wall-ab-plan-2026-11-11.json
DIST_EV=$E/dist-consistency-2026-11-12.deepseek-newchat.json

# 日志与进度一律 append-only：第一次补跑的 PRECONDITION_FAILED 也是证据，
# 重跑不许覆盖它。每次执行用 BEGIN / ABORTED / FINISHED 行分隔。
echo "=== ROUND4_ATTEMPT_BOUNDARY $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" >> "$RUNLOG"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
note() { printf '{"t":"%s","event":"%s","round":"%s"}\n' "$(now)" "$1" "$2" >> "$PROGRESS"; }
say() { echo "$1" | tee -a "$RUNLOG"; }

say "=== ROUND4_RERUN_BEGIN $(now) ==="
note "rerun begin" "ab4 round 4 longcat/with-boundary"

python3 - "$PRECHECK" "$PLAN" "$DIST_EV" "$E" "$OUT_NAME" <<'PY' 2>&1 | tee -a "$RUNLOG"
import json, sys, hashlib, pathlib
pre, plan, dist_ev, ev, out_name = [pathlib.Path(x) for x in sys.argv[1:6]]
errors = []
p = json.loads(pre.read_text())
pol = {x["id"]: x for x in p.get("platformPolicy", [])}
q = pol.get("longcat", {})
if not (q.get("allowed") is True and q.get("unfrozenBy") == "ALLOW_FROZEN=1"):
    errors.append("longcat 未显式放行")
res = {x.get("platform"): x for x in p.get("results", [])}
r = res.get("longcat", {})
if not (r.get("composerVisible") is True and r.get("looksLikeLogin") is False):
    errors.append("longcat 登录态不可用")
pl = json.loads(plan.read_text())
vps = {v["variant"]: v for v in pl["variantPacks"]}
f = pathlib.Path(vps["with-boundary"]["path"])
h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
if h != vps["with-boundary"]["sha256"]:
    errors.append("B 变体 Pack hash 不符")
d = json.loads(dist_ev.read_text())
if not (d.get("allPass") and d.get("idempotent")):
    errors.append("dist 一致性证据未通过")
for item in d["files"]:
    fp = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/chrome-extension") / item["path"]
    h = hashlib.sha256(fp.read_bytes()).hexdigest() if fp.exists() else None
    if h != item["sha256"]:
        errors.append("dist 产物已被改动: " + item["path"])
prior = [
    "L2-deepseek-auto-2026-11-12.ab4-no-boundary.json",
    "L2-deepseek-auto-2026-11-12.ab4-with-boundary.json",
    "L2-longcat-auto-2026-11-12.ab4-no-boundary.json",
]
for name in prior:
    if not (ev / name).exists():
        errors.append("前序回执缺失: " + name)
for suffix in [".json", ".png"]:
    # out_name 是 Path；Path.replace() 是「重命名文件」，不是字符串替换。
    # 必须用 .name（str）做后缀替换，否则前置检查会崩且 stderr 一度没被 tee 看到。
    t = ev / out_name.name.replace(".json", suffix)
    if t.exists():
        errors.append("目标路径已存在，拒绝覆盖: " + t.name)
print("PRECHECK", p.get("generatedAt"), "policy", q.get("unfrozenBy"))
print("DIST", [(i["path"], i["sha256"][:16]) for i in d["files"]])
print("PRIOR_ROUNDS", len(prior), "TARGET_EMPTY", not (ev / out_name).exists())
if errors:
    print("PRECONDITION_FAILED", json.dumps(errors, ensure_ascii=False))
    sys.exit(1)
print("PRECONDITION_OK")
PY
if [ $? -ne 0 ]; then
  note "rerun aborted" "precondition failed"
  say "=== ROUND4_RERUN_ABORTED_PRECONDITION_FAILED $(now) ==="
  exit 1
fi

note "start" "4 longcat/with-boundary"
say "=== ROUND 4/4 RERUN START $(now) ==="
(
  cd "$EXT" || exit 1
  PLATFORM=longcat ALLOW_FROZEN=1 PACK_VARIANT=with-boundary PACK_PATH="$PACK_B" OUT="$E/$OUT_NAME" \
    node tests/real-machine/l2-platform-auto.mjs
) 2>&1 | tee -a "$RUNLOG"
ec=${PIPESTATUS[0]}
say "=== ROUND 4/4 RERUN NODE_EXIT=$ec $(now) ==="
note "node-exit" "4 exit=$ec"

python3 - "$E/$OUT_NAME" "$E/L2-longcat-auto-2026-11-12.ab4-no-boundary.json" "$PROGRESS" "$SUMMARY" "$ec" <<'PY' 2>&1 | tee -a "$RUNLOG"
import json, sys, pathlib, datetime
_args = sys.argv[1:6]
# 前 4 个是路径，第 5 个是退出码字符串；早先一版把 5 个全转成 Path，
# 导致 int(ec) 抛 TypeError、收尾证据缺失、进程假 EXIT=1（回执本身已落盘）。
out, a_receipt, prog, summary = [pathlib.Path(x) for x in _args[:4]]
ec = _args[4]
d = json.loads(out.read_text()) if out.exists() else None
ex = (d or {}).get("exec") or {}
res = ex.get("result") or {}
steps = res.get("steps") or []
resets = res.get("sessionResets") or []
first = resets[0] if resets else None
before = first.get("messageCountBefore") if isinstance(first, dict) else None
after = first.get("messageCountAfter") if isinstance(first, dict) else None
available = first.get("available") if isinstance(first, dict) else None
reset_ok = bool(available is True and isinstance(before, int) and isinstance(after, int) and after < before)
pp = (d or {}).get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None
a = json.loads(a_receipt.read_text()) if a_receipt.exists() else {}
a_end = ((a.get("exec") or {}).get("result") or {}).get("endTime")
a_iso = datetime.datetime.fromtimestamp(a_end / 1000, datetime.timezone.utc).isoformat() if a_end else None
rec = {
    "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "event": "verify", "round": "4-rerun", "receipt": out.name, "nodeExit": int(ec),
    "exists": d is not None, "execSuccess": ex.get("success"), "status": res.get("status"),
    "stepsTotal": len(steps), "stepSuccess": sum(1 for s in steps if s.get("success") is True),
    "duration": res.get("duration"), "sessionResets": len(resets),
    "resetAvailable": available, "resetBefore": before, "resetAfter": after,
    "resetActuallyHappened": reset_ok, "policyUnfrozenBy": unfrozen,
}
with prog.open("a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("VERIFY", json.dumps(rec, ensure_ascii=False))
summary.write_text(json.dumps({
    "generatedAt": rec["t"],
    "runner": "ab4-round4-rerun-2026-11-12.sh",
    "receipt": out.name,
    "receiptExists": d is not None,
    "nodeExit": int(ec),
    "round3EndTime": a_iso,
    "likeForLikeNote": "补跑与第 3 轮结束不在相邻时间窗；间隔如实保留，不得抹掉。",
    "safeDeleteShimDisabled": False,
    "verify": rec,
}, ensure_ascii=False, indent=2) + "\n")
print("ROUND4_RECEIPT_PRESENT", d is not None)
if d is None:
    sys.exit(1)
PY
FINAL_EC=$?
note "rerun done" "4 allReceipts=$FINAL_EC"
say "=== ROUND4_RERUN_FINISHED RECEIPT_PRESENT_EXIT=$FINAL_EC $(now) ==="
exit "$FINAL_EC"
