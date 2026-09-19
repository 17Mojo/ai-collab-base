"""
项目体检脚本 - 自动生成项目状态报告

输出: collaboration/results/HEALTH_CHECK_<date>.md

Usage:
    python scripts/project_healthcheck.py
    python scripts/project_healthcheck.py --json  # 机器可读
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd=None, timeout=60):
    """Run shell command, return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd or REPO_ROOT, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -2, "", str(e)


def section(title):
    return f"\n## {title}\n"


def check_tests():
    """1. 跑测试 + 拿覆盖率"""
    rc, out, err = run(
        "python -m pytest tests/unit -q --no-header -p no:warnings "
        "--cov=ai_collab --cov-report= --no-cov-on-fail 2>&1 | tail -3",
        timeout=180
    )
    lines = out.split("\n") if out else []
    last = lines[-1] if lines else ""
    passed, skipped, failed = 0, 0, 0
    import re
    for pattern, attr in [
        (r"(\d+)\s*passed", "passed"),
        (r"(\d+)\s*failed", "failed"),
        (r"(\d+)\s*skipped", "skipped"),
    ]:
        m = re.search(pattern, last)
        if m:
            if attr == "passed":
                passed = int(m.group(1))
            elif attr == "failed":
                failed = int(m.group(1))
            elif attr == "skipped":
                skipped = int(m.group(1))
    # 单独拿覆盖率数字
    cov_rc, cov_out, _ = run("coverage report 2>&1 | tail -3")
    cov_pct = "N/A"
    cov_miss = "N/A"
    for line in (cov_out or "").split("\n"):
        if line.startswith("TOTAL"):
            parts = line.split()
            if len(parts) >= 4:
                cov_pct = parts[-1].rstrip("%")
                cov_miss = parts[-2]
    return {
        "passed": passed, "skipped": skipped, "failed": failed,
        "coverage_pct": cov_pct, "miss_lines": cov_miss,
        "last_line": last
    }


def check_git():
    """2. git 状态"""
    rc, out, _ = run("git log --oneline -10")
    recent_commits = out.split("\n") if out else []
    rc, out, _ = run("git status --short")
    untracked = [l for l in out.split("\n") if l.startswith("??")] if out else []
    modified = [l for l in out.split("\n") if l.startswith(" M") or l.startswith("M ")] if out else []
    rc, out, _ = run("git remote -v")
    remotes = out
    rc, out, _ = run("git log --oneline origin/main..HEAD 2>/dev/null")
    ahead = out.split("\n") if out and out.strip() else []
    return {
        "recent_commits": recent_commits,
        "untracked_count": len(untracked),
        "modified_count": len(modified),
        "untracked_files": untracked,
        "remotes": remotes,
        "ahead_of_origin": ahead,
    }


def check_code_health():
    """3. 代码健康 (行数、文件数)"""
    rc, out, _ = run(
        "find ai_collab -name '*.py' -not -path '*/__pycache__/*' | wc -l"
    )
    py_files = int(out) if out.isdigit() else 0
    rc, out, _ = run(
        "find ai_collab -name '*.py' -not -path '*/__pycache__/*' "
        "-exec wc -l {} + | tail -1"
    )
    parts = out.split() if out else []
    py_lines = int(parts[0]) if parts and parts[0].isdigit() else 0
    rc, out, _ = run(
        "find tests/unit -name 'test_*.py' | wc -l"
    )
    test_files = int(out) if out.isdigit() else 0
    rc, out, _ = run(
        "find tests/unit -name 'test_*.py' -exec wc -l {} + | tail -1"
    )
    parts = out.split() if out else []
    test_lines = int(parts[0]) if parts and parts[0].isdigit() else 0
    return {
        "py_files": py_files, "py_lines": py_lines,
        "test_files": test_files, "test_lines": test_lines,
        "test_to_code_ratio": round(test_lines / py_lines, 2) if py_lines else 0,
    }


