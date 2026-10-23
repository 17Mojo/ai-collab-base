"""CodeArts 投递桥接脚本的单元测试。

守护三件事：
1. 正文抽取（Exact Forward Message / Pull Snapshot）优先级正确；
2. 凭据解析在拿不到密码时**明确失败**，不静默降级、不假装投递成功；
3. `.vscode/ai-collab.json` 里的 `bridgeCommand` 是合法的 Python format 模板
   ——适配器用 `command.format(...)` 渲染，多一个花括号就会 KeyError。
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "codearts_bridge_deliver.py"
VSCODE_CONFIG = REPO_ROOT / ".vscode" / "ai-collab.json"


def _load_bridge() -> ModuleType:
    spec = importlib.util.spec_from_file_location("codearts_bridge_deliver", BRIDGE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge = _load_bridge()


# ---------------------------------------------------------------------------
# 正文抽取
# ---------------------------------------------------------------------------


def _write_event(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_extract_message_prefers_exact_forward_message(tmp_path: Path):
    artifact = _write_event(
        tmp_path / "artifact.md",
        "## Exact Forward Message\n\n```text\n精确指令\n```\n",
    )
    event = _write_event(
        tmp_path / "event.md",
        "## Pull Snapshot\n\n```text\n快照内容\n```\n",
    )

    message = bridge.extract_message(event_file=event, artifact_file=artifact)

    assert message == "精确指令"


def test_extract_message_falls_back_to_pull_snapshot(tmp_path: Path):
    event = _write_event(
        tmp_path / "event.md",
        "## Pull Snapshot\n\n```text\n快照内容\n```\n",
    )

    message = bridge.extract_message(event_file=event, artifact_file=None)

    assert message == "快照内容"


def test_extract_message_raises_when_no_artifact(tmp_path: Path):
    with pytest.raises(bridge.BridgeError):
        bridge.extract_message(
            event_file=tmp_path / "missing.md", artifact_file=tmp_path / "missing2.md"
        )


# ---------------------------------------------------------------------------
# 凭据
# ---------------------------------------------------------------------------


def test_resolve_credentials_prefers_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENCODE_SERVER_PASSWORD", "from-env")
    monkeypatch.setenv("OPENCODE_SERVER_USERNAME", "codearts")

    username, password = bridge.resolve_credentials()

    assert (username, password) == ("codearts", "from-env")


def test_resolve_credentials_reads_credential_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    # 用户名也必须从环境里清掉：`resolve_credentials()` 让**环境变量优先于
    # 凭据文件**（密码、用户名都是这个优先级，见 resolve_credentials 实现）。
    # 以前只清了密码变量，于是这个用例的成败取决于跑测试的进程环境里有没有
    # `OPENCODE_SERVER_USERNAME`：
    #   - 开发者 shell 里通常没有 → 用例通过；
    #   - CodeArts 会话由 kernel 进程派生，继承了 kernel 的环境（有该变量）
    #     → 用户名变成 "codearts"（DEFAULT_USERNAME 同形，更难看出是环境问题），
    #     用例失败，断言变成 ('codearts', 'from-file') != ('who', 'from-file')。
    # 也就是说：这条用例在**桥接真正运行的场景下反而是红的**。
    monkeypatch.delenv("OPENCODE_SERVER_USERNAME", raising=False)
    credential_file = tmp_path / "kernel-bridge.env"
    credential_file.write_text(
        'OPENCODE_SERVER_PASSWORD="from-file"\n# comment\nOPENCODE_SERVER_USERNAME=who\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", credential_file)

    username, password = bridge.resolve_credentials()

    assert (username, password) == ("who", "from-file")


def test_resolve_credentials_fails_loudly_without_password(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", tmp_path / "absent.env")

    with pytest.raises(bridge.BridgeError) as excinfo:
        bridge.resolve_credentials()

    assert "OPENCODE_SERVER_PASSWORD" in str(excinfo.value)


# ---------------------------------------------------------------------------
# kernel 定位
# ---------------------------------------------------------------------------


def test_discover_kernel_prefers_alive_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    alive = tmp_path / "Vscode_alive" / "server_config.properties"
    dead = tmp_path / "Vscode_dead" / "server_config.properties"
    alive.parent.mkdir(parents=True)
    dead.parent.mkdir(parents=True)
    alive.write_text(f"pid={os.getpid()}\nport=14934\n", encoding="utf-8")
    dead.write_text("pid=999999\nport=1\n", encoding="utf-8")
    # 让 dead 的 mtime 更新，验证"存活优先"而不是"最新优先"
    os.utime(dead, (2_000_000_000, 2_000_000_000))
    monkeypatch.setattr(bridge, "KERNEL_CONFIG_ROOT", tmp_path)

    host, port, pid = bridge._discover_kernel()

    assert host == "127.0.0.1"
    assert port == 14934
    assert pid == os.getpid()


def test_discover_kernel_raises_without_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr(bridge, "KERNEL_CONFIG_ROOT", tmp_path / "absent")

    with pytest.raises(bridge.BridgeError):
        bridge._discover_kernel()


# ---------------------------------------------------------------------------
# HTTP 请求形状
# ---------------------------------------------------------------------------


def test_send_message_uses_expected_path_and_body(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["auth"] = request.get_header("Authorization")
        return _Response()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    client.send_message(
        session_id="ses_abc",
        workspace=Path("/tmp/ws"),
        message="你好",
        agent="build",
    )

    url = str(captured["url"])
    assert url.startswith("http://127.0.0.1:14934/session/ses_abc/message?")
    assert "directory=" in url
    body = captured["body"]
    assert body["parts"] == [{"type": "text", "text": "你好"}]
    assert body["agent"] == "build"
    assert str(captured["auth"]).startswith("Basic ")


def test_send_message_reports_http_error(monkeypatch: pytest.MonkeyPatch):
    def _fake_urlopen(request, timeout=None):
        raise bridge.urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, None
        )

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    with pytest.raises(bridge.BridgeError) as excinfo:
        client.send_message(
            session_id="ses_abc", workspace=Path("/tmp/ws"), message="x", agent="build"
        )

    assert "401" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 投递通道
# ---------------------------------------------------------------------------


class _FakeKernel:
    def __init__(self) -> None:
        self.created: dict[str, object] = {}
        self.fired: dict[str, object] = {}

    def register_project_path(self, workspace: Path):
        return {"projectPath": str(workspace)}

    def create_cron_task(self, *, workspace: Path, prompt: str, cron: str):
        self.created = {"workspace": str(workspace), "prompt": prompt, "cron": cron}
        return {"results": [{"success": True, "taskId": "task-1"}]}

    def fire_cron_task(self, *, workspace: Path, task_ids: list[str]):
        self.fired = {"task_ids": task_ids}
        return {"results": [{"success": True}], "firedCount": 1}


def test_deliver_via_cron_creates_and_fires():
    kernel = _FakeKernel()

    result = bridge.deliver_via_cron(
        kernel, workspace=Path("/tmp/ws"), message="派发内容"  # type: ignore[arg-type]
    )

    assert result["channel"] == "cron"
    assert result["task_id"] == "task-1"
    assert kernel.created["prompt"] == "派发内容"
    assert kernel.fired["task_ids"] == ["task-1"]


def test_deliver_via_cron_raises_when_create_fails():
    class _Failing(_FakeKernel):
        def create_cron_task(self, *, workspace: Path, prompt: str, cron: str):
            return {"results": [{"success": False, "message": "nope"}]}

    with pytest.raises(bridge.BridgeError):
        bridge.deliver_via_cron(
            _Failing(), workspace=Path("/tmp/ws"), message="x"  # type: ignore[arg-type]
        )


def test_next_minute_cron_has_five_fields():
    assert len(bridge._next_minute_cron().split()) == 5


# ---------------------------------------------------------------------------
# inbox 兜底
# ---------------------------------------------------------------------------


def test_write_inbox_copy_creates_audit_file(tmp_path: Path):
    relpath = bridge.write_inbox_copy(
        workspace=tmp_path,
        intervention_id="intervention-abc",
        message="投递正文",
        payload={"channel": "cron"},
    )

    target = tmp_path / relpath
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "投递正文" in text
    assert "intervention-abc" in text


# ---------------------------------------------------------------------------
# kernel 响应解析（序列化格式不统一）
# ---------------------------------------------------------------------------


def test_parse_kernel_payload_reads_standard_json():
    assert bridge.parse_kernel_payload('{"a": 1}') == {"a": 1}


def test_parse_kernel_payload_reads_python_literal():
    """kernel 的 /session 系列路由返回 Python 字面量格式（单引号），不是合法 JSON。"""
    payload = bridge.parse_kernel_payload("[{'id': 'ses_abc', 'title': 'x'}]")

    assert payload == [{"id": "ses_abc", "title": "x"}]


def test_parse_kernel_payload_returns_none_on_garbage():
    assert bridge.parse_kernel_payload("not a payload {") is None
    assert bridge.parse_kernel_payload("   ") is None


def test_request_keeps_full_list_instead_of_truncating(
    monkeypatch: pytest.MonkeyPatch,
):
    """非 JSON 的列表响应必须整体保留。

    原先截断到 2000 字符，会把会话列表砍到只剩第一条消息 —— 静默丢信息。
    """
    sessions = [{"id": f"ses_{i:04d}", "title": "t" * 40} for i in range(80)]
    body = repr(sessions)

    class _Response:
        status = 200

        def read(self) -> bytes:
            return body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        bridge.urllib.request, "urlopen", lambda request, timeout=None: _Response()
    )

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    payload = client.request("GET", "/session")

    raw = payload.get("raw")
    assert isinstance(raw, list)
    assert len(raw) == 80
    assert raw[0]["id"] == "ses_0000"


def test_list_sessions_parses_literal_list(monkeypatch: pytest.MonkeyPatch):
    """`list_sessions` 曾因 raw 是字符串而恒返回空 —— 会话快路径从未生效。"""
    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    monkeypatch.setattr(
        client,
        "request",
        lambda *args, **kwargs: {
            "raw": "[{'id': 'ses_abc', 'time': {'updated': 1}}]",
            "http_status": 200,
        },
    )

    sessions = client.list_sessions(Path("/tmp/ws"))

    assert len(sessions) == 1
    assert sessions[0]["id"] == "ses_abc"


# ---------------------------------------------------------------------------
# 入口行为
# ---------------------------------------------------------------------------


def test_main_returns_nonzero_when_credential_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", tmp_path / "absent.env")
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        [
            "--workspace",
            str(tmp_path),
            "--event-file",
            str(event),
            "--session-id",
            "ses_abc",
        ]
    )

    assert code == 2
    assert "失败" in capsys.readouterr().err


def test_main_dry_run_does_not_require_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        ["--workspace", str(tmp_path), "--event-file", str(event), "--dry-run"]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry-run"
    assert payload["message_length"] == 2


# ---------------------------------------------------------------------------
# 配置守卫：bridgeCommand 必须是合法 format 模板
# ---------------------------------------------------------------------------


def test_repo_bridge_command_is_a_valid_format_template():
    config = json.loads(VSCODE_CONFIG.read_text(encoding="utf-8"))
    command = config["sessionOrchestration"]["codeartsAdapter"]["bridgeCommand"]
    rendered = command.format(
        workspace="/tmp/ws",
        event_file="/tmp/event.md",
        artifact_file="/tmp/artifact.md",
        intervention_id="intervention-abc",
        session_id="codearts-agent-bridge",
        assignee="codearts_agent",
        reason_code="stale_payload",
        model="glm-5.3",
        channel="new_session",
    )
    assert "codearts_bridge_deliver.py" in rendered
    assert "/tmp/ws" in rendered
    assert "glm-5.3" in rendered


def test_repo_codearts_adapter_is_enabled():
    config = json.loads(VSCODE_CONFIG.read_text(encoding="utf-8"))
    assert config["sessionOrchestration"]["codeartsAdapter"]["enabled"] is True


# ---------------------------------------------------------------------------
# 模型钉死（--model）
#
# kernel 的 cron 路由自己决定模型，调用方无法干预 —— 要钉死模型只能
# 自建会话 + 消息体带 model。回执里的 info.modelID 是**实际**用掉的模型，
# 用它来防"静默回落"。
# ---------------------------------------------------------------------------


def test_repo_codearts_adapter_declares_model_pool():
    adapter = json.loads(VSCODE_CONFIG.read_text(encoding="utf-8"))[
        "sessionOrchestration"
    ]["codeartsAdapter"]
    models = adapter.get("models") or []
    assert {"glm-5.3", "deepseek-v4.1-flash", "kimi-k3"} <= set(models)
    assert "{model}" in adapter["bridgeCommand"]
    assert "{channel}" in adapter["bridgeCommand"]


def test_send_message_body_carries_model(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    client.send_message(
        session_id="ses_abc",
        workspace=Path("/tmp/ws"),
        message="你好",
        agent="build",
        model={"providerID": "inferhub-provider", "modelID": "glm-5.3"},
    )

    body = captured["body"]
    assert body["model"] == {"providerID": "inferhub-provider", "modelID": "glm-5.3"}
    assert body["agent"] == "build"


def test_send_message_body_omits_model_when_not_given(
    monkeypatch: pytest.MonkeyPatch,
):
    """不钉模型时**不要**发 model 字段 —— 保持 kernel 默认行为不变。"""
    captured: dict[str, object] = {}

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        bridge.urllib.request,
        "urlopen",
        lambda request, timeout=None: (
            captured.setdefault("body", json.loads(request.data.decode("utf-8"))),
            _Response(),
        )[1],
    )

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    client.send_message(
        session_id="ses_abc", workspace=Path("/tmp/ws"), message="x", agent="build"
    )

    assert "model" not in captured["body"]


def test_create_session_returns_session_id(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"id":"ses_new1","title":"t"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    session_id = client.create_session(workspace=Path("/tmp/ws"), title="派单")

    assert session_id == "ses_new1"
    assert str(captured["url"]).startswith("http://127.0.0.1:14934/session?")
    assert "directory=" in str(captured["url"])
    assert captured["body"] == {"title": "派单"}


def test_create_session_raises_when_response_has_no_id(
    monkeypatch: pytest.MonkeyPatch,
):
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"weird":true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        bridge.urllib.request, "urlopen", lambda request, timeout=None: _Response()
    )

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    with pytest.raises(bridge.BridgeError):
        client.create_session(workspace=Path("/tmp/ws"), title="t")


def test_resolve_model_resolves_provider_from_registry(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        bridge,
        "provider_registry",
        lambda client: {"glm-5.3": "inferhub-provider", "kimi-k3": "inferhub-provider"},
    )

    model, resolved, warning = bridge.resolve_model(object(), spec="glm-5.3")

    assert model == {"providerID": "inferhub-provider", "modelID": "glm-5.3"}
    assert resolved == "inferhub-provider/glm-5.3"
    assert warning == ""


def test_resolve_model_accepts_explicit_provider(monkeypatch: pytest.MonkeyPatch):
    """显式给了 provider 就不必查注册表。"""

    def _boom(client):
        raise AssertionError("显式 provider 时不该查注册表")

    monkeypatch.setattr(bridge, "provider_registry", _boom)

    model, resolved, warning = bridge.resolve_model(object(), spec="myprov/my-model")

    assert model == {"providerID": "myprov", "modelID": "my-model"}
    assert resolved == "myprov/my-model"
    assert warning == ""


def test_resolve_model_warns_when_model_not_in_registry(
    monkeypatch: pytest.MonkeyPatch,
):
    """注册表里没有 → 如实降级 + 告警，绝不静默假装钉住了。"""
    monkeypatch.setattr(bridge, "provider_registry", lambda client: {"kimi-k3": "p"})

    model, resolved, warning = bridge.resolve_model(object(), spec="no-such-model")

    assert model is None
    assert "no-such-model" in warning
    assert "未指定模型" in warning


def test_extract_used_model_reads_info_block():
    payload = {"info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}}

    assert bridge.extract_used_model(payload) == "inferhub-provider/glm-5.3"


def test_extract_used_model_reads_raw_list():
    payload = {"raw": [{"info": {"providerID": "p", "modelID": "m"}}]}

    assert bridge.extract_used_model(payload) == "p/m"


def test_extract_used_model_returns_empty_when_absent():
    assert bridge.extract_used_model({"nothing": 1}) == ""


def test_session_title_from_message_takes_first_line():
    assert bridge.session_title_from_message("# 标题\n\n正文") == "标题"
    assert bridge.session_title_from_message("") == "codearts-dispatch"


def test_main_rejects_model_with_cron_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """cron 通道由 kernel 决定模型，配 --model 必须**明确失败**，不能假绿。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        [
            "--workspace",
            str(tmp_path),
            "--event-file",
            str(event),
            "--channel",
            "cron",
            "--model",
            "glm-5.3",
        ]
    )

    assert code == 2
    assert "cron" in capsys.readouterr().err


