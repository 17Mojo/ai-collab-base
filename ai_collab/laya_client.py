"""Laya MLX API client: typed decision engine for choice/score/noul questions."""

from __future__ import annotations

import json
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8421"
DEFAULT_TIMEOUT = 5.0
MODEL_TYPED = "typed-decisions"
MODEL_MULTI = "multilingual"
PREDICT_PATH = "/predict"
HEALTH_PATH = "/openapi.json"


class LayaError(Exception):
    """Base Laya client error."""


class LayaConnectionError(LayaError):
    """Failed to reach the Laya server."""


class LayaHTTPError(LayaError):
    """Laya server returned a non-2xx response."""

    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"Laya returned HTTP {status_code}: {body[:200]}")
        self.status_code = status_code
        self.body = body


def _flatten_state(state: Any) -> str:
    if isinstance(state, str):
        return state
    try:
        return json.dumps(state, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(state)


def _needs_multilingual(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if (
            0x3040 <= cp <= 0x309F
            or 0x30A0 <= cp <= 0x30FF
            or 0x3400 <= cp <= 0x4DBF
            or 0x4E00 <= cp <= 0x9FFF
            or 0xAC00 <= cp <= 0xD7AF
            or 0x0400 <= cp <= 0x04FF
            or 0x0600 <= cp <= 0x06FF
            or 0x0900 <= cp <= 0x097F
            or 0xF900 <= cp <= 0xFAFF
        ):
            return True
    return False


def detect_model(state: Any) -> str:
    """Auto-route by script: CJK/Cyrillic/Arabic/Devanagari → multilingual; else typed-decisions."""
    text = _flatten_state(state)
    return MODEL_MULTI if _needs_multilingual(text) else MODEL_TYPED


class LayaClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LayaConnectionError(f"Laya request failed: {exc}") from exc
        if response.status_code >= 400:
            raise LayaHTTPError(response.status_code, response.text)
        return response.json()

    def predict(
        self,
        state: Any,
        questions: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Send state + typed questions; Laya returns calibrated answers in a single forward pass."""
        chosen = model or detect_model(state)
        payload = {"state": state, "questions": questions, "model": chosen}
        return self._post(PREDICT_PATH, payload)

    def decide(
        self,
        state: Any,
        questions: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Alias for predict(); mirrors the convenience name from the Laya docs."""
        return self.predict(state, questions, model)

    def health(self) -> bool:
        """Return True if the Laya server is reachable (any response < 500 counts as up)."""
        try:
            response = requests.get(
                f"{self.base_url}{HEALTH_PATH}",
                timeout=min(2.0, self.timeout),
            )
            return response.status_code < 500
        except requests.RequestException:
            return False


def decide(
    state: Any,
    questions: dict[str, Any],
    model: str | None = None,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Module-level convenience: call Laya with default config and return its JSON response."""
    return LayaClient(base_url=base_url, timeout=timeout).decide(state, questions, model)
