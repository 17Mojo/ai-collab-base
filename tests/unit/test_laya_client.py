from unittest.mock import MagicMock

import pytest
import requests

from ai_collab.laya_client import (
    MODEL_MULTI,
    MODEL_TYPED,
    PREDICT_PATH,
    LayaClient,
    LayaConnectionError,
    LayaHTTPError,
    decide,
    detect_model,
)


def _mock_response(status_code: int, json_payload=None, text: str = "") -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    mock.json.return_value = json_payload if json_payload is not None else {}
    return mock


class TestDetectModel:
    def test_english_to_typed(self):
        assert detect_model("Hello world") == MODEL_TYPED

    def test_chinese_to_multilingual(self):
        assert detect_model("你好世界") == MODEL_MULTI

    def test_japanese_to_multilingual(self):
        assert detect_model("こんにちは") == MODEL_MULTI

    def test_korean_to_multilingual(self):
        assert detect_model("안녕하세요") == MODEL_MULTI

    def test_cyrillic_to_multilingual(self):
        assert detect_model("Привет") == MODEL_MULTI

    def test_arabic_to_multilingual(self):
        assert detect_model("مرحبا") == MODEL_MULTI

    def test_devanagari_to_multilingual(self):
        assert detect_model("नमस्ते") == MODEL_MULTI

    def test_dict_state_chinese(self):
        assert detect_model({"subject": "重复扣款", "body": "退款"}) == MODEL_MULTI

    def test_dict_state_english(self):
        assert detect_model({"from": "a@b.com", "subject": "help"}) == MODEL_TYPED

    def test_list_state_chinese(self):
        assert detect_model([{"role": "user", "content": "你好"}]) == MODEL_MULTI


class TestLayaClientPredict:
    def test_explicit_model_in_payload(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {
            "answers": {"dept": {"choice": "billing", "probs": {"billing": 0.9, "tech": 0.1}}},
            "latency_ms": 22,
            "model": "multilingual",
        }))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        result = LayaClient().predict(
            state="any",
            questions={"dept": {"type": "choice", "instructions": "?", "criteria": ["a", "b"]}},
            model="multilingual",
        )
        assert result["answers"]["dept"]["choice"] == "billing"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "multilingual"
        assert mock_post.call_args.args[0] == f"http://127.0.0.1:8421{PREDICT_PATH}"

    def test_auto_routes_chinese_to_multilingual(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 10}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        LayaClient().predict(
            state="你好世界",
            questions={"q": {"type": "noul", "instructions": "?"}},
        )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == MODEL_MULTI

    def test_auto_routes_english_to_typed(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 20}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        LayaClient().predict(
            state="Customer wants a refund",
            questions={"q": {"type": "noul", "instructions": "?"}},
        )
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == MODEL_TYPED

    def test_custom_base_url(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 1}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        LayaClient(base_url="http://example:9999/").predict(
            state="x", questions={"q": {"type": "noul", "instructions": "?"}}
        )
        assert mock_post.call_args.args[0] == f"http://example:9999{PREDICT_PATH}"

    def test_state_passed_through(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 1}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        state = {"from": "a@b.com", "subject": "help"}
        questions = {"dept": {"type": "choice", "instructions": "?", "criteria": ["x", "y"]}}
        LayaClient().predict(state=state, questions=questions)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["state"] == state
        assert payload["questions"] == questions


class TestLayaClientErrors:
    def test_connection_error_raises_laya_connection_error(self, monkeypatch):
        def raise_conn(*args, **kwargs):
            raise requests.ConnectionError("refused")
        monkeypatch.setattr("ai_collab.laya_client.requests.post", raise_conn)
        with pytest.raises(LayaConnectionError):
            LayaClient().predict(state="x", questions={})

    def test_timeout_raises_laya_connection_error(self, monkeypatch):
        def raise_timeout(*args, **kwargs):
            raise requests.Timeout("timed out")
        monkeypatch.setattr("ai_collab.laya_client.requests.post", raise_timeout)
        with pytest.raises(LayaConnectionError):
            LayaClient().predict(state="x", questions={})

    def test_http_500_raises_laya_http_error(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(500, text="internal error"))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        with pytest.raises(LayaHTTPError) as exc_info:
            LayaClient().predict(state="x", questions={})
        assert exc_info.value.status_code == 500
        assert "internal error" in exc_info.value.body

    def test_http_400_raises_laya_http_error(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(400, text="bad request"))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        with pytest.raises(LayaHTTPError):
            LayaClient().predict(state="x", questions={})


class TestLayaClientHealth:
    def test_health_true_on_2xx(self, monkeypatch):
        mock_get = MagicMock(return_value=_mock_response(200, {"openapi": "3.0.0"}))
        monkeypatch.setattr("ai_collab.laya_client.requests.get", mock_get)
        assert LayaClient().health() is True

    def test_health_true_on_404(self, monkeypatch):
        mock_get = MagicMock(return_value=_mock_response(404, text="not found"))
        monkeypatch.setattr("ai_collab.laya_client.requests.get", mock_get)
        assert LayaClient().health() is True

    def test_health_false_on_connection_error(self, monkeypatch):
        def raise_conn(*args, **kwargs):
            raise requests.ConnectionError()
        monkeypatch.setattr("ai_collab.laya_client.requests.get", raise_conn)
        assert LayaClient().health() is False

    def test_health_false_on_timeout(self, monkeypatch):
        def raise_timeout(*args, **kwargs):
            raise requests.Timeout()
        monkeypatch.setattr("ai_collab.laya_client.requests.get", raise_timeout)
        assert LayaClient().health() is False


class TestDecideFunction:
    def test_delegates_to_client(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {
            "answers": {"x": {"noul": 0.8}}, "latency_ms": 15,
        }))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        result = decide(state="hi", questions={"x": {"type": "noul", "instructions": "?"}})
        assert result["answers"]["x"]["noul"] == 0.8

    def test_explicit_model(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 1}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        decide(state="hi", questions={"x": {"type": "noul", "instructions": "?"}}, model=MODEL_TYPED)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == MODEL_TYPED

    def test_custom_base_url(self, monkeypatch):
        mock_post = MagicMock(return_value=_mock_response(200, {"answers": {}, "latency_ms": 1}))
        monkeypatch.setattr("ai_collab.laya_client.requests.post", mock_post)
        decide(
            state="x",
            questions={"q": {"type": "noul", "instructions": "?"}},
            base_url="http://example:9999",
        )
        assert mock_post.call_args.args[0] == f"http://example:9999{PREDICT_PATH}"

    def test_propagates_connection_error(self, monkeypatch):
        def raise_conn(*args, **kwargs):
            raise requests.ConnectionError()
        monkeypatch.setattr("ai_collab.laya_client.requests.post", raise_conn)
        with pytest.raises(LayaConnectionError):
            decide(state="x", questions={"q": {"type": "noul", "instructions": "?"}})
