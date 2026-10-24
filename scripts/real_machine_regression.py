"""
真机回归记录管理器（L1 自动化只读 + L2 人工真实发送）

这个脚本**不做检测**，只做**记录与对账**。检测分两层：

- **L1（自动化、只读）**：生产 adapter 源码打进真实站点页面，调用真实方法，
  判定 DOM 契约是否还对得上。证据是探针写出的 JSON 判定文件。
- **L2（人工、需登录、真实发送）**：人拿已登录的浏览器跑一遍真实 Prompt Pack，
  截图 + 日志留证。

脚本的价值在于**把「没跑」和「跑过」在机器层面区分开**：
没有证据文件的 `pass` 会被判为记录不一致；L1 证据里写着未验证（登录墙/拦截）
却记成 `pass`，会被交叉核对抓出来。

三层不可互相替代：

- L1 全绿 **≠** L2 全绿（L1 只读，不发消息，不等回复）
- L1 + L2 全绿 **≠** 「第一个外部用户」——路线 A/B 决策门禁缺的正是后者，
  本脚本**永远不会**把路线门禁判为关闭。

用法:
    python3 scripts/real_machine_regression.py init \\
        --run-id RMR-2026-10-25-01 --platforms chatgpt,claude,gemini \\
        --locales zh-CN,en-US --operator claude_code

    python3 scripts/real_machine_regression.py record \\
        --run-id RMR-2026-10-25-01 --layer L1 --platform gemini \\
        --status pass --locale zh-CN \\
        --evidence "探针判定 sendButtonVerdict=ok" \\
        --evidence-file collaboration/results/real-machine-runs/RMR-2026-10-25-01-L1-gemini.json

    python3 scripts/real_machine_regression.py verify --run-id RMR-2026-10-25-01
    python3 scripts/real_machine_regression.py list

退出码（verify）:
    0 = 记录一致且完整（L1/L2 全部 pass）
    1 = 记录不一致（有硬错误）
    2 = 记录一致但未跑完（还有 L2 未跑）
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = "collaboration/results/real-machine-runs"

SCHEMA_VERSION = 1
LAYERS = ("L1", "L2")
STATUSES = ("pass", "fail", "unverified", "not-run")
STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_NEEDS_REASON = ("unverified", "not-run")

# 路线 A/B 决策门禁的现状：本脚本只能产出 L1/L2 证据，
# 「第一个外部用户」不在本脚本的证据范围内，因此门禁恒为开启。
ROUTE_GATE_NOTE = (
    "路线 A/B 决策门禁：本记录只覆盖 L1/L2 证据，"
    "不含「第一个外部用户」——门禁仍为开启状态，不得据此拍板路线。"
)


def now_iso() -> str:
    """当前时间（本地时区，秒级）。"""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def results_dir(workspace: Path, override: str | None = None) -> Path:
    """记录目录（默认落在 collaboration/results/real-machine-runs/）。"""
    return workspace / (override or DEFAULT_RESULTS_DIR)


def record_path(workspace: Path, run_id: str, override: str | None = None) -> Path:
    """单个 run 的记录文件路径。"""
    return results_dir(workspace, override) / f"{run_id}.json"


def load_run(path: Path) -> dict:
    """读取 run 记录。"""
    with path.open(encoding="utf-8") as f:
        data: dict = json.load(f)
    return data


def save_run(path: Path, run: dict) -> None:
    """写回 run 记录（原子替换，避免半截文件）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    run["updated_at"] = now_iso()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def cmd_init(args: argparse.Namespace) -> int:
    """建一个空的 run 记录。"""
    workspace = Path(args.workspace).resolve()
    path = record_path(workspace, args.run_id, args.results_dir)
    if path.exists() and not args.force:
        print(f"[FAIL] 记录已存在：{path}（要覆盖请加 --force）", file=sys.stderr)
        return 1

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    locales = [loc.strip() for loc in args.locales.split(",") if loc.strip()]
    if not platforms:
        print("[FAIL] 至少要声明一个平台（--platforms）", file=sys.stderr)
        return 1
    if not locales:
        print("[FAIL] 至少要声明一个语言（--locales）", file=sys.stderr)
        return 1

    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "operator": args.operator,
        "purpose": args.purpose,
        "platforms": platforms,
        "locales": locales,
        "records": [],
    }
    save_run(path, run)
    print(f"[OK] 已创建记录：{path.relative_to(workspace)}")
    print(f"     平台：{', '.join(platforms)}")
    print(f"     语言：{', '.join(locales)}")
    print("     下一步：用 record 子命令逐条登记 L1/L2 结果，再跑 verify 对账。")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    """登记（或覆盖）一条 L1/L2 记录。"""
    workspace = Path(args.workspace).resolve()
    path = record_path(workspace, args.run_id, args.results_dir)
    if not path.exists():
        print(f"[FAIL] 记录不存在：{path}（先跑 init）", file=sys.stderr)
        return 1

    run = load_run(path)
    if args.platform not in run["platforms"]:
        print(f"[FAIL] 平台 {args.platform} 不在本次 run 声明的范围内：{run['platforms']}", file=sys.stderr)
        return 1
    if args.layer == "L1" and not args.locale:
        print("[FAIL] L1 记录必须给 --locale（漂移随界面语言变化，2026-10-25 实测）", file=sys.stderr)
        return 1
    if args.status in STATUS_NEEDS_REASON and not args.reason:
        print(f"[FAIL] 状态 {args.status} 必须给 --reason（写清为什么没跑/没结论）", file=sys.stderr)
        return 1
    if args.status == STATUS_PASS and not args.evidence:
        print("[FAIL] 状态 pass 必须给 --evidence（结论不能没有出处）", file=sys.stderr)
        return 1
    if args.status == STATUS_PASS and not args.evidence_file:
        print("[FAIL] 状态 pass 必须给 --evidence-file（可机检的证据文件）", file=sys.stderr)
        return 1

    entry = {
        "layer": args.layer,
        "platform": args.platform,
        "status": args.status,
        "locale": args.locale or default_locale(run),
        "checked_at": now_iso(),
        "evidence": list(args.evidence or []),
        "evidence_files": list(args.evidence_file or []),
        "reason": args.reason or "",
        "notes": args.notes or "",
    }

    records = run["records"]
    for idx, existing in enumerate(records):
        same = (
            existing.get("layer") == entry["layer"]
            and existing.get("platform") == entry["platform"]
            and existing.get("locale") == entry["locale"]
        )
        if same:
            records[idx] = entry
            save_run(path, run)
            print(f"[OK] 已更新记录：{entry['layer']}/{entry['platform']}/{entry['locale']} → {entry['status']}")
            return 0

    records.append(entry)
    save_run(path, run)
    print(f"[OK] 已登记记录：{entry['layer']}/{entry['platform']}/{entry['locale']} → {entry['status']}")
    return 0


