"""
配置管理模块测试

测试配置加载、验证和访问功能
"""

import sys
from pathlib import Path

# 添加 local-backend 目录到 Python 路径
project_root = Path(__file__).resolve().parents[2]
backend_path = project_root / "local-backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.core.config import (
    Settings,
    get_cors_origins,
    get_database_url,
    get_max_request_size,
    get_settings,
    is_debug_mode,
    reload_settings,
)


class TestSettings:
    """测试 Settings 配置类"""

    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()

        # 基础配置
        assert settings.app_name == "Prompt Pack API"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False

        # 安全配置
        assert settings.max_request_body_size == 10 * 1024 * 1024
        assert "http://localhost:*" in settings.cors_origins
        assert settings.token_expiry_hours == 24

        # 数据库配置
        assert "sqlite" in settings.database_url
        assert settings.database_echo is False

        # 日志配置
        assert settings.log_level == "INFO"

        # API 配置
        assert settings.api_prefix == "/api"
        assert settings.docs_enabled is True

        # 性能配置
        assert settings.cache_ttl == 300
        assert settings.cache_backend == "memory"
        assert settings.cache_max_size == 1000

    def test_debug_validator_with_bool(self):
        """测试 debug 字段验证器 - 布尔值"""
        settings = Settings(debug=True)
        assert settings.debug is True

        settings = Settings(debug=False)
        assert settings.debug is False

    def test_debug_validator_with_string_true(self):
        """测试 debug 字段验证器 - 字符串 true"""
        for value in ["true", "True", "TRUE", "1", "yes", "on", "debug", "dev"]:
            settings = Settings(debug=value)
            assert settings.debug is True, f"Failed for value: {value}"

    def test_debug_validator_with_string_false(self):
        """测试 debug 字段验证器 - 字符串 false"""
        for value in [
            "false",
            "False",
            "FALSE",
            "0",
            "no",
            "off",
            "release",
            "prod",
            "production",
            "",
        ]:
            settings = Settings(debug=value)
            assert settings.debug is False, f"Failed for value: {value}"

    def test_custom_settings(self):
        """测试自定义配置"""
        settings = Settings(app_name="Custom App", debug=True, log_level="DEBUG", cache_ttl=600)

        assert settings.app_name == "Custom App"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.cache_ttl == 600

    def test_cache_backend_options(self):
        """测试缓存后端选项"""
        # Memory backend
        settings = Settings(cache_backend="memory")
        assert settings.cache_backend == "memory"

        # Redis backend
        settings = Settings(cache_backend="redis")
        assert settings.cache_backend == "redis"

        # Auto backend
        settings = Settings(cache_backend="auto")
        assert settings.cache_backend == "auto"

    def test_redis_configuration(self):
        """测试 Redis 配置"""
        settings = Settings(
            redis_url="redis://localhost:6379/1",
            redis_key_prefix="test:",
            redis_socket_timeout=0.5,
            redis_connect_timeout=0.5,
        )

        assert settings.redis_url == "redis://localhost:6379/1"
        assert settings.redis_key_prefix == "test:"
        assert settings.redis_socket_timeout == 0.5
        assert settings.redis_connect_timeout == 0.5


class TestGlobalSettings:
    """测试全局配置实例"""

    def test_get_settings_returns_singleton(self):
        """测试 get_settings 返回单例"""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings_creates_new_instance(self):
        """测试 reload_settings 创建新实例"""
        settings1 = get_settings()
        settings2 = reload_settings()

        # 重新加载后应该是新实例
        assert settings1 is not settings2

        # 但再次获取应该返回新实例
        settings3 = get_settings()
        assert settings2 is settings3


