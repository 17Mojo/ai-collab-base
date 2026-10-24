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
import time
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
# 测试隔离：kernel 定位必须落在 tmp 里，不能依赖开发机
# ---------------------------------------------------------------------------
#
# bridge 的 KERNEL_CONFIG_ROOT / CREDENTIAL_FILE / CRON_STORE_PATH 都是
# Path.home() 下的全局常量。main() 在进入 dry-run 分支**之前**就会先
# `_discover_kernel()`，所以只要没有真机 kernel，这些用例会以
# 「找不到 server_config.properties」失败——开发机装了 kernel 就绿、
# CI runner 上没有就红，是一种最难查的假绿。
#
# 这里用 autouse fixture 把 kernel 根目录钉到 tmp 内的假 kernel
# （pid 用当前进程 pid，保证 `_pid_alive` 判定为存活），
# 整个文件从此与「本机是否装了 CodeArts Doer」无关。
# 需要别的 kernel 布局的用例自行 monkeypatch 覆盖即可。


@pytest.fixture(autouse=True)
def _isolated_kernel_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = tmp_path / "kernel-root" / "Vscode_test" / "server_config.properties"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"pid={os.getpid()}\nport=14934\n", encoding="utf-8")
    monkeypatch.setattr(bridge, "KERNEL_CONFIG_ROOT", tmp_path / "kernel-root")


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
        model_fallback="deepseek-v4.1-flash,kimi-k3",
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
    # 模型池条目有两种写法："glm-5.3"（只给 modelID）或
    # {"providerID": ..., "modelID": ...}（显式给 provider）。这里只关心
    # **声明了哪几个模型**，两种写法归一化后都比 modelID。
    model_ids = set()
    for item in models:
        if isinstance(item, dict):
            model_ids.add(str(item.get("modelID") or "").strip())
        else:
            model_ids.add(str(item).strip().split("/")[-1])
    assert {"glm-5.3", "deepseek-v4.1-flash", "kimi-k3"} <= model_ids
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


def test_provider_registry_queries_provider_with_workspace_scope():
    """注册表必须按工作区目录查。

    真机实测 2026-10-23 18:31：kernel 重启后，不带 directory 的
    `GET /provider` 返回空注册表，带 `?directory=<工作区>` 才拿得到该项目的
    provider 与模型。查空会被误判成"模型不在注册表" → 钉模型静默失效。
    """
    calls: list[str] = []

    class _Client:
        workspace = Path("/tmp/ws")

        def request(self, method, path, *, query=None, body=None):
            calls.append(f"{method} {path} {query or ''}")
            return {
                "all": [
                    {
                        "id": "inferhub-provider",
                        "models": {"glm-5.3": {}, "kimi-k3": {}},
                    }
                ]
            }

    registry = bridge.provider_registry(_Client())

    assert registry == {"glm-5.3": "inferhub-provider", "kimi-k3": "inferhub-provider"}
    assert len(calls) == 1
    assert "'directory': '/tmp/ws'" in calls[0]


def test_provider_registry_falls_back_to_unscoped_query_when_scope_is_empty():
    """作用域查不到 → 退回全局作用域再查一次（老 kernel 把 provider 配在全局）。"""
    calls: list[str] = []

    class _Client:
        workspace = Path("/tmp/ws")

        def request(self, method, path, *, query=None, body=None):
            calls.append(f"{method} {path} {query or ''}")
            if query:
                return {"all": []}
            return {"all": [{"id": "minimax", "models": {"MiniMax-M3.1-Flash": {}}}]}

    registry = bridge.provider_registry(_Client())

    assert registry == {"MiniMax-M3.1-Flash": "minimax"}
    assert len(calls) == 2


