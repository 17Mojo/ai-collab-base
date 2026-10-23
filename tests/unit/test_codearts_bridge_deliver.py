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
from types import ModuleType

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
    alive.write_text("pid=%d\nport=14934\n" % os.getpid(), encoding="utf-8")
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
    )
    assert "codearts_bridge_deliver.py" in rendered
    assert "/tmp/ws" in rendered


def test_repo_codearts_adapter_is_enabled():
    config = json.loads(VSCODE_CONFIG.read_text(encoding="utf-8"))
    assert config["sessionOrchestration"]["codeartsAdapter"]["enabled"] is True


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
    assert "人工清理" in residue["note"]


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


if __name__ == "__main__":
    pytest.main([__file__])
