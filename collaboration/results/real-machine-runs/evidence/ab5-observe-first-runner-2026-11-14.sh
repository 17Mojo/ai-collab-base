#!/usr/bin/env bash
# ab5 observe-first runner：用户 2026-11-14 明令「先跑 A 单轮，判无墙即停」。
#
# 与 ab3/ab4 的本质区别：这里**只有 1 轮**。
#   A = deepseek / no-boundary（用户 AskUserQuestion q-0 裁定，证据 ab5-gate-a-platform-ruling-2026-11-14.json）
#   B 不在本 runner 内：只有 Gate A 6 条机器判据全成立 + 人工视觉闸确认后，
#     才由独立补跑脚本执行同站 B。判无墙即停机，不跑 B、不跑 longcat。
#
# 授权：用户 2026-11-14 明令解冻 deepseek / longcat 并按 observe-first gate 重跑。
#       冻结白名单代码未改；本轮逐次 ALLOW_FROZEN=1，回执 platformPolicy 可复核；用完仍是冻结。
#       提交 / push 用户明示「单独授权、按提交与文件集合分别确认」⇒ 本 runner 不碰 git。
#
# 落盘口径（11-11 后台任务被回收、3 轮回执全丢的教训）：
#   stdout 全程 tee -a；start / node-exit / verify 即时写 append-only JSONL；
#   回执由 l2-platform-auto.mjs 自身即时写 OUT，不依赖 runner 缓冲。
# 不设置 CODEBUDDY_SAFE_DELETE_ENABLED=0：本轮 SW 缓存仅 13 项，远低于 shim 的 50 阈值。
set -u
set -o pipefail

REPO=/Users/raymondna/Documents/AI-collab/ai-collab-base
EXT=$REPO/chrome-extension
E=$REPO/collaboration/results/real-machine-runs/evidence
RUNLOG=$E/ab5-observe-first-2026-11-14.log
PROGRESS=$E/ab5-observe-first-progress-2026-11-14.jsonl
VERIFY_JSON=$E/ab5-observe-first-verify-2026-11-14.json
PACK_A=$E/ab-pack-2026-11-11.no-boundary.json
PRECHECK=$E/L2-precheck-2026-11-14.ab5.deepseek-longcat.json
PRECOND=$E/ab5-precondition-2026-11-14.json
RULING=$E/ab5-gate-a-platform-ruling-2026-11-14.json
PLAN=$E/ab5-observe-first-plan-2026-11-12.json
DIST_EV=$E/dist-consistency-2026-11-12.deepseek-newchat.json
OUT_NAME=L2-deepseek-auto-2026-11-14.ab5-no-boundary.json
OUT=$E/$OUT_NAME

# append-only：绝不覆盖既有证据
touch "$RUNLOG" "$PROGRESS"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
note() { printf '{"t":"%s","event":"%s","round":"%s"}\n' "$(now)" "$1" "$2" >> "$PROGRESS"; }
say() { echo "$1" | tee -a "$RUNLOG"; }

say "=== OBSERVE_FIRST_BEGIN $(now) ==="
say "=== RULING: platform=deepseek, roundsTotal=1, user AskUserQuestion q-0 2026-11-14 ==="
say "=== AUTHORIZED_UNFREEZE: user 2026-11-14; ALLOW_FROZEN=1 per command; whitelist code unchanged ==="
note "runner begin" "ab5 observe-first / 1 round A only"

# ── 前置对账：登录态 / 放行留痕 / 裁定 / dist / Pack / 目标路径全空 ──
python3 - "$PRECHECK" "$PRECOND" "$RULING" "$PLAN" "$DIST_EV" "$E" "$OUT_NAME" "$EXT" <<'PY' 2>&1 | tee -a "$RUNLOG"
import json, sys, hashlib, pathlib
pre, precond, ruling, plan_p, dist_ev = [pathlib.Path(x) for x in sys.argv[1:6]]
ev, out_name, ext = pathlib.Path(sys.argv[6]), sys.argv[7], pathlib.Path(sys.argv[8])
errors = []