def test_resolve_model_uses_workspace_scoped_registry():
    """端到端一点：resolve_model 拿到的 provider 必须来自作用域查询。"""

    class _Client:
        workspace = Path("/tmp/ws")

        def request(self, method, path, *, query=None, body=None):
            assert query == {"directory": "/tmp/ws"}
            return {"all": [{"id": "inferhub-provider", "models": {"glm-5.3": {}}}]}

    model, resolved, warning = bridge.resolve_model(_Client(), spec="glm-5.3")

    assert model == {"providerID": "inferhub-provider", "modelID": "glm-5.3"}
    assert resolved == "inferhub-provider/glm-5.3"
    assert warning == ""


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
        lambda **_: ("codearts", "dummy-s3cret-password-value"),
    )

    code = bridge.main(["--workspace", str(tmp_path), "--setup-credentials"])

    assert code == 0
    written = credential_file.read_text(encoding="utf-8")
    assert "OPENCODE_SERVER_PASSWORD=dummy-s3cret-password-value" in written
    assert "OPENCODE_SERVER_USERNAME=codearts" in written
    assert oct(credential_file.stat().st_mode)[-3:] == "600"

    stdout = capsys.readouterr().out
    assert "dummy-s3cret-password-value" not in stdout
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
    # 凭据解析必须打桩：本用例只关心清理流程，不该依赖本机
    # ~/.codeartsdoer/kernel-bridge.env 里的真实凭据（CI runner 上没有）。
    monkeypatch.setattr(
        bridge, "resolve_credentials", lambda **_: ("codearts", "pw")
    )

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



# ---------------------------------------------------------------------------
# 模型降级链（--model-fallback）与投递回执落盘
#
# 三种"失败"口径（命中即换下一个候选，且每次重试用全新会话）：
#   1. resolve_model 返回 model_payload is None（模型不在注册表）；
#   2. 投递抛 BridgeError（HTTP 错误 / 连接失败 / 建会话失败）；
#   3. 回执里的实际模型 != 请求的模型（静默回落）。
# 全部候选失败 → 退出码 2，绝不静默降级成"不指定模型"。
# ---------------------------------------------------------------------------


