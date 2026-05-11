"""
AI 协作开发系统 - CLI 工具

支持命令行操作：激活、检查冲突、查看任务、管理日志等
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 直接从当前包的子模块导入
from .activation_handler import ActivationHandler, ActivationMode, AIType, VSCodeIntegration
from .state_manager import PatchStatus, StateManager, TaskStatus


def cmd_activate(args):
    """激活 AI 协作系统"""
    ai_type_map = {
        "claude": AIType.CLAUDE_CODE,
        "claude_code": AIType.CLAUDE_CODE,
        "copilot": AIType.COPILOT,
        "codearts": AIType.CODEARTS_AGENT,
        "codearts_agent": AIType.CODEARTS_AGENT,
        # codex 当前沿用 Claude 规则集与会话激活路径
        "codex": AIType.CLAUDE_CODE,
    }

    ai_type = ai_type_map.get(args.ai.lower())
    if not ai_type:
        print(f"错误: 未知的 AI 类型 '{args.ai}'")
        print("支持的类型: claude, claude_code, copilot, codearts_agent, codex")
        return 1

    mode_map = {
        "cli": ActivationMode.CLI,
        "command": ActivationMode.COMMAND,
        "event": ActivationMode.EVENT,
        "on_save": ActivationMode.ON_SAVE,
    }
    mode = mode_map.get(args.mode, ActivationMode.CLI)

    # 设置 workspace 路径环境变量
    if args.workspace:
        os.environ["VSCODE_CWD"] = args.workspace

    # 激活回调函数
    def on_activated(session_id, rules, context):
        print("\n[激活回调]")
        print(f"  会话ID: {session_id}")
        print(f"  加载规则: {', '.join(rules)}")
        if context:
            print(f"  上下文: {json.dumps(context, ensure_ascii=False, indent=2)}")

    handler = ActivationHandler(
        ai_type=ai_type, workspace_path=args.workspace, on_activated=on_activated
    )

    print("=" * 60)
    print(f"AI 协作系统 - 激活 ({args.ai.upper()})")
    print("=" * 60)

    if args.input:
        # 使用自定义输入
        user_input = args.input
    else:
        # 等待用户输入或使用默认激活词
        user_input = f"开始任务 {ActivationHandler.ACTIVATION_KEYWORD}"

    if handler.check_activation(user_input, mode):
        result = handler.activate(mode)

        print("\n激活成功!")
        print(f"  AI类型: {result['ai_type']}")
        print(f"  会话ID: {result['session_id']}")
        print(f"  激活时间: {result['activation_time']}")
        print(f"  模式: {result['mode']}")
        print(f"  加载规则: {', '.join(result['rules_loaded'])}")
        print(f"\n  响应: {result['ack_message']}")

        if args.show_rules:
            print("\n[规则内容]")
            rules_content = handler.get_rules_content()
            for rule_file, content in rules_content.items():
                print(f"\n--- {rule_file} ---")
                print(content[:500] + "..." if len(content) > 500 else content)

        return 0
    else:
        print("\n激活失败: 未检测到激活词")
        return 1


def cmd_check(args):
    """检查文件冲突"""
    ai_type = args.ai.lower() if args.ai else "claude"

    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print(f"AI 协作系统 - 冲突检查 ({ai_type.upper()})")
    print("=" * 60)

    files_to_check = args.files or []
    if not files_to_check:
        print("\n警告: 未指定检查文件，将从当前工作目录查找")
        # 获取 workspace 下的常见文件
        workspace = args.workspace or VSCodeIntegration.get_workspace_path()
        if workspace:
            for root, dirs, files in os.walk(workspace):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file in files:
                    if file.endswith((".ts", ".tsx", ".js", ".py", ".go")):
                        rel_path = os.path.relpath(os.path.join(root, file), workspace)
                        files_to_check.append(rel_path)
                        if len(files_to_check) >= 10:
                            break
                if len(files_to_check) >= 10:
                    break

    if files_to_check:
        print(f"\n检查文件 ({len(files_to_check)} 个):")
        for f in files_to_check:
            print(f"  - {f}")

    check_mode = "both" if args.mode == "both" else "command"
    conflicts = state.check_conflicts(ai_type, files_to_check, check_mode)

    if conflicts:
        print(f"\n检测到 {len(conflicts)} 个冲突:")
        for i, c in enumerate(conflicts, 1):
            print(f"\n  冲突 {i}:")
            print(f"    任务ID: {c['task_id']}")
            print(f"    AI类型: {c['ai_type']}")
            print(f"    描述: {c['description']}")
            print(f"    状态: {c['status']}")
            print(f"    重叠文件: {c['overlapping_files']}")
            print(f"    检测时间: {c['detected_at']}")

            if args.resolve:
                # 自动尝试解决冲突
                conflict_id = c.get("conflict_id", f"conflict-{datetime.now().timestamp()}")
                if state.resolve_conflict(conflict_id, "待用户决策"):
                    print("    → 冲突已标记为待解决")
        return 1
    else:
        print("\n无冲突，可以安全开发")
        return 0


def cmd_tasks(args):
    """任务管理"""
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 任务管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        if args.status == "all":
            tasks = state.get_all_tasks()
        elif args.status == "active":
            tasks = state.get_active_tasks()
        elif args.status == "completed":
            tasks = [t for t in state.get_all_tasks() if t.get("status") == "completed"]
        else:
            tasks = [t for t in state.get_all_tasks() if t.get("status") == args.status]

        print(f"\n任务列表 ({args.status}, {len(tasks)} 个):")
        if tasks:
            for task in tasks:
                print(f"\n  {task['task_id']}")
                print(f"    AI: {task['ai_type']}")
                print(f"    描述: {task['description']}")
                print(f"    状态: {task['status']}")
                print(f"    创建时间: {task.get('created_at', 'N/A')}")
                if task.get("files"):
                    print(
                        f"    文件: {', '.join(task['files'][:3])}"
                        + ("..." if len(task["files"]) > 3 else "")
                    )
        else:
            print("  无任务")

    elif cmd == "register":
        task_id = args.task_id or f"TASK-{int(datetime.now().timestamp())}"
        task = state.register_task(
            task_id=task_id,
            ai_type=args.ai,
            description=args.description or "新任务",
            files=args.files or [],
            vscode_context={"source": "cli"},
        )
        print(f"\n任务已注册: {task_id}")
        print(f"  AI: {task['ai_type']}")
        print(f"  描述: {task['description']}")

    elif cmd == "update":
        if not args.task_id:
            print("\n错误: 需要指定 task_id")
            return 1

        status_map = {
            "pending": TaskStatus.PENDING,
            "planning": TaskStatus.PLANNING,
            "implementing": TaskStatus.IMPLEMENTING,
            "testing": TaskStatus.TESTING,
            "completed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
            "cancelled": TaskStatus.CANCELLED,
        }
        new_status = status_map.get(args.status, TaskStatus.PENDING)

        state.update_task_status(args.task_id, new_status, args.note)
        print(f"\n任务状态已更新: {args.task_id} -> {new_status.value}")

    return 0


def cmd_patches(args):
    """Patch 管理"""
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - Patch 管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        status_filter = None if args.status in (None, "all") else args.status
        patches = state.list_patches(status_filter=status_filter, task_id=args.task_id)
        print(f"\nPatch 列表 ({len(patches)} 个):")
        for patch in patches:
            print(
                f"  {patch.get('patch_id', 'N/A')} "
                f"[{patch.get('status', 'unknown')}] "
                f"task={patch.get('task_id', '')} assignee={patch.get('assignee', '')}"
            )
        if not patches:
            print("  无 patch")
        return 0

    if cmd == "create":
        if not args.task_id:
            print("\n错误: create 需要指定 --task-id")
            return 1
        patch_id = args.patch_id or f"PATCH-{int(datetime.now().timestamp())}"
        title = args.title or args.description or "patch"
        patch = state.register_patch(
            patch_id=patch_id,
            task_id=args.task_id,
            title=title,
            files=args.files or [],
            assignee=args.ai or "",
            note=args.note,
            actor=args.ai or "cli",
            source="cli.patches.create",
            reason=args.note or "",
        )
        print(f"\nPatch 已创建: {patch['patch_id']}")
        return 0

    if cmd == "update":
        status_map = {
            "pending": PatchStatus.PENDING,
            "in_progress": PatchStatus.IN_PROGRESS,
            "completed": PatchStatus.COMPLETED,
            "blocked": PatchStatus.BLOCKED,
            "cancelled": PatchStatus.CANCELLED,
        }
        new_status = status_map.get(args.status)
        if not args.patch_id or not new_status:
            print("\n错误: update 需要指定 --patch-id 和合法 --status")
            return 1
        state.update_patch_status(
            patch_id=args.patch_id,
            status=new_status,
            note=args.note,
            actor=args.ai or "cli",
            source="cli.patches.update",
            reason=args.note or "",
        )
        print(f"\nPatch 状态已更新: {args.patch_id} -> {new_status.value}")
        return 0

    if cmd == "assign":
        if not args.patch_id or not args.ai:
            print("\n错误: assign 需要指定 --patch-id 和 --ai")
            return 1
        patch = state.get_patch(args.patch_id)
        if not patch:
            print(f"\n错误: patch 不存在: {args.patch_id}")
            return 1
        patch["assignee"] = args.ai
        patch["updated_at"] = datetime.now().isoformat()
        patch.setdefault("notes", [])
        if args.note:
            patch["notes"].append(f"[{datetime.now().isoformat()}] {args.note}")
        state._save_state()  # noqa: SLF001
        print(f"\nPatch 已分派: {args.patch_id} -> {args.ai}")
        return 0

    if cmd == "claim":
        ai = args.ai or "codex"
        candidates = [
            p
            for p in state.list_patches(status_filter="pending")
            if not p.get("assignee") or p.get("assignee") == ai
        ]
        if not candidates:
            print("\n无可领取 patch")
            return 0
        target = candidates[0]
        target["assignee"] = ai
        target["updated_at"] = datetime.now().isoformat()
        state._save_state()  # noqa: SLF001
        state.update_patch_status(
            patch_id=target["patch_id"],
            status=PatchStatus.IN_PROGRESS,
            note=args.note or f"claimed by {ai}",
            actor=ai,
            source="cli.patches.claim",
            reason=args.note or "claim",
        )
        print(f"\n已领取: {target['patch_id']}")
        return 0

    print(f"\n错误: 未知 patch 子命令: {cmd}")
    return 1


def cmd_conflicts(args):
    """冲突管理"""
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 冲突管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        status_filter = args.status or None
        conflicts = state.get_conflicts(status_filter)

        print(f"\n冲突列表 ({len(conflicts)} 个):")
        if conflicts:
            for i, c in enumerate(conflicts, 1):
                print(f"\n  冲突 {i}: {c['conflict_id']}")
                print(f"    任务1: {c['task_id_1']} ({c['ai_type_1']})")
                print(f"    任务2: {c['task_id_2']} ({c['ai_type_2']})")
                print(f"    重叠文件: {c['overlapping_files']}")
                print(f"    状态: {c['status']}")
        else:
            print("  无冲突")

    elif cmd == "resolve":
        if not args.conflict_id:
            print("\n错误: 需要指定 conflict_id")
            return 1

        if state.resolve_conflict(args.conflict_id, args.resolution or "已解决"):
            print(f"\n冲突已解决: {args.conflict_id}")
        else:
            print(f"\n解决失败: 冲突 {args.conflict_id} 不存在")
            return 1

    return 0


def cmd_logs(args):
    """日志管理"""
    from .dev_logger import DevLogger

    # 设置 workspace 路径环境变量
    if args.workspace:
        os.environ["VSCODE_CWD"] = args.workspace

    ai_type = args.ai.lower() if args.ai else "claude-code"

    logger = DevLogger(ai_type)

    print("=" * 60)
    print(f"AI 协作系统 - 日志管理 ({ai_type})")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        logs = logger.list_logs(args.month)

        print(f"\n日志列表 ({len(logs)} 个):")
        for log in logs:
            log_name = os.path.basename(log)
            log_size = os.path.getsize(log)
            mtime = datetime.fromtimestamp(os.path.getmtime(log)).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  [{log_size:6d} bytes] {log_name}  ({mtime})")

    elif cmd == "show" and args.log_file:
        full_path = os.path.join(logger.log_dir, args.month, args.log_file) if args.month else ""
        if not full_path or not os.path.exists(full_path):
            # 查找匹配的文件
            logs = logger.list_logs(args.month)
            for log in logs:
                if args.log_file in log:
                    full_path = log
                    break

        if full_path and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                print(f"\n{f.read()}")
        else:
            print(f"\n错误: 日志文件 '{args.log_file}' 不存在")
            return 1

    return 0


def cmd_init(args):
    """初始化项目"""
    workspace = args.workspace or os.getcwd()

    # 设置 workspace 路径环境变量
    os.environ["VSCODE_CWD"] = workspace

    print("=" * 60)
    print("AI 协作系统 - 项目初始化")
    print("=" * 60)

    # 创建目录结构
    dirs_to_create = [
        os.path.join(workspace, ".vscode"),
        os.path.join(workspace, "logs", "activations"),
        os.path.join(workspace, "logs", "claude-code"),
        os.path.join(workspace, "logs", "codearts-agent"),
        os.path.join(workspace, "logs", "copilot"),
        os.path.join(workspace, "logs", "backups"),
        os.path.join(workspace, ".git", "ai-collab", "activations"),
    ]

    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)
        print(f"  ✓ 创建目录: {d}")

    # 创建配置文件
    vscode_config = {
        "version": "1.0.0",
        "rulesDir": "./rules",
        "logsDir": "./logs",
        "stateFile": "./logs/collaboration_state.json",
        "activationKeyword": "2X",
        "conflictCheckOnSave": True,
        "conflictCheckOnCommand": True,
        "enabledAIs": ["claude_code", "codex", "codearts_agent"],
        "agentOrchestration": {
            "autoDetectAgents": True,
            "includeUserAsOperator": True,
            "operatorFirst": False,
            "forceLeadAgent": None,
            "disabledAgents": ["copilot"],
            "intentLeadMap": {
                "architecture": ["codex", "claude_code", "codearts_agent"],
                "implementation": ["claude_code", "codex", "codearts_agent"],
                "testing": ["codearts_agent", "claude_code", "codex"],
                "documentation": ["codearts_agent", "codex", "claude_code"],
            },
            "modelAgentMap": {
                "claude": "claude_code",
                "copilot": "codearts_agent",
                "glm|codearts": "codearts_agent",
                "gpt|codex|openai": "codex",
            },
        },
    }

    config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(vscode_config, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 创建配置: {config_file}")

    # 初始化状态文件
    state = StateManager(workspace_path=workspace)
    print(f"  ✓ 初始化状态: {state.workspace_path}")

    print("\n项目初始化完成!")
    print(f"  工作区: {workspace}")
    print("\n下一步:")
    print("  1. 运行: ai-collab activate --ai claude")
    print("  2. 检测冲突: ai-collab check --files <file-path>")

    return 0


def cmd_clean(args):
    """清理旧日志"""
    from .dev_logger import DevLogger

    # 设置 workspace 路径环境变量
    if args.workspace:
        os.environ["VSCODE_CWD"] = args.workspace

    print("=" * 60)
    print("AI 协作系统 - 清理旧日志")
    print("=" * 60)

    claude_logger = DevLogger("claude-code")
    codearts_logger = DevLogger("codearts-agent")
    copilot_logger = DevLogger("copilot")

    claude_logger.rotate_logs(args.max_files)
    codearts_logger.rotate_logs(args.max_files)
    copilot_logger.rotate_logs(args.max_files)

    # 清理已完成的任务
    state = StateManager(workspace_path=args.workspace)
    result = state.clear_completed_tasks(args.days if args.days else 30)

    print("\n清理完成:")
    print(f"  保留最近日志: {args.max_files} 个")
    print(f"  保留最近任务: {args.days if args.days else 30} 天")
    print(f"  清除任务数: {result['cleared']}")
    print(f"  剩余任务数: {result['remaining']}")

    return 0


def cmd_status(args):
    """显示系统状态"""
    state = StateManager(workspace_path=args.workspace)
    workspace = args.workspace or VSCodeIntegration.get_workspace_path()

    print("=" * 60)
    print("AI 协作系统 - 系统状态")
    print("=" * 60)

    print("\n[工作区]")
    print(f"  路径: {workspace or '未设置'}")

    config = VSCodeIntegration.get_project_config()
    print("\n[项目配置]")
    print(f"  版本: {config.get('version', 'N/A')}")
    print(f"  规则目录: {config.get('rulesDir', './rules')}")
    print(f"  日志目录: {config.get('logsDir', './logs')}")
    print(f"  激活词: {config.get('activationKeyword', '2X')}")
    print(f"  启用AI: {', '.join(config.get('enabledAIs', []))}")

    print("\n[任务统计]")
    active_tasks = state.get_active_tasks()
    all_tasks = state.get_all_tasks()
    completed = [t for t in all_tasks if t.get("status") == "completed"]

    claude_tasks = [t for t in active_tasks if t.get("ai_type") == "claude_code"]
    codearts_tasks = [t for t in active_tasks if t.get("ai_type") == "codearts_agent"]
    copilot_tasks = [t for t in active_tasks if t.get("ai_type") == "copilot"]

    print(f"  总任务数: {len(all_tasks)}")
    print(f"  活跃任务: {len(active_tasks)}")
    print(f"    - Claude Code: {len(claude_tasks)}")
    print(f"    - CodeArts Agent: {len(codearts_tasks)}")
    print(f"    - Copilot: {len(copilot_tasks)}")
    print(f"  已完成任务: {len(completed)}")

    conflicts = state.get_conflicts("open")
    print("\n[冲突状态]")
    print(f"  未解决冲突: {len(conflicts)}")

    if conflicts and args.verbose:
        for c in conflicts[:3]:
            print(f"    - {c['task_id_1']} vs {c['task_id_2']}")

    return 0


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="AI 协作开发系统 - Claude Code + GitHub Copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 激活 Claude Code
  ai-collab activate --ai claude

  # 检查文件冲突
  ai-collab check --ai claude --files src/api.ts

  # 初始化项目
  ai-collab init

  # 查看系统状态
  ai-collab status

  # 查看活跃任务
  ai-collab tasks list --status active
        """,
    )

    parser.add_argument("-w", "--workspace", help="工作区路径")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 2.0.0")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # activate 命令
    activate_parser = subparsers.add_parser("activate", help="激活 AI 协作系统")
    activate_parser.add_argument(
        "--ai",
        choices=["claude", "claude_code", "copilot", "codearts_agent", "codex"],
        default="claude",
        help="AI 类型",
    )
    activate_parser.add_argument(
        "--mode", choices=["cli", "command", "event", "on_save"], default="cli", help="激活模式"
    )
    activate_parser.add_argument("--input", help="自定义激活输入")
    activate_parser.add_argument("--show-rules", action="store_true", help="显示规则内容")

    # check 命令
    check_parser = subparsers.add_parser("check", help="检查文件冲突")
    check_parser.add_argument(
        "--ai", choices=["claude", "copilot", "codearts_agent", "codex"], help="检查的 AI 类型"
    )
    check_parser.add_argument("--files", nargs="*", help="要检查的文件列表")
    check_parser.add_argument(
        "--mode", choices=["on_save", "command", "both"], default="both", help="检查模式"
    )
    check_parser.add_argument("--resolve", action="store_true", help="自动标记冲突")

    # tasks 命令
    tasks_parser = subparsers.add_parser("tasks", help="任务管理")
    tasks_parser.add_argument("subcommand", choices=["list", "register", "update"], help="子命令")
    tasks_parser.add_argument(
        "--status",
        choices=["all", "active", "completed", "pending", "implementing"],
        default="active",
        help="任务状态过滤",
    )
    tasks_parser.add_argument("--task-id", help="任务ID")
    tasks_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codearts_agent", "codex"], help="AI 类型"
    )
    tasks_parser.add_argument("--description", help="任务描述")
    tasks_parser.add_argument("--files", nargs="*", help="涉及文件")
    tasks_parser.add_argument("--note", help="备注")

    # patches 命令
    patches_parser = subparsers.add_parser("patches", help="Patch 管理")
    patches_parser.add_argument(
        "subcommand", choices=["list", "create", "update", "assign", "claim"], help="子命令"
    )
    patches_parser.add_argument("--patch-id", help="Patch ID")
    patches_parser.add_argument("--task-id", help="关联任务ID")
    patches_parser.add_argument(
        "--status",
        choices=["all", "pending", "in_progress", "completed", "blocked", "cancelled"],
        default="all",
        help="Patch 状态过滤",
    )
    patches_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codex", "codearts_agent"], help="AI 类型"
    )
    patches_parser.add_argument("--title", help="Patch 标题")
    patches_parser.add_argument("--description", help="Patch 描述")
    patches_parser.add_argument("--files", nargs="*", help="涉及文件")
    patches_parser.add_argument("--note", help="备注")

    # conflicts 命令
    conflicts_parser = subparsers.add_parser("conflicts", help="冲突管理")
    conflicts_parser.add_argument("subcommand", choices=["list", "resolve"], help="子命令")
    conflicts_parser.add_argument("--status", choices=["open", "resolved"], help="状态过滤")
    conflicts_parser.add_argument("--conflict-id", help="冲突ID")
    conflicts_parser.add_argument("--resolution", help="解决方案")

    # logs 命令
    logs_parser = subparsers.add_parser("logs", help="日志管理")
    logs_parser.add_argument("subcommand", choices=["list", "show"], help="子命令")
    logs_parser.add_argument(
        "--ai", choices=["claude-code", "codearts-agent", "copilot"], help="AI 类型"
    )
    logs_parser.add_argument("--month", help="月份过滤 (YYYY-MM)")
    logs_parser.add_argument("--log-file", help="日志文件名")

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    # 兼容写法：允许 `ai-collab init --workspace .`（全局 `-w/--workspace` 仍可用）
    init_parser.add_argument("--workspace", help="工作区路径（兼容写法，可放在 init 后）")

    # clean 命令
    clean_parser = subparsers.add_parser("clean", help="清理旧日志")
    clean_parser.add_argument("--max-files", type=int, default=30, help="保留日志文件数")
    clean_parser.add_argument("--days", type=int, help="保留任务天数")

    # status 命令
    status_parser = subparsers.add_parser("status", help="显示系统状态")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 命令路由
    if args.command == "activate":
        return cmd_activate(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "tasks":
        return cmd_tasks(args)
    elif args.command == "patches":
        return cmd_patches(args)
    elif args.command == "conflicts":
        return cmd_conflicts(args)
    elif args.command == "logs":
        return cmd_logs(args)
    elif args.command == "init":
        return cmd_init(args)
    elif args.command == "clean":
        return cmd_clean(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
