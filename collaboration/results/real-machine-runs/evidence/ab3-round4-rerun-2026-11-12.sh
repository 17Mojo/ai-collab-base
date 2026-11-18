#!/usr/bin/env bash
# ab3 第 4 轮补跑：longcat / with-boundary（2026-11-12）
#
# 背景：ab3-runner-2026-11-12.sh 的第 4 轮在 launch() 清 SW 缓存时被
# WorkBuddy safe-delete shim 拦截（SAFE_DELETE_BULK_CONFIRM_REQUIRED，
# count 52 > threshold 50，scope=turn），浏览器未启动、页面未打开、
# Pack 未导入、未发送任何内容；verify 记 exists:false。
#
# 本脚本只补这一轮，沿用 ab3 的落盘口径（针对 11-11 后台任务被回收的教训）：
#   1. stdout 全程 tee -a 到独立日志；
#   2. start / node-exit / verify 即时追加独立 JSONL；
#   3. 回执由 l2-platform-auto.mjs 自身即时写 OUT，不依赖 runner 缓冲。
# 不覆盖任何既有证据；不改 dist / 不重建 / 不改任何源码。
# 不设置 CODEBUDDY_SAFE_DELETE_ENABLED=0 —— 单轮清理量远低于 shim 阈值，
# 无需绕过安全门；若仍被拦，如实记录失败而不是禁用守卫。
set -u
set -o pipefail

REPO=/Users/raymondna/Documents/AI-collab/ai-collab-base
EXT=$REPO/chrome-extension
E=$REPO/collaboration/results/real-machine-runs/evidence
RUNLOG=$E/ab3-round4-2026-11-12.log
PROGRESS=$E/ab3-round4-progress-2026-11-12.jsonl
PACK_B=$E/ab-pack-2026-11-11.with-boundary.json
PRECHECK=$E/L2-precheck-2026-11-12.deepseek-longcat.json
PLAN=$E/session-wall-ab-plan-2026-11-11.json
DIST_EV=$E/dist-consistency-2026-11-12.local-fix.json
OUT=$E/L2-longcat-auto-2026-11-12.ab3-with-boundary.json
SHOT=$E/L2-longcat-auto-2026-11-12.ab3-with-boundary.png

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
note() {
  printf '{"t":"%s","event":"%s","round":"%s"}\n' "$(now)" "$1" "$2" >> "$PROGRESS"
}
say() { echo "$1" | tee -a "$RUNLOG"; }

say "=== ROUND4_RERUN_BEGIN $(now) ==="
note "runner begin" "ab3 round 4 / longcat with-boundary"

# 前置对账：只补第 4 轮，目标路径必须仍为空；放行留痕 / Pack / dist 与 ab3 一致
python3 - "$PRECHECK" "$PLAN" "$DIST_EV" "$OUT" "$SHOT" "$PACK_B" <<'PY' | tee -a "$RUNLOG"
import json, sys, hashlib, pathlib
pre, plan, dist_ev, out, shot, pack_b = [pathlib.Path(x) for x in sys.argv[1:7]]
errors = []
p = json.loads(pre.read_text())
pol = {x["id"]: x for x in p.get("platformPolicy", [])}
res = {x.get("platform"): x for x in p.get("results", [])}
q = pol.get("longcat", {})
if not (q.get("allowed") is True and q.get("unfrozenBy") == "ALLOW_FROZEN=1"):
    errors.append("longcat 未显式放行")
r = res.get("longcat", {})
if not (r.get("composerVisible") is True and r.get("looksLikeLogin") is False):
    errors.append("longcat 登录态不可用")
pl = json.loads(plan.read_text())
vp = next((v for v in pl["variantPacks"] if v["variant"] == "with-boundary"), None)
if not vp:
    errors.append("计划里没有 with-boundary 变体")