def test_main_defaults_to_new_session_when_model_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """给了模型就必须走 new_session（cron 钉不住模型）。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "KernelClient", lambda **_: object())
    monkeypatch.setattr(
        bridge,
        "resolve_model",
        lambda client, *, spec: (
            {"providerID": "inferhub-provider", "modelID": spec},
            f"inferhub-provider/{spec}",
            "",
        ),
    )
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    captured: dict[str, object] = {}

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        captured["model"] = model
        return {
            "channel": "new_session",
            "session_id": "ses_new",
            "response": {
                "info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}
            },
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace",
            str(tmp_path),
            "--event-file",
            str(event),
            "--kernel-url",
            "http://127.0.0.1:14934",
            "--model",
            "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    assert captured["model"] == {
        "providerID": "inferhub-provider",
        "modelID": "glm-5.3",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["channel"] == "new_session"
    assert payload["model_requested"] == "inferhub-provider/glm-5.3"
    assert payload["model_used"] == "inferhub-provider/glm-5.3"
    assert payload["model_applied"] is True


def test_main_reports_silent_fallback_in_model_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """请求 A、实际 B → model_applied 必须是 False（不能装作钉住了）。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "KernelClient", lambda **_: object())
    monkeypatch.setattr(
        bridge,
        "resolve_model",
        lambda client, *, spec: (
            {"providerID": "inferhub-provider", "modelID": spec},
            f"inferhub-provider/{spec}",
            "",
        ),
    )
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        return {
            "channel": "new_session",
            "session_id": "ses_new",
            "response": {
                "info": {
                    "providerID": "minimax",
                    "modelID": "MiniMax-M3.1-Flash-Preview",
                }
            },
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace",
            str(tmp_path),
            "--event-file",
            str(event),
            "--kernel-url",
            "http://127.0.0.1:14934",
            "--model",
            "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model_applied"] is False
    assert payload["model_used"] == "minimax/MiniMax-M3.1-Flash-Preview"


