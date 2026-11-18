#!/usr/bin/env bash
# ab3 runner: 修复后 dist 的 4 轮 A/B 复跑（2026-11-12）
#
# 依赖：PRECHECK=1 ALLOW_FROZEN=1 已通过、两站登录态可用、dist 为修复后构建。
# 落盘（针对 11-11 后台任务被回收、3 轮回执全丢的教训）：
#   1. stdout 全程 tee -a 到 ab3-rerun-2026-11-12.log；
#   2. 每轮 start / node-exit / verify 即时追加 ab3-rerun-progress-2026-11-12.jsonl；
#   3. 每轮回执由 l2-platform-auto.mjs 自身即时写 OUT（不依赖 runner 缓冲）。
# 4 轮必须串行：两个变体用 mergeStrategy=overwrite 导入同一个 pack_id。
set -u
set -o pipefail

REPO=/Users/raymondna/Documents/AI-collab/ai-collab-base
EXT=$REPO/chrome-extension
E=$REPO/collaboration/results/real-machine-runs/evidence
RUNLOG=$E/ab3-rerun-2026-11-12.log
PROGRESS=$E/ab3-rerun-progress-2026-11-12.jsonl
PACK_A=$E/ab-pack-2026-11-11.no-boundary.json
PACK_B=$E/ab-pack-2026-11-11.with-boundary.json
PRECHECK=$E/L2-precheck-2026-11-12.deepseek-longcat.json
PLAN=$E/session-wall-ab-plan-2026-11-11.json
DIST_EV=$E/dist-consistency-2026-11-12.local-fix.json

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
note() {
  printf '{"t":"%s","event":"%s","round":"%s"}\n' "$(now)" "$1" "$2" >> "$PROGRESS"
}
say() { echo "$1" | tee -a "$RUNLOG"; }

say "=== RUNNER_BEGIN $(now) ==="
note "runner begin" "ab3 / 4 rounds"

# 前置对账：登录态、放行留痕、Pack hash、dist hash、目标路径全空
python3 - "$PRECHECK" "$PLAN" "$DIST_EV" "$E" <<'PY' | tee -a "$RUNLOG"
import json, sys, hashlib, pathlib
pre, plan, dist_ev, ev = [pathlib.Path(x) for x in sys.argv[1:5]]
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
outs = [
    "L2-deepseek-auto-2026-11-12.ab3-no-boundary.json",
    "L2-deepseek-auto-2026-11-12.ab3-with-boundary.json",
    "L2-longcat-auto-2026-11-12.ab3-no-boundary.json",
    "L2-longcat-auto-2026-11-12.ab3-with-boundary.json",
]
for name in outs:
    for suffix in [".json", ".png"]:
        f = ev / name.replace(".json", suffix)
        if f.exists():
            errors.append("目标路径已存在，拒绝覆盖: " + f.name)
print("PRECHECK", p.get("generatedAt"), "candidates", p.get("candidates"))
print("DIST", [(i["path"], i["sha256"][:16]) for i in d["files"]])
print("PACKS", [(v["variant"], v["sha256"][:16]) for v in pl["variantPacks"]])
print("TARGETS_EMPTY", len(errors) == 0)
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
  ec=$?
  say "=== ROUND $idx/4 NODE_EXIT=$ec $(now) ==="
  note "node-exit" "$idx exit=$ec"
  python3 -c '
import json, sys, pathlib, datetime
p = pathlib.Path(sys.argv[1]); prog = pathlib.Path(sys.argv[2]); idx = sys.argv[3]
d = json.loads(p.read_text()) if p.exists() else None
ex = (d or {}).get("exec") or {}
res = ex.get("result") or {}
steps = res.get("steps") or []
resets = res.get("sessionResets") or []
pp = (d or {}).get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None
rec = {
  "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "verify", "round": idx, "receipt": p.name,
  "exists": d is not None, "execSuccess": ex.get("success"),
  "status": res.get("status"), "stepsTotal": len(steps),
  "stepSuccess": sum(1 for s in steps if s.get("success") is True),
  "duration": res.get("duration"), "sessionResets": len(resets),
  "resetAvailable": [bool(r.get("available")) for r in resets],
  "policyUnfrozenBy": unfrozen,
}
with prog.open("a") as f:
  f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("VERIFY", json.dumps(rec, ensure_ascii=False))
' "$E/$out" "$PROGRESS" "$idx" | tee -a "$RUNLOG"
}

run_round 1 deepseek no-boundary  "$PACK_A" L2-deepseek-auto-2026-11-12.ab3-no-boundary.json
run_round 2 deepseek with-boundary "$PACK_B" L2-deepseek-auto-2026-11-12.ab3-with-boundary.json
run_round 3 longcat  no-boundary  "$PACK_A" L2-longcat-auto-2026-11-12.ab3-no-boundary.json
run_round 4 longcat  with-boundary "$PACK_B" L2-longcat-auto-2026-11-12.ab3-with-boundary.json

note "runner done" "ab3 / 4 rounds"
say "=== RUNNER_FINISHED $(now) ==="