def default_locale(run: dict) -> str:
    """L2 记录没给 locale 时，落到本次 run 声明的第一个语言。"""
    locales = run.get("locales") or []
    return locales[0] if locales else "unspecified"


def _probe_outcome(evidence_file: Path, platform: str) -> str | None:
    """从 L1 探针 JSON 证据里取某个平台的 outcome；不是探针产物则返回 None。"""
    try:
        data = json.loads(evidence_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    platforms = data.get("platforms")
    if not isinstance(platforms, list):
        return None
    for item in platforms:
        if isinstance(item, dict) and item.get("platform") == platform:
            outcome = item.get("outcome")
            return str(outcome) if outcome else None
    return None


def verify_run(run: dict, workspace: Path) -> tuple[list[str], str, bool]:
    """对账：返回 (错误列表, 结论, 是否完整)。"""
    errors: list[str] = []
    records = run.get("records") or []
    platforms = run.get("platforms") or []

    seen: set[tuple[str, str, str]] = set()
    for idx, rec in enumerate(records):
        where = f"records[{idx}]"
        layer = rec.get("layer")
        platform = rec.get("platform")
        status = rec.get("status")
        locale = rec.get("locale")
        if layer not in LAYERS:
            errors.append(f"{where}: layer 非法（{layer}），只能是 {LAYERS}")
        if platform not in platforms:
            errors.append(f"{where}: platform {platform} 不在本次 run 声明的范围 {platforms} 内")
        if status not in STATUSES:
            errors.append(f"{where}: status 非法（{status}），只能是 {STATUSES}")
        if not rec.get("checked_at"):
            errors.append(f"{where}: 缺 checked_at")
        if layer == "L1" and not locale:
            errors.append(f"{where}: L1 记录缺 locale（漂移随界面语言变化）")

        key = (str(layer), str(platform), str(locale))
        if key in seen:
            errors.append(f"{where}: 与前面的记录重复（layer/platform/locale 三元组重复）")
        seen.add(key)

        if status == STATUS_PASS:
            if not rec.get("evidence"):
                errors.append(f"{where}: pass 必须有 evidence")
            evidence_files = rec.get("evidence_files") or []
            if not evidence_files:
                errors.append(f"{where}: pass 必须有 evidence_file")
            for rel in evidence_files:
                ev_path = Path(rel)
                if not ev_path.is_absolute():
                    ev_path = workspace / rel
                if not ev_path.exists():
                    errors.append(f"{where}: 证据文件不存在：{rel}")
                    continue
                outcome = _probe_outcome(ev_path, str(platform))
                if outcome is not None and outcome != STATUS_PASS:
                    errors.append(
                        f"{where}: 证据与结论不符——探针判定 outcome={outcome}，记录却写 pass"
                    )
        if status in STATUS_NEEDS_REASON and not rec.get("reason"):
            errors.append(f"{where}: 状态 {status} 必须写 reason")

    # 每个平台至少要有一条 L1；L2 也必须有条目（可以是 not-run + reason）
    for platform in platforms:
        l1 = [r for r in records if r.get("layer") == "L1" and r.get("platform") == platform]
        l2 = [r for r in records if r.get("layer") == "L2" and r.get("platform") == platform]
        if not l1:
            errors.append(f"平台 {platform}: 缺 L1 记录（先跑 L1 再谈 L2）")
        if not l2:
            errors.append(f"平台 {platform}: 缺 L2 记录（没跑就记 not-run + reason）")
        if any(r.get("status") == STATUS_PASS for r in l2) and not any(
            r.get("status") == STATUS_PASS for r in l1
        ):
            errors.append(f"平台 {platform}: L2 记为 pass，但 L1 没有 pass 的记录")

    # 结论
    has_fail = any(r.get("status") == STATUS_FAIL for r in records)
    l2_complete = all(
        any(
            r.get("layer") == "L2" and r.get("platform") == p and r.get("status") == STATUS_PASS
            for r in records
        )
        for p in platforms
    )
    l1_complete = all(
        any(
            r.get("layer") == "L1" and r.get("platform") == p and r.get("status") == STATUS_PASS
            for r in records
        )
        for p in platforms
    )
    if has_fail:
        verdict = "failed"
    elif l2_complete:
        verdict = "passed"
    elif l1_complete:
        verdict = "l1-only"
    else:
        verdict = "partial"

    complete = verdict == "passed" and not errors
    return errors, verdict, complete


def cmd_verify(args: argparse.Namespace) -> int:
    """对账一条 run 记录。"""
    workspace = Path(args.workspace).resolve()
    path = record_path(workspace, args.run_id, args.results_dir)
    if not path.exists():
        print(f"[FAIL] 记录不存在：{path}", file=sys.stderr)
        return 1

    run = load_run(path)
    errors, verdict, complete = verify_run(run, workspace)

    payload = {
        "run_id": run.get("run_id"),
        "verdict": verdict,
        "complete": complete,
        "errors": errors,
        "route_gate": "open",
        "route_gate_note": ROUTE_GATE_NOTE,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"=== 真机回归记录对账：{run.get('run_id')} ===")
        print(f"  平台：{', '.join(run.get('platforms') or [])}")
        print(f"  语言：{', '.join(run.get('locales') or [])}")
        print(f"  记录条数：{len(run.get('records') or [])}")
        print(f"  结论：{verdict}")
        if errors:
            print("  一致性问题：")
            for err in errors:
                print(f"    - {err}")
        else:
            print("  一致性：✅ 无问题")
        print(f"  {ROUTE_GATE_NOTE}")

    if errors:
        return 1
    return 0 if complete else 2


def cmd_list(args: argparse.Namespace) -> int:
    """列出所有 run 记录及其结论。"""
    workspace = Path(args.workspace).resolve()
    directory = results_dir(workspace, args.results_dir)
    if not directory.exists():
        print(f"[OK] 还没有任何记录（目录 {directory} 不存在）")
        return 0

    print("=== 真机回归记录 ===")
    skipped = 0
    for path in sorted(directory.glob("*.json")):
        try:
            run = load_run(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  {path.stem}: 读取失败（{exc}）")
            continue
        if not isinstance(run, dict) or "run_id" not in run:
            # 同目录下可能还放着 L1 探针的证据 JSON——那不是 run 记录，跳过。
            skipped += 1
            continue
        errors, verdict, complete = verify_run(run, workspace)
        flag = "✅" if not errors else "🔴"
        extra = "" if not errors else f"，{len(errors)} 处不一致"
        done = "，已跑完" if complete else ""
        print(f"  {flag} {run.get('run_id')}: {verdict}{extra}{done}（{len(run.get('records') or [])} 条记录）")
    if skipped:
        print(f"  （跳过 {skipped} 个非记录文件——同目录下的 L1 探针证据 JSON）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """命令行解析器。"""
    parser = argparse.ArgumentParser(
        description="真机回归记录管理器（L1 自动化只读 + L2 人工真实发送）",
    )
    parser.add_argument("--workspace", default=str(REPO_ROOT), help="工作区根目录（默认：仓库根）")
    parser.add_argument("--results-dir", default=None, help=f"记录目录（默认：{DEFAULT_RESULTS_DIR}）")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="创建一条 run 记录")
    p_init.add_argument("--run-id", required=True, help="run 标识，如 RMR-2026-10-25-01")
    p_init.add_argument("--platforms", required=True, help="逗号分隔的平台列表")
    p_init.add_argument("--locales", required=True, help="逗号分隔的界面语言列表")
    p_init.add_argument("--operator", default="", help="执行人")
    p_init.add_argument("--purpose", default="真机回归：L1 DOM 契约 + L2 真实发送", help="本次 run 的目的")
    p_init.add_argument("--force", action="store_true", help="覆盖已存在的记录")
    p_init.set_defaults(func=cmd_init)

    p_record = sub.add_parser("record", help="登记/更新一条 L1/L2 记录")
    p_record.add_argument("--run-id", required=True)
    p_record.add_argument("--layer", required=True, choices=list(LAYERS))
    p_record.add_argument("--platform", required=True)
    p_record.add_argument("--status", required=True, choices=list(STATUSES))
    p_record.add_argument("--locale", default="", help="界面语言（L1 必填）")
    p_record.add_argument("--evidence", action="append", default=[], help="结论出处（可重复）")
    p_record.add_argument("--evidence-file", action="append", default=[], help="可机检的证据文件（可重复）")
    p_record.add_argument("--reason", default="", help="unverified / not-run 的原因")
    p_record.add_argument("--notes", default="", help="补充说明")
    p_record.set_defaults(func=cmd_record)

    p_verify = sub.add_parser("verify", help="对账一条 run 记录")
    p_verify.add_argument("--run-id", required=True)
    p_verify.add_argument("--json", action="store_true", help="输出机器可读结果")
    p_verify.set_defaults(func=cmd_verify)

    p_list = sub.add_parser("list", help="列出所有 run 记录")
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    """入口。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
