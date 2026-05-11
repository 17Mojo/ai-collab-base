"""
AI Integration Feature Flags
Control AI integration modes (mock/fallback/real) with environment variable support
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Dict


class IntegrationMode(str, Enum):
    """Integration Mode Enum"""

    MOCK = "mock"  # Mock only (test environment)
    FALLBACK = "fallback"  # Try real, fallback to mock (production default)
    REAL = "real"  # Real only (production with strict mode)


# Default configuration (can be overridden by environment variables)
DEFAULT_INTEGRATION_MODES: Dict[str, IntegrationMode] = {
    "notebooklm": IntegrationMode.FALLBACK,
    "consensus_engine": IntegrationMode.FALLBACK,
    "soul_injection": IntegrationMode.FALLBACK,
    "codex": IntegrationMode.REAL,  # Already has real implementation
}


def _get_env_mode(module_name: str) -> IntegrationMode | None:
    """
    Get mode from environment variable

    Priority:
    1. AI_INTEGRATION_MODE_<MODULE>=<mode> (per-module override)
    2. AI_INTEGRATION_MODE=<mode> (global override)
    3. None (use default)

    Args:
        module_name: Name of the integration module

    Returns:
        IntegrationMode if set in environment, None otherwise
    """
    # Check per-module override first
    per_module_key = f"AI_INTEGRATION_MODE_{module_name.upper()}"
    per_module_value = os.getenv(per_module_key)
    if per_module_value:
        try:
            return IntegrationMode(per_module_value)
        except ValueError as e:
            raise ValueError(
                f"Invalid {per_module_key} value: '{per_module_value}'. "
                f"Valid values: {[m.value for m in IntegrationMode]}"
            ) from e

    # Check global override
    global_value = os.getenv("AI_INTEGRATION_MODE")
    if global_value:
        try:
            return IntegrationMode(global_value)
        except ValueError as e:
            raise ValueError(
                f"Invalid AI_INTEGRATION_MODE value: '{global_value}'. "
                f"Valid values: {[m.value for m in IntegrationMode]}"
            ) from e

    return None


def get_mode(module_name: str) -> IntegrationMode:
    """
    Get current mode for a specific integration module

    Args:
        module_name: Name of the integration module (e.g., 'notebooklm', 'consensus_engine')

    Returns:
        Current IntegrationMode for the module

    Raises:
        ValueError: If module_name is not configured
    """
    # Check environment variable overrides
    env_mode = _get_env_mode(module_name)
    if env_mode:
        return env_mode

    # Use default configuration
    if module_name not in DEFAULT_INTEGRATION_MODES:
        raise ValueError(
            f"Unknown integration module: '{module_name}'. "
            f"Configured modules: {list(DEFAULT_INTEGRATION_MODES.keys())}"
        )

    return DEFAULT_INTEGRATION_MODES[module_name]


def is_mock_mode(module_name: str) -> bool:
    """
    Check if a module is in mock mode

    Args:
        module_name: Name of the integration module

    Returns:
        True if mode is MOCK, False otherwise
    """
    return get_mode(module_name) == IntegrationMode.MOCK


def should_use_fallback(module_name: str) -> bool:
    """
    Check if a module should use fallback behavior

    Args:
        module_name: Name of the integration module

    Returns:
        True for MOCK or FALLBACK modes, False for REAL mode
    """
    mode = get_mode(module_name)
    return mode in (IntegrationMode.MOCK, IntegrationMode.FALLBACK)
