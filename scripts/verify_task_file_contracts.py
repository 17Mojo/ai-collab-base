#!/usr/bin/env python3
"""用仓库**自己的**校验器，验 `collaboration/tasks/*.md` 的契约与结果文件一致性。

## 为什么需要这个脚本

`python3 -m ai_collab.cli tasks validate-contract` 读的是**运行时状态库**
（`logs/collaboration_state.json`），**不读** `collaboration/tasks/*.md`。
所以「工单文件写好了」**不等于**「工单过了门禁」——必须先把工单登记进状态库，
再让仓库自己的校验器去判。

这个脚本把「登记 → 收口 completed → 契约校验 → 终态一致性审计」串成一步，
而且**只动本工作区的状态文件**，**不写全局状态文件**
（`~/.vscode/ai-collab/collaboration_state.json`）——`_sync_to_global` 与
`_backup_state` 被替换成空操作。全局文件是**镜像**，不是事实源（见 memory）。

## 用法

```bash
python3 scripts/verify_task_file_contracts.py                 # 全部工单
python3 scripts/verify_task_file_contracts.py --task-id TASK-P1-XXX-001
```

退出码：0 = 全部通过；1 = 有契约问题或一致性不一致。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ai_collab.result_consistency_audit import (  # noqa: E402
    run_terminal_result_consistency_audit,
)
from ai_collab.state_manager import StateManager, TaskStatus  # noqa: E402


def parse_frontmatter(path: Path) -> dict:
    """读 `---` 包裹的 YAML frontmatter。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, frontmatter, _body = text.split("---", 2)
    return yaml.safe_load(frontmatter) or {}


def collect_task_files(tasks_dir: Path, only: list[str] | None) -> list[Path]:
    if only:
        return [tasks_dir / f"{task_id}.md" for task_id in only]
    return sorted(p for p in tasks_dir.glob("TASK_*.md") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument("--tasks-dir", default=str(REPO_ROOT / "collaboration" / "tasks"))
    args = parser.parse_args()

    # ── 纪律：全局状态文件与备份一律不写 ───────────────────────────────
    StateManager._sync_to_global = lambda self: None  # type: ignore[method-assign]
    StateManager._backup_state = lambda self: None  # type: ignore[method-assign]

    tasks_dir = Path(args.tasks_dir).resolve()
    files = collect_task_files(tasks_dir, args.task_ids)
    if not files:
        print(f"没找到工单文件：{tasks_dir}")
        return 1

    state = StateManager(workspace_path=str(REPO_ROOT))

    for path in files:
        if not path.exists():
            print(f"[跳过] 工单文件不存在：{path}")
            continue
        fm = parse_frontmatter(path)
        task_id = fm.get("task_id") or path.stem
        if task_id in state.state.get("tasks", {}):
            # 已登记过：**更新**契约字段，不重复登记（脚本要可重复跑）。
            state.update_task_contract(
                task_id=task_id,
                change_id=fm.get("change_id"),
                assignee=fm.get("assignee"),
                assignee_role=fm.get("assignee_role"),
                reviewer=fm.get("reviewer"),
                primary_skill=fm.get("primary_skill"),
                support_skills=fm.get("support_skills"),
                acceptance_commands=fm.get("acceptance_commands"),
                result_file=fm.get("result_file"),
                actor="claude_code",
            )
        else:
            state.register_task(
                task_id=task_id,
                ai_type=fm.get("assignee", "claude_code"),
                description=path.stem,
                files=[],
                vscode_context={"source": "verify_task_file_contracts"},
                change_id=fm.get("change_id"),
                assignee=fm.get("assignee"),
                assignee_role=fm.get("assignee_role"),
                reviewer=fm.get("reviewer"),
                primary_skill=fm.get("primary_skill"),
                support_skills=fm.get("support_skills"),
                acceptance_commands=fm.get("acceptance_commands"),
                result_file=fm.get("result_file"),
            )
        # 收口到 completed：**这一步会触发结果文件门禁**
        # （章节齐备、无负向信号、验收命令逐字出现在结果文件里）。
        state.update_task_status(
            task_id=task_id, status=TaskStatus.COMPLETED, actor="claude_code"
        )
        print(f"已登记并收口：{task_id}")

    print()
    report = state.validate_task_contracts(scope="all")
    print(
        f"契约校验: checked={report.get('checked_tasks')} "
        f"invalid={report.get('invalid_count')} "
        f"skipped={report.get('skipped_tasks')}"
    )
    for item in report.get("issues", []):
        print("  -", item)

    print()
    audit = run_terminal_result_consistency_audit(
        workspace=REPO_ROOT,
        task_id=None,
        report_path="logs/task_result_consistency_report.json",
        summary_path="collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
    )
    print(
        "终态结果一致性审计: "
        f"audited={audit.get('audited_count')} "
        f"consistent={audit.get('consistent_count')} "
        f"mismatch={audit.get('mismatch_count')} "
        f"unparseable={audit.get('unparseable_count')} "
        f"missing_result={audit.get('missing_result_count')}"
    )
    for item in audit.get("issues", [])[:10]:
        print("  issue:", item)

    bad = bool(report.get("issues")) or int(audit.get("issue_count", 0)) > 0
    print()
    print("结论：", "有问题" if bad else "全部通过")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
