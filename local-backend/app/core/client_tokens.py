"""
客户端 Token 管理

支持双端分发模式的安全认证:
- 为可信客户端生成访问令牌
- 验证令牌有效性
- 管理令牌生命周期
"""

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ClientToken:
    """客户端令牌信息"""

    token: str
    client_name: str
    created_at: str
    expires_at: Optional[str] = None
    permissions: list = None
    is_active: bool = True

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

    def to_dict(self) -> dict:
        return asdict(self)

    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now()


class TokenNotFoundError(Exception):
    """令牌不存在异常"""

    pass


class InvalidTokenError(Exception):
    """无效令牌异常"""

    pass


class ExpiredTokenError(Exception):
    """过期令牌异常"""

    pass


class TokenManager:
    """
    令牌管理器

    管理 API 客户端的访问令牌
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化令牌管理器

        Args:
            storage_path: 令牌存储文件路径,默认为 data/client_tokens.json
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # 默认存储在项目的 data 目录
            base_path = Path(__file__).resolve().parent.parent.parent
            self.storage_path = base_path / "data" / "client_tokens.json"

        self.tokens: Dict[str, ClientToken] = {}
        self._load_from_storage()

    def _load_from_storage(self):
        """从存储文件加载令牌"""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建默认的存储文件
            default_data = {
                "tokens": {},
                "version": "1.0.0",
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "description": "客户端 Token 存储文件",
                },
            }
            self.storage_path.write_text(
                json.dumps(default_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return

        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            tokens_data = data.get("tokens", {})

            for token_str, token_data in tokens_data.items():
                if token_data.get("is_active", False):
                    self.tokens[token_str] = ClientToken(**token_data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to load tokens: {e}")
            self.tokens = {}

    def _save_to_storage(self):
        """保存令牌到存储文件"""
        data = {
            "tokens": {token: token_data.to_dict() for token, token_data in self.tokens.items()},
            "version": "1.0.0",
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_tokens": len(self.tokens),
                "active_tokens": len([t for t in self.tokens.values() if t.is_active]),
            },
        }

        self.storage_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def generate_token(
        self,
        client_name: str,
        permissions: Optional[list] = None,
        expires_hours: Optional[int] = None,
    ) -> str:
        """
        生成新的客户端令牌

        Args:
            client_name: 客户端名称
            permissions: 权限列表
            expires_hours: 过期小时数,None 表示永不过期

        Returns:
            生成的令牌字符串
        """
        # 生成随机令牌 (32字节十六进制)
        token = secrets.token_hex(32)

        # 计算过期时间
        expires_at = None
        if expires_hours:
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

        # 创建令牌对象
        client_token = ClientToken(
            token=token,
            client_name=client_name,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            permissions=permissions or [],
            is_active=True,
        )

        # 存储令牌
        self.tokens[token] = client_token
        self._save_to_storage()

        return token

    def verify(self, token: str) -> ClientToken:
        """
        验证令牌

        Args:
            token: 待验证的令牌

        Returns:
            令牌对象

        Raises:
            InvalidTokenError: 令牌无效
            ExpiredTokenError: 令牌过期
            TokenNotFoundError: 令牌不存在
        """
        if token not in self.tokens:
            raise TokenNotFoundError("Token not found")

        client_token = self.tokens[token]

        if not client_token.is_active:
            raise InvalidTokenError("Token is disabled")

        if client_token.is_expired():
            raise ExpiredTokenError("Token has expired")

        return client_token

    def revoke(self, token: str) -> bool:
        """
        撤销令牌

        Args:
            token: 要撤销的令牌

        Returns:
            是否成功撤销
        """
        if token not in self.tokens:
            return False

        self.tokens[token].is_active = False
        self._save_to_storage()
        return True

    def list_tokens(self, include_inactive: bool = False) -> list:
        """
        列出所有令牌

        Args:
            include_inactive: 是否包含已撤销的令牌

        Returns:
            令牌列表
        """
        tokens = []
        for token, client_token in self.tokens.items():
            if include_inactive or client_token.is_active:
                tokens.append(
                    {
                        "token": token[:8] + "...",  # 只显示前8位
                        "client_name": client_token.client_name,
                        "created_at": client_token.created_at,
                        "expires_at": client_token.expires_at,
                        "is_active": client_token.is_active,
                        "permissions": client_token.permissions,
                    }
                )
        return tokens

    def cleanup_expired_tokens(self) -> int:
        """
        清理过期的令牌

        Returns:
            清理的令牌数量
        """
        expired_count = 0
        tokens_to_remove = []

        for token, client_token in self.tokens.items():
            if client_token.is_expired():
                tokens_to_remove.append(token)
                expired_count += 1

        for token in tokens_to_remove:
            del self.tokens[token]

        if expired_count > 0:
            self._save_to_storage()

        return expired_count


# ==================== 全局实例 ====================

# 单例模式的令牌管理器
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """
    获取全局令牌管理器实例

    Returns:
        TokenManager 实例
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def verify_client_token(token: str) -> bool:
    """
    验证客户端令牌 (便捷函数)

    Args:
        token: 待验证的令牌

    Returns:
        是否有效
    """
    try:
        manager = get_token_manager()
        manager.verify(token)
        return True
    except (TokenNotFoundError, InvalidTokenError, ExpiredTokenError):
        return False


# ==================== CLI 命令 ====================


def create_initial_tokens():
    """
    创建初始令牌 (用于开发环境)

    令牌列表:
    1. chrome-extension: Chrome 扩展访问
    2. vscode-backend: VSCode 扩展后端访问
    3. admin: 管理员访问
    """
    manager = get_token_manager()

    # Chrome 扩展令牌 (永久有效期)
    chrome_token = manager.generate_token(
        client_name="chrome-extension",
        permissions=["read", "execute", "write_results"],
        expires_hours=None,
    )

    # VSCode 后端令牌 (永久有效期)
    vscode_token = manager.generate_token(
        client_name="vscode-backend", permissions=["read", "write", "admin"], expires_hours=None
    )

    # 管理员令牌 (永久有效期)
    admin_token = manager.generate_token(
        client_name="admin", permissions=["*"], expires_hours=None  # 所有权限
    )

    print("初始令牌已创建:")
    print(f"Chrome 扩展: {chrome_token}")
    print(f"VSCode 后端: {vscode_token}")
    print(f"管理员: {admin_token}")
    print(f"\n令牌已保存至: {manager.storage_path}")


if __name__ == "__main__":
    # 当直接运行此模块时,创建初始令牌
    print("创建初始客户端令牌...")
    create_initial_tokens()
