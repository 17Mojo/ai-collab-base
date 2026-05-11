#!/usr/bin/env python3
"""
AI协作开发系统 - VSCode 集成版演示

展示 Claude Code 与 GitHub Copilot 在 VSCode 中的协作流程
"""

import json
import os
import sys

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from activation_handler import ActivationHandler, ActivationMode, AIType, VSCodeIntegration
from dev_logger import DevLogger, VSCodeOutputLogger
from state_manager import StateManager, TaskStatus


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def demo_vscode_integration():
    """演示1: VSCode 集成特性"""
    print_separator("演示1: VSCode 集成特性")

    workspace = VSCodeIntegration.get_workspace_path()
    print(f"\n>>> 当前工作区: {workspace or '未检测到 VSCode 工作区'}")

    config = VSCodeIntegration.get_project_config()
    print("\n>>> 项目配置 (.vscode/ai-collab.json):")
    print(json.dumps(config, ensure_ascii=False, indent=2))

    # 测试 VSCode 输出
    print("\n>>> 测试 VSCode 输出面板")
    VSCodeOutputLogger.log("演示日志消息", "AI Collab Demo")
    print("  ✓ 已写入到 ~/.vscode/ai-collab/output_YYYYMMDD.log")


def demo_claude_vs_copilot():
    """演示2: Claude Code 与 Copilot 协作"""
    print_separator("演示2: Claude Code 与 Copilot 协作")

    state = StateManager()

    # Claude Code 开始任务
    print("\n>>> Claude Code 开始重构 API 模块")
    task1 = state.register_task(
        task_id="TASK-API-V2-001",
        ai_type="claude_code",
        description="重构用户认证 API",
        files=["src/api/auth.ts", "src/api/user.ts", "src/services/auth.ts"],
    )
    print(f"  ✓ 已注册 Claude Code 任务: {task1['task_id']}")

    state.update_task_status(task1["task_id"], TaskStatus.IMPLEMENTING, "开始实现代码")
    print("  ✓ Claude Code 状态: implementing")

    # Copilot 尝试修改相同文件（冲突检测）
    print("\n>>> Copilot 尝试补全 src/api/auth.ts（冲突检测）")
    conflicts = state.check_conflicts(
        ai_type="copilot", files=["src/api/auth.ts", "src/utils/helper.ts"], check_mode="on_save"
    )

    if conflicts:
        print(f"  ⚠ 检测到 {len(conflicts)} 个冲突:")
        for c in conflicts:
            print(f"    - 与 {c['task_id']} ({c['ai_type']}) 冲突")
            print(f"      状态: {c['status']}")
            print(f"      检测模式: {c['check_mode']}")
            print("      建议: 等待 Claude Code 完成任务")
    else:
        print("  ✓ 无冲突，安全")

    # Copilot 修改不同文件（无冲突）
    print("\n>>> Copilot 补全 UI 组件（无冲突）")
    task2 = state.register_task(
        task_id="TASK-UI-020",
        ai_type="copilot",
        description="生成登录表单组件",
        files=["src/components/LoginForm.tsx", "src/types/login.ts"],
    )
    print(f"  ✓ Copilot 任务已注册: {task2['task_id']}")

    # 完成任务
    print("\n>>> 完成任务")
    state.update_task_status(task1["task_id"], TaskStatus.COMPLETED, "API 重构完成")
    state.update_task_status(task2["task_id"], TaskStatus.COMPLETED, "UI 组件生成完成")
    print("  ✓ 所有任务已完成")