# 1) 预检：两站显式放行 + 登录态可用；且必须是 2026-11-14 的 ab5 预检，不是旧预检
p = json.loads(pre.read_text())
pol = {x["id"]: x for x in p.get("platformPolicy", [])}
res = {x.get("platform"): x for x in p.get("results", [])}
for pid in ("deepseek", "longcat"):
    q = pol.get(pid, {})
    if not (q.get("allowed") is True and q.get("unfrozenBy") == "ALLOW_FROZEN=1"):
        errors.append("platformPolicy 未显式放行: " + pid)
    r = res.get(pid, {})
    if not (r.get("composerVisible") is True and r.get("looksLikeLogin") is False):
        errors.append("登录态不可用: " + pid)
if "2026-11-14" not in p.get("generatedAt", ""):
    errors.append("预检不是本轮 2026-11-14 生成的")

# 2) 前置对账证据本身必须 pass
pc = json.loads(precond.read_text())
if pc.get("preconditionPass") is not True or pc.get("errors"):
    errors.append("ab5 前置对账未通过")

# 3) 用户裁定必须存在且是单站 deepseek、单轮
ru = json.loads(ruling.read_text())
ch = ru.get("userChoice", {})
eff = ru.get("effectivePlan", {})
if ch.get("platform") != "deepseek":
    errors.append("用户裁定首轮平台不是 deepseek")
if eff.get("roundsTotal") != 1 or eff.get("round1", {}).get("variant") != "no-boundary":
    errors.append("裁定有效计划不是 1 轮 A")

# 4) dist 产物与一致性证据逐文件 hash 复核
d = json.loads(dist_ev.read_text())
if not (d.get("allPass") and d.get("idempotent")):
    errors.append("dist 一致性证据未通过")
for item in d["files"]:
    f = ext / item["path"]
    h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    if h != item["sha256"]:
        errors.append("dist 产物已被改动: " + item["path"])

# 5) 变体 Pack hash 与 plan 声明一致（只核 A 组，B 本 runner 不跑）
pl = json.loads(plan_p.read_text())
expected = {x["variant"]: x["sha256"] for x in pl["packs"]}
pack_a = ev / "ab-pack-2026-11-11.no-boundary.json"
h_a = hashlib.sha256(pack_a.read_bytes()).hexdigest() if pack_a.exists() else None
if h_a != expected.get("no-boundary"):
    errors.append("A 组变体 Pack hash 不符")
if pl.get("status") != "plan-only / NOT-EXECUTED":
    errors.append("ab5 plan 状态异常，可能被偷跑")

# 6) 目标 .json / .png / .dom-samples.json 全部为空，绝不覆盖
stem = out_name[: -len(".json")] if out_name.endswith(".json") else out_name
for suffix in (".json", ".png", ".dom-samples.json"):
    f = ev / (stem + suffix)
    if f.exists():
        errors.append("目标路径已存在，拒绝覆盖: " + f.name)

print("PRECHECK", p.get("generatedAt"), "candidates", p.get("candidates"))
print("RULING", ch.get("platform"), "rounds", eff.get("roundsTotal"))
print("DIST", [(i["path"], i["sha256"][:16]) for i in d["files"]])
print("PACK_A", h_a[:16] if h_a else None)
print("TARGETS_EMPTY", 3, "checked for", stem)
if errors:
    print("PRECONDITION_FAILED", json.dumps(errors, ensure_ascii=False))
    sys.exit(1)
print("PRECONDITION_OK observe-first / 1 round / deepseek no-boundary")
PY
PRE_EC=${PIPESTATUS[0]}
if [ "$PRE_EC" -ne 0 ]; then
  note "runner aborted" "precondition failed"
  say "=== OBSERVE_FIRST_ABORTED_PRECONDITION_FAILED $(now) ==="
  exit 1
fi

