# @Mention 通知系统 - 代码实现
# src/ai_collab/notification.py

"""
@Mention 通知系统
支持三种模式：广播 / 广播+@提醒 / 直接沟通
类比：微信群聊的 @ 提醒机制
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class NotificationMode:
    """通知模式"""

    BROADCAST = "broadcast"  # 广播：所有人可见
    BROADCAST_MENTION = "broadcast@mention"  # 广播+@提醒：所有人+重点提醒某人
    DIRECT = "direct"  # 直接沟通：只有被@的人可见


class Priority:
    """优先级"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification:
    """通知消息"""

    def __init__(
        self,
        content: str,
        mode: str = NotificationMode.BROADCAST,
        sender: str = "system",
        priority: str = Priority.NORMAL,
        mentions: Optional[List[str]] = None,
        direct_target: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        timestamp: Optional[str] = None,
        read_by: Optional[List[str]] = None,
    ):
        self.id = id or f"MSG-{int(datetime.now().timestamp())}"
        self.timestamp = timestamp or datetime.now().isoformat()
        self.content = content
        self.mode = mode
        self.sender = sender
        self.priority = priority
        self.mentions = mentions or []
        self.direct_target = direct_target
        self.metadata = metadata or {}
        self.read_by = read_by or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "content": self.content,
            "mode": self.mode,
            "sender": self.sender,
            "priority": self.priority,
            "mentions": self.mentions,
            "direct_target": self.direct_target,
            "metadata": self.metadata,
            "read_by": self.read_by,
        }


class NotificationQueue:
    """通知消息队列"""

    NOTIFICATION_DIR = "notifications"
    BROADCAST_TARGETS = ["claude_code", "copilot", "codex", "user"]

    def __init__(self):
        self.queue_file = f"{self.NOTIFICATION_DIR}/message_queue.json"
        self.history_file = f"{self.NOTIFICATION_DIR}/notification_history.json"
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        import os

        os.makedirs(self.NOTIFICATION_DIR, exist_ok=True)

    def _load_queue(self) -> List[Dict]:
        """加载消息队列"""
        try:
            with open(self.queue_file, "r") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (OSError, json.JSONDecodeError):
            return []

    def _save_queue(self, messages: List[Dict]):
        """保存消息队列"""
        with open(self.queue_file, "w") as f:
            json.dump({"queue_id": "QUEUE-20260226", "messages": messages}, f, indent=2)

    def emit(self, notification: Notification):
        """发送通知到队列"""
        messages = self._load_queue()
        messages.append(notification.to_dict())
        self._save_queue(messages)
        return notification.id

    def get_pending(self, target_ai: str) -> List[Notification]:
        """获取目标 AI 的待处理通知"""
        messages = self._load_queue()
        pending = []

        for msg in messages:
            # 检查是否是发给当前 AI 的
            target_ai_lower = target_ai.lower()

            # 模式1: 广播 - 所有人都收
            if msg["mode"] == NotificationMode.BROADCAST:
                if target_ai_lower in self.BROADCAST_TARGETS:
                    pending.append(Notification(**msg))

            # 模式2: 广播+@提醒 - 所有人都能看到，被@的特别提醒
            elif msg["mode"] == NotificationMode.BROADCAST_MENTION:
                # 所有人基础检查
                if target_ai_lower in self.BROADCAST_TARGETS:
                    pending.append(Notification(**msg))

            # 模式3: 直接沟通 - 只有被@的目标能看到
            elif msg["mode"] == NotificationMode.DIRECT:
                if msg.get("direct_target", "").lower() == target_ai_lower:
                    pending.append(Notification(**msg))

        return pending

    def mark_read(self, message_id: str, ai: str):
        """标记消息已读"""
        messages = self._load_queue()

        for i, msg in enumerate(messages):
            if msg["id"] == message_id:
                if ai not in msg["read_by"]:
                    msg["read_by"].append(ai)

                # 如果所有目标都已读，移到历史
                all_targets = self._get_target_list(msg["mode"], msg)
                if all(target in msg["read_by"] for target in all_targets):
                    messages.pop(i)
                    break

        self._save_queue(messages)

        # 同时保存到历史
        self._save_to_history(message_id, ai)

    def _get_target_list(self, mode: str, msg: Dict) -> List[str]:
        """获取消息的目标列表"""
        if mode == NotificationMode.BROADCAST:
            return self.BROADCAST_TARGETS
        elif mode == NotificationMode.BROADCAST_MENTION:
            return self.BROADCAST_TARGETS
        elif mode == NotificationMode.DIRECT:
            return [msg.get("direct_target", "")]
        return []

    def _save_to_history(self, message_id: str, ai: str):
        """保存到历史记录"""
        try:
            with open(self.history_file, "r") as f:
                history = json.load(f)
        except (OSError, json.JSONDecodeError):
            history = {"history": []}

        history["history"].append(
            {"message_id": message_id, "read_by": ai, "read_at": datetime.now().isoformat()}
        )

        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    def get_unread_count(self, ai: str) -> int:
        """获取未读消息数量"""
        pending = self.get_pending(ai)
        return len([p for p in pending if ai not in p.read_by])