def _patch_delivery_harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """给降级链用例搭公共桩：凭据 / KernelClient / 残留体检。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "KernelClient", lambda **_: object())
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    return event


def _default_resolve_model(client, *, spec: str):
    return (
        {"providerID": "inferhub-provider", "modelID": spec},
        f"inferhub-provider/{spec}",
        "",
    )


def test_fallback_chain_first_choice_succeeds_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 1：首选生效 → fallback_used=False，model_attempts 长度 1。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(
        bridge,
        "deliver_via_new_session",
        lambda client, *, workspace, message, agent, model=None: {
            "channel": "new_session",
            "session_id": "ses_new_1",
            "response": {"info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}},
        },
    )

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "deepseek-v4.1-flash,kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model_requested"] == "inferhub-provider/glm-5.3"
    assert payload["model_used"] == "inferhub-provider/glm-5.3"
    assert payload["model_applied"] is True
    assert payload["fallback_used"] is False
    assert payload["model_attempts"] == [
        {"model": "inferhub-provider/glm-5.3", "ok": True, "error": ""}
    ]


def test_fallback_chain_silent_fallback_moves_to_next_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 2：首选静默回落（回执 modelID 不同）→ 自动换下一个候选。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    calls: list[dict[str, Any] | None] = []

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        calls.append(model)
        if len(calls) == 1:
            used: dict[str, Any] | None = {
                "providerID": "minimax",
                "modelID": "MiniMax-M3.1-Flash-Preview",
            }
        else:
            used = model
        return {
            "channel": "new_session",
            "session_id": f"ses_new_{len(calls)}",
            "response": {"info": used},
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "deepseek-v4.1-flash,kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model_requested"] == "inferhub-provider/glm-5.3"
    assert payload["model_used"] == "inferhub-provider/deepseek-v4.1-flash"
    assert payload["model_applied"] is False
    assert payload["fallback_used"] is True
    assert len(payload["model_attempts"]) == 2
    assert payload["model_attempts"][0]["ok"] is False
    assert "静默回落" in payload["model_attempts"][0]["error"]
    assert payload["model_attempts"][1] == {
        "model": "inferhub-provider/deepseek-v4.1-flash",
        "ok": True,
        "error": "",
    }


def test_fallback_chain_http_error_moves_to_next_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 3：首选 HTTP 报错 → 换下一个候选。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        if model and model["modelID"] == "glm-5.3":
            raise bridge.BridgeError(
                "POST /session/ses_1/message 返回 HTTP 500: upstream boom"
            )
        return {
            "channel": "new_session",
            "session_id": "ses_new_2",
            "response": {"info": model},
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "deepseek-v4.1-flash",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model_used"] == "inferhub-provider/deepseek-v4.1-flash"
    assert payload["fallback_used"] is True
    assert payload["model_attempts"][0]["ok"] is False
    assert "HTTP 500" in payload["model_attempts"][0]["error"]


def test_fallback_chain_all_candidates_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 4：全部候选失败 → 退出码 2，stderr 逐条列出原因，且没有任何
    一次"不指定模型"的投递。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)

    def _resolve(client, *, spec: str):
        if spec == "kimi-k3":
            return (
                None,
                spec,
                f"模型 {spec} 不在 kernel 注册表中，本次投递未指定模型（由 kernel 决定）",
            )
        return (
            {"providerID": "inferhub-provider", "modelID": spec},
            f"inferhub-provider/{spec}",
            "",
        )

    deliver_calls: list[dict[str, Any] | None] = []

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        deliver_calls.append(model)
        if model and model["modelID"] == "glm-5.3":
            return {
                "channel": "new_session",
                "session_id": "ses_new_1",
                "response": {
                    "info": {"providerID": "minimax", "modelID": "MiniMax-M3.1"}
                },
            }
        raise bridge.BridgeError(
            "无法连接 kernel http://127.0.0.1:14934: connection refused"
        )

    monkeypatch.setattr(bridge, "resolve_model", _resolve)
    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "deepseek-v4.1-flash,kimi-k3",
            "--json",
        ]
    )

    assert code == 2
    captured = capsys.readouterr()
    for spec in ("glm-5.3", "deepseek-v4.1-flash", "kimi-k3"):
        assert spec in captured.err
    assert "静默回落" in captured.err
    assert "无法连接" in captured.err
    assert "不在 kernel 注册表" in captured.err
    # 三种失败路径各自命中一次：静默回落（glm-5.3）、BridgeError（deepseek）、
    # 注册表缺失（kimi-k3，不触发投递）。
    assert deliver_calls and all(m is not None for m in deliver_calls)
    assert captured.out.strip() == ""


def test_fallback_chain_retry_uses_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 5：降级重试必须用全新会话（两次尝试的 session_id 不同）。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    sessions: list[str] = []

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        # deliver_via_new_session 每次调用都会先 create_session —— 用递增
        # 会话号模拟"每次尝试 = 一个全新会话"。
        sessions.append(f"ses_new_{len(sessions) + 1}")
        if len(sessions) == 1:
            used: dict[str, Any] | None = {
                "providerID": "minimax",
                "modelID": "MiniMax-M3.1",
            }
        else:
            used = model
        return {
            "channel": "new_session",
            "session_id": sessions[-1],
            "response": {"info": used},
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert sessions == ["ses_new_1", "ses_new_2"]
    assert len(set(sessions)) == 2
    assert payload["session_id"] == "ses_new_2"


def test_single_model_failure_keeps_legacy_behaviour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """没给 --model-fallback：失败就是失败（退出码 2），不做自动降级、不重试。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    calls: list[int] = []

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        calls.append(1)
        raise bridge.BridgeError("POST /session/ses_1/message 返回 HTTP 500: boom")

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 2
    assert len(calls) == 1


def test_model_fallback_requires_primary_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--model-fallback", "kimi-k3",
        ]
    )

    assert code == 2
    assert "--model-fallback" in capsys.readouterr().err


def test_model_fallback_rejects_cron_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--channel", "cron",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
        ]
    )

    assert code == 2
    assert "cron" in capsys.readouterr().err


