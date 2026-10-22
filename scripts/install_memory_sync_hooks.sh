#!/usr/bin/env sh
set -e
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
hooks_dir="$repo_root/.git/hooks"
mkdir -p "$hooks_dir"
cat > "$hooks_dir/pre-commit" <<'HOOK'
#!/usr/bin/env sh
if [ -f scripts/sync_agent_memory.py ]; then
  python3 scripts/sync_agent_memory.py --check --quiet || \
    echo "[memory-sync] memory/ mirror stale; run: python3 scripts/sync_agent_memory.py"
fi
exit 0
HOOK
chmod +x "$hooks_dir/pre-commit"
echo "installed: $hooks_dir/pre-commit"
echo "near-real-time cron:"
echo "*/5 * * * * cd $repo_root && python3 scripts/sync_agent_memory.py --quiet"