# ==================== AI 通知 API ====================


class NotificationAPI:
    """通知 API - 提供给 Claude 和 Copilot 使用"""

    def __init__(self):
        self.queue = NotificationQueue()

    def broadcast(self, content: str, priority: str = Priority.NORMAL):
        """
        模式1: 广播 - 发消息给所有人
        对应微信群聊：发消息到群里
        """
        notification = Notification(
            content=content, mode=NotificationMode.BROADCAST, priority=priority
        )
        message_id = self.queue.emit(notification)
        for ai in self.queue.BROADCAST_TARGETS:
            self._write_to_target(ai, notification, message_id)
        return message_id

    def mention(self, mention_targets: List[str], content: str, priority: str = Priority.NORMAL):
        """
        模式2: 广播 + @提醒 - 重点提醒
        对应微信群聊：// @某某 看一下
        """
        notification = Notification(
            content=content,
            mode=NotificationMode.BROADCAST_MENTION,
            mentions=mention_targets,
            priority=priority,
        )
        message_id = self.queue.emit(notification)

        # 所有人都写一份，被@的标记为重要
        for ai in self.queue.BROADCAST_TARGETS:
            notification_copy = Notification(**notification.to_dict())
            self._write_to_target(ai, notification_copy, message_id)

        return message_id

    def direct(self, target_ai: str, content: str, priority: str = Priority.HIGH):
        """
        模式3: 直接沟通 - 只有目标能看到
        对应微信群聊：// @某某 私聊消息
        """
        notification = Notification(
            content=content,
            mode=NotificationMode.DIRECT,
            direct_target=target_ai,
            priority=priority,
        )
        message_id = self.queue.emit(notification)
        self._write_to_target(target_ai, notification, message_id)
        return message_id

    def _write_to_target(self, target_ai: str, notification: Notification, message_id: str):
        """将通知写入目标 AI 的文件"""
        target_file = f"{self.queue.NOTIFICATION_DIR}/{target_ai}_notification.json"

        # 通知数据
        notify_data = {
            "message_id": message_id,
            "notification": notification.to_dict(),
            "read": False,
            "received_at": datetime.now().isoformat(),
        }

        with open(target_file, "w") as f:
            json.dump(notify_data, f, indent=2)


# ==================== 便捷函数 ====================

# 全局通知实例
_notifier = NotificationAPI()


def broadcast(content: str, priority: str = "normal"):
    """广播消息"""
    return _notifier.broadcast(content, priority)


def mention(mentions: List[str], content: str, priority: str = "normal"):
    """@提醒某人"""
    return _notifier.mention(mentions, content, priority)


def direct(target: str, content: str, priority: str = "high"):
    """直接沟通"""
    return _notifier.direct(target, content, priority)


# ==================== 检测循环 ====================


class NotificationDetector:
    """通知检测器 - 定期检查新通知"""

    def __init__(self, ai_name: str):
        self.ai_name = ai_name
        self.queue = NotificationQueue()
        self.notification_file = f"{self.queue.NOTIFICATION_DIR}/{ai_name}_notification.json"

    def check(self):
        """检查并处理新通知"""
        pending = self.queue.get_pending(self.ai_name)
        unread = [p for p in pending if self.ai_name not in p.read_by]

        for notification in unread:
            print(f"[新通知] {notification.content}")

            # 处理通知
            self.handle_notification(notification)

            # 标记已读
            self.queue.mark_read(notification.id, self.ai_name)

        return len(unread)

    def handle_notification(self, notification: Notification):
        """处理通知的回调"""
        # 根据通知优先级决定处理方式
        if notification.priority in [Priority.URGENT, Priority.HIGH]:
            print(f"[⚠️ 高优先级通知] {notification.content}")
        elif notification.mode == NotificationMode.DIRECT:
            print(f"[🔒 私密消息] {notification.content}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 1. 广播 - 发消息给所有人
    print("=== 模式1: 广播 ===")
    broadcast("系统状态更新：网络调研完成", priority="high")

    # 2. 广播+@提醒 - @某人看
    print("\n=== 模式2: @提醒 ===")
    mention(["copilot"], "请处理研究结果", priority="normal")

    # 3. 直接沟通 - 私密信息
    print("\n=== 模式3: 直接沟通 ===")
    direct("claude_code", "私密：API配置信息", priority="high")

    print("\n=== 通知已发送，等待自动检测 ===")
