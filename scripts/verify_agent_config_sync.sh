#!/usr/bin/env sh
set -u
cd "$(dirname "$0")/.." || exit 2

pass=0
fail=0

record() {
  if [ "$1" = "0" ]; then
    echo "PASS  $2"
    pass=$((pass + 1))
  else
    echo "FAIL  $2"
    fail=$((fail + 1))
  fi
}

echo "== V1 治理门禁 =="
python3 scripts/validate_collaboration_governance.py --workspace . >/dev/null 2>&1
record $? "governance validation (AGENTS.md + required files)"

echo "== V2 镜像幂等 check =="
python3 scripts/sync_agent_memory.py --check --quiet >/dev/null 2>&1
record $? "memory mirror in sync"

echo "== V3 漂移检测->修复闭环 =="
printf '\n<!-- verify-drift -->\n' >> memory/project.md
python3 scripts/sync_agent_memory.py --check --quiet >/dev/null 2>&1
if [ $? -ne 0 ]; then record 0 "drift detected (expected nonzero)"; else record 1 "drift detected (expected nonzero)"; fi
python3 scripts/sync_agent_memory.py --quiet >/dev/null 2>&1
python3 scripts/sync_agent_memory.py --check --quiet >/dev/null 2>&1
record $? "drift repaired after sync"

echo "== V4 单测 =="
python3 -m pytest tests/unit/test_sync_agent_memory.py -q >/dev/null 2>&1
record $? "unit tests (tests/unit/test_sync_agent_memory.py)"

echo "== V5 AGENTS.md 必读文件纯路径行 =="
ok=0
for f in collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md collaboration/COLLABORATION_GUIDELINES.md collaboration/PROTOCOL.md rules/AI-COLLABORATION-STANDARDS.md; do
  grep -qxF "$f" AGENTS.md || ok=1
done
record $ok "AGENTS.md 4 required refs as bare paths"

echo "== V6 gitignore 白名单 =="
if git check-ignore -q memory/MEMORY.md; then record 1 "memory/MEMORY.md trackable"; else record 0 "memory/MEMORY.md trackable"; fi

echo "== V7 @import 接线 =="
if grep -qxF '@memory/MEMORY.md' CLAUDE.md && [ -f memory/MEMORY.md ]; then record 0 "CLAUDE.md -> @memory/MEMORY.md wired"; else record 1 "CLAUDE.md -> @memory/MEMORY.md wired"; fi

echo
echo "TOTAL: pass=$pass fail=$fail"
if [ "$fail" -eq 0 ]; then exit 0; else exit 1; fi