def demo_activation_modes():
    """演示3: 多种激活模式"""
    print_separator("演示3: 多种激活模式")

    # CLI 模式
    print("\n>>> CLI 激活模式")
    handler = ActivationHandler(AIType.CLAUDE_CODE)
    if handler.check_activation("开始开发 2X", ActivationMode.CLI):
        result = handler.activate(ActivationMode.CLI, {"source": "cli"})
        print(f"  ✓ 激活成功: {result['ack_message']}")
        print(f"    模式: {result['mode']}")
        print(f"    会话ID: {result['session_id']}")

    # VSCode 命令模式
    print("\n>>> VSCode 命令激活模式")
    handler = ActivationHandler(AIType.COPILOT)
    result = handler.activate(ActivationMode.COMMAND, {"source": "vscode_command"})
    print(f"  ✓ 激活成功: {result['ack_message']}")
    print(f"    模式: {result['mode']}")

    # 文件保存检测模式
    print("\n>>> 文件保存检测模式")
    handler = ActivationHandler(AIType.CLAUDE_CODE)
    # 检测 .ts 文件保存
    if handler.check_activation("src/api.ts", ActivationMode.ON_SAVE):
        print("  ✓ 检测到 TypeScript 文件保存")
        print("    可以触发关联操作")
    else:
        print("  - 文件类型不在监控范围内")


def demo_triple_logging():
    """演示4: 三重日志存储"""
    print_separator("演示4: 三重日志存储 (项目本地 + Git + VSCode)")

    claude_logger = DevLogger("claude-code", enable_git_log=True, enable_vsc_log=True)

    print("\n>>> Claude Code 创建日志")
    log_path = claude_logger.create_log(
        task_name="api-auth-refactor",
        task_id="TASK-API-V2-001",
        description="重构认证 API",
        goal="优化性能、增强安全性",
        steps="1. 分析现有代码\n2. 设计新接口\n3. 迁移数据\n4. 测试验证",
        risks="数据库迁移风险、性能回退风险",
    )
    print(f"  ✓ 项目本地日志: {log_path}")

    # 追加执行过程
    print("\n>>> 记录执行过程")
    claude_logger.append_to_log(
        log_path,
        "执行过程",
        "### [10:30:00] 阶段一：Preflight\n"
        + "- [x] 读取 .vscode/ai-collab.json\n"
        + "- [x] 检查冲突状态\n"
        + "- [x] 确认无冲突\n\n"
        + "### [10:45:00] 阶段二：Plan\n"
        + "- 制定执行计划\n"
        + "- 标记风险点\n"
        + "- 计划已确认",
    )
    print("  ✓ 已追加到日志")

    # Copilot 日志
    print("\n>>> Copilot 创建日志")
    copilot_logger = DevLogger("copilot", enable_git_log=True, enable_vsc_log=True)
    copilot_log = copilot_logger.create_log(
        task_name="login-form-gen", task_id="TASK-UI-020", description="生成登录表单组件"
    )
    print(f"  ✓ 项目本地日志: {copilot_log}")
    print("  ✓ Git 追踪: .git/ai-collab/copilot/*")
    print("  ✓ VSCode 输出: ~./vscode/ai-collab/output_*.log")