# ---------------------------------------------------------------------------
# 一次性凭据引导（--setup-credentials）
# ---------------------------------------------------------------------------


def test_setup_credentials_writes_credential_file_without_echoing_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """引导命令把密码写进 0600 文件，且**绝不回显密码**。

    回显密码会把它带进终端滚动记录、CI 日志或 AI 会话上下文，
    那等于没做凭据保护。
    """
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    credential_file = tmp_path / "kernel-bridge.env"
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", credential_file)
    monkeypatch.setattr(
        bridge,
        "resolve_credentials",
        lambda **_: ("codearts", "s3cret-password-value"),
    )

    code = bridge.main(["--workspace", str(tmp_path), "--setup-credentials"])

    assert code == 0
    written = credential_file.read_text(encoding="utf-8")
    assert "OPENCODE_SERVER_PASSWORD=s3cret-password-value" in written
    assert "OPENCODE_SERVER_USERNAME=codearts" in written
    assert oct(credential_file.stat().st_mode)[-3:] == "600"

    stdout = capsys.readouterr().out
    assert "s3cret-password-value" not in stdout
    assert "密码未回显" in stdout


def test_setup_credentials_does_not_deliver_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """引导只写凭据文件，绝不触发任何投递。"""
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", tmp_path / "kernel-bridge.env")
    monkeypatch.setattr(
        bridge, "resolve_credentials", lambda **_: ("codearts", "pw")
    )

    def _boom(*_args, **_kwargs):
        raise AssertionError("引导命令不应发起任何 kernel 请求")

    monkeypatch.setattr(bridge, "KernelClient", _boom)
    monkeypatch.setattr(bridge, "deliver_via_cron", _boom)
    monkeypatch.setattr(bridge, "deliver_via_session", _boom)

    assert bridge.main(["--workspace", str(tmp_path), "--setup-credentials"]) == 0


