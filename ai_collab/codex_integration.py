"""
CC Claude Codex 集成模块

最小落地目标：
- 在项目内维护 .cc-claude-codex/ 状态目录
- 生成 codex-progress.md 批次任务文件
- 调用 codex CLI 执行任务并输出日志
- 将执行进度同步到 ai_collab 状态管理器
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent_orchestrator import AgentOrchestrator
from .state_manager import StateManager, TaskStatus

CODEX_PROMPT = """Read .cc-claude-codex/codex-progress.md now. This is your task file.

Working rules:
1. Read .cc-claude-codex/codex-progress.md first.
2. Start from the first unfinished step.
3. After each finished step, update the progress file:
   - Mark that step as [x]
   - Append changed files in Execution Log
4. If blocked, record the reason in Blockers.
5. After all steps are done, set top status to Completed.

Begin now and follow the file strictly."""


@dataclass
class CodexRunResult:
    exit_reason: str
    return_code: int
    duration_seconds: int
    log_file: str
    output_file: str
    progress_file: str


@dataclass
class HookOperationResult:
    action: str
    settings_file: str
    installed: bool
    details: dict[str, Any]


class CodexIntegration:
    """本地 CC Claude Codex 集成辅助。"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.state_dir = self.workspace / ".cc-claude-codex"
        self.status_file = self.state_dir / "status.md"
        self.progress_file = self.state_dir / "codex-progress.md"
        self.logs_dir = self.state_dir / "logs"
        self.snapshots_dir = self.state_dir / "snapshots"
        self.runtime_file = self.state_dir / "runtime.json"
        self.hooks_dir = Path(__file__).resolve().parent / "hooks"

    def ensure_initialized(self, goal: str = "", context: str = "") -> Path:
        """初始化 .cc-claude-codex 目录和 status.md。"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        if not self.status_file.exists():
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = (
                "# Project Status\n\n"
                f"> Last Updated: {now}\n\n"
                "## Requirement Spec\n\n"
                f"**Goal:** {goal or 'TBD'}\n\n"
                f"**Context:** {context or 'TBD'}\n\n"
                "## Requirements\n\n"
                "### Requirement: Base capability\n\n"
                "The system MUST complete the described task and keep tests passing.\n\n"
                "#### Scenario: Task execution\n"
                "- **WHEN** Codex executes the provided progress file\n"
                "- **THEN** implementation is completed and verified by test output\n\n"
                "## Subtasks\n\n"
                "### Batch 1: Initial batch\n"
                "- [ ] Create codex progress and execute first batch\n\n"
                "## Verification Results\n\n"
                "| Subtask | Scenario Verified | Status | Method | Notes |\n"
                "|---------|-------------------|--------|--------|-------|\n\n"
                "## Technical Decisions\n"
                "- Pending\n\n"
                "## Known Issues\n"
                "- (None)\n\n"
                "## Codex Execution Log\n"
                "| Time | Batch | exit_reason | Notes |\n"
                "|------|-------|-------------|-------|\n"
            )
            self.status_file.write_text(content, encoding="utf-8")

        self._ensure_gitignore_entries()
        return self.status_file

    def write_progress(
        self,
        goal: str,
        steps: list[str],
        tech_stack: str = "",
        follow_patterns: str = "",
        avoid_patterns: str = "",
        related_files: list[str] | None = None,
        test_cmd: str = "",
    ) -> Path:
        """生成 codex-progress.md。"""
        self.ensure_initialized(goal=goal)
        related_files = related_files or []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if not steps:
            steps = [goal]

        step_lines = []
        for idx, step in enumerate(steps, 1):
            step_lines.append(
                f"- [ ] **Step {idx}: {step}**\n"
                f"  - **Scope:** {', '.join(related_files) if related_files else 'TBD'}\n"
                "  - **Acceptance:** Related tests/verification pass and behavior is correct.\n"
            )

        content = (
            "# Codex Task Progress\n\n"
            "> Status: ⏳ In Progress\n"
            f"> Start Time: {now}\n"
            f"> Last Updated: {now}\n\n"
            "## Task Goal\n\n"
            f"{goal}\n\n"
            "## Project Conventions\n\n"
            f"- **Tech stack:** {tech_stack or 'Follow existing project stack'}\n"
            f"- **Patterns to follow:** {follow_patterns or 'Reuse existing project conventions'}\n"
            f"- **Patterns to avoid:** {avoid_patterns or 'Breaking existing APIs and unrelated refactors'}\n"
            f"- **Relevant existing files:** {', '.join(related_files) if related_files else 'TBD'}\n"
            f"- **Test conventions:** {test_cmd or 'Run project tests and keep all green'}\n\n"
            "## Steps\n\n"
            f"{''.join(step_lines)}\n"
            "## Execution Log\n"
            "| Time | Step | Files Changed | Notes |\n"
            "|------|------|---------------|-------|\n\n"
            "## Blockers\n"
            "(None)\n"
        )
        self.progress_file.write_text(content, encoding="utf-8")
        return self.progress_file

    def plan_roles(
        self,
        intent: str,
        models: list[str] | None = None,
        operator: str = "user",
        force_lead: str | None = None,
    ) -> dict[str, Any]:
        """基于意图和模型生成主辅角色计划。"""
        orchestrator = AgentOrchestrator(str(self.workspace))
        plan = orchestrator.build_plan(
            intent=intent,
            models=models or [],
            operator=operator,
            force_lead=force_lead,
        )

        runtime = self._read_runtime()
        runtime["last_intent"] = intent
        runtime["models"] = models or []
        runtime["operator"] = operator
        runtime["role_plan"] = plan.to_dict()
        runtime["last_plan_at"] = datetime.now().isoformat()
        self.runtime_file.write_text(
            json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return plan.to_dict()

    def _terminate_process_safely(self, proc: subprocess.Popen, timeout: int = 5) -> bool:
        """
        安全终止进程，预防僵尸进程

        Args:
            proc: 要终止的进程对象
            timeout: 等待进程退出的超时时间（秒）

        Returns:
            是否成功终止进程
        """
        try:
            if proc.poll() is not None:
                # 进程已经结束
                return True

            # 先尝试 SIGTERM（优雅终止）
            proc.terminate()

            try:
                proc.wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                # SIGTERM 无效，使用 SIGKILL（强制终止）
                proc.kill()

                try:
                    proc.wait(timeout=timeout)
                    return True
                except subprocess.TimeoutExpired:
                    # 强制终止也失败，记录警告
                    import warnings

                    warnings.warn(
                        f"Failed to terminate process {proc.pid} after {timeout * 2} seconds"
                    )
                    return False

        except Exception as e:
            # 终止过程中发生异常
            import warnings

            warnings.warn(f"Exception during process termination: {e}")
            return False

    def run_codex(
        self,
        readonly: bool = False,
        max_timeout: int = 0,
        stale_timeout: int = 120,
        sandbox: str | None = None,
    ) -> CodexRunResult:
        """调用 codex 执行并返回执行结果。"""
        codex_bin = shutil.which("codex")
        if not codex_bin:
            raise RuntimeError("未找到 codex 命令，请先安装并加入 PATH。")
        if not self.progress_file.exists():
            raise RuntimeError("未找到 .cc-claude-codex/codex-progress.md，请先执行 codex progress。")
        progress_info = self.validate_progress()
        if progress_info["total_steps"] <= 0:
            raise RuntimeError("进度文件未定义有效步骤，请先执行 codex progress --step <步骤内容>。")

        run_sandbox = self._resolve_sandbox(sandbox=sandbox, readonly=readonly)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = self.logs_dir / f"codex-{ts}.log"
        out_file = self.logs_dir / f"codex-{ts}-output.md"

        cmd = [codex_bin, "exec", "--sandbox", run_sandbox, "-o", str(out_file), CODEX_PROMPT]
        start_time = time.time()
        exit_reason = "done"
        return_code = 0

        with open(log_file, "w", encoding="utf-8") as lf:
            proc = subprocess.Popen(  # noqa: S603
                cmd,
                cwd=str(self.workspace),
                stdout=lf,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # 使用较短轮询间隔，确保 max_timeout/stale_timeout 能及时生效。
            poll_interval = 2
            last_activity = time.time()
            last_log_size = 0

            while True:
                try:
                    proc.wait(timeout=poll_interval)
                    return_code = proc.returncode
                    if return_code != 0:
                        exit_reason = f"error(code={return_code})"
                    break
                except subprocess.TimeoutExpired:
                    now = time.time()
                    if max_timeout > 0 and int(now - start_time) >= max_timeout:
                        self._terminate_process_safely(proc)
                        return_code = 124
                        exit_reason = f"hard_timeout({max_timeout}s)"
                        break

                    current_size = log_file.stat().st_size
                    if current_size > last_log_size:
                        last_log_size = current_size
                        last_activity = now
                    elif int(now - last_activity) >= stale_timeout:
                        self._terminate_process_safely(proc)
                        return_code = 124
                        exit_reason = f"stale_timeout({stale_timeout}s)"
                        break

        self._ensure_output_file(log_file=log_file, out_file=out_file, exit_reason=exit_reason)
        duration = int(time.time() - start_time)
        result = CodexRunResult(
            exit_reason=exit_reason,
            return_code=return_code,
            duration_seconds=duration,
            log_file=str(log_file),
            output_file=str(out_file),
            progress_file=str(self.progress_file),
        )
        self._write_runtime(result)
        return result

    def install_hooks(self) -> HookOperationResult:
        """安装 Stop/PreCompact/SessionStart/PreToolUse Hook 到 ~/.claude/settings.json。"""
        settings_file = self._claude_settings_file()
        settings = self._read_settings(settings_file)
        hook_config = self._build_hook_config()
        merged = self._merge_hooks(settings=settings, new_hooks=hook_config)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

        details = self.hooks_status().details
        return HookOperationResult(
            action="install",
            settings_file=str(settings_file),
            installed=True,
            details=details,
        )

    def uninstall_hooks(self) -> HookOperationResult:
        """从 ~/.claude/settings.json 卸载本项目 Hook。"""
        settings_file = self._claude_settings_file()
        settings = self._read_settings(settings_file)
        cleaned = self._remove_our_hooks(settings)
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        details = self.hooks_status().details
        return HookOperationResult(
            action="uninstall",
            settings_file=str(settings_file),
            installed=False,
            details=details,
        )

    def hooks_status(self) -> HookOperationResult:
        """检查 Hook 是否已安装。"""
        settings_file = self._claude_settings_file()
        settings = self._read_settings(settings_file)
        status = self._detect_our_hooks(settings)
        installed = all(status.values())
        return HookOperationResult(
            action="status",
            settings_file=str(settings_file),
            installed=installed,
            details=status,
        )

    def doctor_hooks(self, repair: bool = True) -> HookOperationResult:
        """诊断并可选修复 Hook 配置结构问题。"""
        settings_file = self._claude_settings_file()
        raw_settings, invalid_json = self._read_settings_raw(settings_file)
        issues: list[str] = []
        repaired = False

        if invalid_json:
            issues.append("settings.json 不是合法 JSON，已回退为空配置。")

        normalized = self._normalize_settings(raw_settings, issues)
        if repair:
            normalized = self._merge_hooks(normalized, self._build_hook_config())
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            settings_file.write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            repaired = True

        status = self._detect_our_hooks(normalized)
        installed = all(status.values())
        details: dict[str, Any] = dict(status)
        details["issues"] = issues
        details["repaired"] = repaired

        return HookOperationResult(
            action="doctor",
            settings_file=str(settings_file),
            installed=installed,
            details=details,
        )

    def sync_to_state(self, state: StateManager, task_id: str | None = None) -> dict[str, Any]:
        """将 .cc-claude-codex 进度同步到 ai_collab 状态文件。"""
        progress = self.parse_progress()
        runtime = self._read_runtime()
        now = datetime.now().isoformat()

        sync_task_id = task_id or runtime.get("task_id") or f"TASK-CODEX-{int(time.time())}"
        desired_status = self._progress_to_status(progress["total_steps"], progress["done_steps"])
        description = progress["goal"] or "Codex batch execution"
        files = progress["scope_files"]

        task = state.get_task(sync_task_id)
        if not task:
            task = state.register_task(
                task_id=sync_task_id,
                ai_type="codex",
                description=description,
                files=files,
                vscode_context={"source": "cc-claude-codex"},
            )
        else:
            task["description"] = description
            task["files"] = files
            task["ai_type"] = "codex"
            task.setdefault("notes", [])
            task["updated_at"] = now
            state._save_state()  # noqa: SLF001

        note = (
            f"[codex-sync] goal={description}; steps={progress['done_steps']}/{progress['total_steps']}; "
            f"last_run={runtime.get('exit_reason', 'N/A')}"
        )
        if desired_status.value != task.get("status"):
            state.update_task_status(sync_task_id, desired_status, note, actor="codex")
        else:
            task.setdefault("notes", []).append(f"[{now}] {note}")
            task["updated_at"] = now
            state._save_state()  # noqa: SLF001

        runtime["task_id"] = sync_task_id
        runtime["last_synced_at"] = now
        self.runtime_file.write_text(
            json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {
            "task_id": sync_task_id,
            "status": desired_status.value,
            "done_steps": progress["done_steps"],
            "total_steps": progress["total_steps"],
            "goal": description,
        }

    def parse_progress(self) -> dict[str, Any]:
        """读取 codex-progress.md 并提取关键指标。"""
        if not self.progress_file.exists():
            return {"done_steps": 0, "total_steps": 0, "goal": "", "scope_files": []}

        content = self.progress_file.read_text(encoding="utf-8")
        step_matches = re.findall(
            r"^- \[([xX ]?)\] \*\*Step \d+: .+\*\*$", content, flags=re.MULTILINE
        )
        done_steps = sum(1 for m in step_matches if m.lower() == "x")
        total_steps = len(step_matches)

        goal_match = re.search(r"## Task Goal\s+(.+?)(?:\n## |\Z)", content, flags=re.DOTALL)
        goal = goal_match.group(1).strip() if goal_match else ""

        scope_matches = re.findall(r"- \*\*Scope:\*\* (.+)", content)
        scope_files: list[str] = []
        for scope in scope_matches:
            for item in scope.split(","):
                candidate = item.strip()
                if candidate and candidate not in {"TBD", "-"}:
                    scope_files.append(candidate)

        unique_scope = sorted(set(scope_files))
        return {
            "done_steps": done_steps,
            "total_steps": total_steps,
            "goal": goal,
            "scope_files": unique_scope,
        }

    def validate_progress(self) -> dict[str, Any]:
        """对 progress 文件进行轻量预检。"""
        info = self.parse_progress()
        content = (
            self.progress_file.read_text(encoding="utf-8") if self.progress_file.exists() else ""
        )
        issues: list[str] = []

        if info["total_steps"] <= 0:
            issues.append("未检测到任何 Step。")
        if "TBD" in content:
            issues.append("仍包含 TBD，占位内容可能导致执行目标不清晰。")

        info["issues"] = issues
        return info

    def _resolve_sandbox(self, sandbox: str | None, readonly: bool) -> str:
        if sandbox:
            return sandbox
        if readonly:
            return "read-only"
        if platform.system() == "Windows":
            return "danger-full-access"
        return "workspace-write"

    def _write_runtime(self, result: CodexRunResult):
        runtime = self._read_runtime()
        runtime.update(
            {
                "last_run_at": datetime.now().isoformat(),
                "exit_reason": result.exit_reason,
                "return_code": result.return_code,
                "duration_seconds": result.duration_seconds,
                "log_file": result.log_file,
                "output_file": result.output_file,
                "progress_file": result.progress_file,
            }
        )
        self.runtime_file.write_text(
            json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _read_runtime(self) -> dict[str, Any]:
        if self.runtime_file.exists():
            try:
                return json.loads(self.runtime_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def _progress_to_status(self, total_steps: int, done_steps: int) -> TaskStatus:
        if total_steps > 0 and done_steps >= total_steps:
            return TaskStatus.COMPLETED
        if done_steps > 0:
            return TaskStatus.IMPLEMENTING
        return TaskStatus.PLANNING

    def _ensure_gitignore_entries(self):
        gitignore = self.workspace / ".gitignore"
        if not gitignore.exists():
            return

        content = gitignore.read_text(encoding="utf-8")
        additions = [
            ".cc-claude-codex/",
            ".cc-claude-codex/logs/",
            ".cc-claude-codex/snapshots/",
        ]
        new_lines = []
        for item in additions:
            if item not in content:
                new_lines.append(item)

        if new_lines:
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write("\n# CC Claude Codex\n")
                for line in new_lines:
                    f.write(f"{line}\n")

    def _ensure_output_file(self, log_file: Path, out_file: Path, exit_reason: str):
        if out_file.exists():
            return

        log_tail = self._tail_text(log_file, max_lines=120)
        fallback = (
            "# Codex Output (Fallback)\n\n"
            "未生成最终消息文件，已回填日志尾部用于排障。\n\n"
            f"- exit_reason: {exit_reason}\n"
            f"- log_file: {log_file}\n\n"
            "## Log Tail\n\n"
            "```text\n"
            f"{log_tail}\n"
            "```\n"
        )
        out_file.write_text(fallback, encoding="utf-8")

    def _tail_text(self, path: Path, max_lines: int = 80) -> str:
        if not path.exists():
            return "(log file missing)"
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) <= max_lines:
            return "\n".join(lines)
        return "\n".join(lines[-max_lines:])

    def _claude_settings_file(self) -> Path:
        return Path.home() / ".claude" / "settings.json"

    def _read_settings(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _read_settings_raw(self, path: Path) -> tuple[dict[str, Any], bool]:
        if not path.exists():
            return {}, False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data, False
            return {}, True
        except json.JSONDecodeError:
            return {}, True

    def _normalize_settings(self, settings: dict[str, Any], issues: list[str]) -> dict[str, Any]:
        normalized = settings if isinstance(settings, dict) else {}
        hooks = normalized.get("hooks")

        if hooks is None:
            normalized["hooks"] = {}
            issues.append("缺少 hooks 节点，已创建。")
            return normalized

        if not isinstance(hooks, dict):
            normalized["hooks"] = {}
            issues.append("hooks 不是对象，已重置为空。")
            return normalized

        cleaned: dict[str, list[dict[str, Any]]] = {}
        for event, entries in hooks.items():
            if not isinstance(entries, list):
                issues.append(f"{event} 配置不是数组，已重置为空。")
                cleaned[event] = []
                continue
            clean_entries: list[dict[str, Any]] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    issues.append(f"{event} 含非法 entry，已移除。")
                    continue
                hook_items = entry.get("hooks")
                if hook_items is None:
                    entry = {**entry, "hooks": []}
                    issues.append(f"{event} entry 缺少 hooks，已补空数组。")
                elif not isinstance(hook_items, list):
                    entry = {**entry, "hooks": []}
                    issues.append(f"{event} entry hooks 不是数组，已重置。")
                clean_entries.append(entry)
            cleaned[event] = clean_entries

        normalized["hooks"] = cleaned
        return normalized

    def _python_cmd(self) -> str:
        return "python" if platform.system() == "Windows" else "python3"

    def _build_hook_config(self) -> dict[str, list[dict[str, Any]]]:
        py = self._python_cmd()
        stop_script = (self.hooks_dir / "stop_check.py").as_posix()
        pre_script = (self.hooks_dir / "pre_compact.py").as_posix()
        session_script = (self.hooks_dir / "session_inject.py").as_posix()
        spawn_preflight_script = (self.hooks_dir / "spawn_agent_preflight.py").as_posix()

        return {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": f'{py} "{stop_script}"', "timeout": 10000}
                    ],
                }
            ],
            "PreCompact": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": f'{py} "{pre_script}"', "timeout": 5000}
                    ],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": f'{py} "{session_script}"', "timeout": 5000}
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Agent",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f'{py} "{spawn_preflight_script}"',
                            "timeout": 10000,
                        }
                    ],
                }
            ],
        }

    def _merge_hooks(
        self, settings: dict[str, Any], new_hooks: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        hooks = settings.get("hooks", {})
        for event, entries in new_hooks.items():
            existing = hooks.get(event, [])
            filtered = [entry for entry in existing if not self._entry_is_our_hook(entry)]
            hooks[event] = filtered + entries
        settings["hooks"] = hooks
        return settings

    def _remove_our_hooks(self, settings: dict[str, Any]) -> dict[str, Any]:
        hooks = settings.get("hooks", {})
        cleaned: dict[str, Any] = {}
        for event, entries in hooks.items():
            kept = [entry for entry in entries if not self._entry_is_our_hook(entry)]
            if kept:
                cleaned[event] = kept
        settings["hooks"] = cleaned
        return settings

    def _detect_our_hooks(self, settings: dict[str, Any]) -> dict[str, bool]:
        hooks = settings.get("hooks", {})
        status = {"Stop": False, "PreCompact": False, "SessionStart": False, "PreToolUse": False}
        for event in status:
            for entry in hooks.get(event, []):
                if self._entry_is_our_hook(entry):
                    status[event] = True
                    break
        return status

    def _entry_is_our_hook(self, entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        hook_items = entry.get("hooks")
        if not isinstance(hook_items, list):
            return False
        markers = (
            "ai_collab/hooks/stop_check.py",
            "ai_collab/hooks/pre_compact.py",
            "ai_collab/hooks/session_inject.py",
            "ai_collab/hooks/spawn_agent_preflight.py",
        )
        for hook in hook_items:
            if isinstance(hook, dict):
                command = str(hook.get("command", ""))
                if any(marker in command for marker in markers):
                    return True
        return False