def test_model_fallback_rejects_session_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """降级重试必须用全新会话 —— 复用已有会话的 session 通道不兼容降级链。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--channel", "session",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
        ]
    )

    assert code == 2
    assert "new_session" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 投递回执落盘（R4）：logs/codearts_delivery_receipt.json
# ---------------------------------------------------------------------------


def test_delivery_receipt_written_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(
        bridge,
        "deliver_via_new_session",
        lambda client, *, workspace, message, agent, model=None: {
            "channel": "new_session",
            "session_id": "ses_new",
            "response": {"info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}},
        },
    )

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--intervention-id", "int-rcpt-1",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    receipt_path = tmp_path / "logs" / "codearts_delivery_receipt.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["intervention_id"] == "int-rcpt-1"
    assert receipt["session_id"] == "ses_new"
    assert receipt["model_requested"] == "inferhub-provider/glm-5.3"
    assert receipt["model_used"] == "inferhub-provider/glm-5.3"
    assert receipt["model_applied"] is True
    assert receipt["fallback_used"] is False
    assert receipt["model_attempts"][0]["ok"] is True
    assert receipt["generated_at"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt_file"] == "logs/codearts_delivery_receipt.json"


def test_delivery_receipt_overwritten_per_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """每次投递覆盖写：回执文件只有一个，内容是最近一次投递。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(
        bridge,
        "deliver_via_new_session",
        lambda client, *, workspace, message, agent, model=None: {
            "channel": "new_session",
            "session_id": "ses_new",
            "response": {"info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}},
        },
    )

    for intervention_id in ("int-first", "int-second"):
        code = bridge.main(
            [
                "--workspace", str(tmp_path),
                "--event-file", str(event),
                "--kernel-url", "http://127.0.0.1:14934",
                "--intervention-id", intervention_id,
                "--model", "glm-5.3",
                "--json",
            ]
        )
        assert code == 0

    receipt_files = list((tmp_path / "logs").glob("codearts_delivery_receipt*.json"))
    assert len(receipt_files) == 1
    receipt = json.loads(receipt_files[0].read_text(encoding="utf-8"))
    assert receipt["intervention_id"] == "int-second"


def test_delivery_receipt_write_failure_only_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """写回执失败只告警，不影响投递成功（与 inbox 副本的容错口径一致）。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(
        bridge,
        "deliver_via_new_session",
        lambda client, *, workspace, message, agent, model=None: {
            "channel": "new_session",
            "session_id": "ses_new",
            "response": {"info": {"providerID": "inferhub-provider", "modelID": "glm-5.3"}},
        },
    )

    def _boom(**_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(bridge, "write_delivery_receipt", _boom)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    err = capsys.readouterr().err
    assert "写投递回执失败" in err


def test_inbox_copy_carries_fallback_trace_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """write_inbox_copy 落的 payload 里必须带 fallback_used / model_attempts。"""
    event = _patch_delivery_harness(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    calls: list[dict[str, Any] | None] = []

    def _fake_deliver(client, *, workspace, message, agent, model=None):
        calls.append(model)
        if len(calls) == 1:
            used: dict[str, Any] | None = {
                "providerID": "minimax",
                "modelID": "MiniMax-M3.1",
            }
        else:
            used = model
        return {
            "channel": "new_session",
            "session_id": f"ses_new_{len(calls)}",
            "response": {"info": used},
        }

    monkeypatch.setattr(bridge, "deliver_via_new_session", _fake_deliver)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--intervention-id", "int-trace-1",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    inbox_files = list(
        (tmp_path / "collaboration" / "monitoring" / "codearts_inbox").glob("*.md")
    )
    assert len(inbox_files) == 1
    text = inbox_files[0].read_text(encoding="utf-8")
    assert "fallback_used" in text
    assert "model_attempts" in text
    assert "model_requested" in text


# ---------------------------------------------------------------------------
# R1b：等回执超时 ≠ 投递失败
#
# 真机教训（2026-10-23 17:34 那一轮派单本身）：POST /session/{id}/message
# 等回执 120 秒超时 → 抛 TimeoutError（不是 BridgeError，降级链和 main()
# 都没接住）→ 脚本以 traceback 结束、退出码 1 → 适配器判 failed → failed
# 是可重试状态 → 下一轮再投一次 → 对方那边再建一个会话 → 两个会话并发
# 改同一个工作区（2026-10-22 22:01 事故的成因）。
#
# 所以超时时**先核实**（GET /session/{id}/message）：
#   - 看得到本条用户消息 → 消息已被 kernel 接受 → 视为投递成功
#     （退出码 0、不降级、不重投），留痕 accepted_without_receipt=true；
#   - 看不到 → 消息确实没被接受 → 这次候选才算失败（换下一个候选）。
# ---------------------------------------------------------------------------


class _TimeoutKernel:
    """等回执超时的 kernel 桩。

    - `accepted_calls`：第几次投递算"消息已被 kernel 接受"（1 基）；
      不在集合里 → 核实时返回空列表（= 消息确实没被接受）。
    - `with_assistant`：核实时能否看到 assistant 消息（能看到才取得到
      实际用掉的模型；看不到 → model_used 为空、model_applied 为 null）。
    """

    def __init__(
        self,
        *,
        accepted_calls: set[int] | None = None,
        with_assistant: bool = False,
        receipt_timeout: int = 600,
    ) -> None:
        self.accepted_calls = accepted_calls or set()
        self.with_assistant = with_assistant
        self.receipt_timeout = receipt_timeout
        self.sessions: list[str] = []
        self.calls = 0
        self.messages: dict[str, list[str]] = {}

    def create_session(self, *, workspace: Path, title: str) -> str:
        session_id = f"ses_new_{len(self.sessions) + 1}"
        self.sessions.append(session_id)
        self.messages[session_id] = []
        return session_id

    def send_message(
        self,
        *,
        session_id: str,
        workspace: Path,
        message: str,
        agent: str,
        model: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        self.calls += 1
        self.messages.setdefault(session_id, []).append(message)
        raise bridge.BridgeTimeoutError(
            f"POST /session/{session_id}/message 等待超时（{timeout}s）: timed out"
        )

    def list_messages(self, *, session_id: str, workspace: Path) -> list[dict[str, Any]]:
        if self.calls not in self.accepted_calls:
            return []
        created = int(time.time() * 1000)
        items: list[dict[str, Any]] = [
            {
                "info": {"role": "user", "time": {"created": created}, "id": f"msg_{index}"},
                "parts": [{"type": "text", "text": text}],
            }
            for index, text in enumerate(self.messages.get(session_id, []))
        ]
        if self.with_assistant:
            items.append(
                {
                    "info": {
                        "role": "assistant",
                        "providerID": "inferhub-provider",
                        "modelID": "glm-5.3",
                    },
                    "parts": [{"type": "text", "text": "已完成"}],
                }
            )
        return items


def test_receipt_timeout_accepted_is_success_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 1：等回执超时但核实到消息已被接受 → 成功、不降级、不重投。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel(accepted_calls={1})
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted_without_receipt"] is True
    # agent 可能还在跑 → 回执里没有 assistant 消息 → model_used 空、
    # model_applied null（**不许**因此判成"模型没生效"触发假降级）。
    assert payload["model_used"] == ""
    assert payload["model_applied"] is None
    assert payload["fallback_used"] is False
    # 不降级、不重投：只投递了一次、只建了一个会话。
    assert kernel.calls == 1
    assert len(kernel.sessions) == 1
    assert payload["model_attempts"] == [
        {
            "model": "inferhub-provider/glm-5.3",
            "ok": True,
            "error": "",
            "accepted_without_receipt": True,
        }
    ]


def test_receipt_timeout_accepted_keeps_actual_model_from_assistant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 2：核实到 assistant 消息 → model_used 取实际用掉的模型。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel(accepted_calls={1}, with_assistant=True)
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted_without_receipt"] is True
    assert payload["model_used"] == "inferhub-provider/glm-5.3"
    assert payload["model_applied"] is True
    assert payload["fallback_used"] is False


def test_receipt_timeout_not_accepted_falls_back_to_next_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 3：核实不到消息（确实没被接受）→ 这次候选失败，换下一个。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel(accepted_calls={2})
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted_without_receipt"] is True
    # 第一次没被接受 → 失败并换候选；第二次被接受 → 成功即止。
    assert kernel.calls == 2
    assert len(kernel.sessions) == 2
    attempts = payload["model_attempts"]
    assert len(attempts) == 2
    assert attempts[0]["ok"] is False
    assert "等回执超时" in attempts[0]["error"]
    assert attempts[1]["ok"] is True
    assert attempts[1]["accepted_without_receipt"] is True


def test_receipt_timeout_all_candidates_fail_exits_with_reasons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 4：所有候选都超时且都没被接受 → 退出码 2 + 逐条原因。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel()
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--model-fallback", "kimi-k3",
            "--json",
        ]
    )

    assert code == 2
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert "glm-5.3" in captured.err
    assert "kimi-k3" in captured.err
    assert "等回执超时" in captured.err
    assert "Traceback" not in captured.err


def test_receipt_timeout_single_candidate_exits_two_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 5：单候选（无降级链）超时且没被接受 → 退出码 2，不许 traceback。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel()
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 2
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert "等回执超时" in captured.err
    assert "Traceback" not in captured.err


def test_receipt_timeout_is_forwarded_to_kernel_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 6：--receipt-timeout 单独管等回执窗口，默认 600 秒。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel(accepted_calls={1, 2})
    captured: dict[str, Any] = {}

    def _factory(**kwargs: Any) -> _TimeoutKernel:
        captured.update(kwargs)
        return kernel

    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", _factory)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    assert captured["receipt_timeout"] == bridge.DEFAULT_RECEIPT_TIMEOUT
    capsys.readouterr()

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--model", "glm-5.3",
            "--receipt-timeout", "42",
            "--json",
        ]
    )

    assert code == 0
    assert captured["receipt_timeout"] == 42
    # --timeout 仍然管短请求，两者分开。
    assert captured["timeout"] == 120
    capsys.readouterr()


def test_accepted_without_receipt_is_written_to_receipt_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """R1b 用例 7：accepted_without_receipt 落进回执文件。"""
    event = _write_event(
        tmp_path / "event.md", "## Pull Snapshot\n\n```text\n正文\n```\n"
    )
    kernel = _TimeoutKernel(accepted_calls={1})
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "inspect_cron_residue", lambda client, *, workspace: {})
    monkeypatch.setattr(bridge, "resolve_model", _default_resolve_model)
    monkeypatch.setattr(bridge, "KernelClient", lambda **kwargs: kernel)

    code = bridge.main(
        [
            "--workspace", str(tmp_path),
            "--event-file", str(event),
            "--kernel-url", "http://127.0.0.1:14934",
            "--intervention-id", "int-accepted-1",
            "--model", "glm-5.3",
            "--json",
        ]
    )

    assert code == 0
    capsys.readouterr()
    receipt_path = tmp_path / "logs" / "codearts_delivery_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["accepted_without_receipt"] is True
    assert receipt["model_used"] == ""
    assert receipt["model_applied"] is None
    assert receipt["model_attempts"][0]["accepted_without_receipt"] is True


def test_request_wraps_socket_timeout_into_bridge_timeout(
    monkeypatch: pytest.MonkeyPatch,
):
    """R1b 用例 8：socket 超时必须被包成 BridgeTimeoutError，不许裸逃逸。"""

    def _fake_urlopen(request, timeout=None):
        raise TimeoutError("timed out")

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    with pytest.raises(bridge.BridgeTimeoutError) as excinfo:
        client.send_message(
            session_id="ses_abc", workspace=Path("/tmp/ws"), message="x", agent="build"
        )

    assert isinstance(excinfo.value, bridge.BridgeError)
    assert "等待超时" in str(excinfo.value)


def test_request_wraps_connection_error_into_bridge_error(
    monkeypatch: pytest.MonkeyPatch,
):
    """R1b 用例 9：连接中断也收口成 BridgeError，不许 traceback 逃逸。"""

    def _fake_urlopen(request, timeout=None):
        raise ConnectionResetError("peer closed")

    monkeypatch.setattr(bridge.urllib.request, "urlopen", _fake_urlopen)

    client = bridge.KernelClient(
        base_url="http://127.0.0.1:14934", username="codearts", password="pw"
    )
    with pytest.raises(bridge.BridgeError):
        client.send_message(
            session_id="ses_abc", workspace=Path("/tmp/ws"), message="x", agent="build"
        )


def test_verify_message_accepted_ignores_messages_from_before_the_send(
    monkeypatch: pytest.MonkeyPatch,
):
    """R1b 用例 10：发送之前的旧消息不算"本条被接受"。"""
    sent_at_ms = int(time.time() * 1000)

    class _Kernel:
        def list_messages(self, *, session_id, workspace):
            return [
                {
                    "info": {
                        "role": "user",
                        "time": {"created": sent_at_ms - 600_000},
                        "id": "msg_old",
                    },
                    "parts": [{"type": "text", "text": "正文"}],
                }
            ]

    accepted, assistants = bridge.verify_message_accepted(
        _Kernel(),  # type: ignore[arg-type]
        session_id="ses_1",
        workspace=Path("/tmp/ws"),
        message="正文",
        sent_at_ms=sent_at_ms,
    )

    assert accepted is False
    assert assistants == []


def test_verify_message_accepted_matches_by_content(
    monkeypatch: pytest.MonkeyPatch,
):
    """R1b 用例 11：内容匹配即认定已被接受，并带回其后的 assistant 消息。"""
    sent_at_ms = int(time.time() * 1000)

    class _Kernel:
        def list_messages(self, *, session_id, workspace):
            return [
                {
                    "info": {
                        "role": "user",
                        "time": {"created": sent_at_ms},
                        "id": "msg_new",
                    },
                    "parts": [{"type": "text", "text": "正文"}],
                },
                {
                    "info": {
                        "role": "assistant",
                        "providerID": "inferhub-provider",
                        "modelID": "glm-5.3",
                    },
                    "parts": [{"type": "text", "text": "已完成"}],
                },
            ]

    accepted, assistants = bridge.verify_message_accepted(
        _Kernel(),  # type: ignore[arg-type]
        session_id="ses_1",
        workspace=Path("/tmp/ws"),
        message="正文",
        sent_at_ms=sent_at_ms,
    )

    assert accepted is True
    assert len(assistants) == 1
    assert bridge._first_assistant_model_info(assistants) == {
        "providerID": "inferhub-provider",
        "modelID": "glm-5.3",
    }



def test_verify_message_accepted_ignores_identical_message_from_before_the_send():
    """R1b 用例 12：只有"发送之前的同内容旧消息"不算本条被接受。"""
    sent_at_ms = int(time.time() * 1000)

    class _Kernel:
        def list_messages(self, *, session_id, workspace):
            return [
                {
                    "info": {
                        "role": "user",
                        "time": {"created": sent_at_ms - 600_000},
                        "id": "msg_old",
                    },
                    "parts": [{"type": "text", "text": "正文"}],
                }
            ]

    accepted, assistants = bridge.verify_message_accepted(
        _Kernel(),  # type: ignore[arg-type]
        session_id="ses_1",
        workspace=Path("/tmp/ws"),
        message="正文",
        sent_at_ms=sent_at_ms,
    )

    assert accepted is False
    assert assistants == []


def test_verify_message_accepted_accepts_message_without_timestamp():
    """R1b 用例 13：kernel 没给时间戳时，内容匹配也算已接受。"""
    sent_at_ms = int(time.time() * 1000)

    class _Kernel:
        def list_messages(self, *, session_id, workspace):
            return [
                {
                    "info": {"role": "user", "id": "msg_nodate"},
                    "parts": [{"type": "text", "text": "正文"}],
                }
            ]

    accepted, assistants = bridge.verify_message_accepted(
        _Kernel(),  # type: ignore[arg-type]
        session_id="ses_1",
        workspace=Path("/tmp/ws"),
        message="正文",
        sent_at_ms=sent_at_ms,
    )

    assert accepted is True
    assert assistants == []



def test_verify_message_accepted_rejects_unrelated_recent_message():
    """R1b 用例 14：会话里有别的（刚发的）用户消息也不算本条被接受。

    放宽成"有用户消息就算接受"会把"本条根本没发出去"误判成成功 →
    投递被静默吞掉，再也不会有人重投。
    """
    sent_at_ms = int(time.time() * 1000)

    class _Kernel:
        def list_messages(self, *, session_id, workspace):
            return [
                {
                    "info": {
                        "role": "user",
                        "time": {"created": sent_at_ms + 1000},
                        "id": "msg_other",
                    },
                    "parts": [{"type": "text", "text": "另一条完全无关的正文"}],
                }
            ]

    accepted, assistants = bridge.verify_message_accepted(
        _Kernel(),  # type: ignore[arg-type]
        session_id="ses_1",
        workspace=Path("/tmp/ws"),
        message="正文",
        sent_at_ms=sent_at_ms,
    )

    assert accepted is False
    assert assistants == []



if __name__ == "__main__":
    pytest.main([__file__])
