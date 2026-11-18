#!/usr/bin/env bash
# ab4 runner：deepseek 精确文案逃生口落地后（新 dist）的 4 轮 A/B 真机复跑
#
# 授权：用户 2026-11-12 20:1x 明确「解冻并授权真机重跑」。
#       冻结白名单代码未改；逐次 ALLOW_FROZEN=1 留痕，回执 platformPolicy 可复核。
#       提交 / push 用户明示「单独授权」⇒ 本 runner 不碰 git。
#
# 相对 ab3 的三处硬修正：
#   1. DIST_EV 换成本轮 dist-consistency-2026-11-12.deepseek-newchat.json
#      （ab3 写死指向 local-fix 证据，新 dist 下必然报 hash 不符）；
#   2. 全部 OUT 换成 *.ab4-*，且不覆盖任何既有证据，前置检查 .json/.png 全空；
#   3. 结尾显式 ALL_RECEIPTS_PRESENT 逐份核回执，RUNNER_FINISHED 不再等于「四轮都跑完」。
#
# 落盘口径（11-11 后台任务被回收、3 轮回执全丢的教训）：
#   stdout 全程 tee -a；每轮 start / node-exit / verify 即时写 append-only JSONL；
#   每轮回执由 l2-platform-auto.mjs 自身即时写 OUT，不依赖 runner 缓冲。
#
# 4 轮严格串行：两个变体用 mergeStrategy=overwrite 导入同一个 pack_id，并行会互相覆盖。
# 不设置 CODEBUDDY_SAFE_DELETE_ENABLED=0：本轮 SW 缓存仅 13 文件，远低于 shim 的 50 阈值。
set -u
set -o pipefail

REPO=/Users/raymondna/Documents/AI-collab/ai-collab-base
EXT=$REPO/chrome-extension
E=$REPO/collaboration/results/real-machine-runs/evidence
RUNLOG=$E/ab4-rerun-2026-11-12.log
PROGRESS=$E/ab4-rerun-progress-2026-11-12.jsonl
SUMMARY=$E/ab4-runner-summary-2026-11-12.json
PACK_A=$E/ab-pack-2026-11-11.no-boundary.json
PACK_B=$E/ab-pack-2026-11-11.with-boundary.json
PRECHECK=$E/L2-precheck-2026-11-12.ab4.deepseek-longcat.json
PLAN=$E/session-wall-ab-plan-2026-11-11.json
DIST_EV=$E/dist-consistency-2026-11-12.deepseek-newchat.json

: > "$RUNLOG"
: > "$PROGRESS"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
note() {
  printf '{"t":"%s","event":"%s","round":"%s"}\n' "$(now)" "$1" "$2" >> "$PROGRESS"
}
say() { echo "$1" | tee -a "$RUNLOG"; }

OUTS=(
  "L2-deepseek-auto-2026-11-12.ab4-no-boundary.json"
  "L2-deepseek-auto-2026-11-12.ab4-with-boundary.json"
  "L2-longcat-auto-2026-11-12.ab4-no-boundary.json"
  "L2-longcat-auto-2026-11-12.ab4-with-boundary.json"
)

say "=== RUNNER_BEGIN $(now) ==="
say "=== AUTHORIZED_UNFREEZE: user 2026-11-12, ALLOW_FROZEN=1 per round, whitelist unchanged ==="
note "runner begin" "ab4 / 4 rounds"

# ── 前置对账：登录态、放行留痕、Pack hash、新 dist hash、目标路径全空 ──
python3 - "$PRECHECK" "$PLAN" "$DIST_EV" "$E" "${OUTS[@]}" <<'PY' | tee -a "$RUNLOG"
import json, sys, hashlib, pathlib
pre, plan, dist_ev, ev = [pathlib.Path(x) for x in sys.argv[1:5]]
outs = sys.argv[5:]
errors = []
p = json.loads(pre.read_text())
pol = {x["id"]: x for x in p.get("platformPolicy", [])}
res = {x.get("platform"): x for x in p.get("results", [])}
for pid in ["deepseek", "longcat"]:
    q = pol.get(pid, {})
    if not (q.get("allowed") is True and q.get("unfrozenBy") == "ALLOW_FROZEN=1"):
        errors.append("platformPolicy 未显式放行: " + pid)
    r = res.get(pid, {})
    if not (r.get("composerVisible") is True and r.get("looksLikeLogin") is False):
        errors.append("登录态不可用: " + pid)
pl = json.loads(plan.read_text())
for vp in pl["variantPacks"]:
    f = pathlib.Path(vp["path"])
    h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    if h != vp["sha256"]:
        errors.append("变体 Pack hash 不符: " + vp["variant"])
d = json.loads(dist_ev.read_text())
if not (d.get("allPass") and d.get("idempotent")):
    errors.append("dist 一致性证据未通过")
for item in d["files"]:
    f = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/chrome-extension") / item["path"]
    h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    if h != item["sha256"]:
        errors.append("dist 产物已被改动: " + item["path"])
# 变体只差 fresh_session 一个变量的计划态必须仍成立
variants = {v.get("packVariant") for v in pl.get("variants", [])}
if variants and variants != {"no-boundary", "with-boundary"}:
    errors.append("A/B 变体集合异常: " + str(sorted(variants)))
for name in outs:
    for suffix in [".json", ".png"]:
        f = ev / name.replace(".json", suffix)
        if f.exists():
            errors.append("目标路径已存在，拒绝覆盖: " + f.name)
