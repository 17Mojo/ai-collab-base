# 双向交接回通知机制
# src/ai_collab/handoff_notification.py

"""
双向交接回通知机制
支持 Claude Code 和 Copilot 之间的任务交接和回馈

工作流程:
1. Claude Code 完成任务 → 发送交接通知给 Copilot
2. Copilot 接收通知 → 处理任务 → 发送回馈通知给 Claude Code
3. Claude Code 接收回馈 → 确认完成

类比：接力赛中的交接棒 + 回报机制
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HandoffStatus(Enum):
    """交接状态"""

    PENDING = "pending"  # 待处理
    ACCEPTED = "accepted"  # 已接受
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    FEEDBACK_SENT = "feedback_sent"  # 回馈已发送
    CONFIRMED = "confirmed"  # 已确认


class HandoffType(Enum):
    """交接类型"""

    TASK_HANDOFF = "task_handoff"  # 任务交接
    CODE_REVIEW = "code_review"  # 代码审查
    RESEARCH_RESULT = "research_result"  # 研究结果
    CONFLICT_RESOLUTION = "conflict_resolution"  # 冲突解决


class HandoffNotification:
    """交接通知"""

    def __init__(
        self,
        handoff_id: str,
        from_ai: str,
        to_ai: str,
        handoff_type: str,
        title: str,
        description: str,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = HandoffStatus.PENDING.value,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.handoff_id = handoff_id
        self.from_ai = from_ai
        self.to_ai = to_ai
        self.handoff_type = handoff_type
        self.title = title
        self.description = description
        self.files = files or []
        self.metadata = metadata or {}
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "handoff_id": self.handoff_id,
            "from_ai": self.from_ai,
            "to_ai": self.to_ai,
            "handoff_type": self.handoff_type,
            "title": self.title,
            "description": self.description,
            "files": self.files,
            "metadata": self.metadata,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class HandoffManager:
    """交接管理器"""

    HANDOFF_DIR = "notifications/handoffs"

    def __init__(self):
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        import os

        os.makedirs(self.HANDOFF_DIR, exist_ok=True)

    def _get_handoff_file(self, handoff_id: str) -> str:
        """获取交接文件路径"""
        return f"{self.HANDOFF_DIR}/{handoff_id}.json"

    def create_handoff(
        self,
        from_ai: str,
        to_ai: str,
        handoff_type: str,
        title: str,
        description: str,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建交接通知"""
        handoff_id = f"HANDOFF-{int(datetime.now().timestamp())}"

        handoff = HandoffNotification(
            handoff_id=handoff_id,
            from_ai=from_ai,
            to_ai=to_ai,
            handoff_type=handoff_type,
            title=title,
            description=description,
            files=files,
            metadata=metadata,
        )

        # 保存交接文件
        handoff_file = self._get_handoff_file(handoff_id)
        with open(handoff_file, "w", encoding="utf-8") as f:
            json.dump(handoff.to_dict(), f, indent=2, ensure_ascii=False)

        # 同时写入目标AI的通知文件
        self._write_to_target(to_ai, handoff)

        print(f"[交接创建] {handoff_id}")
        print(f"  从: {from_ai} → 到: {to_ai}")
        print(f"  类型: {handoff_type}")
        print(f"  标题: {title}")

        return handoff_id

    def accept_handoff(self, handoff_id: str, by_ai: str) -> bool:
        """接受交接"""
        handoff = self._load_handoff(handoff_id)
        if not handoff:
            return False

        if handoff["to_ai"] != by_ai:
            print(f"[错误] {by_ai} 不是此交接的目标接收者")
            return False

        handoff["status"] = HandoffStatus.ACCEPTED.value
        handoff["updated_at"] = datetime.now().isoformat()

        self._save_handoff(handoff)
        print(f"[交接接受] {handoff_id} by {by_ai}")

        return True

    def complete_handoff(
        self, handoff_id: str, by_ai: str, feedback: str, result_files: Optional[List[str]] = None
    ) -> bool:
        """完成交接并发送回馈"""
        handoff = self._load_handoff(handoff_id)
        if not handoff:
            return False

        # 更新状态
        handoff["status"] = HandoffStatus.COMPLETED.value
        handoff["updated_at"] = datetime.now().isoformat()
        handoff["metadata"]["feedback"] = feedback
        if result_files:
            handoff["metadata"]["result_files"] = result_files

        self._save_handoff(handoff)

        # 发送回馈通知给原始发送者
        self._send_feedback(handoff, feedback, result_files)

        print(f"[交接完成] {handoff_id}")
        print(f"  回馈: {feedback}")

        return True

    def confirm_handoff(self, handoff_id: str, by_ai: str) -> bool:
        """确认交接完成"""
        handoff = self._load_handoff(handoff_id)
        if not handoff:
            return False

        if handoff["from_ai"] != by_ai:
            print(f"[错误] {by_ai} 不是此交接的原始发送者")
            return False

        handoff["status"] = HandoffStatus.CONFIRMED.value
        handoff["updated_at"] = datetime.now().isoformat()

        self._save_handoff(handoff)
        print(f"[交接确认] {handoff_id} by {by_ai}")

        return True

    def get_pending_handoffs(self, for_ai: str) -> List[Dict[str, Any]]:
        """获取待处理的交接"""
        import os

        handoffs = []

        for filename in os.listdir(self.HANDOFF_DIR):
            if filename.endswith(".json"):
                handoff_file = os.path.join(self.HANDOFF_DIR, filename)
                with open(handoff_file, "r", encoding="utf-8") as f:
                    handoff = json.load(f)

                if handoff["to_ai"] == for_ai and handoff["status"] in [
                    HandoffStatus.PENDING.value,
                    HandoffStatus.ACCEPTED.value,
                ]:
                    handoffs.append(handoff)

        return handoffs

    def _load_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """加载交接"""
        handoff_file = self._get_handoff_file(handoff_id)
        try:
            with open(handoff_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _save_handoff(self, handoff: Dict[str, Any]):
        """保存交接"""
        handoff_file = self._get_handoff_file(handoff["handoff_id"])
        with open(handoff_file, "w", encoding="utf-8") as f:
            json.dump(handoff, f, indent=2, ensure_ascii=False)

    def _write_to_target(self, target_ai: str, handoff: HandoffNotification):
        """写入目标AI的通知文件"""
        target_file = f"{self.HANDOFF_DIR}/{target_ai}_pending.json"

        # 加载现有通知
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {"pending_handoffs": []}

        # 添加新通知
        data["pending_handoffs"].append(
            {
                "handoff_id": handoff.handoff_id,
                "from_ai": handoff.from_ai,
                "title": handoff.title,
                "created_at": handoff.created_at,
            }
        )

        # 保存
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _send_feedback(
        self, handoff: Dict[str, Any], feedback: str, result_files: Optional[List[str]]
    ):
        """发送回馈通知"""
        from_ai = handoff["to_ai"]
        to_ai = handoff["from_ai"]

        feedback_id = f"FEEDBACK-{int(datetime.now().timestamp())}"

        feedback_data = {
            "feedback_id": feedback_id,
            "handoff_id": handoff["handoff_id"],
            "from_ai": from_ai,
            "to_ai": to_ai,
            "feedback": feedback,
            "result_files": result_files or [],
            "created_at": datetime.now().isoformat(),
        }

        # 写入回馈文件
        feedback_file = f"{self.HANDOFF_DIR}/{to_ai}_feedback.json"

        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_list = json.load(f)
        except (OSError, json.JSONDecodeError):
            feedback_list = {"feedbacks": []}

        feedback_list["feedbacks"].append(feedback_data)

        with open(feedback_file, "w", encoding="utf-8") as f:
            json.dump(feedback_list, f, indent=2, ensure_ascii=False)

        print(f"[回馈发送] {feedback_id}")
        print(f"  从: {from_ai} → 到: {to_ai}")


# ==================== 便捷函数 ====================

_handoff_manager = HandoffManager()


def create_handoff(
    from_ai: str,
    to_ai: str,
    handoff_type: str,
    title: str,
    description: str,
    files: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """创建交接通知"""
    return _handoff_manager.create_handoff(
        from_ai, to_ai, handoff_type, title, description, files, metadata
    )


def accept_handoff(handoff_id: str, by_ai: str) -> bool:
    """接受交接"""
    return _handoff_manager.accept_handoff(handoff_id, by_ai)


def complete_handoff(
    handoff_id: str, by_ai: str, feedback: str, result_files: Optional[List[str]] = None
) -> bool:
    """完成交接并发送回馈"""
    return _handoff_manager.complete_handoff(handoff_id, by_ai, feedback, result_files)


def confirm_handoff(handoff_id: str, by_ai: str) -> bool:
    """确认交接完成"""
    return _handoff_manager.confirm_handoff(handoff_id, by_ai)


def get_pending_handoffs(for_ai: str) -> List[Dict[str, Any]]:
    """获取待处理的交接"""
    return _handoff_manager.get_pending_handoffs(for_ai)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=== 双向交接回通知机制演示 ===\n")

    # 1. Claude Code 创建交接给 Copilot
    print("步骤1: Claude Code 创建交接")
    handoff_id = create_handoff(
        from_ai="claude_code",
        to_ai="copilot",
        handoff_type=HandoffType.RESEARCH_RESULT.value,
        title="网络调研结果交接",
        description="已完成API设计调研，请审查结果",
        files=["research/api_design.md"],
        metadata={"priority": "high"},
    )

    # 2. Copilot 接受交接
    print("\n步骤2: Copilot 接受交接")
    accept_handoff(handoff_id, "copilot")

    # 3. Copilot 完成交接并发送回馈
    print("\n步骤3: Copilot 完成交接并发送回馈")
    complete_handoff(
        handoff_id,
        "copilot",
        feedback="调研结果已审查，建议采用方案A",
        result_files=["research/api_design_review.md"],
    )

    # 4. Claude Code 确认交接
    print("\n步骤4: Claude Code 确认交接")
    confirm_handoff(handoff_id, "claude_code")

    print("\n=== 交接流程完成 ===")