def test_setup_credentials_reports_failure_when_credential_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """拿不到凭据时明确失败并给出补救提示，不写空文件。"""
    monkeypatch.delenv("OPENCODE_SERVER_PASSWORD", raising=False)
    monkeypatch.delenv("CODEARTS_KERNEL_PASSWORD", raising=False)
    credential_file = tmp_path / "kernel-bridge.env"
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", credential_file)

    def _raise(**_kwargs):
        raise bridge.BridgeError("缺少 kernel 密码")

    monkeypatch.setattr(bridge, "resolve_credentials", _raise)

    code = bridge.main(["--workspace", str(tmp_path), "--setup-credentials"])

    assert code == 2
    assert not credential_file.exists()
    assert "kernel-bridge.env" in capsys.readouterr().err


def test_setup_credentials_uses_env_password_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """环境变量里已有密码时，引导直接把它固化到文件里。"""
    monkeypatch.setenv("OPENCODE_SERVER_PASSWORD", "env-provided-pw")
    credential_file = tmp_path / "kernel-bridge.env"
    monkeypatch.setattr(bridge, "CREDENTIAL_FILE", credential_file)

    code = bridge.main(["--workspace", str(tmp_path), "--setup-credentials"])

    assert code == 0
    assert "OPENCODE_SERVER_PASSWORD=env-provided-pw" in credential_file.read_text(
        encoding="utf-8"
    )
    assert "env-provided-pw" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 投递任务残留体检（僵尸 cron 任务）
