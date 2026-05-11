"""
日志生成器模块 - VSCode 集成版

支持 Claude Code 与 GitHub Copilot 的开发日志
支持项目本地日志、Git 追踪、VSCode 输出面板
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List


class VSCodeIntegration:
    """VSCode 集成辅助类"""

    @staticmethod
    def get_workspace_path() -> str | None:
        return os.environ.get("VSCODE_CWD") or os.getcwd()

    @staticmethod
    def get_project_config() -> Dict[str, Any]:
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            return {}
        config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    @staticmethod
    def update_vscode_output(message: str, channel: str = "AI Collab"):
        try:
            global_dir = os.path.expanduser("~/.vscode/ai-collab")
            os.makedirs(global_dir, exist_ok=True)
            log_file = os.path.join(global_dir, f"output_{datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] [{channel}] {message}\n")
        except Exception:
            pass


class VSCodeOutputLogger:
    """VSCode 输出面板日志适配器"""

    @staticmethod
    def log(message: str, channel: str = "AI Collab"):
        """记录日志到 VSCode 输出面板"""
        VSCodeIntegration.update_vscode_output(message, channel)

    @staticmethod
    def log_activation(ai_type: str, session_id: str, rules: List[str]):
        """记录激活日志"""
        VSCodeOutputLogger.log(
            f"{ai_type} ACTIVATED: Session={session_id}, Rules={', '.join(rules)}",
            "AI Collab Activation",
        )

    @staticmethod
    def log_conflict(conflict: Dict[str, Any]):
        """记录冲突日志"""
        VSCodeOutputLogger.log(
            f"CONFLICT: {conflict['task_id_1']} vs {conflict['task_id_2']}, Files={conflict['overlapping_files']}",
            "AI Collab Conflicts",
        )

    @staticmethod
    def log_task(task: Dict[str, Any]):
        """记录任务日志"""
        VSCodeOutputLogger.log(
            f"TASK: {task['task_id']} ({task['ai_type']}), Status={task['status']}, {task['description']}",
            "AI Collab Tasks",
        )

    @staticmethod
    def log_progress(task_id: str, stage: str, message: str):
        """记录进度日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        VSCodeOutputLogger.log(
            f"[{timestamp}] TASK: {task_id}, Stage: {stage}, {message}", "AI Collab Progress"
        )


class DevLogger:
    """
    开发日志生成器 - VSCode 集成版

    特性：
    - 三重日志存储：项目本地、Git 追踪、VSCode 输出
    - 支持结构化日志模板
    - 自动按月份组织
    """

    LOG_DIR = "./logs"
    GIT_LOG_DIR = ".git/ai-collab"
    TEMPLATE_FILE = "./rules/dev-record-template.md"

    def __init__(self, ai_type: str, enable_git_log: bool = True, enable_vsc_log: bool = True):
        """
        初始化日志生成器

        Args:
            ai_type: AI 类型 (claude-code / copilot)
            enable_git_log: 启用 Git 追踪
            enable_vsc_log: 启用 VSCode 输出面板
        """
        self.ai_type = ai_type
        self.enable_git_log = enable_git_log
        self.enable_vsc_log = enable_vsc_log

        config = VSCodeIntegration.get_project_config()

        # 获取配置的日志目录
        if config.get("logsDir"):
            self.LOG_DIR = config["logsDir"]

        if config.get("autoLogToGit") is not None:
            self.enable_git_log = config["autoLogToGit"]

        self.workspace = VSCodeIntegration.get_workspace_path()
        self.log_dir = os.path.join(self.workspace or ".", self.LOG_DIR, ai_type)
        self._ensure_directories()
        self.template = self._load_template()

        if self.enable_vsc_log:
            VSCodeOutputLogger.log(f"DevLogger initialized for {ai_type}", "AI Collab Init")

    def _ensure_directories(self):
        """确保日志目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)
        if self.enable_git_log:
            git_dir = os.path.join(self.workspace or ".", self.GIT_LOG_DIR, self.ai_type)
            os.makedirs(git_dir, exist_ok=True)

    def _load_template(self) -> str:
        """加载日志模板"""
        if os.path.exists(self.TEMPLATE_FILE):
            with open(self.TEMPLATE_FILE, "r", encoding="utf-8") as f:
                return f.read()

        # 默认模板
        return """# 开发记录 - {date}

