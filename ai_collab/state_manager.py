"""
状态管理器模块 - VSCode 集成版

管理 Claude Code 与 GitHub Copilot 的协作状态
支持项目级和全局配置同步
"""

import json
import os
import re
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PatchStatus(str, Enum):
    """补丁状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class FileStatus(str, Enum):
    """文件状态枚举"""

    CLEAN = "clean"
    MODIFIED = "modified"
    CONFLICT = "conflict"
    LOCKED = "locked"


@dataclass
class Task:
    """任务数据类"""

    task_id: str
    ai_type: str
    description: str
    files: List[str]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    notes: List[str] = field(default_factory=list)
    vscode_context: Dict[str, Any] = field(default_factory=dict)
    change_id: str | None = None
    assignee: str | None = None
    reviewer: str | None = None
    primary_skill: str | None = None
    support_skills: List[str] = field(default_factory=list)
    acceptance_commands: List[str] = field(default_factory=list)
    result_file: str | None = None
    contract_required: bool = False
    ownership: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Patch:
    """Patch 一等对象"""

    patch_id: str
    task_id: str
    title: str
    files: List[str]
    assignee: str = ""
    status: PatchStatus = PatchStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    result_file: str | None = None
    notes: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """冲突数据类"""

    conflict_id: str
    task_id_1: str
    task_id_2: str
    ai_type_1: str
    ai_type_2: str
    overlapping_files: List[str]
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "open"
    resolution: str | None = None


class VSCodeStateManager:
    """VSCode 集成状态管理辅助类"""

    @staticmethod
    def get_project_state_file() -> str:
        """获取项目状态文件路径"""
        workspace = VSCodeIntegration.get_workspace_path()
        config = VSCodeIntegration.get_project_config()
        state_file = config.get("stateFile", "./logs/collaboration_state.json")

        if workspace:
            state_file = os.path.join(workspace, state_file)
        else:
            # workspace 为 None 时，使用当前工作目录的绝对路径
            # 避免相对路径解析为无效路径（如 /./logs）
            cwd = os.path.abspath(os.getcwd())
            if cwd and VSCodeIntegration._is_valid_workspace(cwd):
                state_file = os.path.join(cwd, state_file)
            else:
                # 最后的 fallback：使用全局目录
                global_dir = os.path.expanduser("~/.vscode/ai-collab")
                state_file = os.path.join(global_dir, "collaboration_state.json")

        # 规范化路径，去除 ./ 等
        state_file = os.path.normpath(state_file)

        # 确保目录存在
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        return state_file

    @staticmethod
    def get_global_state_file() -> str:
        """获取全局状态文件路径"""
        global_dir = os.path.expanduser("~/.vscode/ai-collab")
        os.makedirs(global_dir, exist_ok=True)
        return os.path.join(global_dir, "collaboration_state.json")

    @staticmethod
    def get_issues_file() -> str:
        """获取问题记录文件路径"""
        workspace = VSCodeIntegration.get_workspace_path()
        if workspace:
            return os.path.join(workspace, "logs", "collaboration_issues.json")

        # workspace 为 None 时，使用当前工作目录或全局目录
        cwd = os.path.abspath(os.getcwd())
        if cwd and VSCodeIntegration._is_valid_workspace(cwd):
            return os.path.join(cwd, "logs", "collaboration_issues.json")

        # fallback：使用全局目录
        global_dir = os.path.expanduser("~/.vscode/ai-collab")
        return os.path.join(global_dir, "collaboration_issues.json")

    @staticmethod
    def get_backup_dir() -> str:
        """获取备份目录"""
        workspace = VSCodeIntegration.get_workspace_path()
        if workspace:
            dir_path = os.path.join(workspace, "logs", "backups")
        else:
            # workspace 为 None 时，使用当前工作目录
            cwd = os.path.abspath(os.getcwd())
            if cwd and VSCodeIntegration._is_valid_workspace(cwd):
                dir_path = os.path.join(cwd, "logs", "backups")
            else:
                # fallback：使用全局目录
                dir_path = os.path.expanduser("~/.vscode/ai-collab/backups")

        os.makedirs(dir_path, exist_ok=True)
        return dir_path


# 导入前向引用的类
class VSCodeIntegration:
    """VSCode 集成辅助类"""

    @staticmethod
    def _is_valid_workspace(path: str) -> bool:
        """验证工作区路径，过滤掉无效根路径。"""
        if not path:
            return False

        resolved = os.path.abspath(path)
        if resolved == os.path.abspath(os.sep):
            return False

        return os.path.isdir(resolved)

    @staticmethod
    def get_workspace_path() -> str | None:
        """获取当前 VSCode 工作区路径"""
        workspace = os.environ.get("VSCODE_CWD")
        if workspace and VSCodeIntegration._is_valid_workspace(workspace):
            return os.path.abspath(workspace)

        cwd = os.path.abspath(os.getcwd())
        if cwd:
            path = cwd
            while path and path != os.path.dirname(path):
                if os.path.exists(os.path.join(path, ".vscode")) or os.path.exists(
                    os.path.join(path, "package.json")
                ):
                    return path
                path = os.path.dirname(path)
        return cwd

    @staticmethod
    def get_project_config() -> Dict[str, Any]:
        """获取项目级 AI 协作配置"""
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            return {}

        config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @staticmethod
    def update_vscode_output(message: str, channel: str = "AI Collab"):
        """更新 VSCode 输出面板"""
        try:
            global_config_dir = os.path.expanduser("~/.vscode/ai-collab")
            os.makedirs(global_config_dir, exist_ok=True)
            log_file = os.path.join(
                global_config_dir, f"output_{datetime.now().strftime('%Y%m%d')}.log"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] [{channel}] {message}\n")
        except Exception:
            pass


class StateManager:
    """
    状态管理器 - VSCode 集成版

    特性：
    - 项目级 + 全局状态同步
    - 冲突检测（文件保存 + 命令触发）
    - 自动备份
    """

    # 会触发冲突的任务状态
    CONFLICT_STATUSES = {TaskStatus.IMPLEMENTING, TaskStatus.TESTING, TaskStatus.PLANNING}
    TASK_STATUS_ALIASES = {
        "in_progress": TaskStatus.IMPLEMENTING.value,
    }
    TASK_CONTRACT_REQUIRED_STR_FIELDS = (
        "change_id",
        "assignee",
        "reviewer",
        "primary_skill",
        "result_file",
    )
    TASK_CONTRACT_REQUIRED_LIST_FIELDS = (
        "support_skills",
        "acceptance_commands",
    )
    TASK_CONTRACT_DEFAULT_CHANGE_ID = "legacy/task-contract-migration"
    TASK_CONTRACT_DEFAULT_REVIEWER = "codex"
    TASK_CONTRACT_DEFAULT_SUPPORT_SKILLS = ("legacy-contract-migration",)
    TASK_CONTRACT_DEFAULT_ACCEPTANCE_COMMANDS = (
        "python3 -m ai_collab.cli tasks validate-contract --scope all --strict",
    )
    TASK_CONTRACT_SPECIAL_CHANGE_IDS = {
        "bugfix/no-spec",
        TASK_CONTRACT_DEFAULT_CHANGE_ID,
    }
    TASK_RESULT_REQUIRED_SECTION_GROUPS = (
        ("执行命令", "acceptance_commands", "verification commands"),
        ("测试结论", "验证结果", "test conclusion"),
        ("风险", "回滚", "risk"),
    )
    TASK_RESULT_NEGATIVE_SIGNAL_MARKERS = (
        "⚠️ blocked",
        "❌ blocked",
        "❌ file not found",
        "❌ not found",
        "未集成",
        "待集成",
        "待添加",
        "- [ ]",
    )
    OWNERSHIP_SYSTEM_ACTORS = {
        "system",
        "receipt_bridge",
        "controller",
        "task_controller_daemon",
        "reconcile_state_drift",
        "synthesize_verification_results",
    }

    def __init__(self, workspace_path: str | None = None):
        """
        初始化状态管理器

        Args:
            workspace_path: 工作区路径（可选）
        """
        self.workspace_path = workspace_path or VSCodeIntegration.get_workspace_path()
        self.state = self._load_state()

    def _get_state_file(self) -> str:
        """获取项目状态文件路径（使用实例的 workspace_path）"""
        config = VSCodeIntegration.get_project_config()
        state_file = config.get("stateFile", "./logs/collaboration_state.json")

        if self.workspace_path:
            state_file = os.path.join(self.workspace_path, state_file)

        # 确保目录存在
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        return state_file

    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件"""
        state_file = self._get_state_file()

        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    loaded_state = json.load(f)
                    return self._normalize_state(loaded_state)
            except json.JSONDecodeError:
                return self._create_initial_state()

        return self._create_initial_state()

    def _normalize_state(self, loaded_state: Dict[str, Any]) -> Dict[str, Any]:
        """兼容旧版状态文件，补齐缺失字段。"""
        normalized = self._create_initial_state()
        now = datetime.now().isoformat()

        if not isinstance(loaded_state, dict):
            return normalized

        for key, value in loaded_state.items():
            if key not in {"tasks", "patches"}:
                normalized[key] = value

        tasks = loaded_state.get("tasks", {})
        normalized["tasks"] = {}
        if isinstance(tasks, dict):
            for task_id, raw_task in tasks.items():
                task = dict(raw_task) if isinstance(raw_task, dict) else {}

                task["task_id"] = task.get("task_id") or task_id
                task["ai_type"] = task.get("ai_type") or task.get("assigned_to") or "unknown"
                task["description"] = task.get("description", "")

                files = task.get("files")
                task["files"] = files if isinstance(files, list) else []

                notes = task.get("notes")
                task["notes"] = notes if isinstance(notes, list) else []

                status = task.get("status") or TaskStatus.PENDING.value
                task["status"] = self._normalize_task_status_value(status)

                created_at = task.get("created_at", now)
                task["created_at"] = created_at
                task["updated_at"] = task.get("updated_at", created_at)
                task["completed_at"] = task.get("completed_at")

                vscode_context = task.get("vscode_context")
                task["vscode_context"] = vscode_context if isinstance(vscode_context, dict) else {}
                ownership = task.get("ownership")
                task["ownership"] = ownership if isinstance(ownership, dict) else {}

                normalized["tasks"][task_id] = task

        patches = loaded_state.get("patches", {})
        normalized["patches"] = {}
        if isinstance(patches, dict):
            for patch_id, raw_patch in patches.items():
                patch = dict(raw_patch) if isinstance(raw_patch, dict) else {}
                patch["patch_id"] = patch.get("patch_id") or patch_id
                patch["task_id"] = patch.get("task_id") or ""
                patch["title"] = patch.get("title", "")

                files = patch.get("files")
                patch["files"] = files if isinstance(files, list) else []

                notes = patch.get("notes")
                patch["notes"] = notes if isinstance(notes, list) else []

                status = patch.get("status") or PatchStatus.PENDING.value
                patch["status"] = status.value if isinstance(status, PatchStatus) else str(status)
                patch["assignee"] = str(patch.get("assignee", ""))

                created_at = patch.get("created_at", now)
                patch["created_at"] = created_at
                patch["updated_at"] = patch.get("updated_at", created_at)
                patch["completed_at"] = patch.get("completed_at")
                patch["result_file"] = patch.get("result_file")

                normalized["patches"][patch_id] = patch

        active_tasks = normalized.get("active_tasks")
        normalized["active_tasks"] = active_tasks if isinstance(active_tasks, list) else []

        completed_tasks = normalized.get("completed_tasks")
        normalized["completed_tasks"] = completed_tasks if isinstance(completed_tasks, list) else []

        conflicts = normalized.get("conflicts")
        normalized["conflicts"] = conflicts if isinstance(conflicts, list) else []

        file_status = normalized.get("file_status")
        normalized["file_status"] = file_status if isinstance(file_status, dict) else {}

        # 修复历史状态文件中 active/completed 与任务状态不一致的问题。
        terminal_statuses = {
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        }
        task_ids = set(normalized["tasks"].keys())

        active_list = [task_id for task_id in normalized["active_tasks"] if task_id in task_ids]
        completed_list = [
            task_id for task_id in normalized["completed_tasks"] if task_id in task_ids
        ]

        active_set = set(active_list)
        completed_set = set(completed_list)
        for task_id, task in normalized["tasks"].items():
            status = str(task.get("status", TaskStatus.PENDING.value))
            if status in terminal_statuses:
                completed_set.add(task_id)
                active_set.discard(task_id)
                task["completed_at"] = task.get("completed_at") or task.get("updated_at") or now
            else:
                active_set.add(task_id)
                completed_set.discard(task_id)
                task["completed_at"] = None

        # 去重并保持原有顺序
        normalized["active_tasks"] = [
            task_id for task_id in active_list if task_id in active_set
        ] + [
            task_id
            for task_id in normalized["tasks"]
            if task_id in active_set and task_id not in active_list
        ]
        normalized["completed_tasks"] = [
            task_id for task_id in completed_list if task_id in completed_set
        ] + [
            task_id
            for task_id in normalized["tasks"]
            if task_id in completed_set and task_id not in completed_list
        ]

        return normalized

    def _normalize_task_status_value(self, status: Any) -> str:
        """标准化任务状态，兼容历史别名。"""
        if isinstance(status, TaskStatus):
            raw = status.value
        else:
            raw = str(status or TaskStatus.PENDING.value).strip().lower()
        if not raw:
            return TaskStatus.PENDING.value

        mapped = self.TASK_STATUS_ALIASES.get(raw, raw)
        valid_values = {item.value for item in TaskStatus}
        if mapped in valid_values:
            return mapped
        return raw

    def _create_initial_state(self) -> Dict[str, Any]:
        """创建初始状态"""
        return {
            "version": "2.0.0",
            "workspace": self.workspace_path or "",
            "last_updated": datetime.now().isoformat(),
            "tasks": {},
            "patches": {},
            "active_tasks": [],
            "completed_tasks": [],
            "conflicts": [],
            "file_status": {},
        }

    def _get_backup_dir(self) -> str:
        """获取备份目录（使用实例的 workspace_path）"""
        if self.workspace_path:
            dir_path = os.path.join(self.workspace_path, "./logs/backups")
        else:
            dir_path = "./logs/backups"
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _get_issues_file(self) -> str:
        """获取问题记录文件路径（使用实例的 workspace_path）"""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "./logs/collaboration_issues.json")
        return "./logs/collaboration_issues.json"

    def _get_patch_ops_file(self) -> str:
        """获取 patch 操作日志文件路径。"""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "./logs/patch_ops.jsonl")
        return "./logs/patch_ops.jsonl"

    def _get_task_ops_file(self) -> str:
        """获取 task 操作日志文件路径。"""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "./logs/task_ops.jsonl")
        return "./logs/task_ops.jsonl"

    def _append_patch_op(
        self,
        patch_id: str,
        task_id: str,
        old_status: str,
        new_status: str,
        actor: str = "system",
        source: str = "state_manager",
        reason: str = "",
    ):
        """追加写 patch 操作日志（JSONL）。"""
        ops_file = self._get_patch_ops_file()
        os.makedirs(os.path.dirname(ops_file) or ".", exist_ok=True)
        payload = {
            "op_id": f"POP-{uuid.uuid4().hex}",
            "ts": datetime.now().isoformat(),
            "actor": actor,
            "source": source,
            "task_id": task_id,
            "patch_id": patch_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        }
        with self._file_lock(ops_file):
            with open(ops_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _append_task_op(
        self,
        *,
        task_id: str,
        op_type: str,
        actor: str = "system",
        source: str = "state_manager",
        reason: str = "",
        note: str = "",
        old_assignee: str = "",
        new_assignee: str = "",
    ) -> None:
        """追加写 task 元数据操作日志（JSONL）。"""
        ops_file = self._get_task_ops_file()
        os.makedirs(os.path.dirname(ops_file) or ".", exist_ok=True)
        payload = {
            "op_id": f"TOP-{uuid.uuid4().hex}",
            "ts": datetime.now().isoformat(),
            "actor": actor,
            "source": source,
            "task_id": task_id,
            "op_type": op_type,
            "reason": reason,
            "note": note,
            "old_assignee": old_assignee,
            "new_assignee": new_assignee,
        }
        with self._file_lock(ops_file):
            with open(ops_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _atomic_write_json(self, target_file: str, payload: Dict[str, Any]):
        """原子写 JSON，避免并发写导致状态文件损坏。"""
        directory = os.path.dirname(target_file) or "."
        os.makedirs(directory, exist_ok=True)
        fd, temp_file = tempfile.mkstemp(prefix=".state_tmp_", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, target_file)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _to_epoch(self, ts: Any) -> float:
        """将时间戳字段转换为可比较的 epoch，异常时返回 -1。"""
        if not ts:
            return -1.0
        try:
            value = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(value).timestamp()
        except (TypeError, ValueError):
            return -1.0

    def _pick_newer_task(
        self, latest_task: Dict[str, Any], local_task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """按 updated_at/created_at 选择更新的任务版本。"""
        latest_ts = self._to_epoch(latest_task.get("updated_at") or latest_task.get("created_at"))
        local_ts = self._to_epoch(local_task.get("updated_at") or local_task.get("created_at"))
        return local_task if local_ts >= latest_ts else latest_task

    def _merge_conflicts(self, latest_conflicts: Any, local_conflicts: Any) -> List[Dict[str, Any]]:
        """按 conflict_id 合并冲突列表，保留无 ID 条目。"""
        merged_by_id: Dict[str, Dict[str, Any]] = {}
        no_id_items: List[Dict[str, Any]] = []

        for conflict in latest_conflicts or []:
            if not isinstance(conflict, dict):
                continue
            conflict_id = conflict.get("conflict_id")
            if conflict_id:
                merged_by_id[str(conflict_id)] = conflict
            else:
                no_id_items.append(conflict)

        for conflict in local_conflicts or []:
            if not isinstance(conflict, dict):
                continue
            conflict_id = conflict.get("conflict_id")
            if conflict_id:
                merged_by_id[str(conflict_id)] = conflict
            else:
                no_id_items.append(conflict)

        return list(merged_by_id.values()) + no_id_items

    def _merge_states_with_latest(self, latest_state: Dict[str, Any]) -> Dict[str, Any]:
        """将本地内存状态与磁盘最新状态合并，降低并发覆盖风险。"""
        latest_norm = self._normalize_state(latest_state if isinstance(latest_state, dict) else {})
        local_norm = self._normalize_state(self.state if isinstance(self.state, dict) else {})

        merged = dict(latest_norm)
        merged["version"] = local_norm.get("version") or latest_norm.get("version") or "2.0.0"
        merged["workspace"] = (
            local_norm.get("workspace")
            or latest_norm.get("workspace")
            or (self.workspace_path or "")
        )
        merged["file_status"] = {
            **(latest_norm.get("file_status") or {}),
            **(local_norm.get("file_status") or {}),
        }
        merged["conflicts"] = self._merge_conflicts(
            latest_norm.get("conflicts"), local_norm.get("conflicts")
        )

        merged_tasks: Dict[str, Dict[str, Any]] = {}
        all_task_ids = set((latest_norm.get("tasks") or {}).keys()) | set(
            (local_norm.get("tasks") or {}).keys()
        )
        for task_id in all_task_ids:
            latest_task = (latest_norm.get("tasks") or {}).get(task_id)
            local_task = (local_norm.get("tasks") or {}).get(task_id)
            if latest_task and local_task:
                merged_tasks[task_id] = self._pick_newer_task(latest_task, local_task)
            elif local_task:
                merged_tasks[task_id] = local_task
            elif latest_task:
                merged_tasks[task_id] = latest_task

        merged["tasks"] = merged_tasks
        merged_patches: Dict[str, Dict[str, Any]] = {}
        all_patch_ids = set((latest_norm.get("patches") or {}).keys()) | set(
            (local_norm.get("patches") or {}).keys()
        )
        for patch_id in all_patch_ids:
            latest_patch = (latest_norm.get("patches") or {}).get(patch_id)
            local_patch = (local_norm.get("patches") or {}).get(patch_id)
            if latest_patch and local_patch:
                merged_patches[patch_id] = self._pick_newer_task(latest_patch, local_patch)
            elif local_patch:
                merged_patches[patch_id] = local_patch
            elif latest_patch:
                merged_patches[patch_id] = latest_patch

        merged["patches"] = merged_patches
        merged["active_tasks"] = list(latest_norm.get("active_tasks") or []) + [
            task_id
            for task_id in (local_norm.get("active_tasks") or [])
            if task_id not in (latest_norm.get("active_tasks") or [])
        ]
        merged["completed_tasks"] = list(latest_norm.get("completed_tasks") or []) + [
            task_id
            for task_id in (local_norm.get("completed_tasks") or [])
            if task_id not in (latest_norm.get("completed_tasks") or [])
        ]

        return self._normalize_state(merged)

    @contextmanager
    def _file_lock(
        self,
        target_file: str,
        timeout_sec: float = 5.0,
        stale_sec: float = 120.0,
        poll_interval: float = 0.05,
    ):
        """通过 lock 文件提供跨进程互斥，避免并发写冲突。"""
        lock_file = f"{target_file}.lock"
        start = time.time()
        fd = None
        token = uuid.uuid4().hex

        while True:
            try:
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                lock_payload = f"{token}|{os.getpid()}|{datetime.now().isoformat()}\n"
                os.write(fd, lock_payload.encode("utf-8"))
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(lock_file) > stale_sec:
                        os.remove(lock_file)
                        continue
                except FileNotFoundError:
                    continue

                if time.time() - start >= timeout_sec:
                    raise TimeoutError(f"获取文件锁超时: {lock_file}")
                time.sleep(poll_interval)

        try:
            yield
        finally:
            if fd is not None:
                os.close(fd)
            try:
                if os.path.exists(lock_file):
                    content = ""
                    with open(lock_file, "r", encoding="utf-8") as f:
                        content = f.read(128)
                    if content.startswith(f"{token}|"):
                        os.remove(lock_file)
            except (FileNotFoundError, OSError):
                pass

    def _save_state(self):
        """保存状态到文件（项目 + 全局）"""
        project_state_file = self._get_state_file()
        with self._file_lock(project_state_file):
            latest_state: Dict[str, Any] = {}
            if os.path.exists(project_state_file):
                try:
                    with open(project_state_file, "r", encoding="utf-8") as f:
                        latest_state = json.load(f)
                except json.JSONDecodeError:
                    latest_state = {}

            self.state = self._merge_states_with_latest(latest_state)
            self.state["last_updated"] = datetime.now().isoformat()

            # 创建备份
            self._backup_state()

            # 保存项目状态
            self._atomic_write_json(project_state_file, self.state)

            # 同步到全局状态
            self._sync_to_global()

            # 更新 VSCode 输出
            VSCodeIntegration.update_vscode_output(
                f"状态已更新: {len(self.state['active_tasks'])} 个活跃任务", "AI Collab State"
            )

    def _commit_state_transaction(
        self,
        *,
        mutate: Callable[[], Any],
        output_message: str | None = None,
        output_channel: str = "AI Collab Tasks",
    ) -> Any:
        """在持有项目状态锁时刷新最新状态、执行修改并落盘。"""
        state_file = self._get_state_file()
        with self._file_lock(state_file):
            latest_state: Dict[str, Any] = {}
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        latest_state = json.load(f)
                except json.JSONDecodeError:
                    latest_state = {}

            self.state = self._merge_states_with_latest(latest_state)
            result = mutate()
            self.state["last_updated"] = datetime.now().isoformat()
            self._backup_state()
            self._atomic_write_json(state_file, self.state)

        self._sync_to_global()
        if output_message:
            VSCodeIntegration.update_vscode_output(output_message, output_channel)
        return result

    def _backup_state(self):
        """创建状态备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self._get_backup_dir(), f"state_{timestamp}.json")

        try:
            self._atomic_write_json(backup_file, self.state)
        except Exception as e:
            print(f"警告: 状态备份失败: {e}")

    def _sync_to_global(self):
        """同步状态到全局配置"""
        global_state_file = VSCodeStateManager.get_global_state_file()
        with self._file_lock(global_state_file):
            # 读取现有全局状态
            global_state: Dict[str, Any] = {}
            if os.path.exists(global_state_file):
                try:
                    with open(global_state_file, "r", encoding="utf-8") as f:
                        global_state = json.load(f)
                except json.JSONDecodeError:
                    pass

            # 更新当前工作区的状态
            workspace_key = self.workspace_path or "unknown"
            global_state[workspace_key] = {
                "last_sync": datetime.now().isoformat(),
                "tasks": self.state["tasks"],
                "patches": self.state.get("patches", {}),
                "active_tasks": self.state["active_tasks"],
                "conflicts": self.state["conflicts"],
            }

            # 保存全局状态
            self._atomic_write_json(global_state_file, global_state)

    def register_task(
        self,
        task_id: str,
        ai_type: str,
        description: str,
        files: List[str],
        vscode_context: Dict[str, Any] | None = None,
        change_id: str | None = None,
        assignee: str | None = None,
        reviewer: str | None = None,
        primary_skill: str | None = None,
        support_skills: List[str] | None = None,
        acceptance_commands: List[str] | None = None,
        result_file: str | None = None,
        contract_required: bool = True,
    ) -> Dict[str, Any]:
        """
        注册新任务

        Args:
            task_id: 任务唯一标识
            ai_type: AI 类型 (claude_code / copilot)
            description: 任务描述
            files: 涉及的文件列表
            vscode_context: VSCode 上下文信息

        Returns:
            任务信息字典
        """
        task = Task(
            task_id=task_id,
            ai_type=ai_type,
            description=description,
            files=files,
            status=TaskStatus.PENDING,
            vscode_context=vscode_context or {},
            change_id=change_id,
            assignee=assignee,
            reviewer=reviewer,
            primary_skill=primary_skill,
            support_skills=[
                item for item in (support_skills or []) if isinstance(item, str) and item.strip()
            ],
            acceptance_commands=[
                item
                for item in (acceptance_commands or [])
                if isinstance(item, str) and item.strip()
            ],
            result_file=result_file,
            contract_required=contract_required,
        )

        def _mutate() -> Dict[str, Any]:
            if task_id in self.state["tasks"]:
                raise ValueError(f"任务ID已存在: {task_id}")
            self.state["tasks"][task_id] = asdict(task)
            if task_id not in self.state["active_tasks"]:
                self.state["active_tasks"].append(task_id)
            return asdict(task)

        return self._commit_state_transaction(
            mutate=_mutate,
            output_message=f"任务已注册: {task_id} ({ai_type})",
        )

    def _normalize_actor_id(self, actor: str | None) -> str | None:
        """标准化状态写入 actor。"""
        if not isinstance(actor, str):
            return None
        normalized = actor.strip().lower()
        return normalized or None

    def _current_task_owner(self, task: Dict[str, Any]) -> str | None:
        """获取任务当前 owner。"""
        return (
            self._normalize_non_empty_str(task.get("assignee"))
            or self._normalize_non_empty_str(task.get("ai_type"))
            or self._normalize_non_empty_str(task.get("assigned_to"))
        )

    def _active_ownership_lock(self, task: Dict[str, Any]) -> Dict[str, Any] | None:
        """获取激活中的 owner lock。"""
        ownership = task.get("ownership")
        if not isinstance(ownership, dict):
            return None

        owner = self._normalize_actor_id(str(ownership.get("owner", "")))
        if not owner:
            return None
        if not bool(ownership.get("lock_active", False)):
            return None

        lock_payload = dict(ownership)
        lock_payload["owner"] = owner
        return lock_payload

    def _assert_task_update_actor_allowed(
        self,
        *,
        task_id: str,
        task: Dict[str, Any],
        status: TaskStatus,
        actor: str | None,
    ) -> None:
        """在 owner lock 激活时，拒绝非 owner 的迟到写入。"""
        lock = self._active_ownership_lock(task)
        if not lock:
            return

        normalized_actor = self._normalize_actor_id(actor)
        if normalized_actor in self.OWNERSHIP_SYSTEM_ACTORS:
            return
        if normalized_actor == lock["owner"]:
            return

        requested = status.value if isinstance(status, TaskStatus) else str(status)
        actor_display = normalized_actor or "<unspecified>"
        raise ValueError(
            "任务接管防并发拦截: "
            f"{task_id}; actor={actor_display}; owner={lock['owner']}; "
            f"requested_status={requested}. "
            "请先显式接管任务，或使用归属 owner 执行状态更新。"
        )

    def takeover_task(
        self,
        task_id: str,
        owner: str,
        *,
        actor: str | None = None,
        note: str | None = None,
        reason: str | None = None,
        source: str = "tasks.takeover",
    ) -> Dict[str, Any]:
        """将任务归属锁定到指定 owner，防止其他 actor 迟到写入。"""
        normalized_owner = self._normalize_actor_id(owner)
        if not normalized_owner:
            raise ValueError("owner 不能为空")

        normalized_actor = self._normalize_actor_id(actor) or normalized_owner

        def _mutate() -> Dict[str, Any]:
            if task_id not in self.state["tasks"]:
                raise ValueError(f"任务不存在: {task_id}")

            task = self.state["tasks"][task_id]
            old_owner = self._current_task_owner(task)
            now = datetime.now().isoformat()
            ownership = dict(task.get("ownership") or {})
            ownership.update(
                {
                    "owner": normalized_owner,
                    "previous_owner": old_owner,
                    "lock_active": True,
                    "locked_at": now,
                    "locked_by": normalized_actor,
                    "reason": (reason or "").strip(),
                    "source": source,
                }
            )
            task["ownership"] = ownership
            task["assignee"] = normalized_owner
            task["updated_at"] = now
            task.setdefault("notes", [])

            detail_parts = [
                f"[ownership] locked owner={normalized_owner}",
                f"previous_owner={old_owner or '<none>'}",
                f"actor={normalized_actor}",
            ]
            if reason:
                detail_parts.append(f"reason={reason.strip()}")
            if note:
                detail_parts.append(f"note={note.strip()}")
            task["notes"].append(f"[{now}] {'; '.join(detail_parts)}")

            return {
                "task_id": task_id,
                "owner": normalized_owner,
                "previous_owner": old_owner,
                "locked_at": now,
                "locked_by": normalized_actor,
                "lock_active": True,
            }

        return self._commit_state_transaction(
            mutate=_mutate,
            output_message=f"任务 owner 已锁定: {task_id} -> {normalized_owner}",
        )

    def repair_task_assignee(
        self,
        task_id: str,
        assignee: str,
        *,
        actor: str | None = None,
        note: str | None = None,
        reason: str | None = None,
        source: str = "tasks.repair_assignee",
    ) -> Dict[str, Any]:
        """修复任务 assignee 元数据，并记录审计痕迹。"""
        normalized_assignee = self._normalize_actor_id(assignee)
        if not normalized_assignee:
            raise ValueError("assignee 不能为空")

        normalized_actor = self._normalize_actor_id(actor) or "system"

        def _mutate() -> Dict[str, Any]:
            if task_id not in self.state["tasks"]:
                raise ValueError(f"任务不存在: {task_id}")

            task = self.state["tasks"][task_id]
            old_assignee = self._current_task_owner(task) or ""
            now = datetime.now().isoformat()
            task["assignee"] = normalized_assignee
            task["updated_at"] = now
            task.setdefault("notes", [])

            detail_parts = [
                f"[assignee-repair] old_assignee={old_assignee or '<none>'}",
                f"new_assignee={normalized_assignee}",
                f"actor={normalized_actor}",
            ]
            if reason:
                detail_parts.append(f"reason={reason.strip()}")
            if note:
                detail_parts.append(f"note={note.strip()}")
            if source:
                detail_parts.append(f"source={source}")
            task["notes"].append(f"[{now}] {'; '.join(detail_parts)}")

            self._append_task_op(
                task_id=task_id,
                op_type="repair_assignee",
                actor=normalized_actor,
                source=source,
                reason=(reason or "").strip(),
                note=(note or "").strip(),
                old_assignee=old_assignee,
                new_assignee=normalized_assignee,
            )

            return {
                "task_id": task_id,
                "old_assignee": old_assignee,
                "new_assignee": normalized_assignee,
                "actor": normalized_actor,
                "updated_at": now,
            }

        return self._commit_state_transaction(
            mutate=_mutate,
            output_message=f"任务 assignee 已修复: {task_id} -> {normalized_assignee}",
        )

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        note: str | None = None,
        actor: str | None = None,
    ) -> Dict[str, Any]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            note: 可选备注
        """

        def _mutate() -> Dict[str, Any]:
            if task_id not in self.state["tasks"]:
                raise ValueError(f"任务不存在: {task_id}")

            task = self.state["tasks"][task_id]
            old_status = task["status"]
            self._assert_task_update_actor_allowed(
                task_id=task_id,
                task=task,
                status=status,
                actor=actor,
            )

            # 新工单契约门禁：契约任务不得在字段缺失时进入 implementing。
            if status == TaskStatus.IMPLEMENTING:
                contract_check = self.validate_task_contract(task_id)
                if not contract_check.get("valid", True):
                    missing = ",".join(contract_check.get("missing_fields", []))
                    invalid = ",".join(contract_check.get("invalid_fields", []))
                    raise ValueError(
                        f"任务契约校验失败: {task_id}; missing=[{missing}] invalid=[{invalid}]"
                    )
            if status == TaskStatus.COMPLETED:
                self._validate_result_artifact_for_completion(task_id, task)

            now = datetime.now().isoformat()
            task["status"] = status.value
            task["updated_at"] = now

            if note:
                task.setdefault("notes", [])
                task["notes"].append(f"[{now}] {note}")

            if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                task["completed_at"] = now
                if task_id in self.state["active_tasks"]:
                    self.state["active_tasks"].remove(task_id)
                if task_id not in self.state["completed_tasks"]:
                    self.state["completed_tasks"].append(task_id)
            else:
                task["completed_at"] = None
                if task_id in self.state["completed_tasks"]:
                    self.state["completed_tasks"].remove(task_id)
                if task_id not in self.state["active_tasks"]:
                    self.state["active_tasks"].append(task_id)

            return {
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status.value,
                "updated_at": task["updated_at"],
            }

        return self._commit_state_transaction(
            mutate=_mutate,
            output_message=f"任务状态更新: {task_id} -> {status.value}",
        )

    def register_patch(
        self,
        patch_id: str,
        task_id: str,
        title: str,
        files: List[str],
        assignee: str = "",
        status: PatchStatus = PatchStatus.PENDING,
        note: str | None = None,
        actor: str = "system",
        source: str = "patch.create",
        reason: str = "",
    ) -> Dict[str, Any]:
        """注册 patch。"""
        patches = self.state.setdefault("patches", {})
        if patch_id in patches:
            raise ValueError(f"Patch ID已存在: {patch_id}")

        patch = Patch(
            patch_id=patch_id,
            task_id=task_id,
            title=title,
            files=files,
            assignee=assignee,
            status=status,
        )
        item = asdict(patch)
        if note:
            item["notes"].append(f"[{datetime.now().isoformat()}] {note}")
        patches[patch_id] = item
        self._append_patch_op(
            patch_id=patch_id,
            task_id=task_id,
            old_status="",
            new_status=status.value,
            actor=actor,
            source=source,
            reason=reason or note or "create",
        )
        self._save_state()
        return item

    def update_patch_status(
        self,
        patch_id: str,
        status: PatchStatus,
        note: str | None = None,
        result_file: str | None = None,
        actor: str = "system",
        source: str = "patch.update",
        reason: str = "",
    ) -> Dict[str, Any]:
        """更新 patch 状态。"""
        patches = self.state.setdefault("patches", {})
        if patch_id not in patches:
            raise ValueError(f"Patch 不存在: {patch_id}")

        patch = patches[patch_id]
        old_status = str(patch.get("status", PatchStatus.PENDING.value))
        patch["status"] = status.value
        patch["updated_at"] = datetime.now().isoformat()
        patch.setdefault("notes", [])

        if note:
            patch["notes"].append(f"[{datetime.now().isoformat()}] {note}")
        if result_file:
            patch["result_file"] = result_file
        if status in {PatchStatus.COMPLETED, PatchStatus.CANCELLED}:
            patch["completed_at"] = datetime.now().isoformat()
        elif status == PatchStatus.IN_PROGRESS:
            patch["completed_at"] = None

        self._append_patch_op(
            patch_id=patch_id,
            task_id=str(patch.get("task_id", "")),
            old_status=old_status,
            new_status=status.value,
            actor=actor,
            source=source,
            reason=reason or note or "",
        )
        self._save_state()
        return {
            "patch_id": patch_id,
            "old_status": old_status,
            "new_status": status.value,
            "updated_at": patch["updated_at"],
        }

    def get_patch(self, patch_id: str) -> Dict[str, Any] | None:
        """获取 patch 信息。"""
        return self.state.get("patches", {}).get(patch_id)

    def list_patches(
        self,
        status_filter: str | None = None,
        task_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """列出 patch。"""
        patches = list(self.state.get("patches", {}).values())
        if status_filter:
            patches = [p for p in patches if str(p.get("status")) == status_filter]
        if task_id:
            patches = [p for p in patches if str(p.get("task_id")) == task_id]
        return patches

    def check_conflicts(
        self, ai_type: str, files: List[str], check_mode: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        检查文件冲突

        Args:
            ai_type: 当前 AI 类型
            files: 要修改的文件列表
            check_mode: 检查模式 ('on_save', 'command', 'both')

        Returns:
            冲突列表
        """
        conflicts = []
        file_set = set(files)

        # 标记文件状态为修改中
        for file_path in files:
            self.state.setdefault("file_status", {})[file_path] = FileStatus.MODIFIED.value

        # 检查与其他任务的冲突
        for task_id, task in self.state["tasks"].items():
            # 跳过自己 AI 的任务
            if task.get("ai_type") == ai_type:
                continue

            # 只检查活跃状态的任务
            if task.get("status") not in [s.value for s in self.CONFLICT_STATUSES]:
                continue

            # 检查文件重叠
            task_files_raw = task.get("files", [])
            task_files = set(task_files_raw if isinstance(task_files_raw, list) else [])
            overlapping = file_set & task_files

            if overlapping:
                conflict = {
                    "task_id": task_id,
                    "ai_type": task.get("ai_type", "unknown"),
                    "description": task.get("description", ""),
                    "status": task.get("status", TaskStatus.PENDING.value),
                    "overlapping_files": list(overlapping),
                    "detected_at": datetime.now().isoformat(),
                    "check_mode": check_mode,
                }
                conflicts.append(conflict)

                # 标记文件为冲突状态
                for file_path in overlapping:
                    self.state.setdefault("file_status", {})[file_path] = FileStatus.CONFLICT.value

                # 记录冲突
                self._record_conflict(task_id, ai_type, list(overlapping), check_mode)

                # VSCode 通知
                VSCodeIntegration.update_vscode_output(
                    f"冲突检测: {ai_type} 与 {task_id} 在 {len(overlapping)} 个文件上冲突",
                    "AI Collab Conflicts",
                )

        self._save_state()
        return conflicts

    def _record_conflict(
        self, task_id: str, conflicting_ai: str, files: List[str], check_mode: str
    ):
        """记录冲突到问题文件"""
        task = self.state["tasks"].get(task_id)
        if not task:
            return

        conflict_entry = {
            "conflict_id": f"CONFLICT-{uuid.uuid4().hex}",
            "task_id_1": task_id,
            "task_id_2": f"ATTEMPT-{conflicting_ai}",
            "ai_type_1": task.get("ai_type", "unknown"),
            "ai_type_2": conflicting_ai,
            "overlapping_files": files,
            "detected_at": datetime.now().isoformat(),
            "status": "open",
            "check_mode": check_mode,
        }

        issues_file = self._get_issues_file()
        os.makedirs(os.path.dirname(issues_file) or ".", exist_ok=True)

        with self._file_lock(issues_file):
            # 加载或创建问题文件
            issues: Dict[str, Any] = {"issues": []}
            if os.path.exists(issues_file):
                try:
                    with open(issues_file, "r", encoding="utf-8") as f:
                        issues = json.load(f)
                except (OSError, json.JSONDecodeError):
                    issues = {"issues": []}

            if not isinstance(issues.get("issues"), list):
                issues["issues"] = []

            issues["issues"].append(conflict_entry)
            self._atomic_write_json(issues_file, issues)

    def get_task(self, task_id: str) -> Dict[str, Any] | None:
        """获取任务信息"""
        return self.state["tasks"].get(task_id)

    def _evaluate_task_contract(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个任务是否满足工单契约字段。"""
        missing_fields: List[str] = []
        invalid_fields: List[str] = []

        for field_name in self.TASK_CONTRACT_REQUIRED_STR_FIELDS:
            value = task.get(field_name)
            if value is None:
                missing_fields.append(field_name)
                continue
            if not isinstance(value, str) or not value.strip():
                invalid_fields.append(field_name)
                continue
            if field_name == "change_id" and not self._is_valid_change_id(value):
                invalid_fields.append(field_name)

        for field_name in self.TASK_CONTRACT_REQUIRED_LIST_FIELDS:
            value = task.get(field_name)
            if value is None:
                missing_fields.append(field_name)
                continue
            if not isinstance(value, list) or not value:
                invalid_fields.append(field_name)
                continue
            if any(not isinstance(item, str) or not item.strip() for item in value):
                invalid_fields.append(field_name)

        valid = not missing_fields and not invalid_fields
        return {
            "valid": valid,
            "missing_fields": missing_fields,
            "invalid_fields": invalid_fields,
        }

    def _normalize_non_empty_str(self, value: Any) -> str | None:
        """标准化非空字符串。"""
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized if normalized else None

    def _normalize_non_empty_list(self, value: Any) -> List[str]:
        """标准化字符串列表，过滤空值。"""
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    def _default_primary_skill(self, ai_type: str) -> str:
        """按执行者默认主技能。"""
        normalized = ai_type.strip().lower()
        mapping = {
            "codex": "duoai-coordinator",
            "claude_code": "backend-architect",
            "codearts_agent": "api-test-pro",
            "copilot": "api-test-pro",
        }
        return mapping.get(normalized, "planning-with-files")

    def _default_result_file(self, task_id: str) -> str:
        """生成默认结果文件路径。"""
        safe_task_id = task_id.strip() or "UNKNOWN-TASK"
        return f"collaboration/results/RESULT_{safe_task_id}.md"

    def _workspace_root(self) -> str:
        """获取工作区根目录。"""
        return self.workspace_path or VSCodeIntegration.get_workspace_path() or os.getcwd()

    def _resolve_result_file_path(self, result_file: str) -> str:
        """将 result_file 解析为绝对路径。"""
        normalized = result_file.strip()
        if os.path.isabs(normalized):
            return normalized
        return os.path.join(self._workspace_root(), normalized)

    def _normalize_command_text(self, command: str) -> str:
        """压缩命令文本中的空白，便于在结果文件中做稳健匹配。"""
        return " ".join(str(command or "").split())

    def _validate_result_artifact_for_completion(self, task_id: str, task: Dict[str, Any]):
        """completed 状态门禁：结果文件必须存在、具备最小章节，并覆盖验收命令。"""
        result_file = self._normalize_non_empty_str(task.get("result_file"))
        if not result_file:
            inferred_path = os.path.join(
                self._workspace_root(),
                "collaboration",
                "results",
                f"RESULT_{task_id}.md",
            )
            if os.path.exists(inferred_path):
                result_file = os.path.relpath(inferred_path, self._workspace_root())
                task["result_file"] = result_file
            else:
                raise ValueError(f"任务结果门禁失败: {task_id}; missing result_file")

        resolved_path = self._resolve_result_file_path(result_file)
        if not os.path.exists(resolved_path):
            raise ValueError(f"任务结果门禁失败: {task_id}; result_file not found: {result_file}")

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            raise ValueError(
                f"任务结果门禁失败: {task_id}; unable to read result_file: {result_file}"
            ) from exc

        if not content.strip():
            raise ValueError(f"任务结果门禁失败: {task_id}; result_file is empty: {result_file}")

        lowered = content.lower()
        missing_sections: List[str] = []
        for section_group in self.TASK_RESULT_REQUIRED_SECTION_GROUPS:
            if not any(marker.lower() in lowered for marker in section_group):
                missing_sections.append(section_group[0])

        if missing_sections:
            missing_label = ",".join(missing_sections)
            raise ValueError(f"任务结果门禁失败: {task_id}; result_file missing sections=[{missing_label}]")

        negative_hits: List[str] = []
        for marker in self.TASK_RESULT_NEGATIVE_SIGNAL_MARKERS:
            if marker.lower() in lowered:
                negative_hits.append(marker)
        if negative_hits:
            negative_label = ",".join(negative_hits)
            raise ValueError(
                f"任务结果门禁失败: {task_id}; result_file contains_negative_signals=[{negative_label}]"
            )

        acceptance_commands = task.get("acceptance_commands")
        if isinstance(acceptance_commands, list):
            normalized_content = self._normalize_command_text(content)
            missing_commands: List[str] = []
            for command in acceptance_commands:
                normalized_command = self._normalize_command_text(command)
                if normalized_command and normalized_command not in normalized_content:
                    missing_commands.append(str(command))
            if missing_commands:
                missing_label = " | ".join(missing_commands)
                raise ValueError(
                    f"任务结果门禁失败: {task_id}; result_file missing acceptance_commands=[{missing_label}]"
                )

    def _is_valid_change_id(self, change_id: str) -> bool:
        """校验 change_id 是否为白名单标签或真实 OpenSpec 变更。"""
        normalized = change_id.strip()
        if normalized in self.TASK_CONTRACT_SPECIAL_CHANGE_IDS:
            return True

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized):
            return False

        workspace = self._workspace_root()
        open_changes_dir = os.path.join(workspace, "openspec", "changes")
        direct_change_dir = os.path.join(open_changes_dir, normalized)
        if os.path.isdir(direct_change_dir):
            return True

        archive_root = os.path.join(open_changes_dir, "archive")
        if not os.path.isdir(archive_root):
            return False

        suffix = f"-{normalized}"
        for item in os.listdir(archive_root):
            archive_item = os.path.join(archive_root, item)
            if item.endswith(suffix) and os.path.isdir(archive_item):
                return True
        return False

    def validate_task_contract(self, task_id: str) -> Dict[str, Any]:
        """
        校验单个任务工单契约。
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        check = self._evaluate_task_contract(task)
        check["task_id"] = task_id
        check["skipped"] = False
        return check

    def validate_task_contracts(
        self,
        scope: str = "active",
    ) -> Dict[str, Any]:
        """
        批量校验工单契约。

        Args:
            scope: active | all
        """
        if scope not in {"active", "all"}:
            raise ValueError(f"不支持的 scope: {scope}")

        if scope == "active":
            tasks = self.get_active_tasks()
        else:
            tasks = self.get_all_tasks()

        checked = 0
        skipped = 0
        issues: List[Dict[str, Any]] = []

        for task in tasks:
            task_id = str(task.get("task_id", ""))
            if not task_id:
                continue

            checked += 1
            check = self._evaluate_task_contract(task)
            if check["valid"]:
                continue

            issues.append(
                {
                    "task_id": task_id,
                    "missing_fields": check["missing_fields"],
                    "invalid_fields": check["invalid_fields"],
                    "remediation": (
                        "re-register task with --change-id --assignee --reviewer "
                        "--primary-skill --support-skills --acceptance-commands --result-file "
                        "or update task metadata to satisfy contract"
                    ),
                }
            )

        return {
            "scope": scope,
            "checked_tasks": checked,
            "skipped_tasks": skipped,
            "invalid_count": len(issues),
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def migrate_task_contracts(
        self,
        scope: str = "all",
        dry_run: bool = False,
        default_change_id: str | None = None,
        reviewer: str | None = None,
    ) -> Dict[str, Any]:
        """
        迁移历史任务到契约完整态，消除 legacy 分支依赖。

        Args:
            scope: active | all
            dry_run: 仅预览，不落盘
            default_change_id: 缺省 change_id
            reviewer: 缺省 reviewer
        """
        if scope not in {"active", "all"}:
            raise ValueError(f"不支持的 scope: {scope}")

        change_id_fallback = (
            self._normalize_non_empty_str(default_change_id) or self.TASK_CONTRACT_DEFAULT_CHANGE_ID
        )
        reviewer_fallback = (
            self._normalize_non_empty_str(reviewer) or self.TASK_CONTRACT_DEFAULT_REVIEWER
        )

        if scope == "active":
            candidate_ids = [
                task_id
                for task_id in self.state.get("active_tasks", [])
                if task_id in self.state.get("tasks", {})
            ]
        else:
            candidate_ids = list(self.state.get("tasks", {}).keys())

        migrated_task_ids: List[str] = []
        already_compliant = 0
        legacy_detected = 0
        invalid_after_migration: List[Dict[str, Any]] = []
        changed_any = False

        for task_id in candidate_ids:
            raw_task = self.state.get("tasks", {}).get(task_id)
            if not isinstance(raw_task, dict):
                continue

            if not bool(raw_task.get("contract_required", False)):
                legacy_detected += 1

            check_before = self._evaluate_task_contract(raw_task)
            if bool(raw_task.get("contract_required", False)) and check_before["valid"]:
                already_compliant += 1
                continue

            task = dict(raw_task)
            normalized_task_id = self._normalize_non_empty_str(task.get("task_id")) or task_id
            ai_type = (
                self._normalize_non_empty_str(task.get("assignee"))
                or self._normalize_non_empty_str(task.get("ai_type"))
                or self._normalize_non_empty_str(task.get("assigned_to"))
                or "legacy_agent"
            )

            task["task_id"] = normalized_task_id
            task["change_id"] = (
                self._normalize_non_empty_str(task.get("change_id")) or change_id_fallback
            )
            task["assignee"] = self._normalize_non_empty_str(task.get("assignee")) or ai_type
            task["reviewer"] = (
                self._normalize_non_empty_str(task.get("reviewer")) or reviewer_fallback
            )
            task["primary_skill"] = self._normalize_non_empty_str(
                task.get("primary_skill")
            ) or self._default_primary_skill(ai_type)

            support_skills = self._normalize_non_empty_list(task.get("support_skills"))
            task["support_skills"] = support_skills or list(
                self.TASK_CONTRACT_DEFAULT_SUPPORT_SKILLS
            )

            acceptance_commands = self._normalize_non_empty_list(task.get("acceptance_commands"))
            task["acceptance_commands"] = acceptance_commands or list(
                self.TASK_CONTRACT_DEFAULT_ACCEPTANCE_COMMANDS
            )

            task["result_file"] = self._normalize_non_empty_str(
                task.get("result_file")
            ) or self._default_result_file(normalized_task_id)
            task["contract_required"] = True
            task.setdefault("notes", [])
            if not isinstance(task.get("notes"), list):
                task["notes"] = []
            task["notes"].append(
                f"[{datetime.now().isoformat()}] migrated task contract to eliminate legacy path"
            )
            task["updated_at"] = datetime.now().isoformat()

            check_after = self._evaluate_task_contract(task)
            if check_after["valid"]:
                migrated_task_ids.append(task_id)
                if not dry_run:
                    self.state["tasks"][task_id] = task
                    changed_any = True
            else:
                invalid_after_migration.append(
                    {
                        "task_id": task_id,
                        "missing_fields": check_after["missing_fields"],
                        "invalid_fields": check_after["invalid_fields"],
                    }
                )

        if changed_any:
            self._save_state()

        remaining_legacy = len(
            [
                task
                for task in self.state.get("tasks", {}).values()
                if isinstance(task, dict) and not bool(task.get("contract_required", False))
            ]
        )
        if dry_run:
            # dry-run 下 remaining_legacy 使用迁移后的估算值，避免误导。
            remaining_legacy = max(
                0,
                remaining_legacy - len(migrated_task_ids),
            )

        return {
            "scope": scope,
            "dry_run": dry_run,
            "total_tasks": len(candidate_ids),
            "legacy_detected": legacy_detected,
            "already_compliant": already_compliant,
            "migrated_count": len(migrated_task_ids),
            "migrated_task_ids": migrated_task_ids,
            "invalid_after_migration_count": len(invalid_after_migration),
            "invalid_after_migration": invalid_after_migration,
            "remaining_legacy": remaining_legacy,
            "legacy_branch_eliminated": remaining_legacy == 0,
            "valid": len(invalid_after_migration) == 0 and remaining_legacy == 0,
        }

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取所有活跃任务"""
        return [
            self.state["tasks"][task_id]
            for task_id in self.state["active_tasks"]
            if task_id in self.state["tasks"]
        ]

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return list(self.state["tasks"].values())

    def get_conflicts(self, status: str | None = None) -> List[Dict[str, Any]]:
        """
        获取冲突列表

        Args:
            status: 按状态过滤 ('open', 'resolved', None 表示全部)
        """
        issues_file = self._get_issues_file()

        if not os.path.exists(issues_file):
            return []

        with open(issues_file, "r", encoding="utf-8") as f:
            issues = json.load(f)

        conflicts = issues.get("issues", [])

        if status:
            conflicts = [c for c in conflicts if c.get("status") == status]

        return conflicts

    def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        """
        解决冲突

        Args:
            conflict_id: 冲突ID
            resolution: 解决方案描述
        """
        issues_file = self._get_issues_file()

        if not os.path.exists(issues_file):
            return False

        with open(issues_file, "r", encoding="utf-8") as f:
            issues = json.load(f)

        updated = False
        for conflict in issues.get("issues", []):
            if conflict.get("conflict_id") == conflict_id:
                conflict["status"] = "resolved"
                conflict["resolution"] = resolution
                conflict["resolved_at"] = datetime.now().isoformat()
                updated = True

                # 清除文件冲突状态
                for file_path in conflict.get("overlapping_files", []):
                    if self.state["file_status"].get(file_path) == FileStatus.CONFLICT.value:
                        self.state["file_status"][file_path] = FileStatus.CLEAN.value

        if updated:
            with open(issues_file, "w", encoding="utf-8") as f:
                json.dump(issues, f, ensure_ascii=False, indent=2)
            self._save_state()

        return updated

    def clear_completed_tasks(self, days: int = 7) -> Dict[str, int]:
        """
        清理已完成的任务

        Args:
            days: 保留最近几天的任务
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        to_remove: List[str] = []

        for task_id in self.state["completed_tasks"]:
            task = self.state["tasks"].get(task_id)
            if task and task.get("completed_at"):
                completed_time = datetime.fromisoformat(task["completed_at"]).timestamp()
                if completed_time < cutoff:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self.state["tasks"][task_id]
            self.state["completed_tasks"].remove(task_id)

        self._save_state()

        return {"cleared": len(to_remove), "remaining": len(self.state["completed_tasks"])}

    # ==================== 双向交接回通知功能 ====================

    def _get_handoff_file(self) -> str:
        """获取主交接状态文件路径。"""
        config = VSCodeIntegration.get_project_config()
        handoff_file = config.get("handoffFile", "./logs/handoff_status.json")
        handoff_file = str(handoff_file)
        if self.workspace_path and not os.path.isabs(handoff_file):
            return os.path.join(self.workspace_path, handoff_file)
        return handoff_file

    def _get_legacy_handoff_file(self) -> str:
        """获取历史交接文件路径（兼容旧流程）。"""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "handoff_status.json")
        return "./handoff_status.json"

    def _read_handoff_file(self, handoff_file: str) -> Dict[str, Any]:
        """读取单个交接文件。"""
        if not os.path.exists(handoff_file):
            return {}
        try:
            with open(handoff_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
                return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _write_handoff_file(self, handoff_file: str, handoffs: Dict[str, Any]):
        """原子写交接文件。"""
        os.makedirs(os.path.dirname(handoff_file) or ".", exist_ok=True)
        with self._file_lock(handoff_file):
            self._atomic_write_json(handoff_file, handoffs)

    def create_handoff(
        self,
        from_ai: str,
        to_ai: str,
        task_description: str,
        files: List[str] | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        创建交接任务

        Args:
            from_ai: 发起方 AI
            to_ai: 接收方 AI
            task_description: 任务描述
            files: 涉及的文件列表
            context: 上下文信息

        Returns:
            交接任务信息
        """
        handoff_id = f"HANDOFF-{int(time.time())}"
        handoff = {
            "handoff_id": handoff_id,
            "from_ai": from_ai,
            "to_ai": to_ai,
            "task_description": task_description,
            "files": files or [],
            "context": context or {},
            "status": "PENDING",
            "created_at": datetime.now().isoformat(),
            "processed_at": None,
            "return_status": None,
        }

        # 保存交接状态
        handoffs = self._load_handoffs()
        handoffs[handoff_id] = handoff
        self._save_handoffs(handoffs)

        VSCodeIntegration.update_vscode_output(
            f"交接任务已创建: {handoff_id} ({from_ai} -> {to_ai})", "AI Collab Handoff"
        )

        return handoff

    def _load_handoffs(self) -> Dict[str, Any]:
        """加载所有交接任务"""
        primary = self._get_handoff_file()
        legacy = self._get_legacy_handoff_file()

        for handoff_file in [primary, legacy]:
            payload = self._read_handoff_file(handoff_file)
            if payload:
                return payload
        return {}

    def _save_handoffs(self, handoffs: Dict[str, Any]):
        """保存交接任务"""
        primary = self._get_handoff_file()
        self._write_handoff_file(primary, handoffs)

        # 兼容旧流程：如果历史文件存在，则同步一份避免老轮询器失联。
        legacy = self._get_legacy_handoff_file()
        if os.path.abspath(legacy) != os.path.abspath(primary) and os.path.exists(legacy):
            self._write_handoff_file(legacy, handoffs)

    def get_handoff(self, handoff_id: str) -> Dict[str, Any] | None:
        """
        获取交接任务信息

        Args:
            handoff_id: 交接 ID

        Returns:
            交接任务信息，不存在则返回 None
        """
        handoffs = self._load_handoffs()
        return handoffs.get(handoff_id)

    def get_pending_handoffs(self, to_ai: str | None = None) -> List[Dict[str, Any]]:
        """
        获取待处理的交接任务

        Args:
            to_ai: 按接收方 AI 过滤

        Returns:
            待处理的交接任务列表
        """
        handoffs = self._load_handoffs()
        pending = [h for h in handoffs.values() if h.get("status") == "PENDING"]

        if to_ai:
            pending = [h for h in pending if h.get("to_ai") == to_ai]

        return pending

    def acknowledge_handoff(
        self, handoff_id: str, status: str, message: str = "", result_files: List[str] | None = None
    ) -> Dict[str, Any]:
        """
        确认交接并更新状态（双向交接回通知）

        Args:
            handoff_id: 交接 ID
            status: 处理状态 (completed, failed, pending)
            message: 处理结果消息
            result_files: 处理结果文件列表

        Returns:
            更新后的交接状态
        """
        handoffs = self._load_handoffs()

        if handoff_id not in handoffs:
            raise ValueError(f"交接任务不存在: {handoff_id}")

        handoff = handoffs[handoff_id]

        # 更新状态
        status_map = {
            "completed": "ACKNOWLEDGED_COMPLETED",
            "failed": "ACKNOWLEDGED_FAILED",
            "pending": "ACKNOWLEDGED_PROCESSING",
        }
        handoff["status"] = status_map.get(status, f"ACKNOWLEDGED_{status.upper()}")
        handoff["processed_at"] = datetime.now().isoformat()

        # 添加回通知信息（双向交接的关键）
        handoff["return_status"] = {
            "from_ai": handoff["to_ai"],  # 回通知发送方
            "to_ai": handoff["from_ai"],  # 回通知接收方（原发送方）
            "status": status,
            "message": message,
            "result_files": result_files or [],
            "acknowledged_at": datetime.now().isoformat(),
        }

        # 保存更新
        handoffs[handoff_id] = handoff
        self._save_handoffs(handoffs)

        VSCodeIntegration.update_vscode_output(
            f"交接已确认: {handoff_id} -> {status} (回通知: {handoff['to_ai']} -> {handoff['from_ai']})",
            "AI Collab Handoff",
        )

        return handoff

    def list_handoffs(
        self, status: str | None = None, from_ai: str | None = None, to_ai: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        列出交接任务

        Args:
            status: 按状态过滤
              from_ai: 按发送方过滤
              to_ai: 按接收方过滤

        Returns:
            交接任务列表
        """
        handoffs = self._load_handoffs()
        result = list(handoffs.values())

        if status:
            result = [h for h in result if h.get("status") == status]
        if from_ai:
            result = [h for h in result if h.get("from_ai") == from_ai]
        if to_ai:
            result = [h for h in result if h.get("to_ai") == to_ai]

        # 按创建时间倒序
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result
