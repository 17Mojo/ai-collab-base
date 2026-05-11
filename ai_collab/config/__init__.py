"""
AI Integration Configuration Module
Configuration for AI integration modes (mock/fallback/real)
"""

__all__ = ["IntegrationMode", "get_mode", "is_mock_mode", "should_use_fallback"]

from .integration_flags import IntegrationMode, get_mode, is_mock_mode, should_use_fallback