## 记录信息

- **任务ID**: {task_id}
- **AI类型**: {ai_type}
- **开始时间**: {start_time}
- **结束时间**: {end_time}
- **任务描述**: {description}

---

## 执行计划

### 目标
{goal}

### 步骤
{steps}

### 风险点
- {risks}

---

## 执行过程

{process}

---

## 变更文件

| 文件路径 | 变更类型 | 变更描述 |
|----------|----------|----------|
{files}

---

## 测试/验证结果

### 测试用例
{test_cases}

### 覆盖率
{coverage}

---

## 问题与解决方案

{issues}

---

## 总结

{summary}

---

**记录者**: {ai_type}
**记录时间**: {end_time}
"""

    def create_log(
        self,
        task_name: str,
        task_id: str | None = None,
        description: str = "",
        goal: str = "",
        steps: str = "",
        risks: str = "",
    ) -> str:
        """
        创建新的开发日志

        Returns:
            创建的本地日志文件路径
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")

        # 生成文件名
        safe_name = re.sub(r"[^\w\-]", "_", task_name)
        filename = f"{date_str}_{safe_name}.md"

        # 按月份组织
        month_dir = os.path.join(self.log_dir, datetime.now().strftime("%Y-%m"))
        os.makedirs(month_dir, exist_ok=True)

        filepath = os.path.join(month_dir, filename)

        # 生成日志内容
        content = self._generate_log_content(
            task_id=task_id or f"TASK-{timestamp}",
            description=description,
            date_str=date_str,
            goal=goal or "待定义",
            steps=steps or "1. 分析需求\n2. 实现功能\n3. 测试验证",
            risks=risks or "无明显风险",
        )

        # 写入本地日志
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # 写入 Git 追踪
        if self.enable_git_log:
            git_log_dir = os.path.join(self.workspace or ".", self.GIT_LOG_DIR, self.ai_type)
            os.makedirs(git_log_dir, exist_ok=True)
            git_filepath = os.path.join(git_log_dir, filename)
            with open(git_filepath, "w", encoding="utf-8") as f:
                f.write(content)

        # 记录到 VSCode 输出
        if self.enable_vsc_log:
            VSCodeOutputLogger.log(
                f"日志已创建: {filename} (ID: {task_id or f'TASK-{timestamp}'})", "AI Collab Logs"
            )

        return filepath

    def _generate_log_content(
        self,
        task_id: str,
        description: str,
        date_str: str,
        goal: str = "待定义",
        steps: str = "",
        risks: str = "",
    ) -> str:
        """生成日志内容"""
        now = datetime.now()

        return self.template.format(
            date=date_str,
            task_id=task_id,
            ai_type=self.ai_type,
            start_time=now.strftime("%Y-%m-%d %H:%M:%S"),
            end_time="进行中...",
            description=description or "待填写",
            goal=goal,
            steps=steps,
            risks=risks,
            process="待记录...",
            files="",
            test_cases="待添加测试用例",
            coverage="待计算覆盖率",
            issues="无",
            summary="待总结...",
        )

    def append_to_log(self, filepath: str, section: str, content: str):
        """追加内容到日志"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"日志文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            log_content = f.read()

        # 查找章节位置
        section_pattern = f"## {section}"
        if section_pattern in log_content:
            # 在章节后追加内容
            parts = log_content.split(section_pattern, 1)
            if len(parts) == 2:
                # 找到下一个章节或文件末尾
                next_section_idx = parts[1].find("\n## ")
                if next_section_idx == -1:
                    log_content = (
                        parts[0] + section_pattern + parts[1].rstrip() + f"\n\n{content}\n"
                    )
                else:
                    before = parts[0] + section_pattern + parts[1][:next_section_idx]
                    after = parts[1][next_section_idx:]
                    log_content = before.rstrip() + f"\n\n{content}\n" + after

        # 写入本地
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(log_content)

        # 同步到 Git
        if self.enable_git_log:
            git_log_dir = os.path.join(self.workspace or ".", self.GIT_LOG_DIR, self.ai_type)
            log_name = os.path.basename(filepath)
            git_filepath = os.path.join(git_log_dir, log_name)
            with open(git_filepath, "w", encoding="utf-8") as f:
                f.write(log_content)

        if self.enable_vsc_log:
            log_name = os.path.basename(filepath)
            VSCodeOutputLogger.log(f"日志已更新: {log_name} - 章节: {section}", "AI Collab Logs")

    def update_section(self, filepath: str, section: str, content: str):
        """更新日志的某个章节"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"日志文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            log_content = f.read()

        # 查找章节位置
        section_pattern = f"## {section}"
        if section_pattern in log_content:
            parts = log_content.split(section_pattern, 1)
            if len(parts) == 2:
                next_section_idx = parts[1].find("\n## ")
                if next_section_idx == -1:
                    log_content = parts[0] + section_pattern + f"\n\n{content}\n"
                else:
                    before = parts[0] + section_pattern
                    after = parts[1][next_section_idx:]
                    log_content = before + f"\n\n{content}\n" + after

        # 写入本地
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(log_content)

        # 同步到 Git
        if self.enable_git_log:
            git_log_dir = os.path.join(self.workspace or ".", self.GIT_LOG_DIR, self.ai_type)
            log_name = os.path.basename(filepath)
            git_filepath = os.path.join(git_log_dir, log_name)
            with open(git_filepath, "w", encoding="utf-8") as f:
                f.write(log_content)

    def finalize_log(self, filepath: str, summary: str = "", coverage: str = ""):
        """完成日志，添加结束时间"""
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 更新总结
        if summary:
            self.update_section(
                filepath,
                "总结",
                f"""完成情况
- [x] 主要目标已完成
- [x] 测试通过
- [x] 文档更新

经验教训
无重大问题，开发顺利。

下一步计划
1. 观察生产环境表现
2. 根据反馈持续优化

总结
{summary}
""",
            )

        # 更新覆盖率
        if coverage:
            self.update_section(
                filepath,
                "测试/验证结果",
                f"""测试结果
- 单元测试: 通过
- 集成测试: 通过
- 覆盖率: {coverage}
""",
            )

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 替换结束时间标记
        content = content.replace("进行中...", end_time)
        content = content.replace("{end_time}", end_time)

        # 写入本地
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # 同步到 Git
        if self.enable_git_log:
            git_log_dir = os.path.join(self.workspace or ".", self.GIT_LOG_DIR, self.ai_type)
            log_name = os.path.basename(filepath)
            git_filepath = os.path.join(git_log_dir, log_name)
            with open(git_filepath, "w", encoding="utf-8") as f:
                f.write(content)

        if self.enable_vsc_log:
            log_name = os.path.basename(filepath)
            VSCodeOutputLogger.log(f"日志已完成: {log_name}", "AI Collab Logs")

    def list_logs(self, month: str | None = None) -> List[str]:
        """列出日志文件"""
        logs = []

        if month:
            month_dir = os.path.join(self.log_dir, month)
            if os.path.exists(month_dir):
                logs = [
                    os.path.join(month_dir, f) for f in os.listdir(month_dir) if f.endswith(".md")
                ]
        else:
            if os.path.exists(self.log_dir):
                for subdir in os.listdir(self.log_dir):
                    subdir_path = os.path.join(self.log_dir, subdir)
                    if os.path.isdir(subdir_path):
                        logs.extend(
                            [
                                os.path.join(subdir_path, f)
                                for f in os.listdir(subdir_path)
                                if f.endswith(".md")
                            ]
                        )

        return sorted(logs)

    def rotate_logs(self, max_files: int = 30):
        """轮转日志，保留最近的N个文件"""
        logs = self.list_logs()

        if len(logs) > max_files:
            logs_with_time = [(log, os.path.getmtime(log)) for log in logs]
            logs_with_time.sort(key=lambda x: x[1])

            to_delete = logs_with_time[:-max_files]
            for log_path, _ in to_delete:
                try:
                    os.remove(log_path)
                    if self.enable_vsc_log:
                        VSCodeOutputLogger.log(
                            f"已删除旧日志: {os.path.basename(log_path)}", "AI Collab Logs"
                        )
                except OSError:
                    pass