# ---------------------------------------------------------------------------


class _ResidueKernel:
    def __init__(self, tasks: list[dict[str, object]]) -> None:
        self.tasks = tasks

    def list_cron_tasks(self, *, workspace: Path):
        return self.tasks


def test_inspect_cron_residue_flags_active_running_task():
    kernel = _ResidueKernel(
        [
            {
                "id": "aa844576",
                "status": "expired",
                "isRunning": False,
                "cron": "48 0 * * *",
            },
            {
                "id": "296fc444",
                "status": "active",
                "isRunning": True,
                "cron": "56 22 * * *",
                "sessionID": "ses_e9be3df",
                "lastResult": {"firedAt": 1792686927000, "status": "running"},
            },
        ]
    )

    residue = bridge.inspect_cron_residue(
        kernel, workspace=Path("/tmp/ws")  # type: ignore[arg-type]
    )

    assert residue["total"] == 2
    assert residue["stuck_count"] == 1
    assert residue["stuck"][0]["id"] == "296fc444"
    assert residue["stuck"][0]["sessionID"] == "ses_e9be3df"
    # 提示里必须给出**可执行**的清理路径，而不是"请人工处理"。
    assert "--purge-residue" in residue["note"]
    assert "/cag/cron/tasks/delete" in residue["note"]


