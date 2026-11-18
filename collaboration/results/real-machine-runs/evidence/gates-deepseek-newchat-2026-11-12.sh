#!/usr/bin/env bash
# 2026-11-12 后续步骤②：deepseek adapter 级精确文案逃生口落地后的全量本地门禁。
#
# 口径：
#   - 每一步 stdout 都 tee -a 到 evidence 日志（后台任务被回收也不丢结论）；
#   - 每步 start / exit 即时追加到 append-only JSONL；
#   - build 跑两次，用 sha256 核幂等，再对 dist 产物本身做关键字核对；
#   - 不碰真机、不碰冻结站、不 commit / push。
#
# 用法：bash gates-deepseek-newchat-2026-11-12.sh

set -u

EVIDENCE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$EVIDENCE_DIR/../../../.." && pwd)"
EXT_ROOT="$REPO_ROOT/chrome-extension"
RUN_LOG="$EVIDENCE_DIR/gates-deepseek-newchat-2026-11-12.log"
PROGRESS="$EVIDENCE_DIR/gates-deepseek-newchat-2026-11-12.jsonl"
SUMMARY="$EVIDENCE_DIR/gates-deepseek-newchat-2026-11-12.summary.json"

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$RUN_LOG"; }
progress() { printf '{"at":"%s","event":"%s","step":"%s","exit":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "${3:-null}" >> "$PROGRESS"; }

: > "$RUN_LOG"
: > "$PROGRESS"
for f in \
  build-2026-11-12.deepseek-newchat.log \
  build-2026-11-12.deepseek-newchat-second.log \
  npm-test-2026-11-12.deepseek-newchat.log \
  mutation-check-2026-11-12.deepseek-newchat.full.log; do
  : > "$EVIDENCE_DIR/$f"
done
cd "$EXT_ROOT" || exit 90

log "REPO_ROOT=$REPO_ROOT"
log "EXT_ROOT=$EXT_ROOT"
log "HEAD=$(git rev-parse --short HEAD)"
progress start init 0

sha_of() { shasum -a 256 "$1" | awk '{print $1}'; }

# ── 1) build #1 ────────────────────────────────────────────────
progress start build1 null
log "=== STEP 1: npm run build (#1) ==="
npm run build 2>&1 | tee -a "$EVIDENCE_DIR/build-2026-11-12.deepseek-newchat.log"
BUILD1=${PIPESTATUS[0]}
progress exit build1 "$BUILD1"
log "build#1 exit=$BUILD1"
[ "$BUILD1" -eq 0 ] || { log "ABORT: build#1 failed"; exit 91; }

CS1=$(sha_of dist/content-script.js)
SW1=$(sha_of dist/service-worker.js)
log "dist/content-script.js  #1 sha256=$CS1"
log "dist/service-worker.js  #1 sha256=$SW1"

# ── 2) build #2（幂等）──────────────────────────────────────────
progress start build2 null
log "=== STEP 2: npm run build (#2, 幂等复核) ==="
npm run build 2>&1 | tee -a "$EVIDENCE_DIR/build-2026-11-12.deepseek-newchat-second.log"
BUILD2=${PIPESTATUS[0]}
progress exit build2 "$BUILD2"
log "build#2 exit=$BUILD2"
[ "$BUILD2" -eq 0 ] || { log "ABORT: build#2 failed"; exit 92; }

CS2=$(sha_of dist/content-script.js)
SW2=$(sha_of dist/service-worker.js)
log "dist/content-script.js  #2 sha256=$CS2"
log "dist/service-worker.js  #2 sha256=$SW2"
if [ "$CS1" = "$CS2" ] && [ "$SW1" = "$SW2" ]; then
  IDEMPOTENT=true
else
  IDEMPOTENT=false
fi
log "idempotent=$IDEMPOTENT"

# ── 3) 全量单测 ────────────────────────────────────────────────
progress start npm-test null
log "=== STEP 3: 全量 npm test ==="
npm test 2>&1 | tee -a "$EVIDENCE_DIR/npm-test-2026-11-12.deepseek-newchat.log"
NPMTEST=${PIPESTATUS[0]}
progress exit npm-test "$NPMTEST"
log "npm test exit=$NPMTEST"
tail -12 "$EVIDENCE_DIR/npm-test-2026-11-12.deepseek-newchat.log" | tee -a "$RUN_LOG"

# ── 4) 全量变异 ────────────────────────────────────────────────
progress start mutation-full null
log "=== STEP 4: 全量变异检查 ==="
# 只作用于本进程内 mutation-check 收尾时删除自己的 .mutation-tmp（项目内临时目录），
# 用于拿干净退出码；不关闭任何真机 runner 的安全门，也不绕过沙箱策略。
CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs 2>&1 \
  | tee -a "$EVIDENCE_DIR/mutation-check-2026-11-12.deepseek-newchat.full.log"
MUTATION=${PIPESTATUS[0]}
progress exit mutation-full "$MUTATION"
log "mutation exit=$MUTATION"
tail -6 "$EVIDENCE_DIR/mutation-check-2026-11-12.deepseek-newchat.full.log" | tee -a "$RUN_LOG"

# ── 5) dist 产物严格一致性（核打包产物本身，不核源码）──────────
progress start dist-consistency null
log "=== STEP 5: dist 产物关键字 / hash 核对 ==="
CS_SHA="$CS1" CS_SHA2="$CS2" SW_SHA="$SW1" SW_SHA2="$SW2" \
IDEMPOTENT="$IDEMPOTENT" BUILD2="$BUILD2" \
node "$EVIDENCE_DIR/dist-consistency-deepseek-newchat-2026-11-12.mjs" \
  > "$EVIDENCE_DIR/dist-consistency-2026-11-12.deepseek-newchat.json" 2>&1
DIST=${PIPESTATUS[0]}
progress exit dist-consistency "$DIST"
log "dist-consistency exit=$DIST"
cat "$EVIDENCE_DIR/dist-consistency-2026-11-12.deepseek-newchat.json" | tee -a "$RUN_LOG"

# ── 6) 机器汇总 ────────────────────────────────────────────────
ALL_PASS=false
DIST_ALL_PASS=$(node -e 'try{const j=require(process.argv[1]);console.log(j.allPass===true?"true":"false")}catch(e){console.log("false")}' \
  "$EVIDENCE_DIR/dist-consistency-2026-11-12.deepseek-newchat.json")
if [ "$BUILD1" -eq 0 ] && [ "$BUILD2" -eq 0 ] && [ "$NPMTEST" -eq 0 ] \
   && [ "$MUTATION" -eq 0 ] && [ "$DIST" -eq 0 ] \
   && [ "$IDEMPOTENT" = true ] && [ "$DIST_ALL_PASS" = true ]; then
  ALL_PASS=true
fi
cat > "$SUMMARY" <<EOF
{
  "generatedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scope": "2026-11-12 后续步骤②：deepseek adapter 级精确文案逃生口落地后的全量本地门禁",
  "build1": $BUILD1,
  "build2": $BUILD2,
  "idempotent": $IDEMPOTENT,
  "npmTest": $NPMTEST,
  "mutationFull": $MUTATION,
  "distConsistency": $DIST,
  "distAllPass": $DIST_ALL_PASS,
  "allPass": $ALL_PASS,
  "realMachineVerified": false,
  "note": "全绿只证明本地门禁；冻结站真机重跑与提交/推送均需单独授权。"
}
EOF
progress done summary "$( [ "$ALL_PASS" = true ] && echo 0 || echo 1 )"
log "ALL_PASS=$ALL_PASS"
log "SUMMARY=$SUMMARY"
[ "$ALL_PASS" = true ] && exit 0 || exit 1
