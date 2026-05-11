"""
集中式配置管理模块

统一管理应用配置，支持环境变量覆盖
"""

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    app_name: str = "Prompt Pack API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 安全配置
    max_request_body_size: int = Field(default=10 * 1024 * 1024, description="最大请求体大小（字节）")
    cors_origins: List[str] = Field(
        default=["http://localhost:*", "http://127.0.0.1:*"], description="允许的 CORS 来源"
    )
    token_expiry_hours: int = Field(default=24, description="Token 默认过期时间（小时）")

    # 数据库配置
    database_url: str = Field(default="sqlite:///./data/packs.db", description="数据库连接URL")
    database_echo: bool = Field(default=False, description="是否显示 SQL 查询")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # API 配置
    api_prefix: str = "/api"
    docs_enabled: bool = Field(default=True, description="是否启用 API 文档")

    # 安全头配置
    enable_security_headers: bool = Field(default=True, description="是否启用安全头")
    hsts_max_age: int = Field(default=31536000, description="HSTS 最大年龄（秒）")

    # 性能配置
    cache_ttl: int = Field(default=300, description="缓存 TTL（秒）")
    cache_backend: str = Field(default="memory", description="缓存后端: memory/redis/auto")
    cache_max_size: int = Field(default=1000, description="内存缓存最大条目数")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", description="Redis 连接 URL")
    redis_key_prefix: str = Field(default="prompt_pack:", description="Redis 键前缀")
    redis_socket_timeout: float = Field(default=0.2, description="Redis 读写超时（秒）")
    redis_connect_timeout: float = Field(default=0.2, description="Redis 连接超时（秒）")
    max_connections: int = Field(default=100, description="最大连接数")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """兼容 release/prod 等非标准布尔值。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production", ""}:
                return False
        return bool(value)


# 全局配置实例
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    获取全局配置实例

    Returns:
        Settings 实例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    重新加载配置

    Returns:
        新的 Settings 实例
    """
    global _settings
    _settings = Settings()
    return _settings


# 便捷访问函数
def get_cors_origins() -> List[str]:
    """获取 CORS 允许的来源"""
    return get_settings().cors_origins


def get_max_request_size() -> int:
    """获取最大请求大小"""
    return get_settings().max_request_body_size


def is_debug_mode() -> bool:
    """是否为调试模式"""
    return get_settings().debug


def get_database_url() -> str:
    """获取数据库 URL"""
    return get_settings().database_url


if __name__ == "__main__":
    # 测试配置加载
    settings = get_settings()
    print("📋 当前配置:")
    print(f"  应用名称: {settings.app_name}")
    print(f"  版本: {settings.app_version}")
    print(f"  调试模式: {settings.debug}")
    print(f"  最大请求大小: {settings.max_request_body_size // (1024*1024)}MB")
    print(f"  CORS 来源: {len(settings.cors_origins)} 个")
    print(f"  数据库 URL: {settings.database_url}")
    print(f"  日志级别: {settings.log_level}")