def check_coverage_breakdown():
    """4. 关键模块覆盖率分解"""
    rc, out, _ = run(
        "coverage report 2>&1 | grep -E '^ai_collab' "
        "| awk '{print $1, $5}' | sort -k2 -n | head -10"
    )
    low_modules = []
    for line in (out or "").split("\n"):
        parts = line.split()
        if len(parts) == 2:
            try:
                pct = int(parts[1].rstrip("%"))
                if pct < 80:
                    low_modules.append((parts[0], pct))
            except Exception:
                pass
    return {"low_coverage_modules": low_modules}


def check_static_analysis():
    """5. 静态检查状态"""
    rc, out, _ = run("ruff check ai_collab 2>&1 | tail -3")
    ruff_errors = 0
    for line in (out or "").split("\n"):
        if "Found" in line and "error" in line:
            try:
                ruff_errors = int(line.split()[1])
            except Exception:
                pass
    rc, out, _ = run("mypy ai_collab 2>&1 | tail -3")
    mypy_errors = 0
    for line in (out or "").split("\n"):
        if "Found" in line and "error" in line:
            try:
                mypy_errors = int(line.split()[1])
            except Exception:
                pass
    return {
        "ruff_errors": ruff_errors,
        "mypy_errors": mypy_errors,
    }


def check_dependencies():
    """6. 依赖安全（如果 pip-audit 可用）"""
    rc, out, _ = run("which pip-audit 2>&1")
    has_pip_audit = bool(out)
    pip_audit_status = "skipped" if not has_pip_audit else "available"
    return {"pip_audit": pip_audit_status}


def check_health_rules():
    """7. 应用 CLAUDE.md 中 3 条长期经验"""
    rc, out, _ = run("grep -c '长期经验' CLAUDE.md 2>/dev/null || echo 0")
    try:
        rules_in_claude = int(out) > 0 if out else False
    except ValueError:
        rules_in_claude = False
    return {
        "claude_md_has_rules": rules_in_claude,
        "gitignore_present": Path(".gitignore").exists(),
    }