else:
    h = hashlib.sha256(pack_b.read_bytes()).hexdigest() if pack_b.exists() else None
    if h != vp["sha256"]:
        errors.append("with-boundary Pack hash 不符")
    d = json.loads(pack_b.read_text())
    fresh = [(s.get("id"), s["fresh_session"]) for s in d["workflow"]["steps"] if "fresh_session" in s]
    if fresh != [("step_8_output", "prefer")]:
        errors.append("变体 Pack 的 fresh_session 位置被改动: " + repr(fresh))
d = json.loads(dist_ev.read_text())
if not (d.get("allPass") and d.get("idempotent")):
    errors.append("dist 一致性证据未通过")
for item in d["files"]:
    f = pathlib.Path("/Users/raymondna/Documents/AI-collab/ai-collab-base/chrome-extension") / item["path"]
    h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    if h != item["sha256"]:
        errors.append("dist 产物已被改动: " + item["path"])
for f in (out, shot):
    if f.exists():
        errors.append("目标路径已存在，拒绝覆盖: " + f.name)
print("PRECHECK", p.get("generatedAt"), "candidates", p.get("candidates"))
print("DIST", [(i["path"], i["sha256"][:16]) for i in d["files"]])
print("PACK_B_SHA256", hashlib.sha256(pack_b.read_bytes()).hexdigest()[:16])
print("TARGETS_EMPTY", not any(x.name in (out.name, shot.name) for x in (out, shot) if x.exists()))
print("ERRORS", len(errors))
if errors:
    print("PRECONDITION_FAILED", json.dumps(errors, ensure_ascii=False))
    sys.exit(1)
print("PRECONDITION_OK")
PY
if [ $? -ne 0 ]; then
  note "runner aborted" "precondition failed"
  say "=== ROUND4_ABORTED_PRECONDITION_FAILED $(now) ==="
  exit 1
fi

note "start" "4 longcat/with-boundary"
say "=== ROUND 4/4 START platform=longcat variant=with-boundary $(now) ==="
(
  cd "$EXT" || exit 1
  PLATFORM=longcat ALLOW_FROZEN=1 PACK_VARIANT=with-boundary PACK_PATH="$PACK_B" \
    OUT="$OUT" SHOT="$SHOT" node tests/real-machine/l2-platform-auto.mjs
) 2>&1 | tee -a "$RUNLOG"
ec=$?
say "=== ROUND 4/4 NODE_EXIT=$ec $(now) ==="
note "node-exit" "4 exit=$ec"

python3 - "$OUT" "$PROGRESS" <<'PY' | tee -a "$RUNLOG"
import json, sys, pathlib, datetime
p = pathlib.Path(sys.argv[1]); prog = pathlib.Path(sys.argv[2])
d = json.loads(p.read_text()) if p.exists() else None
ex = (d or {}).get("exec") or {}
res = ex.get("result") or {}
steps = res.get("steps") or []
resets = res.get("sessionResets") or []
pp = (d or {}).get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None
rec = {
  "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "verify", "round": "4", "receipt": p.name,
  "exists": d is not None, "execSuccess": ex.get("success"),
  "status": res.get("status"), "stepsTotal": len(steps),
  "stepSuccess": sum(1 for s in steps if s.get("success") is True),
  "duration": res.get("duration"), "sessionResets": len(resets),
  "resetAvailable": [bool(r.get("available")) for r in resets],
  "resetStrategy": [r.get("strategy") for r in resets],
  "messageCountBefore": [r.get("messageCountBefore") for r in resets],
  "messageCountAfter": [r.get("messageCountAfter") for r in resets],
  "failedSteps": [
    {"id": s.get("id"), "duration": s.get("duration"), "error": s.get("error")}
    for s in steps if s.get("success") is not True
  ],
  "policyUnfrozenBy": unfrozen,
}
with prog.open("a") as f:
  f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("VERIFY", json.dumps(rec, ensure_ascii=False))
PY
note "runner done" "ab3 round 4"
say "=== ROUND4_RERUN_FINISHED $(now) ==="