# ── Gate A 唯一的 1 轮：deepseek / no-boundary ──────────────────
note "start" "1/1 deepseek/no-boundary"
say "=== ROUND 1/1 (A) START platform=deepseek variant=no-boundary $(now) ==="
(
  cd "$EXT" || exit 1
  PLATFORM=deepseek ALLOW_FROZEN=1 PACK_VARIANT=no-boundary PACK_PATH="$PACK_A" OUT="$OUT" \
    node tests/real-machine/l2-platform-auto.mjs
) 2>&1 | tee -a "$RUNLOG"
NODE_EC=${PIPESTATUS[0]}
say "=== ROUND 1/1 NODE_EXIT=$NODE_EC $(now) ==="
note "node-exit" "1/1 exit=$NODE_EC"

# 每轮即时复核：回执存在性 + Gate A 6 条机器判据的原始字段（裁定另由只读脚本机械推导）
python3 - "$OUT" "$PROGRESS" "$VERIFY_JSON" "$NODE_EC" <<'PY' 2>&1 | tee -a "$RUNLOG"
import json, sys, pathlib, datetime
p = pathlib.Path(sys.argv[1]); prog = pathlib.Path(sys.argv[2])
verify_path = pathlib.Path(sys.argv[3]); ec = sys.argv[4]
d = json.loads(p.read_text()) if p.exists() else None
ex = (d or {}).get("exec") or {}
r = ex.get("result") or {}
steps = r.get("steps") or []
resets = r.get("sessionResets") or []
pp = (d or {}).get("platformPolicy")
unfrozen = pp.get("unfrozenBy") if isinstance(pp, dict) else None
failed = [s for s in steps if s.get("success") is not True]
first_failed = failed[0] if failed else None
rec = {
  "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "event": "verify", "round": "1/1", "receipt": p.name, "nodeExit": int(ec),
  "exists": d is not None,
  "platform": (d or {}).get("platform"),
  "packVariant": (d or {}).get("packVariant"),
  "policyUnfrozenBy": unfrozen,
  "execSuccess": ex.get("success"),
  "status": r.get("status"),
  "duration": r.get("duration"),
  "stepsTotal": len(steps),
  "stepSuccess": sum(1 for s in steps if s.get("success") is True),
  "firstFailedStepId": first_failed.get("id") if isinstance(first_failed, dict) else None,
  "firstFailedStepError": first_failed.get("error") if isinstance(first_failed, dict) else None,
  "earlierStepsAllSucceeded": all(s.get("success") is True for s in steps[:7]) and len(steps) >= 7,
  "sessionResets": len(resets),
  "wallStepDurationMs": next((s.get("duration") for s in steps if s.get("id") == "step_8_output"), None),
}
with prog.open("a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
verify_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
print("VERIFY", json.dumps(rec, ensure_ascii=False))
PY

note "verify written" "1/1"
say "=== OBSERVE_FIRST_A_DONE $(now) | B NOT RUN | gate A verdict is a separate read-only step ==="

# 收尾：只核「A 单轮回执确实落盘」，不等于 Gate A 成立，更不等于命题成立
python3 - "$OUT" "$RUNLOG" <<'PY' 2>&1 | tee -a "$RUNLOG"
import json, sys, pathlib
p = pathlib.Path(sys.argv[1])
ok = p.exists() and p.stat().st_size > 0
print("RECEIPT_PRESENT", ok, p.name, p.stat().st_size if p.exists() else 0)
if ok:
    d = json.loads(p.read_text())
    print("RECEIPT_PLATFORM", d.get("platform"), "VARIANT", d.get("packVariant"))
if not ok:
    sys.exit(1)
PY
FINAL_EC=${PIPESTATUS[0]}
note "runner done" "ab5 observe-first / A only / receiptExit=$FINAL_EC"
say "=== OBSERVE_FIRST_FINISHED RECEIPT_PRESENT_EXIT=$FINAL_EC $(now) ==="
say "=== NEXT: run ab5-gate-a-verdict-2026-11-14.py (read-only) to decide ABORT_NO_WALL or proceed to B ==="
exit "$FINAL_EC"
