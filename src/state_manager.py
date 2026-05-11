"""
状态管理器模块 - VSCode 集成版.

管理 Claude Code 与 GitHub Copilot 的协作状态
支持项目级和全局配置同步
"""

import json
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class TaskStatus(str, Enum):
    """任务状态枚举."""

    PENDING = "pending"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PatchStatus(str, Enum):
    """补丁状态枚举."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class FileStatus(str, Enum):
    """文件状态枚举."""

    CLEAN = "clean"
    MODIFIED = "modified"
    CONFLICT = "conflict"
    LOCKED = "locked"


@dataclass
class Task:
    """任务数据类."""

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


@dataclass
class Patch:
    """Patch 一等对象."""

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
    """冲突数据类."""

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
    """VSCode 集成状态管理辅助类."""

    @staticmethod
    def get_project_state_file() -> str:
        """获取项目状态文件路径."""
        workspace = VSCodeIntegration.get_workspace_path()
        config = VSCodeIntegration.get_project_config()
        state_file = config.get("stateFile", "./logs/collaboration_state.json")

        if workspace:
            state_file = os.path.join(workspace, state_file)

        # 确保目录存在
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        return state_file

    @staticmethod
    def get_global_state_file() -> str:
        """获取全局状态文件路径."""
        global_dir = os.path.expanduser("~/.vscode/ai-collab")
        os.makedirs(global_dir, exist_ok=True)
        return os.path.join(global_dir, "collaboration_state.json")

    @staticmethod
    def get_issues_file() -> str:
        """获取问题记录文件路径."""
        workspace = VSCodeIntegration.get_workspace_path()
        if workspace:
            return os.path.join(workspace, "./logs/collaboration_issues.json")
        return "./logs/collaboration_issues.json"

    @staticmethod
    def get_backup_dir() -> str:
        """获取备份目录."""
        workspace = VSCodeIntegration.get_workspace_path()
        if workspace:
            dir_path = os.path.join(workspace, "./logs/backups")
        else:
            dir_path = "./logs/backups"
        os.makedirs(dir_path, exist_ok=True)
        return dir_path


# 导入前向引用的类
class VSCodeIntegration:
    """VSCode 集成辅助类."""

    @staticmethod
    def get_workspace_path() -> str | None:
        """获取当前 VSCode 工作区路径."""
        workspace = os.environ.get("VSCODE_CWD")
        if workspace and os.path.exists(workspace):
            return workspace

        cwd = os.getcwd()
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
        """获取项目级 AI 协作配置."""
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
        """更新 VSCode 输出面板."""
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

    def __init__(self, workspace_path: str | None = None):
        """
        初始化状态管理器

        Args:
            workspace_path: 工作区路径（可选）
        """
        self.workspace_path = workspace_path or VSCodeIntegration.get_workspace_path()
        self.state = self._load_state()

    def _get_state_file(self) -> str:
        """获取项目状态文件路径（使用实例的 workspace_path）."""
        config = VSCodeIntegration.get_project_config()
        state_file = config.get("stateFile", "./logs/collaboration_state.json")

        # 规范化路径，去除 ./ 等
        state_file = os.path.normpath(state_file)

        # 获取工作区路径，添加多层 fallback
        workspace = self.workspace_path
        if not workspace:
            # 尝试从环境变量获取
            workspace = os.environ.get("VSCODE_CWD")
        if not workspace:
            # 尝试从当前目录获取
            cwd = os.path.abspath(os.getcwd())
            # 检查是否包含 .vscode 或 collaboration 目录（有效项目标识）
            if cwd and (os.path.exists(os.path.join(cwd, ".vscode")) or
                       os.path.exists(os.path.join(cwd, "collaboration"))):
                workspace = cwd
            else:
                # 最后的 fallback：使用全局目录
                workspace = os.path.expanduser("~/.vscode/ai-collab")

        # 确保使用绝对路径
        if not os.path.isabs(state_file):
            state_file = os.path.join(workspace, state_file)

        # 再次规范化，防止拼接后出现 /./ 等
        state_file = os.path.normpath(state_file)

        # 验证路径有效性（不能是根目录）
        if state_file.startswith("/.") or os.path.dirname(state_file) == "/":
            # 使用全局目录作为 fallback
            global_dir = os.path.expanduser("~/.vscode/ai-collab/logs")
            state_file = os.path.join(global_dir, "collaboration_state.json")

        # 确保目录存在
        state_dir = os.path.dirname(state_file)
        if state_dir:  # 只有当 dirname 不为空时才创建目录
            os.makedirs(state_dir, exist_ok=True)
        return state_file

    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件."""
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
        """兼容旧版状态文件，补齐缺失字段."""
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
                task["status"] = status.value if isinstance(status, TaskStatus) else str(status)

                created_at = task.get("created_at", now)
                task["created_at"] = created_at
                task["updated_at"] = task.get("updated_at", created_at)
                task["completed_at"] = task.get("completed_at")

                vscode_context = task.get("vscode_context")
                task["vscode_context"] = vscode_context if isinstance(vscode_context, dict) else {}

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

    def _create_initial_state(self) -> Dict[str, Any]:
        """创建初始状态."""
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
        """获取备份目录（使用实例的 workspace_path）."""
        if self.workspace_path:
            dir_path = os.path.join(self.workspace_path, "./logs/backups")
        else:
            dir_path = "./logs/backups"
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _get_issues_file(self) -> str:
        """获取问题记录文件路径（使用实例的 workspace_path）."""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "./logs/collaboration_issues.json")
        return "./logs/collaboration_issues.json"

    def _get_patch_ops_file(self) -> str:
        """获取 patch 操作日志文件路径."""
        if self.workspace_path:
            return os.path.join(self.workspace_path, "./logs/patch_ops.jsonl")
        return "./logs/patch_ops.jsonl"

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
        """追加写 patch 操作日志（JSONL）."""
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

    def _atomic_write_json(self, target_file: str, payload: Dict[str, Any]):
        """原子写 JSON，避免并发写导致状态文件损坏."""
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
        """将时间戳字段转换为可比较的 epoch，异常时返回 -1."""
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
        """按 updated_at/created_at 选择更新的任务版本."""
        latest_ts = self._to_epoch(latest_task.get("updated_at") or latest_task.get("created_at"))
        local_ts = self._to_epoch(local_task.get("updated_at") or local_task.get("created_at"))
        return local_task if local_ts >= latest_ts else latest_task

    def _merge_conflicts(self, latest_conflicts: Any, local_conflicts: Any) -> List[Dict[str, Any]]:
        """按 conflict_id 合并冲突列表，保留无 ID 条目."""
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
        """将本地内存状态与磁盘最新状态合并，降低并发覆盖风险."""
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
        """通过 lock 文件提供跨进程互斥，避免并发写冲突."""
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
        """保存状态到文件（项目 + 全局）."""
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

    def _backup_state(self):
        """创建状态备份."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self._get_backup_dir(), f"state_{timestamp}.json")

        try:
            self._atomic_write_json(backup_file, self.state)
        except Exception as e:
            print(f"警告: 状态备份失败: {e}")

    def _sync_to_global(self):
        """同步状态到全局配置."""
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
        if task_id in self.state["tasks"]:
            raise ValueError(f"任务ID已存在: {task_id}")

        task = Task(
            task_id=task_id,
            ai_type=ai_type,
            description=description,
            files=files,
            status=TaskStatus.PENDING,
            vscode_context=vscode_context or {},
        )

        self.state["tasks"][task_id] = asdict(task)
        self.state["active_tasks"].append(task_id)
        self._save_state()

        VSCodeIntegration.update_vscode_output(f"任务已注册: {task_id} ({ai_type})", "AI Collab Tasks")

        return asdict(task)

    def update_task_status(
        self, task_id: str, status: TaskStatus, note: str | None = None
    ) -> Dict[str, Any]:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            note: 可选备注
        """
        if task_id not in self.state["tasks"]:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.state["tasks"][task_id]
        old_status = task["status"]
        task["status"] = status.value
        task["updated_at"] = datetime.now().isoformat()

        if note:
            task["notes"].append(f"[{datetime.now().isoformat()}] {note}")

        # 如果任务完成，移动到已完成列表
        if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            task["completed_at"] = datetime.now().isoformat()
            if task_id in self.state["active_tasks"]:
                self.state["active_tasks"].remove(task_id)
            if task_id not in self.state["completed_tasks"]:
                self.state["completed_tasks"].append(task_id)

        self._save_state()

        # 更新 VSCode 输出
        VSCodeIntegration.update_vscode_output(
            f"任务状态更新: {task_id} {old_status} -> {status.value}", "AI Collab Tasks"
        )

        return {
            "task_id": task_id,
            "old_status": old_status,
            "new_status": status.value,
            "updated_at": task["updated_at"],
        }

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
        """注册 patch."""
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
        """更新 patch 状态."""
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
        """获取 patch 信息."""
        return self.state.get("patches", {}).get(patch_id)

    def list_patches(
        self,
        status_filter: str | None = None,
        task_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """列出 patch."""
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
            if task["ai_type"] == ai_type:
                continue

            # 只检查活跃状态的任务
            if task["status"] not in [s.value for s in self.CONFLICT_STATUSES]:
                continue

            # 检查文件重叠
            task_files = set(task["files"])
            overlapping = file_set & task_files

            if overlapping:
                conflict = {
                    "task_id": task_id,
                    "ai_type": task["ai_type"],
                    "description": task["description"],
                    "status": task["status"],
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
        """记录冲突到问题文件."""
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
        """获取任务信息."""
        return self.state["tasks"].get(task_id)

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取所有活跃任务."""
        return [
            self.state["tasks"][task_id]
            for task_id in self.state["active_tasks"]
            if task_id in self.state["tasks"]
        ]

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务."""
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
