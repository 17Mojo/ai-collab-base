#!/usr/bin/env bash
set -uo pipefail
[ -d .git ] || { echo "错误：当前目录不是 git 仓库（$(pwd)）"; exit 1; }
OUT="docs/FACTS_$(date +%Y-%m-%d_%H%M%S).md"
mkdir -p docs
{
  echo "# 项目事实快照"
  echo
  echo "**生成时间**: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "**生成方式**: scripts/gen_facts.sh（自动生成，请勿手工编辑）"
  echo "**仓库路径**: $(pwd)"
  echo "**仓库 HEAD**: $(git rev-parse HEAD 2>&1)"
  echo
  echo "## 1. Git 状态"
  echo '```'; echo "\$ git status --short --branch"; git status --short --branch 2>&1 | head -50; echo '```'
  echo
  echo "## 2. 最近 20 次提交"
  echo '```'; git log --oneline -20 2>&1; echo '```'
  echo
  echo "## 3. 远端同步状态"
  echo '```'
  echo "unpushed=$(git rev-list --count HEAD..origin/main 2>&1)"
  echo "ahead=$(git rev-list --count origin/main..HEAD 2>&1)"
  echo '```'
  echo
  echo "## 4. 目录树（2 层）"
  echo '```'
  find . -maxdepth 2 -type d -not -path '*/.git*' -not -path '*/node_modules*' \
    -not -path '*/__pycache__*' -not -path '*/.pytest_cache*' -not -path '*/venv*' -not -path '*/.venv*' | sort
  echo '```'
  echo
  echo "## 5. Python 模块行数 Top 40"
  echo '```'
  find . -name '*.py' -not -path '*/.git/*' -not -path '*/venv/*' -not -path '*/.venv/*' \
    | xargs wc -l 2>/dev/null | sort -rn | head -41 < /dev/null
  echo '```'
  echo
  echo "## 6. CLI 实际入口"
  echo '```'
  echo "\$ ls -d src ai_collab 2>&1"; ls -d src ai_collab 2>&1
  echo "\$ python3 -m ai_collab.cli --help"; python3 -m ai_collab.cli --help 2>&1 | head -70
  echo '```'
  echo
  echo "## 7. 角色编排配置"
  echo '```'
  echo "\$ cat config/agent-orchestration.json"; cat config/agent-orchestration.json 2>&1
  echo '```'
  echo
  echo "## 8. Chrome 适配器"
  echo '```'
  find . -path '*adapter*' -name '*.js' -not -path '*/node_modules/*' 2>&1 | sort
  echo '```'
  echo
  echo "## 9. 测试收集"
  echo '```'
  echo "\$ python3 -m pytest -q --collect-only 2>&1 | tail -5"
  python3 -m pytest -q --collect-only 2>&1 | tail -5
  echo '```'
  echo
  echo "## 10. 活跃任务"
  echo '```'
  echo "\$ python3 -m ai_collab.cli tasks list 2>&1"; python3 -m ai_collab.cli tasks list 2>&1 | head -40
  echo '```'
  echo
  echo "## 11. 关键路径存在性"
  echo '```'
  for f in ARCHITECTURE.md CLAUDE.md README.md docs/ARCHAEOLOGY_CODE_INVENTORY.md \
           collaboration/PROTOCOL.md collaboration/results openspec local-backend \
           chrome-extension packs tests/unit pyproject.toml requirements.txt; do
    if [ -e "$f" ]; then echo "EXISTS  $f"; else echo "MISSING $f"; fi
  done
  echo '```'
  echo
  echo "## 12. 最大的 20 个文件"
  echo '```'
  find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' \
    | xargs ls -la 2>/dev/null | sort -k5 -rn | head -20 < /dev/null
  echo '```'
} > "$OUT"
echo "已生成: $OUT"
echo "绝对路径: $(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
