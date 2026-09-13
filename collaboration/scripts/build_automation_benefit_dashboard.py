#!/usr/bin/env python3
"""Build automation benefit dashboard from dispatch/receipt history."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--dispatch-history", required=True)
    p.add_argument("--receipt-history", required=True)
    p.add_argument("--target-ratio", type=float, default=3.0)
    p.add_argument("--window", type=int, default=14)
    p.add_argument("--report", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    workspace = Path(args.workspace)
    dispatch_items = read_jsonl(workspace / args.dispatch_history)
    receipt_items = read_jsonl(workspace / args.receipt_history)

    # Aggregate by day
    by_day: dict = {}

    def day_of(ts: str) -> str:
        return (ts or "")[:10]

    for item in dispatch_items:
        d = day_of(item.get("generated_at", ""))
        if d:
            by_day.setdefault(d, {"dispatch": 0, "receipt": 0})
            by_day[d]["dispatch"] += int(item.get("dispatched_count", 0))

    for item in receipt_items:
        d = day_of(item.get("generated_at", ""))
        if d:
            by_day.setdefault(d, {"dispatch": 0, "receipt": 0})
            by_day[d]["receipt"] += int(item.get("completed_count", 0))

    day_count = len(by_day)
    total_ratio_sum = 0.0
    days = []
    for d, v in sorted(by_day.items()):
        ratio = (v["dispatch"] + v["receipt"]) / 2 if (v["dispatch"] + v["receipt"]) > 0 else 0.0
        achieved = ratio >= args.target_ratio
        total_ratio_sum += ratio
        days.append({"date": d, "dispatch": v["dispatch"], "receipt": v["receipt"],
                     "ratio": ratio, "achieved": achieved})

    overall_ratio = (total_ratio_sum / day_count) if day_count else 0.0
    overall_achieved = overall_ratio >= args.target_ratio if day_count else False

    report = {
        "generated_at": datetime.now().isoformat(),
        "day_count": day_count,
        "target_ratio": args.target_ratio,
        "window": args.window,
        "overall_efficiency_ratio": overall_ratio,
        "overall_target_achieved": overall_achieved,
        "days": days,
    }

    if args.dry_run:
        print(f"mode=dry-run day_count={day_count} ratio={overall_ratio:.2f}")
        return 0

    report_path = workspace / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown dashboard
    lines = [
        "# 自动化收益看板（自动生成）",
        "",
        f"- 生成时间: {report['generated_at']}",
        f"- 统计天数: {day_count}",
        f"- 目标效率比: >= {args.target_ratio:.2f}",
        f"- 总体效率比: {overall_ratio:.2f}",
        f"- 总体达标: {'YES' if overall_achieved else 'NO'}",
        "",
        "## 日维度明细",
        "",
        "| 日期 | dispatch | receipt | ratio | 达标 |",
        "|---|---:|---:|---:|---:|",
    ]
    for d in days:
        lines.append(
            f"| {d['date']} | {d['dispatch']} | {d['receipt']} | {d['ratio']:.2f} | "
            f"{'YES' if d['achieved'] else 'NO'} |"
        )

    output_path = workspace / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[OK] dashboard generated: day_count={day_count} ratio={overall_ratio:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
