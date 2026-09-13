#!/usr/bin/env python3
"""Run daily benefit snapshot - aggregate dispatch/receipt history into daily reports."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional


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


def extract_date_from_ts(ts: str) -> str:
    try:
        return ts[:10]  # YYYY-MM-DD
    except (TypeError, IndexError):
        return datetime.now().strftime("%Y-%m-%d")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--dispatch-history", required=True)
    p.add_argument("--receipt-history", required=True)
    p.add_argument("--latest-report", required=True)
    p.add_argument("--latest-dashboard", required=True)
    p.add_argument("--dated-report-dir", required=True)
    p.add_argument("--daily-history", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    workspace = Path(args.workspace)
    dispatch_items = read_jsonl(workspace / args.dispatch_history)
    receipt_items = read_jsonl(workspace / args.receipt_history)

    # Compute totals from last entry of each
    dispatch_total = dispatch_items[-1].get("dispatched_count", 0) if dispatch_items else 0
    receipt_total = receipt_items[-1].get("completed_count", 0) if receipt_items else 0
    # ratio = (dispatch + receipt) / 2 (average manual effort)
    ratio = (dispatch_total + receipt_total) / 2 if (dispatch_total + receipt_total) > 0 else 0

    # Use today's date
    now_ts = datetime.now().isoformat()
    today = now_ts[:10]

    manual_baseline = max((dispatch_total + receipt_total) / 2, 1)
    report = {
        "overall_efficiency_ratio": ratio,
        "overall_target_achieved": ratio >= 3.0,
        "dispatch_total": dispatch_total,
        "receipt_total": receipt_total,
        "automation_touches": dispatch_total + receipt_total,
        "manual_baseline": manual_baseline,
        "generated_at": now_ts,
    }

    dashboard = f"""# Automation Benefit Dashboard

Generated: {now_ts}

## Summary
- Dispatch: {dispatch_total}
- Receipt: {receipt_total}
- Ratio: {ratio:.2f}
- Target Achieved: {report["overall_target_achieved"]}
"""

    if args.dry_run:
        print(f"mode=dry-run dispatch={dispatch_total} receipt={receipt_total} ratio={ratio:.2f}")
        return 0

    # Write latest files
    latest_report_path = workspace / args.latest_report
    latest_report_path.parent.mkdir(parents=True, exist_ok=True)
    latest_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    latest_dashboard_path = workspace / args.latest_dashboard
    latest_dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    latest_dashboard_path.write_text(dashboard, encoding="utf-8")

    # Write dated report
    dated_dir = workspace / args.dated_report_dir / today
    dated_dir.mkdir(parents=True, exist_ok=True)
    (dated_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (dated_dir / "dashboard.md").write_text(dashboard, encoding="utf-8")

    # Update daily history (upsert: replace existing entry for same date)
    history_path = workspace / args.daily_history
    history_path.parent.mkdir(parents=True, exist_ok=True)

    existing_lines = []
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line.strip())
                if extract_date_from_ts(entry.get("generated_at", "")) != today:
                    existing_lines.append(line)
            except json.JSONDecodeError:
                continue
    existing_lines.append(json.dumps(report, ensure_ascii=False))
    history_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

    print(f"daily snapshot written: dispatch={dispatch_total} receipt={receipt_total} ratio={ratio:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