def demo_complete_vscode_workflow():
    """演示5: 完整 VSCode 工作流程"""
    print_separator("演示5: 完整 VSCode 工作流程")

    print("\n>>> 场景: 在 VSCode 中开发新功能")
    print("-" * 70)

    # 步骤1: 用户触发 VSCode 任务
    print("\n[步骤1] 用户运行 VSCode 任务")
    print("  命令: Tasks: Run Task -> AI Collab: Activate Claude Code")

    handler = ActivationHandler(AIType.CLAUDE_CODE)
    result = handler.activate(
        ActivationMode.COMMAND,
        {"source": "vscode_task", "workspace": VSCodeIntegration.get_workspace_path()},
    )
    print(f"  ✓ {result['ack_message']}")

    # 步骤2: 检查 VSCode 项目配置
    print("\n[步骤2] 检查项目配置")
    config = VSCodeIntegration.get_project_config()
    print(f"  规则目录: {config.get('rulesDir', './rules')}")
    print(f"  冲突检测(保存): {config.get('conflictCheckOnSave', True)}")
    print(f"  冲突检测(命令): {config.get('conflictCheckOnCommand', True)}")

    # 步骤3: 注册任务
    print("\n[步骤3] 注册开发任务")
    state = StateManager()
    task = state.register_task(
        task_id="TASK-VSC-001",
        ai_type="claude_code",
        description="用户认证功能开发",
        files=["src/auth/index.ts", "src/auth/types.ts", "src/components/AuthForm.tsx"],
        vscode_context={"trigger": "vscode_task"},
    )
    print(f"  ✓ 任务已注册: {task['task_id']}")

    # 步骤4: 保存文件触发冲突检测
    print("\n[步骤4] 保存文件触发冲突检测")
    print("  用户保存: src/auth/index.ts")
    state.update_task_status(task["task_id"], TaskStatus.IMPLEMENTING)

    # 模拟 Copilot 同时操作
    copilot_conflicts = state.check_conflicts(
        ai_type="copilot", files=["src/types/user.ts"], check_mode="on_save"  # 不同文件，无冲突
    )

    if copilot_conflicts:
        print("  ⚠ 检测到冲突")
    else:
        # 检查与 Claude Code 的冲突
        copilot_conflicts = state.check_conflicts(
            ai_type="copilot", files=["src/auth/index.ts"], check_mode="on_save"  # 相同文件，冲突！
        )
        if copilot_conflicts:
            print("  ⚠ Copilot 无法修改此文件: Claude Code 正在编辑")
            print("    - VSCode 状态栏显示冲突警告")

    # 步骤5: 创建日志
    print("\n[步骤5] 创建开发日志")
    logger = DevLogger("claude-code", enable_vsc_log=True)
    log_path = logger.create_log(
        task_name="auth-feature-dev", task_id=task["task_id"], description="用户认证功能"
    )
    print("  ✓ 日志已创建")
    print(f"    项目: {log_path}")
    print("    Git: .git/ai-collab/claude-code/*")
    print("    VSCode: 输出面板 'AI Collab Logs'")

    # 步骤6: 记录进度到 VSCode
    print("\n[步骤6] 记录进度")
    VSCodeOutputLogger.log_progress(task["task_id"], "Implement", "认证逻辑实现中...")
    logger.append_to_log(log_path, "执行过程", "### [11:00] 实现认证逻辑\n- JWT token 生成\n- 密码加密")
    print("  ✓ 进度已记录")

    # 步骤7: 完成
    print("\n[步骤7] 任务完成")
    state.update_task_status(task["task_id"], TaskStatus.COMPLETED, "功能开发完成")
    logger.finalize_log(log_path, summary="用户认证功能完成, 包含登录/注册/密码重置")
    VSCodeOutputLogger.log(f"任务完成: {task['task_id']}", "AI Collab Tasks")
    print("  ✓ 任务已完成")
    print("    状态: completed")
    print("    日志: 已归档")
    print("    VSCode: 显示完成通知")

    print("\n" + "-" * 70)
    print(">>> VSCode 工作流程演示完成")


def demo_cli_commands():
    """演示6: CLI 命令使用"""
    print_separator("演示6: CLI 命令使用")

    print("\n>>> 可用的 CLI 命令")
    commands = [
        ("ai-collab activate --ai claude", "激活 Claude Code"),
        ("ai-collab activate --ai copilot", "激活 Copilot"),
        ("ai-collab check --ai claude --files src/api.ts", "检查文件冲突"),
        ("ai-collab tasks list --status active", "列出活跃任务"),
        ("ai-collab tasks register --ai claude --desc 'xxx'", "注册新任务"),
        ("ai-collab tasks update --task-id XXX --status completed", "更新任务状态"),
        ("ai-collab conflicts list", "列出冲突"),
        ("ai-collab logs list", "列出日志"),
        ("ai-collab status", "查看系统状态"),
        ("ai-collab init", "初始化项目"),
        ("ai-collab clean --days 7", "清理旧日志"),
    ]

    for cmd, desc in commands:
        print(f"  {cmd:45} # {desc}")

    print("\n>>> 在 VSCode 中运行")
    print("  方式1: 终端运行命令")
    print("  方式2: tasks.json 配置的任务")
    print("  方式3: keybindings.json 绑定快捷键")


