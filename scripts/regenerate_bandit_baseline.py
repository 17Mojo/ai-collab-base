#!/usr/bin/env python3
"""bandit baseline 的唯一合法重生成入口。

直接用文本编辑器改 ``.github/bandit-baseline.json`` 会被 CI 拒绝：
门禁会校验 ``_audit.results_sha256`` 与 results 的规范化摘要一致，并核对
append-only 审计日志 ``.github/bandit-baseline-audit.jsonl`` 的末条记录。
本脚本同时生成元数据、写 baseline、追加审计日志，三者保持原子一致。

用法（在仓库根目录执行，需已安装 bandit）：

    python3 scripts/regenerate_bandit_baseline.py \
        --reason "修复 43 条存量 findings 后清零 baseline（PR #XX）"

可选：
    --report <path>   复用已有的 bandit JSON 完整报告，不重新扫描
    --dry-run         只打印将写入的摘要，不改任何文件
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.metadata
import json
import pathlib
import re
import subprocess
import sys

BASELINE = pathlib.Path(".github/bandit-baseline.json")
AUDIT_LOG = pathlib.Path(".github/bandit-baseline-audit.jsonl")
SCAN_PATH = "ai_collab/"
SCHEMA_VERSION = 1

REQUIRED_AUDIT_FIELDS = (
    "schema_version",
    "generated_at",
    "generated_from_commit",
    "bandit_version",
    "scan_path",
    "result_count",
    "results_sha256",
    "reason",
)


def canonical_digest(rows: list) -> str:
    """与 security.yml / Evaluate severity 完全一致的规范化摘要。"""
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def git_head() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out if re.fullmatch(r"[0-9a-f]{7,40}", out) else "unknown"


def bandit_version() -> str:
    try:
        return importlib.metadata.version("bandit")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def run_bandit(report: pathlib.Path) -> None:
    cmd = ["bandit", "-r", SCAN_PATH, "-f", "json", "-o", str(report)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # bandit exit 1 = 有 findings，是正常结果；>=2 才是工具崩溃
    if proc.returncode >= 2:
        print(f"bandit 执行失败 (exit {proc.returncode}):\n{proc.stderr[-800:]}", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="重生成 bandit baseline（含强制审计记录）")
    ap.add_argument("--reason", required=True, help="重生成理由，至少 10 个字符，会写入审计日志")
    ap.add_argument("--report", type=pathlib.Path, help="复用已有完整报告而非重新扫描")
    ap.add_argument("--baseline", type=pathlib.Path, default=BASELINE)
    ap.add_argument("--audit-log", type=pathlib.Path, default=AUDIT_LOG)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reason = args.reason.strip()
    if len(reason) < 10:
        print("::error::--reason 至少 10 个字符，必须写明「为什么允许这批 findings」。", file=sys.stderr)
        return 2

    report = args.report
    if report is None:
        report = pathlib.Path("/tmp/bandit-regenerate-report.json")
        run_bandit(report)
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"::error::无法读取 bandit 报告 {report}: {exc}", file=sys.stderr)
        return 2

    if data.get("errors"):
        print(f"::error::bandit 报告含 {len(data['errors'])} 条执行错误，拒绝生成 baseline。", file=sys.stderr)
        return 2
    scanned = [k for k in data.get("metrics", {}) if k != "_totals"]
    if not scanned:
        print("::error::bandit 扫描了 0 个文件，拒绝生成 baseline。", file=sys.stderr)
        return 2

    rows = data.get("results", [])
    if not isinstance(rows, list):
        print("::error::bandit 报告 results 不是列表。", file=sys.stderr)
        return 2

    digest = canonical_digest(rows)
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_head()
    version = bandit_version()

    audit = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "generated_from_commit": commit,
        "bandit_version": version,
        "scan_path": SCAN_PATH,
        "result_count": len(rows),
        "results_sha256": digest,
        "reason": reason,
    }
    assert all(audit.get(k) not in (None, "") for k in REQUIRED_AUDIT_FIELDS)

    # 保留 bandit 原始报告字段（errors / metrics / generated_at / results），
    # 只增补 _audit —— `bandit -b` 依赖完整 results 做七元组比较，不能精简。
    out = dict(data)
    out["_audit"] = audit

    record = {
        "at": now,
        "commit": commit,
        "reason": reason,
        "result_count": len(rows),
        "results_sha256": digest,
        "bandit_version": version,
        "scan_path": SCAN_PATH,
    }

    print(f"result_count  = {len(rows)}")
    print(f"scanned_files = {len(scanned)}")
    print(f"results_sha256= {digest}")
    print(f"commit        = {commit}")
    print(f"reason        = {reason}")

    if args.dry_run:
        print("--dry-run：未写入任何文件")
        return 0

    args.baseline.parent.mkdir(parents=True, exist_ok=True)
    # 沿用 bandit 原生报告格式（indent=2 / ensure_ascii=True / 无末尾换行），
    # 避免每次重生成都产生全文件 diff，审计时只需看实际变化的行。
    args.baseline.write_text(json.dumps(out, indent=2), encoding="utf-8")
    args.audit_log.parent.mkdir(parents=True, exist_ok=True)
    with args.audit_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"已写入 {args.baseline}")
    print(f"已追加审计记录 {args.audit_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
