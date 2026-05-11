# AI platform adapter base interfaces.

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAIAdapter(ABC):
    """Base interface for AI platform adapters."""

    def __init__(self, platform_name: str, config: Optional[Dict[str, Any]] = None):
        self.platform_name = platform_name
        self.config = config or {}
        self.is_connected = False
        self.session_id: Optional[str] = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to platform."""

    @abstractmethod
    def send_message(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a message to platform."""

    @abstractmethod
    def receive_message(self, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Receive a message from platform."""

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from platform."""

    def get_platform_info(self) -> Dict[str, Any]:
        return {
            "platform_name": self.platform_name,
            "is_connected": self.is_connected,
            "session_id": self.session_id,
            "config": self.config,
        }

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        print(f"[{self.platform_name}] {action}: {details or ''}")

    def __enter__(self) -> "BaseAIAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()


class AIAdapterError(Exception):
    """Base adapter exception."""


class ConnectionError(AIAdapterError):
    """Connection exception."""


class MessageError(AIAdapterError):
    """Message exception."""


class TimeoutError(AIAdapterError):
    """Timeout exception."""