def render_markdown(data):
    """渲染 Markdown 报告"""
    lines = []
    lines.append(f"# 项目体检报告 - {data['generated_at']}")
    lines.append("")
    lines.append(f"> 自动生成于 `{datetime.now().isoformat()}` by `scripts/project_healthcheck.py`")
    lines.append("")

    # 1. 测试
    lines.append(section("测试"))
    t = data["tests"]
    status = "✅" if t["failed"] == 0 else "🔴"
    lines.append(f"- {status} **测试结果**: {t['passed']} passed, "
                 f"{t['failed']} failed, {t['skipped']} skipped")
    lines.append(f"- **覆盖率**: {t['coverage_pct']}% "
                 f"(miss {t['miss_lines']} 行)")
    if t["last_line"]:
        lines.append(f"```\n{t['last_line']}\n```")

    # 2. Git
    lines.append(section("Git 状态"))
    g = data["git"]
    lines.append(f"- **最近 commit** ({len(g['recent_commits'])}):")
    for c in g["recent_commits"][:5]:
        lines.append(f"  - `{c}`")
    lines.append(f"- **未跟踪文件**: {g['untracked_count']} 个")
    lines.append(f"- **已修改未提交**: {g['modified_count']} 个")
    if g["untracked_files"]:
        for f in g["untracked_files"][:5]:
            lines.append(f"  - `{f}`")
    if g["ahead_of_origin"]:
        lines.append(f"- ⚠️ **领先 origin/main {len(g['ahead_of_origin'])} 个 commit** (未推送)")
    else:
        lines.append("- ✅ 与 origin/main 同步")

    # 3. 代码
    lines.append(section("代码规模"))
    c = data["code_health"]
    lines.append(f"- **生产代码**: {c['py_files']} 文件 / {c['py_lines']} 行")
    lines.append(f"- **测试代码**: {c['test_files']} 文件 / {c['test_lines']} 行")
    lines.append(f"- **测试/代码比**: {c['test_to_code_ratio']} "
                 f"({'✅ 健康' if c['test_to_code_ratio'] >= 0.5 else '⚠️ 偏低'})")

    # 4. 覆盖率分解
    lines.append(section("覆盖率分解（<80% 模块）"))
    cb = data["coverage_breakdown"]
    if cb["low_coverage_modules"]:
        lines.append("| 模块 | 覆盖率 |")
        lines.append("|------|--------|")
        for mod, pct in cb["low_coverage_modules"]:
            lines.append(f"| `{mod}` | {pct}% |")
    else:
        lines.append("✅ 所有模块覆盖率 ≥ 80%")

    # 5. 静态检查
    lines.append(section("静态检查"))
    s = data["static_analysis"]
    lines.append(f"- **ruff**: {s['ruff_errors']} 个问题 "
                 f"({'✅' if s['ruff_errors'] < 50 else '⚠️'})")
    lines.append(f"- **mypy**: {s['mypy_errors']} 个错误 "
                 f"({'✅' if s['mypy_errors'] < 50 else '⚠️'})")

    # 6. 依赖
    lines.append(section("依赖安全"))
    d = data["dependencies"]
    lines.append(f"- **pip-audit**: {d['pip_audit']}")

    # 7. 健康规则
    lines.append(section("项目健康规则"))
    h = data["health_rules"]
    lines.append(f"- **CLAUDE.md 含 3 条长期经验**: "
                 f"{'✅' if h['claude_md_has_rules'] else '🔴'}")
    lines.append(f"- **.gitignore 存在**: "
                 f"{'✅' if h['gitignore_present'] else '🔴'}")

    # 总评
    lines.append(section("总评"))
    score = 0
    score += 30 if data["tests"]["failed"] == 0 else 0
    try:
        cov = float(data["tests"]["coverage_pct"])
        if cov >= 80:
            score += 25
        elif cov >= 70:
            score += 15
    except Exception:
        pass
    score += 20 if data["git"]["untracked_count"] == 0 else 0
    score += 15 if not data["git"]["ahead_of_origin"] else 0
    score += 10 if data["health_rules"]["claude_md_has_rules"] else 0
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D"
    lines.append(f"### 🏥 总分: {score}/100 ({grade})")
    lines.append("")
    if score >= 90:
        lines.append("**健康状态**: 优秀 — 项目状态极佳，可放心推进")
    elif score >= 80:
        lines.append("**健康状态**: 良好 — 关键指标达标，可持续维护")
    elif score >= 70:
        lines.append("**健康状态**: 中等 — 建议补强短板")
    else:
        lines.append("**健康状态**: 需关注 — 存在多个待改进项")
    lines.append("")

    lines.append("---")
    lines.append(f"\n*报告路径: `collaboration/results/HEALTH_CHECK_{data['date_stamp']}.md`*")
    lines.append("*查看历史: `ls collaboration/results/HEALTH_CHECK_*.md`*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON 而非 Markdown")
    args = parser.parse_args()

    print("🔍 Running project health check...")
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "date_stamp": datetime.now().strftime("%Y-%m-%d"),
        "tests": check_tests(),
        "git": check_git(),
        "code_health": check_code_health(),
        "coverage_breakdown": check_coverage_breakdown(),
        "static_analysis": check_static_analysis(),
        "dependencies": check_dependencies(),
        "health_rules": check_health_rules(),
    }

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0

    md = render_markdown(data)

    # 写到文件
    out_dir = REPO_ROOT / "collaboration" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"HEALTH_CHECK_{data['date_stamp']}.md"
    out_path.write_text(md, encoding="utf-8")

    # 也打印到 stdout
    print(md)
    print(f"\n📄 报告已写入: {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