class TestConvenienceFunctions:
    """测试便捷访问函数"""

    def test_get_cors_origins(self):
        """测试获取 CORS 来源"""
        origins = get_cors_origins()

        assert isinstance(origins, list)
        assert len(origins) > 0
        assert "http://localhost:*" in origins

    def test_get_max_request_size(self):
        """测试获取最大请求大小"""
        max_size = get_max_request_size()

        assert isinstance(max_size, int)
        assert max_size > 0
        assert max_size == 10 * 1024 * 1024

    def test_is_debug_mode(self):
        """测试调试模式检查"""
        # 默认应该是 False
        reload_settings()
        assert is_debug_mode() is False

    def test_get_database_url(self):
        """测试获取数据库 URL"""
        db_url = get_database_url()

        assert isinstance(db_url, str)
        assert len(db_url) > 0
        assert "sqlite" in db_url


class TestEnvironmentVariables:
    """测试环境变量覆盖"""

    def test_env_override_debug(self, monkeypatch):
        """测试环境变量覆盖 debug"""
        monkeypatch.setenv("DEBUG", "true")
        settings = reload_settings()

        assert settings.debug is True

    def test_env_override_log_level(self, monkeypatch):
        """测试环境变量覆盖日志级别"""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = reload_settings()

        assert settings.log_level == "DEBUG"

    def test_env_override_cache_ttl(self, monkeypatch):
        """测试环境变量覆盖缓存 TTL"""
        monkeypatch.setenv("CACHE_TTL", "600")
        settings = reload_settings()

        assert settings.cache_ttl == 600

    def test_env_override_database_url(self, monkeypatch):
        """测试环境变量覆盖数据库 URL"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        settings = reload_settings()

        assert settings.database_url == "sqlite:///./test.db"


class TestSecuritySettings:
    """测试安全相关配置"""

    def test_security_headers_enabled_by_default(self):
        """测试默认启用安全头"""
        settings = Settings()
        assert settings.enable_security_headers is True

    def test_hsts_max_age_default(self):
        """测试 HSTS 最大年龄默认值"""
        settings = Settings()
        assert settings.hsts_max_age == 31536000  # 1 year

    def test_token_expiry_default(self):
        """测试 Token 过期时间默认值"""
        settings = Settings()
        assert settings.token_expiry_hours == 24

    def test_max_request_body_size_reasonable(self):
        """测试最大请求体大小合理"""
        settings = Settings()

        # 应该大于 1MB
        assert settings.max_request_body_size >= 1 * 1024 * 1024
        # 应该小于 100MB
        assert settings.max_request_body_size <= 100 * 1024 * 1024


class TestPerformanceSettings:
    """测试性能相关配置"""

    def test_cache_settings_reasonable(self):
        """测试缓存设置合理"""
        settings = Settings()

        # TTL 应该在合理范围
        assert 60 <= settings.cache_ttl <= 3600

        # 最大缓存条目应该合理
        assert 100 <= settings.cache_max_size <= 10000

    def test_connection_settings(self):
        """测试连接设置"""
        settings = Settings()

        # 最大连接数应该合理
        assert 10 <= settings.max_connections <= 1000

        # Redis 超时应该合理
        assert 0.1 <= settings.redis_socket_timeout <= 5.0
        assert 0.1 <= settings.redis_connect_timeout <= 5.0


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_cors_origins(self):
        """测试空 CORS 来源列表"""
        settings = Settings(cors_origins=[])
        assert settings.cors_origins == []

    def test_multiple_cors_origins(self):
        """测试多个 CORS 来源"""
        origins = ["http://localhost:3000", "http://localhost:8080", "https://example.com"]
        settings = Settings(cors_origins=origins)

        assert len(settings.cors_origins) == 3
        assert "http://localhost:3000" in settings.cors_origins

    def test_custom_redis_url(self):
        """测试自定义 Redis URL"""
        custom_url = "redis://user:password@host:6379/2"
        settings = Settings(redis_url=custom_url)

        assert settings.redis_url == custom_url

    def test_zero_cache_ttl(self):
        """测试零缓存 TTL"""
        settings = Settings(cache_ttl=0)
        assert settings.cache_ttl == 0

    def test_very_large_max_request_size(self):
        """测试非常大的最大请求大小"""
        large_size = 1000 * 1024 * 1024  # 1GB
        settings = Settings(max_request_body_size=large_size)

        assert settings.max_request_body_size == large_size