def demo_sync_mechanisms():
    """演示7: 状态同步机制"""
    print_separator("演示7: 状态同步机制")

    print("\n>>> 两种状态存储方式")

    # 项目级状态
    print("\n[项目级状态]")
    print("  文件: .vscode/ai-collab.json + ./logs/collaboration_state.json")
    print("  作用: 项目内的协作状态")
    print("  内容: 任务列表、冲突记录、文件状态")

    state = StateManager()
    print(f"  当前活跃任务: {len(state.get_active_tasks())} 个")
    print(f"  未解决冲突: {len(state.get_conflicts('open'))} 个")

    # 全局状态
    print("\n[全局状态]")
    print("  文件: ~/.vscode/ai-collab/collaboration_state.json")
    print("  作用: 跨项目协作追踪")
    print("  内容: 所有工作区的任务摘要")

    global_file = os.path.expanduser("~/.vscode/ai-collab/collaboration_state.json")
    if os.path.exists(global_file):
        with open(global_file, "r") as f:
            global_state = json.load(f)
        print(f"  追踪的工作区数量: {len(global_state)}")
        for workspace, data in global_state.items():
            print(f"    - {workspace}: {data.get('last_sync', 'N/A')}")


def cleanup_demo_data():
    """清理演示数据"""
    print_separator("清理演示数据")

    # 清理日志
    import glob

    log_patterns = [
        "./logs/activations/*.jsonl",
        "./logs/claude-code/**/*.md",
        "./logs/copilot/**/*.md",
        "./logs/collaboration_state.json",
        "./logs/collaboration_issues.json",
    ]

    for pattern in log_patterns:
        files = glob.glob(pattern, recursive=True)
        for f in files:
            try:
                os.remove(f)
                print(f"  ✓ 已删除: {f}")
            except Exception as e:
                print(f"  ✗ 删除失败: {f} - {e}")

    # 清理 Git 追踪
    git_patterns = [".git/ai-collab/**/*.md", ".git/ai-collab/activations/*.jsonl"]

    for pattern in git_patterns:
        files = glob.glob(pattern, recursive=True)
        for f in files:
            try:
                os.remove(f)
                print(f"  ✓ 已删除: {f}")
            except Exception as e:
                print(f"  ✗ 删除失败: {f} - {e}")

    print("\n  ✓ 演示数据已清理")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" AI协作开发系统 - VSCode 集成演示")
    print("    Claude Code + GitHub Copilot")
    print("=" * 70)
    print("\n本演示展示 AI 协作开发系统在 VSCode 中的完整功能：")
    print("  1. VSCode 集成特性")
    print("  2. Claude Code 与 Copilot 协作")
    print("  3. 多种激活模式")
    print("  4. 三重日志存储")
    print("  5. 完整 VSCode 工作流程")
    print("  6. CLI 命令使用")
    print("  7. 状态同步机制")

    try:
        demo_vscode_integration()
        demo_claude_vs_copilot()
        demo_activation_modes()
        demo_triple_logging()
        demo_complete_vscode_workflow()
        demo_cli_commands()
        demo_sync_mechanisms()

        cleanup_demo_data()

        print("\n" + "=" * 70)
        print(" 演示完成！")
        print("=" * 70)
        print("\n项目结构:")
        print("  .vscode/")
        print("    ├── settings.json       # VSCode 配置")
        print("    ├── tasks.json         # VSCode 任务")
        print("    ├── ai-collab.json     # 项目 AI 配置")
        print("    └── ai-collab.code-snippets  # 代码片段")
        print("")
        print("  rules/")
        print("    ├── claude_code_memory.md   # Claude Code 规则")
        print("    ├── copilot_rules.md        # Copilot 规则")
        print("    └── dev-record-template.md  # 日志模板")
        print("")
        print("  logs/")
        print("    ├── claude-code/      # Claude Code 日志")
        print("    ├── copilot/          # Copilot 日志")
        print("    ├── activations/      # 激活记录")
        print("    └── collaboration_state.json  # 协作状态")
        print("")
        print("  .git/ai-collab/         # Git 追踪日志")
        print("")
        print("  ~./vscode/ai-collab/    # 全局配置和输出")
        print("")
        print("开始使用:")
        print("  1. 在 VSCode 中运行任务: Ctrl+Shift+P -> Tasks: Run Task")
        print("  2. 或在终端运行: python -m ai_collab.cli activate --ai claude")
        print("  3. 保存文件时自动触发冲突检测")
        print("  4. 查看 VSCode 输出面板查看协作日志")

    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n\n演示出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