def test_inspect_cron_residue_marks_past_next_fire_as_stale():
    """nextFireTime 停在过去 = 手动触发未走完成回调的残留，不是待触发的计划。"""
    past_ms = int(
        (datetime.now() - timedelta(hours=9)).timestamp() * 1000
    )
    kernel = _ResidueKernel(
        [
            {
                "id": "296fc444",
                "status": "active",
                "isRunning": True,
                "nextFireTime": past_ms,
            }
        ]
    )

    residue = bridge.inspect_cron_residue(
        kernel, workspace=Path("/tmp/ws")  # type: ignore[arg-type]
    )

    stuck = residue["stuck"][0]
    assert stuck["staleNextFire"] is True
    assert stuck["nextFireTimeLocal"] is not None


def test_inspect_cron_residue_future_next_fire_is_not_stale():
    future_ms = int((datetime.now() + timedelta(days=1)).timestamp() * 1000)
    kernel = _ResidueKernel(
        [
            {
                "id": "296fc444",
                "status": "active",
                "isRunning": True,
                "nextFireTime": future_ms,
            }
        ]
    )

    residue = bridge.inspect_cron_residue(
        kernel, workspace=Path("/tmp/ws")  # type: ignore[arg-type]
    )

    assert residue["stuck"][0]["staleNextFire"] is False


def test_inspect_cron_residue_clean_when_no_stuck_task():
    kernel = _ResidueKernel(
        [{"id": "aa844576", "status": "expired", "isRunning": False}]
    )

    residue = bridge.inspect_cron_residue(
        kernel, workspace=Path("/tmp/ws")  # type: ignore[arg-type]
    )

    assert residue["stuck_count"] == 0
    assert residue["stuck"] == []
    assert "无僵尸投递任务" in residue["note"]


def test_list_cron_tasks_parses_json_body(monkeypatch: pytest.MonkeyPatch):
    class _Response:
        status = 200

        def read(self) -> bytes:
            return b'{"tasks":[{"id":"aa844576","status":"expired","isRunning":false}]}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        bridge.urllib.request, "urlopen", lambda request, timeout=None: _Response()
    )

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    tasks = client.list_cron_tasks(workspace=Path("/tmp/ws"))

    assert [task["id"] for task in tasks] == ["aa844576"]