print("PRECHECK", p.get("generatedAt"), "candidates", p.get("candidates"))
print("DIST", [(i["path"], i["sha256"][:16]) for i in d["files"]])
print("PACKS", [(v["variant"], v["sha256"][:16]) for v in pl["variantPacks"]])
print("TARGETS_EMPTY", len(outs) * 2, "checked")
if errors:
    print("PRECONDITION_FAILED", json.dumps(errors, ensure_ascii=False))
    sys.exit(1)
print("PRECONDITION_OK")
PY
if [ $? -ne 0 ]; then
  note "runner aborted" "precondition failed"
  say "=== RUNNER_ABORTED_PRECONDITION_FAILED $(now) ==="
  exit 1
fi

run_round() {
  idx=$1; platform=$2; variant=$3; pack=$4; out=$5
  note "start" "$idx $platform/$variant"
  say "=== ROUND $idx/4 START platform=$platform variant=$variant $(now) ==="
  (
    cd "$EXT" || exit 1
    PLATFORM="$platform" ALLOW_FROZEN=1 PACK_VARIANT="$variant" PACK_PATH="$pack" OUT="$E/$out" \
      node tests/real-machine/l2-platform-auto.mjs
  ) 2>&1 | tee -a "$RUNLOG"
  ec=${PIPESTATUS[0]}
  say "=== ROUND $idx/4 NODE_EXIT=$ec $(now) ==="
  note "node-exit" "$idx exit=$ec"
  # 每轮即时复核：回执存在、步数、边界是否真的执行、B 组硬判据是否成立
  python3 - "$E/$out" "$PROGRESS" "$idx" "$ec" <<'PY' | tee -a "$RUNLOG"
import json, sys, pathlib, datetime
p = pathlib.Path(sys.argv[1]); prog = pathlib.Path(sys.argv[2]); idx = sys.argv[3]; ec = sys.argv[4]
d = json.loads(p.read_text()) if p.exists() else None
ex = (d or {}).get("exec") or {}
res = ex.get("result") or {}
steps = res.get("steps") or []
resets = res.get("sessionResets") or []
pp = (d or {}).get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None
first = resets[0] if resets else None
before = first.get("messageCountBefore") if isinstance(first, dict) else None
after = first.get("messageCountAfter") if isinstance(first, dict) else None
available = first.get("available") if isinstance(first, dict) else None
reset_ok = bool(available is True and isinstance(before, int) and isinstance(after, int) and after < before)
boundary_step_reached = any("fresh_session" in json.dumps(s, ensure_ascii=False) for s in steps)
rec = {
  "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "verify", "round": idx, "receipt": p.name, "nodeExit": int(ec),
  "exists": d is not None, "execSuccess": ex.get("success"),
  "status": res.get("status"), "stepsTotal": len(steps),
  "stepSuccess": sum(1 for s in steps if s.get("success") is True),
  "duration": res.get("duration"),
  "sessionResets": len(resets),
  "resetAvailable": available,
  "resetBefore": before, "resetAfter": after,
  "resetActuallyHappened": reset_ok,
  "boundaryStepReached": boundary_step_reached,
  "policyUnfrozenBy": unfrozen,
}
with prog.open("a") as f:
  f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("VERIFY", json.dumps(rec, ensure_ascii=False))
PY
}

run_round 1 deepseek no-boundary   "$PACK_A" "${OUTS[0]}"
run_round 2 deepseek with-boundary "$PACK_B" "${OUTS[1]}"
run_round 3 longcat  no-boundary   "$PACK_A" "${OUTS[2]}"
run_round 4 longcat  with-boundary "$PACK_B" "${OUTS[3]}"

# ── 收尾：逐份核回执，明确区分「跑完」与「没跑」──────────────────
python3 - "$E" "$PROGRESS" "$SUMMARY" "${OUTS[@]}" <<'PY' | tee -a "$RUNLOG"
import json, sys, pathlib, datetime
ev, prog, summary = [pathlib.Path(x) for x in sys.argv[1:4]]
outs = sys.argv[4:]
items = []
for i, name in enumerate(outs, 1):
    p = ev / name
    items.append({"round": i, "receipt": name, "exists": p.exists(),
                  "bytes": p.stat().st_size if p.exists() else 0})
all_present = all(x["exists"] and x["bytes"] > 0 for x in items)
rec = {"t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "event": "runner-summary", "allReceiptsPresent": all_present, "rounds": len(outs)}
with prog.open("a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
summary.write_text(json.dumps({
    "generatedAt": rec["t"],
    "runner": "ab4-runner-2026-11-12.sh",
    "allFourRoundsExecuted": all_present,
    "rounds": items,
    "note": "allFourRoundsExecuted=true 只表示 4 份回执都落盘，不代表 A/B 判据成立；裁定另由 verdict 生成器机械推导。",
}, ensure_ascii=False, indent=2) + "\n")
print("ALL_RECEIPTS_PRESENT", all_present, json.dumps(items, ensure_ascii=False))
if not all_present:
    sys.exit(1)
PY
FINAL_EC=$?
note "runner done" "ab4 / 4 rounds / allReceipts=$FINAL_EC"
say "=== RUNNER_FINISHED ALL_RECEIPTS_PRESENT_EXIT=$FINAL_EC $(now) ==="
exit "$FINAL_EC"
