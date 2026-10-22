#!/usr/bin/env python3
"""Agent Dispatch Bridge - 自动派单桥接脚本"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def read_state(workspace: Path) -> dict:
    state_file = workspace / "logs" / "collaboration_state.json"
    if not state_file.exists():
        return {"tasks": {}, "global_state": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"tasks": {}, "global_state": {}}


def read_dispatch_state(workspace: Path) -> dict:
    state_file = workspace / "logs" / "agent_dispatch_state.json"
    if not state_file.exists():
        return {"items": {}}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}}


def write_dispatch_state(workspace: Path, state: dict) -> None:
    state_file = workspace / "logs" / "agent_dispatch_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report(workspace: Path, report: dict) -> None:
    report_file = workspace / "logs" / "task_dispatch_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def write_history(workspace: Path, line: str) -> None:
    history_file = workspace / "logs" / "agent_dispatch_history.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def build_update_command(order: dict) -> str:
    task_id = order.get("task_id", "")
    ai = order.get("ai_type", order.get("assignee", "claude_code"))
    return (
        f"python3 -m ai_collab.cli tasks update "
        f"--task-id {task_id} --ai {ai} --status implementing"
    )


DEFAULT_ORDERS_RELPATH = "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md"

# 与 ai_collab/dispatch_trigger.py 的 DISPLAY_NAME 保持一致
ASSIGNEE_DISPLAY_NAMES = {
    "claude_code": "Claude",
    "codearts_agent": "CodeArts",
    "codex": "Codex",
}


def write_orders_markdown(
    workspace: Path,
    orders: list,
    dispatch_state: dict = None,
    task_lookup: dict = None,
    orders_relpath: str = DEFAULT_ORDERS_RELPATH,
) -> None:
    # 输出路径由 --orders 决定。写死文件名会让 `trigger` 找不到指令包
    # （trigger 读的是 config 里配置的 orders 路径），整条派单链路直接断掉。
    md_file = workspace / orders_relpath
    md_file.parent.mkdir(parents=True, exist_ok=True)
    if dispatch_state is None:
        dispatch_state = {"items": {}}
    if task_lookup is None:
        task_lookup = {}
    lines = [
        "# Agent Dispatch Orders",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
    ]
    # 按执行方分组：trigger 用 `## 发送给 \`Name\` (\`assignee\`)` 标题切分指令包，
    # 没有这些标题，payload 就会退化成"当前无待派发任务"。
    grouped: dict[str, list[dict]] = {}
    for order in orders:
        assignee = str(
            order.get("assignee") or order.get("ai_type") or "claude_code"
        ).strip().lower()
        grouped.setdefault(assignee, []).append(order)

    for assignee, assignee_orders in grouped.items():
        display = ASSIGNEE_DISPLAY_NAMES.get(assignee, assignee)
        lines.append(f"## 发送给 `{display}` (`{assignee}`)")
        lines.append("")
        for o in assignee_orders:
            lines.append("")
            # Check if this task was previously dispatched
            existing = dispatch_state.get("items", {}).get(o["task_id"])
            is_reopened = existing and existing.get("status") == "pending"

            if is_reopened:
                lines.append("### 返工重派说明（必须先读）")
                lines.append("")
                lines.append(f"**任务**: {o['task_id']}")
                lines.append(f"**原状态**: {existing.get('status')}")
                lines.append(f"**新状态**: {o.get('status')}")
                lines.append("")
                # Include notes from task
                task_notes = task_lookup.get(o["task_id"], {}).get("notes", [])
                if task_notes:
                    lines.append("**任务 notes (review 反馈)**:")
                    lines.append("")
                    for note in task_notes:
                        lines.append(f"- {note}")
                    lines.append("")
                lines.append("此任务之前已 dispatch，但被 review 拒绝。")
                lines.append("重新 dispatch 前请先读 `notes` 字段了解拒绝原因。")
                lines.append("")
                lines.append(
                    "**禁止因为 result_file 已存在或任务曾到过 testing 就回复 noop。**"
                )
                lines.append("")

            lines.append(f"### {o['task_id']}")
            lines.append("")
            task = task_lookup.get(o["task_id"], {}) or {}
            contract = _task_contract_lines(o, task, workspace)
            if contract:
                lines.extend(contract)
            constraints = _execution_constraints_lines(
                str(o.get("assignee") or o.get("ai_type") or "")
            )
            if constraints:
                lines.extend(constraints)
            lines.append("#### 执行步骤")
            lines.append("")
            lines.append("1. 先把状态翻成 implementing（下面这条命令）：")
            lines.append("")
            lines.append("```bash")
            lines.append(build_update_command(o))
            lines.append("```")
            lines.append("")
            lines.append("2. 按上面的**任务描述**动手实现，产出**结果文件**。")
            lines.append("3. 逐条跑下面的**验收命令**，必须全部通过。")
            lines.append("4. 写完结果文件后回一行 ACK（用任务块里的 ack 命令生成，原样回复）。")
            lines.append("")
            cmds = o.get("commands", [])
            if cmds:
                lines.append("#### Acceptance Commands")
                for c in cmds:
                    lines.append(f"- `{c}`")
    md_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_order(task: dict) -> dict:
    return {
        "task_id": task.get("task_id"),
        "ai_type": task.get("ai_type", "claude_code"),
        "assignee": task.get("assignee", "claude_code"),
        "status": task.get("status", "planning"),
        "commands": task.get("acceptance_commands", []),
        "result_file": task.get("result_file", ""),
        "dispatched_at": datetime.now().isoformat(),
    }


def _task_contract_lines(
    order: dict, task: dict, workspace: Path
) -> list[str]:
    """渲染任务契约段。

    之前 payload 的任务块只有「任务 ID + 改状态的命令 + 验收命令」，
    没有描述、没有涉及文件、没有结果文件 —— 接收方只能从任务 ID 和验收命令
    反推要做什么。真机实测：CodeArts 收到这种 payload 后花了 5 分钟探索仓库，
    一个文件也没产出（会话中途被中止）。

    任务记录里本来就有 description / files / result_file / change_id /
    assignee_role，这里原样带过去，让接收方一眼知道「做什么、交什么」。
    """
    task_id = str(order.get("task_id") or "")
    lines: list[str] = []

    description = str(task.get("description") or "").strip()
    if description:
        lines.append(f"**任务描述**: {description}")
        lines.append("")

    files = task.get("files") or []
    if files:
        lines.append("**涉及文件**:")
        for f in files:
            lines.append(f"- `{f}`")
        lines.append("")

    result_file = str(order.get("result_file") or task.get("result_file") or "").strip()
    if result_file:
        lines.append(f"**结果文件**（必须写）: `{result_file}`")
        lines.append("")
        lines.append(
            "  按 PROTOCOL §7.3 契约写入四段："
            "`## 执行命令` / `## 验证结果` / `## 风险` / `## 回滚`。"
        )
        lines.append("")

    change_id = str(task.get("change_id") or "").strip()
    if change_id:
        lines.append(f"**change_id**: `{change_id}`")
        lines.append("")

    role = str(task.get("assignee_role") or "").strip()
    if role:
        lines.append(f"**角色**: `{role}`（{order.get('assignee')}）")
        lines.append("")

    ticket = workspace / "collaboration" / "tasks" / f"{task_id}.md"
    if ticket.exists():
        lines.append(f"**任务工单**: `collaboration/tasks/{task_id}.md`")
        lines.append("")

    return lines


def _execution_constraints_lines(assignee: str) -> list[str]:
    """渲染接收方环境约束段（只对已知会卡死的 provider 渲染）。

    真机实测（2026-10-22，CodeArts Doer kernel）：
    - 会话 `ses_e9be3df` 在 `write` 工具调用上**永久挂起**（tool 状态停在
      `running`），文件没有落盘，会话随后中止；
    - 会话 `ses_e9c15` 在 `task`（派生子代理）调用上报 `MessageAbortedError`，
      父会话与子会话一起中止；
    - 同期 `bash` / `read` / `todowrite` 调用**全部正常完成**。

    也就是说：写文件和派生子代理这两条路会把整个会话带死，而这两件事
    完全可以用 bash 替代。payload 里直接写清楚，比事后排查便宜得多。
    """
    if str(assignee or "").strip().lower() != "codearts_agent":
        return []
    return [
        "#### 执行环境约束（真机实测，必须遵守）",
        "",
        "本执行环境里有两个工具会把整个会话卡死并中止，**不要用**：",
        "",
        "- `write` / `edit`：实测会话在 `write` 调用上永久挂起，"
        "文件没有落盘，会话随后中止。",
        "- `task`（派生子代理）：实测报 `MessageAbortedError`，"
        "父会话与子会话一起中止。",
        "",
        "**写文件一律用 bash（heredoc）**——"
        "`bash` / `read` / `todowrite` 在真机实测里全部正常完成：",
        "",
        "```bash",
        "cat > path/to/file.py <<'EOF'",
        "...文件内容...",
        "EOF",
        "```",
        "",
        "写完立刻自检，确认文件真的落盘了（不要假设写成功）：",
        "",
        "```bash",
        "ls -l path/to/file.py && wc -l path/to/file.py",
        "```",
        "",
        "自己直接做完，不要派生子代理。",
        "",
    ]


def classify_task(task: dict, existing: dict, args) -> dict:
    """Classify a task for dispatch.

    Logic:
    1. New task (not in dispatch_state): always candidate
    2. Existing + --redispatch: reopened/candidate (regardless of --include-pending)
    3. Existing + status=planning (not redispatched): keep in candidate (or already)
    4. Existing + status=implementing (not redispatched): skipped (already)
    5. Existing + status=pending/other (not redispatched): need --include-pending

    Returns: {
        "candidate": bool,    # should appear in candidate_count
        "dispatched": bool,   # should count as dispatched
        "already": bool,      # should count as already_dispatched
        "reopened": bool,      # reopened (redispatch after implementing)
    }
    """
    status = task.get("status", "")
    include_pending = args.include_pending
    redispatch = args.redispatch
    dry_run = args.dry_run

    if not existing:
        # New task: subject to --include-pending filter
        if not include_pending and status != "planning":
            return {"candidate": False, "dispatched": False, "already": False, "reopened": False}
        return {"candidate": True, "dispatched": True, "already": False, "reopened": False}

    # Existing task in dispatch_state
    if redispatch:
        # --redispatch mode: any status reopened
        if status == "implementing":
            return {"candidate": True, "dispatched": True, "already": False, "reopened": True}
        # planning or pending: redispatch
        return {"candidate": True, "dispatched": True, "already": False, "reopened": False}

    # No redispatch
    if status == "planning":
        # Was dispatched, never started → dry-run keeps as candidate
        if dry_run:
            return {"candidate": True, "dispatched": True, "already": False, "reopened": False}
        # No dry-run: still candidate but already (no new dispatch)
        return {"candidate": True, "dispatched": False, "already": True, "reopened": False}

    if status == "implementing":
        # Already implementing: skip
        return {"candidate": False, "dispatched": False, "already": True, "reopened": False}

    # Other status (pending, etc.) - need --include-pending
    if not include_pending:
        return {"candidate": False, "dispatched": False, "already": False, "reopened": False}

    return {"candidate": True, "dispatched": True, "already": False, "reopened": False}


def dispatch_once(args) -> int:
    workspace = Path(args.workspace)
    state = read_state(workspace)
    dispatch_state = read_dispatch_state(workspace)
    tasks = state.get("tasks", {})

    candidates: list[str] = []
    candidate_tasks: list[dict] = []  # Task objects with status
    dispatched: list[str] = []
    already: list[str] = []
    reopened: list[str] = []

    for tid, task in tasks.items():
        existing = dispatch_state.get("items", {}).get(tid)
        result = classify_task(task, existing, args)

        if not result["candidate"]:
            continue

        candidates.append(tid)
        candidate_tasks.append(task)

        if result["reopened"]:
            reopened.append(tid)

        if result["already"]:
            already.append(tid)

        if result["dispatched"]:
            dispatched.append(tid)
            if not args.dry_run:
                order = build_order(task)
                dispatch_state.setdefault("items", {})[tid] = order

    if not args.dry_run:
        write_dispatch_state(workspace, dispatch_state)

    # NotebookLM 增强
    notebooklm_enriched = 0
    if args.enrich_notebooklm and not args.dry_run:
        # dry-run 仍报告（但 0）用于测试
        notebooklm_enriched = enrich_with_notebooklm(
            [t for t in tasks.values() if isinstance(t, dict)],
            mode=args.notebooklm_mode,
        )

    report = {
        "candidate_count": len(candidates),
        "dispatched_count": len(dispatched),
        "notebooklm_enriched": notebooklm_enriched,
        "already_dispatched_count": len(already),
        "reopened_count": len(reopened),
        "dispatched_tasks": dispatched,
        "already_dispatched_tasks": already,
        "candidate_tasks": candidate_tasks,
        "reopened_tasks": reopened,
        "timestamp": datetime.now().isoformat(),
    }

    write_report(workspace, report)
    if args.orders:
        orders = list(dispatch_state.get("items", {}).values())
        # Build task lookup for note extraction
        task_lookup = {tid: task for tid, task in tasks.items()}
        write_orders_markdown(
            workspace, orders, dispatch_state, task_lookup, args.orders
        )
    if args.history and not args.dry_run:
        write_history(workspace, json.dumps({"event": "dispatch", "count": len(dispatched)}))

    # 同时输出 key=value 摘要（用于 shell 解析）
    print(f"mode={args.notebooklm_mode}")
    print(f"candidate_count={report['candidate_count']}")
    print(f"dispatched_count={report['dispatched_count']}")
    print(f"already_dispatched_count={report['already_dispatched_count']}")
    print(f"stale_marked_blocked={report.get('stale_marked_blocked', 0)}")
    print(f"stale_marked_failed={report.get('stale_marked_failed', 0)}")
    print(f"patch_candidates={report.get('patch_candidates', 0)}")
    print(f"patches_created={report.get('patches_created', 0)}")
    print(f"prewarning_detected={report.get('prewarning_detected', 0)}")
    print(f"prewarning_applied={report.get('prewarning_applied', 0)}")
    print(f"task_contract_checked={report.get('task_contract_checked', 0)}")
    print(f"task_contract_invalid={report.get('task_contract_invalid', 0)}")
    print(f"notebooklm_enriched={report.get('notebooklm_enriched', 0)}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", default=".", required=False,
                   help="Workspace path (default: current directory)")
    p.add_argument("--include-pending", action="store_true")
    p.add_argument("--redispatch", action="store_true")
    p.add_argument("--force-workspace", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report")
    p.add_argument("--history")
    p.add_argument("--state")
    p.add_argument("--orders")
    p.add_argument("--enrich-notebooklm", action="store_true",
                   help="Enrich dispatch with NotebookLM knowledge")
    p.add_argument("--notebooklm-mode", default="fallback",
                   choices=["fallback", "mock", "real"],
                   help="NotebookLM integration mode")
    args = p.parse_args()
    return dispatch_once(args)


if __name__ == "__main__":
    sys.exit(main())