def test_main_check_residue_does_not_deliver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """--check-residue 只体检，不投递、不建会话。"""
    monkeypatch.setattr(
        bridge, "resolve_credentials", lambda **_: ("codearts", "pw")
    )
    monkeypatch.setattr(
        bridge,
        "KernelClient",
        lambda **_: _ResidueKernel(
            [{"id": "296fc444", "status": "active", "isRunning": True}]
        ),
    )

    def _boom(*_args, **_kwargs):
        raise AssertionError("体检模式不应触发投递")

    monkeypatch.setattr(bridge, "deliver_via_cron", _boom)
    monkeypatch.setattr(bridge, "deliver_via_session", _boom)

    code = bridge.main(["--workspace", str(tmp_path), "--check-residue"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stuck_count"] == 1
    assert payload["stuck"][0]["id"] == "296fc444"


# ---------------------------------------------------------------------------
# 僵尸投递任务清理（--purge-residue）
#
# kernel 的 cron 路由一共 6 条（GET/POST/PUT /tasks、POST /tasks/fire、
# POST /tasks/delete、GET /tasks/logs），但 **`/cag/*` 路由不在 kernel 的
# OpenAPI（/doc）里** —— 路由存不存在不能靠 /doc 判断。
#
# 删除路由对「手动触发后会话中途死掉」的任务会拒绝：
# 那类任务的 fire promise 永不落定，调度器的 in-flight 集合永远留着它的 id。
# 所以清理要走「官方路由 → 文件级兜底」两级。
# ---------------------------------------------------------------------------


class _PurgeKernel:
    """模拟 kernel：官方删除路由 + 任务列表。"""

    def __init__(
        self,
        tasks: list[dict[str, object]],
        *,
        refuse_running: bool = False,
    ) -> None:
        self.tasks = tasks
        self.refuse_running = refuse_running
        self.delete_calls: list[list[str]] = []

    def list_cron_tasks(self, *, workspace: Path):
        return list(self.tasks)

    def delete_cron_task(self, *, workspace: Path, task_ids: list[str]):
        self.delete_calls.append(list(task_ids))
        if self.refuse_running:
            return {
                "results": [
                    {
                        "taskId": tid,
                        "success": False,
                        "error": "任务正在执行，无法删除，如需操作，请先终止该任务",
                    }
                    for tid in task_ids
                ],
                "deletedCount": 0,
                "failedCount": len(task_ids),
            }
        for tid in task_ids:
            self.tasks = [t for t in self.tasks if t.get("id") != tid]
        return {
            "results": [{"taskId": tid, "success": True} for tid in task_ids],
            "deletedCount": len(task_ids),
            "failedCount": 0,
        }


def _write_store(path: Path, task_ids: list[str], *, active: str | None = None) -> None:
    """写入 cron 存储；`active` 指定哪一条是 active（默认全部 expired）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": tid,
                        "status": "active" if tid == active else "expired",
                        "projectPath": "/tmp/ws",
                    }
                    for tid in task_ids
                ],
                "version": 3,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_purge_uses_kernel_delete_route_first(tmp_path: Path):
    kernel = _PurgeKernel(
        [
            {"id": "296fc444", "status": "active", "isRunning": True},
            {"id": "aa844576", "status": "expired", "isRunning": False},
        ]
    )

    result = bridge.purge_cron_residue(kernel, workspace=tmp_path)  # type: ignore[arg-type]

    assert kernel.delete_calls == [["296fc444"]]
    assert result["purged"] == ["296fc444"]
    assert result["still_stuck"] == []
    assert result["api_refused_running"] == []


def test_purge_falls_back_to_file_when_route_refuses_running_task(
    tmp_path: Path, monkeypatch
):
    """官方路由拒绝「正在执行」的任务时，走文件级兜底。"""
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["296fc444", "aa844576"], active="296fc444")
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)

    kernel = _PurgeKernel(
        [{"id": "296fc444", "status": "active", "isRunning": True}],
        refuse_running=True,
    )

    # 复核用：kernel 读的就是这个文件，改完应立刻反映。
    def _list(*, workspace: Path):
        payload = json.loads(store.read_text(encoding="utf-8"))
        return [
            {"id": t["id"], "status": t["status"], "isRunning": t["status"] == "active"}
            for t in payload["tasks"]
        ]

    monkeypatch.setattr(kernel, "list_cron_tasks", _list)

    result = bridge.purge_cron_residue(kernel, workspace=tmp_path)  # type: ignore[arg-type]

    assert result["api_refused_running"] == ["296fc444"]
    assert result["file_fallback"]["ok"] is True
    assert result["file_fallback"]["removed"] == ["296fc444"]
    assert result["still_stuck"] == []
    assert result["purged"] == ["296fc444"]

    remaining = json.loads(store.read_text(encoding="utf-8"))
    assert [t["id"] for t in remaining["tasks"]] == ["aa844576"]
    assert remaining["version"] == 3


def test_purge_dry_run_touches_nothing(tmp_path: Path, monkeypatch):
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["296fc444"])
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)
    before = store.read_text(encoding="utf-8")

    kernel = _PurgeKernel(
        [{"id": "296fc444", "status": "active", "isRunning": True}]
    )

    result = bridge.purge_cron_residue(
        kernel, workspace=tmp_path, dry_run=True  # type: ignore[arg-type]
    )

    assert result["mode"] == "dry-run"
    assert result["would_purge"] == ["296fc444"]
    assert kernel.delete_calls == []
    assert store.read_text(encoding="utf-8") == before


def test_purge_with_no_stuck_task_is_a_noop(tmp_path: Path):
    kernel = _PurgeKernel([{"id": "aa844576", "status": "expired", "isRunning": False}])

    result = bridge.purge_cron_residue(kernel, workspace=tmp_path)  # type: ignore[arg-type]

    assert result["purged"] == []
    assert kernel.delete_calls == []


def test_running_refusal_detection_covers_chinese_and_english():
    assert bridge._residue_is_running_refusal("任务正在执行，无法删除，如需操作，请先终止该任务")
    assert bridge._residue_is_running_refusal("Task is running, cannot delete")
    assert not bridge._residue_is_running_refusal("Task not found")
    assert not bridge._residue_is_running_refusal("")


def test_remove_from_cron_store_keeps_other_tasks(tmp_path: Path, monkeypatch):
    store = tmp_path / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2", "c3"])
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)

    result = bridge._remove_from_cron_store(["b2"])

    assert result["ok"] is True
    assert result["removed"] == ["b2"]
    payload = json.loads(store.read_text(encoding="utf-8"))
    assert [t["id"] for t in payload["tasks"]] == ["a1", "c3"]


def test_remove_from_cron_store_is_idempotent(tmp_path: Path, monkeypatch):
    store = tmp_path / "scheduled_tasks.json"
    _write_store(store, ["a1"])
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)

    result = bridge._remove_from_cron_store(["nope"])

    assert result["ok"] is True
    assert result["removed"] == []
    payload = json.loads(store.read_text(encoding="utf-8"))
    assert [t["id"] for t in payload["tasks"]] == ["a1"]


def test_purge_residue_cli_flag_runs_purge(tmp_path: Path, monkeypatch, capsys):
    kernel = _PurgeKernel([{"id": "296fc444", "status": "active", "isRunning": True}])
    monkeypatch.setattr(bridge, "KernelClient", lambda **_: kernel)

    def _boom(*_args, **_kwargs):
        raise AssertionError("清理模式不应触发投递")

    monkeypatch.setattr(bridge, "deliver_via_cron", _boom)
    monkeypatch.setattr(bridge, "deliver_via_session", _boom)

    code = bridge.main(["--workspace", str(tmp_path), "--purge-residue"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["purged"] == ["296fc444"]
    assert kernel.delete_calls == [["296fc444"]]


# ---------------------------------------------------------------------------
# 文件级兜底的锁纪律（2026-10-23）
#
# `scheduled_tasks.lock` 是 kernel 自己的锁。
# 兜底删除**只读它、绝不删它** —— 删掉别人持有的锁会让 kernel
# 认为自己没在写，从而与本进程并发写同一份存储。
# ---------------------------------------------------------------------------


def test_remove_from_cron_store_never_deletes_kernel_lock(tmp_path: Path, monkeypatch):
    """kernel 正在写（锁文件在）时，兜底删除不得把锁文件带走。"""
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2"])
    lock = store.with_name("scheduled_tasks.lock")
    lock.write_text('{"process": 1, "timestamp": 0}', encoding="utf-8")
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)
    # 用 stub 替换 time 模块（raising=False）：这样本用例在旧实现上
    # 也会因为「锁被删掉」而失败，而不是因为缺少 time 属性而失败。
    monkeypatch.setattr(
        bridge, "time", SimpleNamespace(sleep=lambda _s: None), raising=False
    )

    result = bridge._remove_from_cron_store(["b2"])

    assert result["ok"] is True
    assert result["removed"] == ["b2"]
    assert lock.exists(), "不能删除 kernel 自己持有的锁文件"
    assert lock.read_text(encoding="utf-8") == '{"process": 1, "timestamp": 0}'


def test_remove_from_cron_store_reports_lock_conflict(tmp_path: Path, monkeypatch):
    """锁冲突必须如实报出来（运维要能看到这次写入有竞态风险）。"""
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2"])
    store.with_name("scheduled_tasks.lock").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)
    # 用 stub 替换 time 模块（raising=False）：这样本用例在旧实现上
    # 也会因为「锁被删掉」而失败，而不是因为缺少 time 属性而失败。
    monkeypatch.setattr(
        bridge, "time", SimpleNamespace(sleep=lambda _s: None), raising=False
    )

    result = bridge._remove_from_cron_store(["b2"])

    assert result["lock_conflict"] is True


def test_remove_from_cron_store_reports_no_lock_conflict(tmp_path: Path, monkeypatch):
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2"])
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)

    result = bridge._remove_from_cron_store(["b2"])

    assert result["lock_conflict"] is False


def test_remove_from_cron_store_rereads_store_after_lock_conflict(
    tmp_path: Path, monkeypatch
):
    """锁冲突时重新读一次存储：kernel 在这期间加的任务不能被覆盖掉。"""
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2"])
    store.with_name("scheduled_tasks.lock").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)
    # 用 stub 替换 time 模块（raising=False）：这样本用例在旧实现上
    # 也会因为「锁被删掉」而失败，而不是因为缺少 time 属性而失败。
    monkeypatch.setattr(
        bridge, "time", SimpleNamespace(sleep=lambda _s: None), raising=False
    )

    calls = {"n": 0}
    real_read = bridge._read_cron_store

    def _fake_read():
        calls["n"] += 1
        if calls["n"] == 1:
            return real_read()
        payload, error = real_read()
        if error:
            return None, error
        payload["tasks"].append({"id": "c3", "status": "active"})
        return payload, None

    monkeypatch.setattr(bridge, "_read_cron_store", _fake_read)

    result = bridge._remove_from_cron_store(["b2"])

    assert result["ok"] is True
    assert result["removed"] == ["b2"]
    payload = json.loads(store.read_text(encoding="utf-8"))
    assert sorted(t["id"] for t in payload["tasks"]) == ["a1", "c3"]


def test_remove_from_cron_store_leaves_no_temp_file(tmp_path: Path, monkeypatch):
    """临时文件必须被 rename 掉，不能在 kernel 的目录里留垃圾。"""
    store = tmp_path / "cron" / "scheduled_tasks.json"
    _write_store(store, ["a1", "b2"])
    monkeypatch.setattr(bridge, "CRON_STORE_PATH", store)

    bridge._remove_from_cron_store(["b2"])

    leftovers = [p.name for p in store.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


if __name__ == "__main__":
    pytest.main([__file__])
