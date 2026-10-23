#!/usr/bin/env python3
"""CodeArts 投递桥接：把控制面生成的 payload 送进 CodeArts Doer 会话。

背景（2026-10-22 Claude Code × CodeArts 共创搭建）：

`ai_collab/adapters/codearts_adapter.py` 负责"拉"：从干预队列取出待投递的
intervention，生成 pull event 工件，然后执行 `.vscode/ai-collab.json`
里配置的 `bridgeCommand` 把消息真正送出去。本脚本就是那个
`bridgeCommand` 的实现。

投递目标是 CodeArts Doer 内置的 opencode kernel（CodeMate WebServer，
默认 127.0.0.1:14934）。两条可用通道：

**主通道（cron 一次性任务 + 立即 fire）** —— 不需要预先存在的会话。

    GET  /cag/cron/tasks?directory=<ws>            # 注册 project path（10 分钟有效）
    POST /cag/cron/tasks?directory=<ws>            # 建一次性任务（status 必须 active）
    POST /cag/cron/tasks/fire?directory=<ws>       # 立即触发，kernel 自建会话

kernel 自己会新建 CodeArts 会话并把 markdown 当成用户消息投进去，这正是
"Claude → CodeArts 自动派发"的语义；`cron.task.fired` 事件里带 sessionID。

**快路径（直发已有会话）** —— 当调用方明确给出 `ses_xxx` 会话 ID 时使用。

    GET  /session?directory=<ws>                   # 列出会话（directory 必填，否则返回 []）
    POST /session/{id}/message?directory=<ws>      # 发消息，同步返回 assistant 回复

`directory` 查询参数在所有会话路由上都是必填的：缺失时 `/session` 静默
返回空数组，是最容易踩的坑。

**模型钉死（`--model`）** —— cron 路由**自己决定**用哪个模型，调用方无法
指定（实测：不带 model 的投递全部落在 kernel 的默认模型上）。要钉死模型
只能自己建会话、再用带 model 的消息体投递：

    POST /session?directory=<ws>                   # 自建会话
    POST /session/{id}/message?directory=<ws>      # 消息体带 model

消息体里的 model 形如 `{"providerID": "...", "modelID": "..."}`。回执里的
`info.providerID` / `info.modelID` 是**实际**用掉的模型 —— 用它来防
"静默回落"（注册表里有 ≠ 真的被选中）。

**模型降级链（`--model-fallback`）** —— 首选模型不可用（不在注册表 /
投递 HTTP 失败 / 回证实为静默回落）时，按候选顺序换下一个模型重试，
每次重试都用全新会话；全部候选失败则明确失败（退出码 2），绝不静默
降级成"不指定模型"。投递结果与 `logs/codearts_delivery_receipt.json`
回执里都带 `model_requested` / `model_used` / `model_applied` /
`fallback_used` / `model_attempts` 留痕字段。

鉴权是 HTTP Basic。密码由运行环境提供，本脚本不硬编码、不落盘：

    1. 环境变量 `OPENCODE_SERVER_PASSWORD`（用户名默认 `codearts`，
       可用 `OPENCODE_SERVER_USERNAME` 覆盖）
    2. 或密钥文件 `~/.codeartsdoer/kernel-bridge.env`（KEY=VALUE 形式）
    3. 或显式加 `--allow-process-env-discovery`，从 kernel 进程环境里读取
       （仅限同机同用户；属于本机开发服务器凭据，默认关闭）

三者都拿不到时脚本以非零码退出并给出明确说明。此时适配器会把这次投递
标记为 failed，但 intervention 仍保持 open（failed 不是终态），下次轮询
会重试；payload 工件也保留在 intervention 目录里，运维可以人工粘贴，
不会静默丢失。

每次投递都会额外在 `collaboration/monitoring/codearts_inbox/` 落一份
审计副本，作为 kernel 不可用时的兜底通道。
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_KERNEL_URL = "http://127.0.0.1:14934"
DEFAULT_USERNAME = "codearts"
DEFAULT_AGENT = "build"
CREDENTIAL_FILE = Path.home() / ".codeartsdoer" / "kernel-bridge.env"
KERNEL_CONFIG_ROOT = Path.home() / ".codeartsdoer" / "Visual_Studio_Code"
# kernel 侧 cron 任务的持久化落点（真机实测 2026-10-23）。
# kernel 的 cron 存储是**纯文件、无内存任务表**的：二进制里
# `addTask`/`removeTask`/`expireTask` 每次都 `readTasks()` 再 `writeCronTasks()`，
# 且有文件监听器在文件变动后 reload —— 所以运行中直接改这个文件是安全的，
# 不需要先停 kernel。
CRON_STORE_PATH = Path.home() / ".codeartsdoer" / "vscode-data" / "cron" / "scheduled_tasks.json"
INBOX_DIR = "collaboration/monitoring/codearts_inbox"
SESSION_REGISTRY = "logs/session_registry_state.json"
DELIVERY_RECEIPT_RELATIVE = "logs/codearts_delivery_receipt.json"

# 非 JSON 响应（kernel 部分 GET 路由返回 Python 字面量格式）解析失败时的兜底保留长度。
# 原先写死 2000，会把会话列表截断到只剩第一条消息 —— 静默丢信息，最难查的一类。
MAX_RAW_RESPONSE_CHARS = 200_000

# `ast.literal_eval` 的输入上限，防止畸形响应把解析器拖死。
MAX_LITERAL_PARSE_CHARS = 1_000_000

EXACT_MESSAGE_PATTERN = re.compile(
    r"## Exact Forward Message\s+```text\s*(?P<message>.*?)\s*```",
    flags=re.DOTALL,
)
PULL_SNAPSHOT_PATTERN = re.compile(
    r"## Pull Snapshot\s+```text\s*(?P<message>.*?)\s*```",
    flags=re.DOTALL,
)
SESSION_ID_PATTERN = re.compile(r"^ses_[A-Za-z0-9]+$")


class BridgeError(RuntimeError):
    """投递失败，调用方应以非零码退出。"""


def _fail(message: str) -> int:
    print(f"[codearts-bridge] 失败: {message}", file=sys.stderr)
    return 2


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BridgeError(f"无法读取 {path}: {exc}") from exc


# --------------------------------------------------------------------------
# 正文抽取
# --------------------------------------------------------------------------


def extract_message(*, event_file: Path | None, artifact_file: Path | None) -> str:
    """从工件里取出要投递的原文。

    优先用干预工件里的 "## Exact Forward Message"（那是给目标会话的
    原样指令），其次用 pull event 里的 "## Pull Snapshot"。
    """
    for path, pattern in (
        (artifact_file, EXACT_MESSAGE_PATTERN),
        (event_file, PULL_SNAPSHOT_PATTERN),
    ):
        if path is None or not path.exists():
            continue
        text = _read_text(path)
        match = pattern.search(text)
        if match:
            message = str(match.group("message")).strip()
            if message:
                return message
        stripped = text.strip()
        if stripped:
            return stripped
    raise BridgeError("事件工件与干预工件里都没有可投递的正文")


# --------------------------------------------------------------------------
# 凭据
# --------------------------------------------------------------------------


def _load_credential_file() -> dict[str, str]:
    if not CREDENTIAL_FILE.exists():
        return {}
    values: dict[str, str] = {}
    try:
        raw = CREDENTIAL_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _kernel_config_files() -> list[Path]:
    """所有历史版本的 kernel server_config.properties。"""
    if not KERNEL_CONFIG_ROOT.is_dir():
        return []
    return sorted(KERNEL_CONFIG_ROOT.glob("Vscode_*/server_config.properties"))


def _parse_kernel_config(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    pid_match = re.search(r"^pid=(\d+)", text, flags=re.MULTILINE)
    port_match = re.search(r"^port=(\d+)", text, flags=re.MULTILINE)
    if not pid_match or not port_match:
        raise BridgeError(f"{path} 里缺少 pid/port 字段")
    return int(pid_match.group(1)), int(port_match.group(1))


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _discover_kernel() -> tuple[str, int, int]:
    """定位当前运行中的 kernel：(host, port, pid)。

    只读进程配置文件，不涉及任何凭据。优先选 pid 仍然存活的那一份，
    否则退回最新写入的一份。
    """
    candidates = _kernel_config_files()
    if not candidates:
        raise BridgeError(
            "找不到 CodeArts Doer kernel 的 server_config.properties，"
            f"查找路径：{KERNEL_CONFIG_ROOT}"
        )
    parsed: list[tuple[Path, int, int]] = []
    for path in candidates:
        try:
            pid, port = _parse_kernel_config(path)
        except (BridgeError, OSError):
            continue
        parsed.append((path, pid, port))
    if not parsed:
        raise BridgeError("所有 server_config.properties 都无法解析出 pid/port")
    alive = [item for item in parsed if _pid_alive(item[1])]
    chosen = (
        max(alive, key=lambda item: item[0].stat().st_mtime)
        if alive
        else max(parsed, key=lambda item: item[0].stat().st_mtime)
    )
    return "127.0.0.1", chosen[2], chosen[1]


def _credentials_from_process_env(pid: int) -> tuple[str, str]:
    """从 kernel 进程环境里读 Basic Auth 凭据（仅限同机同用户）。

    这属于本机开发服务器凭据，默认不启用：调用方必须显式传
    `--allow-process-env-discovery`。
    """
    try:
        result = subprocess.run(
            ["ps", "eww", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BridgeError(f"读取 kernel 进程环境失败: {exc}") from exc
    if result.returncode != 0:
        raise BridgeError(f"读取 kernel 进程环境失败: {result.stderr.strip()}")
    password = re.search(r"\bOPENCODE_SERVER_PASSWORD=(\S+)", result.stdout)
    if not password:
        raise BridgeError(f"pid={pid} 的进程环境里没有 OPENCODE_SERVER_PASSWORD")
    username = re.search(r"\bOPENCODE_SERVER_USERNAME=(\S+)", result.stdout)
    return (
        username.group(1) if username else DEFAULT_USERNAME,
        password.group(1),
    )


def resolve_credentials(
    *,
    allow_process_env_discovery: bool = False,
    kernel_url: str = DEFAULT_KERNEL_URL,
) -> tuple[str, str]:
    """返回 (username, password)。拿不到密码就抛错，绝不静默降级。"""
    file_values = _load_credential_file()
    password = (
        os.environ.get("OPENCODE_SERVER_PASSWORD")
        or os.environ.get("CODEARTS_KERNEL_PASSWORD")
        or file_values.get("OPENCODE_SERVER_PASSWORD")
        or ""
    ).strip()
    username = (
        os.environ.get("OPENCODE_SERVER_USERNAME")
        or file_values.get("OPENCODE_SERVER_USERNAME")
        or DEFAULT_USERNAME
    ).strip()
    if password:
        return username, password

    if allow_process_env_discovery:
        host, port, pid = _discover_kernel()
        if kernel_url.rstrip("/").endswith(str(port)) or kernel_url == DEFAULT_KERNEL_URL:
            return _credentials_from_process_env(pid)

    raise BridgeError(
        "缺少 kernel 密码。请设置环境变量 OPENCODE_SERVER_PASSWORD，"
        f"或在 {CREDENTIAL_FILE} 写入 OPENCODE_SERVER_PASSWORD=<password>；"
        "若确认从本机 kernel 进程环境读取凭据可接受，"
        "可加 --allow-process-env-discovery。"
    )


def _discover_kernel_pid() -> int:
    return _discover_kernel()[2]


# --------------------------------------------------------------------------
# 会话解析
# --------------------------------------------------------------------------


def _session_from_registry(workspace: Path) -> str | None:
    state_file = workspace / SESSION_REGISTRY
    if not state_file.exists():
        return None
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    sessions = payload.get("sessions", payload)
    if not isinstance(sessions, dict):
        return None
    best_id = ""
    best_seen = ""
    for session_id, session in sessions.items():
        if not isinstance(session, dict):
            continue
        if str(session.get("assignee") or "").strip().lower() != "codearts_agent":
            continue
        if str(session.get("session_status") or "active").strip().lower() != "active":
            continue
        seen = str(session.get("last_seen_at") or session.get("updated_at") or "")
        if seen >= best_seen:
            best_seen = seen
            best_id = str(session_id)
    return best_id or None


def _session_from_opencode_db(workspace: Path) -> str | None:
    db = Path.home() / ".codeartsdoer" / "vscode-data" / "opencode-data" / "opencode.db"
    if not db.exists():
        return None
    try:
        connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        rows = connection.execute(
            "SELECT id FROM session WHERE directory = ? ORDER BY time_updated DESC LIMIT 1",
            (str(workspace),),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        connection.close()
    if not rows:
        return None
    return str(rows[0][0])


# --------------------------------------------------------------------------
# kernel HTTP
# --------------------------------------------------------------------------


def parse_kernel_payload(raw: str) -> Any:
    """解析 kernel 响应体。

    kernel 的序列化**不统一**：`/cag/cron/tasks` 返回标准 JSON，
    而 `/session` 与 `/session/{id}/message` 返回 Python 字面量格式
    （单引号、`True`/`None`），不是合法 JSON。

    先按 JSON 试，再按字面量试，都不行返回 None（交给调用方走兜底）。
    """
    text = raw.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if len(text) > MAX_LITERAL_PARSE_CHARS:
        return None
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None


# --------------------------------------------------------------------------
# 模型解析
#
# 模型有两个来源，语义完全不同：
#   1. kernel 的 `/provider` 注册表 —— 有哪些模型可用（但注册 ≠ 真能用）；
#   2. 投递消息体里的 model 字段 —— 决定**这次**用哪个模型。
#
# 只给 modelID 时，providerID 从注册表实时解析（provider 改名/换家时不会
# 因为配置里写死而失效）；注册表里查不到就**如实降级**并告警，绝不假装
# 钉住了模型。
# --------------------------------------------------------------------------


def parse_model_spec(spec: str) -> tuple[str, str]:
    """'provider/model' → ('provider', 'model')；'model' → ('', 'model')。"""
    text = str(spec or "").strip()
    if not text:
        return "", ""
    provider, sep, model = text.partition("/")
    if sep:
        return provider.strip(), model.strip()
    return "", text


def provider_registry(client: KernelClient) -> dict[str, str]:
    """kernel 的模型注册表：model_id → provider_id。

    **必须按工作区目录查**（真机实测 2026-10-23 18:31）：kernel 重启后，
    不带 directory 的 `GET /provider` 返回空注册表
    （`{"all":[],"default":{},"connected":[]}`），而带
    `?directory=<工作区>` 的同一个路由能拿到该项目的 provider 与模型。
    查空 → 以为"模型不在注册表" → 静默降级成"不指定模型" → 钉模型功能
    整个失效，而且现场看不出任何异常。

    查法：**先按 client 的工作区查，查不到再退回无目录查询**（兼容把
    provider 配在全局作用域的老 kernel）。两边都查不到才算真的没有。
    """
    workspace = getattr(client, "workspace", None)
    payload = client.request(
        "GET",
        "/provider",
        query={"directory": str(workspace)} if workspace is not None else None,
    )
    mapping = _provider_mapping(payload)
    if not mapping and workspace is not None:
        payload = client.request("GET", "/provider")
        mapping = _provider_mapping(payload)
    return mapping


def _provider_mapping(payload: dict[str, Any]) -> dict[str, str]:
    """从 /provider 的响应里抽出 model_id → provider_id。"""
    mapping: dict[str, str] = {}
    providers = payload.get("all") if isinstance(payload, dict) else None
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            provider_id = str(provider.get("id") or "")
            models = provider.get("models")
            if isinstance(models, dict):
                items = list(models.keys())
            elif isinstance(models, list):
                items = [
                    str(item.get("id")) for item in models if isinstance(item, dict) and item.get("id")
                ]
            else:
                items = []
            for model_id in items:
                mapping[str(model_id)] = provider_id
    return mapping


def resolve_model(
    client: KernelClient, *, spec: str
) -> tuple[dict[str, str] | None, str, str]:
    """解析模型规格。

    返回 `(model_payload, resolved, warning)`：

    - `model_payload` 为 None 表示**模型没有生效**（未指定 / 不在注册表里）；
      这时 `warning` 必非空 —— 绝不静默降级。
    - `resolved` 是 `provider/model` 形态的最终模型标识。
    """
    provider, model = parse_model_spec(spec)
    if not model:
        return None, "", ""
    if not provider:
        registry = provider_registry(client)
        provider = registry.get(model, "")
        if not provider:
            # 注册表键大小写敏感（"GLM-5.2" 与 "glm-5.3" 混用），加不敏感兜底
            canonical = {k.lower(): k for k in registry}.get(model.lower(), "")
            if canonical:
                provider = registry.get(canonical, "")
                model = canonical
    if not provider:
        return (
            None,
            model,
            f"模型 {model} 不在 kernel 注册表中，本次投递未指定模型（由 kernel 决定）",
        )
    return {"providerID": provider, "modelID": model}, f"{provider}/{model}", ""


def extract_used_model(payload: Any) -> str:
    """从回执里取**实际**用掉的模型（`provider/model`）。

    回执形状有两种：直接带 `info`，或 `raw` 列表里每项带 `info`。
    """
    holders: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        info = payload.get("info")
        if isinstance(info, dict):
            holders.append(info)
        holders.append(payload)
        raw = payload.get("raw")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("info"), dict):
                    holders.append(item["info"])
    for holder in holders:
        provider = str(holder.get("providerID") or holder.get("providerId") or "")
        model = str(holder.get("modelID") or holder.get("modelId") or "")
        if provider and model:
            return f"{provider}/{model}"
        if model:
            return model
    return ""


def extract_session_id(payload: Any) -> str:
    """从响应里取 `ses_` 会话 ID。"""
    if isinstance(payload, dict):
        for key in ("id", "sessionID", "session_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ("info", "session"):
            nested = payload.get(key)
            if isinstance(nested, dict):
                value = nested.get("id")
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


def session_title_from_message(message: str) -> str:
    """会话标题：取正文第一行（与 kernel cron 路由的命名习惯一致）。"""
    for line in str(message or "").splitlines():
        text = line.strip().lstrip("#").strip()
        if text:
            return text[:80]
    return "codearts-dispatch"


class KernelClient:
    """CodeArts Doer kernel（opencode）HTTP 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 120,
        workspace: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # 工作区作用域：kernel 的 provider 注册表是**按项目**查的
        # （不带 directory 的 /provider 会返回空注册表，见 provider_registry）。
        self.workspace = workspace
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self._auth = f"Basic {token}"

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", self._auth)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise BridgeError(f"{method} {path} 返回 HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise BridgeError(f"无法连接 kernel {self.base_url}: {exc.reason}") from exc
        if not raw.strip():
            return {"http_status": status}
        decoded: Any = parse_kernel_payload(raw)
        if isinstance(decoded, dict):
            result: dict[str, Any] = decoded
        elif isinstance(decoded, list):
            result = {"raw": decoded}
        else:
            result = {"raw": raw[:MAX_RAW_RESPONSE_CHARS]}
        result.setdefault("http_status", status)
        return result

    # -- 会话 ---------------------------------------------------------------

    def list_sessions(self, workspace: Path) -> list[dict[str, Any]]:
        payload = self.request("GET", "/session", query={"directory": str(workspace)})
        items = payload.get("sessions")
        if not isinstance(items, list):
            items = payload.get("raw")
        if isinstance(items, str):
            # kernel 的 /session 返回 Python 字面量格式，request() 已尝试解析；
            # 这里再兜一次，覆盖解析失败但内容仍可读的情况。
            items = parse_kernel_payload(items)
        if isinstance(items, list):
            return [dict(item) for item in items if isinstance(item, dict)]
        return []

    def create_session(self, *, workspace: Path, title: str) -> str:
        """自建会话，返回 `ses_` 会话 ID。

        kernel 的 cron 路由自己建会话，但**模型由 kernel 决定**；要钉死模型
        只能自己建会话，再用带 model 的消息体投递。
        """
        payload = self.request(
            "POST", "/session", query={"directory": str(workspace)}, body={"title": title}
        )
        session_id = extract_session_id(payload)
        if not session_id:
            raise BridgeError(
                f"创建会话失败: {json.dumps(payload, ensure_ascii=False)[:300]}"
            )
        return session_id

    def send_message(
        self,
        *,
        session_id: str,
        workspace: Path,
        message: str,
        agent: str,
        model: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "parts": [{"type": "text", "text": message}],
            "agent": agent,
        }
        if model:
            body["model"] = {
                "providerID": str(model.get("providerID") or ""),
                "modelID": str(model.get("modelID") or ""),
            }
        return self.request(
            "POST",
            f"/session/{urllib.parse.quote(session_id)}/message",
            query={"directory": str(workspace)},
            body=body,
        )

    # -- cron ---------------------------------------------------------------

    def register_project_path(self, workspace: Path) -> Any:
        """cron 路由要求 project path 先注册（有效期 10 分钟）。"""
        return self.request(
            "GET", "/cag/cron/tasks", query={"directory": str(workspace)}
        )

    def create_cron_task(
        self, *, workspace: Path, prompt: str, cron: str
    ) -> dict[str, Any]:
        body = {
            "tasks": [
                {
                    "cron": cron,
                    "prompt": prompt,
                    "recurring": False,
                    "status": "active",
                    "category": "code",
                }
            ]
        }
        return self.request(
            "POST",
            "/cag/cron/tasks",
            query={"directory": str(workspace)},
            body=body,
        )

    def fire_cron_task(self, *, workspace: Path, task_ids: list[str]) -> dict[str, Any]:
        return self.request(
            "POST",
            "/cag/cron/tasks/fire",
            query={"directory": str(workspace)},
            body={"ids": task_ids},
        )

    def list_cron_tasks(self, *, workspace: Path) -> list[dict[str, Any]]:
        """列出本工作区下的 cron 任务（投递任务的生命周期记录）。"""
        payload = self.request("GET", "/cag/cron/tasks", query={"directory": str(workspace)})
        items = payload.get("tasks")
        if not isinstance(items, list):
            items = payload.get("raw")
        if isinstance(items, str):
            items = parse_kernel_payload(items)
        if isinstance(items, list):
            return [dict(item) for item in items if isinstance(item, dict)]
        return []

    def delete_cron_task(
        self, *, workspace: Path, task_ids: list[str]
    ) -> dict[str, Any]:
        """永久删除本工作区下的 cron 任务（kernel 的 `POST /cag/cron/tasks/delete`）。

        kernel 的删除路由会先查调度器的 in-flight 集合：
        命中「手动触发后会话中途死掉、fire 的 promise 永不落定」的任务时，
        返回 `TASK_RUNNING_CANNOT_DELETE`（任务正在执行，无法删除）。
        那类任务只能走 `purge_cron_residue()` 的文件级兜底。
        """
        return self.request(
            "POST",
            "/cag/cron/tasks/delete",
            query={"directory": str(workspace)},
            body={"ids": list(task_ids)},
        )



# --------------------------------------------------------------------------
# 模型降级链（--model-fallback）
#
# 钉死的模型不可用时自动降级到下一个候选，派单不中断；降级全程留痕。
# 某个候选"失败"的口径（三者任一，命中即换下一个候选、并使用全新会话）：
#   1. resolve_model 返回 model_payload is None（模型不在 kernel 注册表）；
#   2. 投递过程抛 BridgeError（HTTP 错误、连接失败、创建会话失败等）；
#   3. 投递成功但回执里的实际模型 != 请求的模型（静默回落）。
# 全部候选失败 → 明确失败（退出码 2），绝不静默降级成"不指定模型"——
# 那等于假装钉住了模型。
# --------------------------------------------------------------------------


def parse_fallback_models(raw: str) -> list[str]:
    """'a,b,c' → ['a', 'b', 'c']（去空白、滤空项，不去重）。"""
    items: list[str] = []
    for piece in str(raw or "").split(","):
        text = piece.strip()
        if text:
            items.append(text)
    return items


def build_model_candidates(primary: str, fallback: list[str]) -> list[str]:
    """候选序列 = [primary] + fallback 里尚未出现过的项（去重、保持原序）。"""
    candidates: list[str] = []
    for spec in [primary, *fallback]:
        if spec and spec not in candidates:
            candidates.append(spec)
    return candidates


def deliver_with_model_fallback(
    client: KernelClient,
    *,
    workspace: Path,
    message: str,
    agent: str,
    candidates: list[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """按候选顺序投递（new_session 通道），失败换下一个候选。

    每次尝试都调用 deliver_via_new_session —— 它每次都新建会话，
    所以降级重试天然使用全新会话（不在已被污染的会话里重试）。

    返回 (delivery, attempts)：delivery 已组装好 model_requested /
    model_used / model_applied / fallback_used / model_attempts 字段
    （model_* 都以**首选**模型为基准）；delivery 为 None 表示全部候选
    失败（attempts 里逐条记录了每个候选的失败原因）。
    """
    attempts: list[dict[str, Any]] = []
    first_requested = ""
    for index, spec in enumerate(candidates):
        try:
            model_payload, model_resolved, model_warning = resolve_model(
                client, spec=spec
            )
        except BridgeError as exc:
            attempts.append(
                {"model": spec, "ok": False, "error": f"解析模型失败: {exc}"}
            )
            continue
        if index == 0:
            first_requested = model_resolved or spec
        if model_payload is None:
            attempts.append(
                {
                    "model": spec,
                    "ok": False,
                    "error": model_warning or f"模型 {spec} 不在 kernel 注册表中",
                }
            )
            continue
        try:
            delivery = deliver_via_new_session(
                client,
                workspace=workspace,
                message=message,
                agent=agent,
                model=model_payload,
            )
        except BridgeError as exc:
            attempts.append(
                {"model": model_resolved, "ok": False, "error": str(exc)}
            )
            continue
        model_used = extract_used_model(delivery.get("response"))
        if model_used and model_used != model_resolved:
            attempts.append(
                {
                    "model": model_resolved,
                    "ok": False,
                    "error": (
                        f"静默回落：请求 {model_resolved}，实际用了 {model_used}"
                    ),
                }
            )
            continue
        attempts.append({"model": model_resolved, "ok": True, "error": ""})
        delivery["model_requested"] = first_requested or candidates[0]
        delivery["model_used"] = model_used
        if not model_used:
            delivery["model_applied"] = None  # 回执里没带模型信息，无法证实
        else:
            delivery["model_applied"] = model_used == delivery["model_requested"]
        delivery["fallback_used"] = bool(
            model_used
            and delivery["model_requested"]
            and model_used != delivery["model_requested"]
        )
        delivery["model_attempts"] = attempts
        return delivery, attempts
    return None, attempts


def write_delivery_receipt(*, workspace: Path, delivery: dict[str, Any]) -> str:
    """把本次投递的关键信息写成回执文件（每次覆盖写，只有一个文件）。

    调用方（适配器）按 intervention_id 把回执对到具体哪一单，从这里读
    "实际用的模型" —— 不解析桥接进程的 stdout。写文件失败由调用方
    告警兜底，不影响投递成功（与 inbox 副本的容错口径一致）。
    """
    receipt = {
        "intervention_id": str(delivery.get("intervention_id") or ""),
        "session_id": str(delivery.get("session_id") or ""),
        "model_requested": delivery.get("model_requested", ""),
        "model_used": delivery.get("model_used", ""),
        "model_applied": delivery.get("model_applied"),
        "fallback_used": bool(delivery.get("fallback_used")),
        "model_attempts": list(delivery.get("model_attempts") or []),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    target = workspace / DELIVERY_RECEIPT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return str(target.relative_to(workspace))


def _next_minute_cron() -> str:
    """下一分钟的一次性 cron 表达式（5 段，本地时区）。

    真正的触发不依赖这个表达式 —— 紧接着还会显式调 fire 接口。
    """
    target = datetime.now() + timedelta(minutes=1)
    return f"{target.minute} {target.hour} * * *"


# --------------------------------------------------------------------------
# 投递通道
# --------------------------------------------------------------------------


def deliver_via_cron(
    client: KernelClient, *, workspace: Path, message: str
) -> dict[str, Any]:
    """主通道：建一次性 cron 任务并立即触发，kernel 自建会话。"""
    client.register_project_path(workspace)
    created = client.create_cron_task(
        workspace=workspace, prompt=message, cron=_next_minute_cron()
    )
    results = created.get("results") if isinstance(created, dict) else None
    first = results[0] if isinstance(results, list) and results else {}
    task_id = str((first or {}).get("taskId") or "").strip()
    if not task_id:
        raise BridgeError(f"创建 cron 任务失败: {json.dumps(created, ensure_ascii=False)[:500]}")
    if (first or {}).get("success") is False:
        raise BridgeError(
            f"创建 cron 任务被拒绝: {(first or {}).get('message', 'unknown')}"
        )
    fired = client.fire_cron_task(workspace=workspace, task_ids=[task_id])
    fired_count = int(fired.get("firedCount", 0)) if isinstance(fired, dict) else 0
    if fired_count < 1:
        raise BridgeError(
            f"触发 cron 任务失败: {json.dumps(fired, ensure_ascii=False)[:500]}"
        )
    return {
        "channel": "cron",
        "task_id": task_id,
        "fired_count": fired_count,
        "fired": fired,
    }


def deliver_via_session(
    client: KernelClient,
    *,
    workspace: Path,
    message: str,
    session_id: str,
    agent: str,
    model: dict[str, str] | None = None,
) -> dict[str, Any]:
    """快路径：直发已有会话。"""
    response = client.send_message(
        session_id=session_id,
        workspace=workspace,
        message=message,
        agent=agent,
        model=model,
    )
    return {"channel": "session", "session_id": session_id, "response": response}


def deliver_via_new_session(
    client: KernelClient,
    *,
    workspace: Path,
    message: str,
    agent: str,
    model: dict[str, str] | None = None,
) -> dict[str, Any]:
    """自建会话 + 投递（模型可钉死）。

    这是**唯一能钉死模型**的通道：cron 路由自己建会话、自己选模型，
    调用方无法干预。
    """
    title = session_title_from_message(message)
    session_id = client.create_session(workspace=workspace, title=title)
    response = client.send_message(
        session_id=session_id,
        workspace=workspace,
        message=message,
        agent=agent,
        model=model,
    )
    return {
        "channel": "new_session",
        "session_id": session_id,
        "session_title": title,
        "response": response,
    }


# --------------------------------------------------------------------------
# 投递任务残留体检
# --------------------------------------------------------------------------

# 判定"僵尸任务"的口径（真机实测，2026-10-23）：
#   正常终态 → status=expired, isRunning=false, nextFireTime 被清空
#   僵尸     → status=active,  isRunning=true,  nextFireTime 停在触发前的时间点
# 触发原因：手动 fire 之后对方的运行没有走完完成回调，kernel 就再也不会
# 把这条任务转成 expired。实测它**不会**自己复发（9 小时无新会话），
# 也**不影响**同 projectPath 的新投递（同目录成功建过新任务），
# 但 kernel 侧没有删除路由，只能人工清理 —— 所以我们改成"看得见"。
RESIDUE_STUCK_STATUSES = {"active"}
RESIDUE_STUCK_RUNNING = True


def _epoch_ms_to_iso(value: Any) -> str | None:
    """kernel 用 epoch 毫秒表示时间戳；转成可读的本地时间。"""
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value / 1000).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None


def inspect_cron_residue(client: KernelClient, *, workspace: Path) -> dict[str, Any]:
    """体检 kernel 侧本工作区的投递任务残留。

    返回结构刻意做成纯数据，方便塞进投递报告（JSON），
    也方便 `--check-residue` 单独打印。
    """
    tasks = client.list_cron_tasks(workspace=workspace)
    stuck: list[dict[str, Any]] = []
    for task in tasks:
        status = str(task.get("status") or "").strip().lower()
        running = task.get("isRunning")
        if status in RESIDUE_STUCK_STATUSES and running is RESIDUE_STUCK_RUNNING:
            last_result = task.get("lastResult")
            next_fire = task.get("nextFireTime")
            next_fire_iso = _epoch_ms_to_iso(next_fire)
            stuck.append(
                {
                    "id": str(task.get("id") or ""),
                    "status": status,
                    "isRunning": running,
                    "cron": task.get("cron"),
                    "createdAt": task.get("createdAt"),
                    "sessionID": task.get("sessionID"),
                    "lastResult": last_result if isinstance(last_result, dict) else None,
                    "nextFireTime": next_fire,
                    "nextFireTimeLocal": next_fire_iso,
                    # nextFireTime 停在过去 = 手动触发没走完成回调的残留，
                    # 不是待触发的计划（真机实测：9 小时没有复发）。
                    "staleNextFire": bool(
                        next_fire_iso is not None
                        and datetime.fromisoformat(next_fire_iso) < datetime.now()
                    ),
                }
            )
    return {
        "total": len(tasks),
        "stuck_count": len(stuck),
        "stuck": stuck,
        "store_path": str(CRON_STORE_PATH) if CRON_STORE_PATH.exists() else None,
        "note": (
            "僵尸投递任务：kernel 侧的删除路由（POST /cag/cron/tasks/delete）"
            "会拒绝仍在调度器 in-flight 集合里的任务，"
            "需要用 --purge-residue 走「API + 文件级兜底」清理。"
            "实测不影响新投递（不会自己复发、不阻塞同目录建任务）。"
        )
        if stuck
        else "无僵尸投递任务",
    }


# kernel 侧删除路由拒绝时的错误文案（真机实测 2026-10-23）：
#   "任务正在执行，无法删除，如需操作，请先终止该任务"
# 这类任务卡在调度器的 in-flight 集合里 —— 手动触发后对方的会话中途死掉，
# fire 的 promise 永不落定，finally 里的 inFlight.delete 也就永远不执行。
RESIDUE_RUNNING_REFUSAL_MARKERS = ("正在执行", "cannot delete", "running")


def _residue_is_running_refusal(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in RESIDUE_RUNNING_REFUSAL_MARKERS)


def _read_cron_store() -> tuple[dict[str, Any] | None, str | None]:
    """读 kernel 的 cron 存储。返回 (payload, error)。"""
    try:
        payload = json.loads(CRON_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"读取 cron 存储失败: {exc}"
    if not isinstance(payload, dict):
        return None, "cron 存储结构异常：根节点不是对象"
    return payload, None


def _remove_from_cron_store(task_ids: list[str]) -> dict[str, Any]:
    """文件级兜底：把指定任务从 kernel 的 cron 存储里摘掉。

    kernel 的 cron 存储是**纯文件、无内存任务表**的（真机实测：kernel 二进制里
    `addTask`/`removeTask`/`expireTask` 每次都 `readTasks()` 再 `writeCronTasks()`，
    读写都落在磁盘上），并且有文件监听器在改动后 reload。
    所以运行中直接改这个文件是安全的 —— 不需要停 kernel。

    写入用「临时文件 + rename」（与 kernel 自己的做法一致），
    临时文件名带 pid，避免与 kernel 的临时文件撞名。

    **锁文件纪律**：`scheduled_tasks.lock` 是 kernel 自己的锁
    （由它按 {process, timestamp} 判定新鲜度）。
    本函数**只读它、绝不删它** —— 删掉别人持有的锁会让 kernel
    以为自己没在写，从而与本进程并发写同一份存储。
    检测到锁存在时，重新读一次存储再写，尽量把「读-写」窗口压到最小，
    并把冲突事实报给调用方。
    """
    if not CRON_STORE_PATH.exists():
        return {"ok": False, "error": f"cron 存储不存在: {CRON_STORE_PATH}"}

    lock_path = CRON_STORE_PATH.with_name("scheduled_tasks.lock")
    lock_conflict = lock_path.exists()

    payload, error = _read_cron_store()
    if error:
        return {"ok": False, "error": error}

    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return {"ok": False, "error": "cron 存储结构异常：缺少 tasks 列表"}

    if lock_conflict:
        # kernel 正在写：等它一下，然后**重新读**再算，避免用陈旧快照覆盖。
        time.sleep(0.2)
        payload, error = _read_cron_store()
        if error:
            return {"ok": False, "error": error, "lock_conflict": True}
        tasks = payload.get("tasks")
        if not isinstance(tasks, list):
            return {"ok": False, "error": "cron 存储结构异常：缺少 tasks 列表", "lock_conflict": True}

    targets = set(task_ids)
    kept = [t for t in tasks if str(t.get("id") or "") not in targets]
    removed = [str(t.get("id") or "") for t in tasks if str(t.get("id") or "") in targets]
    if not removed:
        return {"ok": True, "removed": [], "note": "目标不在存储里，无需改动", "lock_conflict": lock_conflict}

    payload["tasks"] = kept
    tmp_path = CRON_STORE_PATH.with_name(f"{CRON_STORE_PATH.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        tmp_path.replace(CRON_STORE_PATH)
    except OSError as exc:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return {"ok": False, "error": f"写回 cron 存储失败: {exc}", "lock_conflict": lock_conflict}
    return {"ok": True, "removed": removed, "kept": len(kept), "lock_conflict": lock_conflict}


def purge_cron_residue(
    client: KernelClient, *, workspace: Path, dry_run: bool = False
) -> dict[str, Any]:
    """清理本工作区下的僵尸投递任务。

    两条路：
    1. **kernel 官方删除路由** `POST /cag/cron/tasks/delete` —— 首选。
    2. **文件级兜底** —— 官方路由对「仍在 in-flight 集合里」的任务会拒绝，
       而这类任务恰恰就是手动触发后会话中途死掉的僵尸。

    注意：`/cag/*` 路由不在 kernel 的 OpenAPI（`/doc`）里，
    所以路由是否存在不能靠 `/doc` 判断 —— 要从 kernel 二进制里查。
    """
    residue = inspect_cron_residue(client, workspace=workspace)
    stuck_ids = [str(item.get("id") or "") for item in residue.get("stuck") or []]
    stuck_ids = [tid for tid in stuck_ids if tid]
    if not stuck_ids:
        return {"mode": "apply" if not dry_run else "dry-run", "purged": [], "residue": residue}

    if dry_run:
        return {
            "mode": "dry-run",
            "would_purge": stuck_ids,
            "residue": residue,
        }

    api_result: dict[str, Any] = {}
    api_refused: list[str] = []
    try:
        api_result = client.delete_cron_task(workspace=workspace, task_ids=stuck_ids)
    except BridgeError as exc:
        api_result = {"error": str(exc)}

    for item in api_result.get("results") or []:
        if not isinstance(item, dict):
            continue
        if item.get("success"):
            continue
        message = str(item.get("error") or "")
        if _residue_is_running_refusal(message):
            api_refused.append(str(item.get("taskId") or ""))

    file_result: dict[str, Any] = {}
    if api_refused:
        file_result = _remove_from_cron_store(api_refused)

    # 复核：官方路由与文件兜底都试过之后，以 kernel 自己的列表为准。
    after = inspect_cron_residue(client, workspace=workspace)
    still_stuck = [str(item.get("id") or "") for item in after.get("stuck") or []]
    return {
        "mode": "apply",
        "requested": stuck_ids,
        "api": api_result,
        "api_refused_running": api_refused,
        "file_fallback": file_result,
        "still_stuck": still_stuck,
        "purged": [tid for tid in stuck_ids if tid not in still_stuck],
        "residue_after": after,
    }


def resolve_direct_session(
    client: KernelClient, *, workspace: Path, explicit: str
) -> str | None:
    """挑一个可用的 CodeArts 会话（优先显式指定，其次工作区最近更新的）。"""
    if explicit and SESSION_ID_PATTERN.match(explicit.strip()):
        return explicit.strip()
    if explicit.strip():
        # 显式给了但不是 ses_ 形态 —— 可能是我们自己的内部会话 ID，不能直接用
        print(
            f"[codearts-bridge] 提示: 会话 ID {explicit.strip()!r} 不是 kernel 的 "
            "ses_ 形态，改用 cron 通道。",
            file=sys.stderr,
        )
        return None
    for session in client.list_sessions(workspace):
            session_id = str(session.get("id") or session.get("sessionID") or "").strip()
            if SESSION_ID_PATTERN.match(session_id):
                return session_id
    return None


# --------------------------------------------------------------------------
# 兜底：文件型 inbox
# --------------------------------------------------------------------------


def write_inbox_copy(
    *, workspace: Path, intervention_id: str, message: str, payload: dict[str, Any]
) -> str:
    """落一份审计/兜底副本到 codearts_inbox。"""
    inbox = workspace / INBOX_DIR
    inbox.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", intervention_id or "unknown")
    target = inbox / f"{safe_id}.md"
    header = (
        "---\n"
        f"intervention_id: {intervention_id}\n"
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}\n"
        f"delivery: {json.dumps(payload, ensure_ascii=False)}\n"
        "---\n\n"
    )
    target.write_text(header + message + "\n", encoding="utf-8")
    return str(target.relative_to(workspace))


def _setup_credentials(*, kernel_url: str) -> int:
    """一次性凭据引导：把 kernel 密码写进本机凭据文件后退出。

    **这个子命令由用户本人在本机终端执行**，AI 助手不应代跑：
    密码只在用户自己的 shell 与本机文件之间流动，不进入任何对话上下文、
    不进入 shell 历史、不进入仓库。

    写入目标 `~/.codeartsdoer/kernel-bridge.env`（0600），
    供后续 `resolve_credentials` 的常规路径（环境变量 → 凭据文件）读取，
    于是**日常投递不再需要** `--allow-process-env-discovery`。
    """
    resolved_url = kernel_url
    if not resolved_url:
        try:
            host, port, _pid = _discover_kernel()
            resolved_url = f"http://{host}:{port}"
        except BridgeError as exc:
            return _fail(str(exc))

    try:
        username, password = resolve_credentials(
            allow_process_env_discovery=True,
            kernel_url=resolved_url,
        )
    except BridgeError as exc:
        return _fail(
            f"{exc}\n"
            f"提示：也可手动创建 {CREDENTIAL_FILE}，写入一行 "
            "OPENCODE_SERVER_PASSWORD=<password>（用户名默认 codearts）。"
        )

    try:
        CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIAL_FILE.write_text(
            "# CodeArts Doer kernel 凭据（由 --setup-credentials 生成，权限 0600）\n"
            f"OPENCODE_SERVER_USERNAME={username}\n"
            f"OPENCODE_SERVER_PASSWORD={password}\n",
            encoding="utf-8",
        )
        CREDENTIAL_FILE.chmod(0o600)
    except OSError as exc:
        return _fail(f"写凭据文件失败: {exc}")

    # 刻意不回显密码本身，也不回显长度等可推断信息。
    print(f"[codearts-bridge] 凭据已写入 {CREDENTIAL_FILE}（权限 0600）")
    print(f"[codearts-bridge] 用户名: {username}")
    print("[codearts-bridge] 密码未回显。现在可以正常投递，无需 --allow-process-env-discovery。")
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------


def _check_residue_only(
    *, workspace: Path, kernel_url: str, purge: bool = False, dry_run: bool = False
) -> int:
    """残留体检（--check-residue）；带 --purge-residue 时顺便清理。"""
    resolved_url = kernel_url
    if not resolved_url:
        try:
            host, port, _pid = _discover_kernel()
            resolved_url = f"http://{host}:{port}"
        except BridgeError as exc:
            return _fail(str(exc))
    try:
        username, password = resolve_credentials(kernel_url=resolved_url)
        client = KernelClient(
            base_url=resolved_url, username=username, password=password
        )
        if purge:
            result = purge_cron_residue(client, workspace=workspace, dry_run=dry_run)
        else:
            result = inspect_cron_residue(client, workspace=workspace)
    except BridgeError as exc:
        return _fail(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把控制面 payload 投递到 CodeArts Doer (opencode kernel)"
    )
    parser.add_argument("--workspace", required=True, help="工作区根目录")
    parser.add_argument("--event-file", help="pull event 工件路径")
    parser.add_argument("--artifact-file", help="干预工件路径")
    parser.add_argument("--intervention-id", default="", help="干预 ID")
    parser.add_argument("--session-id", default="", help="目标 CodeArts 会话 ID")
    parser.add_argument("--assignee", default="", help="目标执行方")
    parser.add_argument("--reason-code", default="", help="干预原因码")
    parser.add_argument("--kernel-url", default="", help="kernel 地址（默认自动发现）")
    parser.add_argument("--agent", default=DEFAULT_AGENT, help="目标 agent 名称")
    parser.add_argument(
        "--model",
        default="",
        help="钉死本次投递使用的模型（modelID 或 providerID/modelID）",
    )
    parser.add_argument(
        "--model-fallback",
        default="",
        help=(
            "模型降级链：逗号分隔的候选列表（如 glm-5.3,deepseek-v4.1-flash,kimi-k3）。"
            "首选（--model）不可用时按顺序降级到下一个候选（每次重试用全新会话），"
            "全部候选失败则明确失败；只支持 new_session 通道"
        ),
    )
    parser.add_argument("--timeout", type=int, default=120, help="请求超时（秒）")
    parser.add_argument(
        "--channel",
        choices=("auto", "cron", "session", "new_session"),
        default="",
        help=(
            "投递通道；空=有 --model 走 new_session，否则走 cron（保持旧行为）；"
            "cron=由 kernel 新建会话（模型由 kernel 决定，**不能**配 --model）；"
            "session=直发已有会话；new_session=自建会话（模型可钉死）"
        ),
    )
    parser.add_argument(
        "--allow-process-env-discovery",
        action="store_true",
        help="允许从本机 kernel 进程环境读取 Basic Auth 凭据（默认关闭）",
    )
    parser.add_argument(
        "--setup-credentials",
        action="store_true",
        help=(
            "一次性凭据引导：把 kernel 密码写入 "
            f"{CREDENTIAL_FILE}（0600 权限）后退出，不做任何投递。"
            "由用户本人在本机执行——密码不经过任何 AI 会话。"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="只解析不发送")
    parser.add_argument(
        "--check-residue",
        action="store_true",
        help="只体检 kernel 侧本工作区的投递任务残留（僵尸 cron 任务），不做投递",
    )
    parser.add_argument(
        "--purge-residue",
        action="store_true",
        help="清理本工作区的僵尸投递任务（先走 kernel 官方删除路由，不行再文件级兜底）",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        return _fail(f"工作区不存在: {workspace}")

    if args.setup_credentials:
        return _setup_credentials(kernel_url=args.kernel_url)

    if args.check_residue or args.purge_residue:
        return _check_residue_only(
            workspace=workspace,
            kernel_url=args.kernel_url,
            purge=args.purge_residue,
            dry_run=args.dry_run,
        )

    try:
        message = extract_message(
            event_file=Path(args.event_file) if args.event_file else None,
            artifact_file=Path(args.artifact_file) if args.artifact_file else None,
        )
    except BridgeError as exc:
        return _fail(str(exc))

    # 模型降级链候选：首选 + fallback（去重、保持原序）。
    fallback_models = parse_fallback_models(args.model_fallback)
    if fallback_models and not args.model:
        return _fail(
            "--model-fallback 需要与 --model 一起使用：没有首选模型就谈不上降级链"
        )
    candidates = build_model_candidates(args.model, fallback_models)

    # 通道选择：默认保持旧行为（cron），只有钉了模型才走 new_session。
    channel = args.channel or ("new_session" if args.model else "cron")
    if channel == "cron" and (args.model or fallback_models):
        return _fail(
            "cron 通道由 kernel 决定模型，无法配合 --model/--model-fallback 使用；"
            "请改用 --channel new_session（自建会话 + 消息体带模型）"
        )
    if fallback_models and channel != "new_session":
        return _fail(
            "--model-fallback 只支持 new_session 通道"
            f"（降级重试必须用全新会话），当前通道: {channel}"
        )

    kernel_url = args.kernel_url
    if not kernel_url:
        try:
            host, port, _pid = _discover_kernel()
            kernel_url = f"http://{host}:{port}"
        except BridgeError as exc:
            return _fail(str(exc))

    if args.dry_run:
        result = {
            "mode": "dry-run",
            "kernel_url": kernel_url,
            "channel": channel,
            "model_requested": args.model,
            "model_fallback": fallback_models,
            "message_length": len(message),
            "message_preview": message[:500],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    try:
        username, password = resolve_credentials(
            allow_process_env_discovery=args.allow_process_env_discovery,
            kernel_url=kernel_url,
        )
    except BridgeError as exc:
        return _fail(str(exc))

    client = KernelClient(
        base_url=kernel_url,
        username=username,
        password=password,
        timeout=args.timeout,
        workspace=workspace,
    )

    # 模型降级链：候选 >= 2 才启用；单候选保持既有行为（失败就是失败，
    # 不做自动降级，也不改变"查不到模型 → 告警后如实不指定模型投递"）。
    use_fallback_chain = len(candidates) >= 2
    delivery: dict[str, Any]
    if use_fallback_chain:
        try:
            delivery, attempts = deliver_with_model_fallback(
                client,
                workspace=workspace,
                message=message,
                agent=args.agent,
                candidates=candidates,
            )
        except BridgeError as exc:
            return _fail(f"模型降级链投递失败: {exc}")
        if delivery is None:
            for attempt in attempts:
                print(
                    "[codearts-bridge] 候选模型 "
                    f"{attempt['model']} 失败: {attempt['error']}",
                    file=sys.stderr,
                )
            return _fail(
                f"全部 {len(candidates)} 个候选模型都失败，未做任何投递；"
                "拒绝降级成不指定模型（那等于假装钉住了模型）"
            )
    else:
        # 解析模型：查不到就如实降级并告警（不静默假装钉住了）。
        model_payload: dict[str, str] | None = None
        model_resolved = ""
        model_warning = ""
        if args.model:
            try:
                model_payload, model_resolved, model_warning = resolve_model(
                    client, spec=args.model
                )
            except BridgeError as exc:
                return _fail(f"解析模型失败: {exc}")

        try:
            if channel == "session":
                session_id = resolve_direct_session(
                    client, workspace=workspace, explicit=args.session_id
                )
                if not session_id:
                    return _fail(
                        "未找到可用的 CodeArts 会话，且指定了 --channel session"
                    )
                delivery = deliver_via_session(
                    client,
                    workspace=workspace,
                    message=message,
                    session_id=session_id,
                    agent=args.agent,
                    model=model_payload,
                )
            elif channel == "new_session":
                delivery = deliver_via_new_session(
                    client,
                    workspace=workspace,
                    message=message,
                    agent=args.agent,
                    model=model_payload,
                )
            elif channel == "cron":
                delivery = deliver_via_cron(
                    client, workspace=workspace, message=message
                )
            else:  # auto
                session_id = resolve_direct_session(
                    client, workspace=workspace, explicit=args.session_id
                )
                if session_id:
                    delivery = deliver_via_session(
                        client,
                        workspace=workspace,
                        message=message,
                        session_id=session_id,
                        agent=args.agent,
                        model=model_payload,
                    )
                elif model_payload:
                    delivery = deliver_via_new_session(
                        client,
                        workspace=workspace,
                        message=message,
                        agent=args.agent,
                        model=model_payload,
                    )
                else:
                    delivery = deliver_via_cron(
                        client, workspace=workspace, message=message
                    )
        except BridgeError as exc:
            return _fail(str(exc))

    delivery["intervention_id"] = args.intervention_id
    delivery["assignee"] = args.assignee
    if not use_fallback_chain:
        # 回执取证：model_used 是 kernel **实际**用掉的模型，model_applied 判断
        # 有没有静默回落（请求 A、实际 B → False）。
        delivery["model_requested"] = model_resolved or args.model
        delivery["model_used"] = extract_used_model(delivery.get("response"))
        if model_payload is None:
            delivery["model_applied"] = None
        elif not delivery["model_used"]:
            delivery["model_applied"] = None  # 回执里没带模型信息，无法证实
        else:
            delivery["model_applied"] = delivery["model_used"] == model_resolved
        # 降级留痕（与降级链统一口径）：fallback_used 的判据是
        # "实际干活的模型不是首选" —— 静默回落同样算（kernel 单方面换模型）。
        delivery["fallback_used"] = bool(
            delivery["model_used"]
            and delivery["model_requested"]
            and delivery["model_used"] != delivery["model_requested"]
        )
        if args.model:
            attempt_error = ""
            if model_payload is None:
                attempt_error = model_warning
            elif delivery["model_applied"] is False:
                attempt_error = (
                    f"静默回落：请求 {model_resolved}，"
                    f"实际用了 {delivery['model_used']}"
                )
            delivery["model_attempts"] = [
                {
                    "model": model_resolved or args.model,
                    "ok": (
                        delivery["model_applied"] is not False
                        and model_payload is not None
                    ),
                    "error": attempt_error,
                }
            ]
        else:
            delivery["model_attempts"] = []
        if model_warning:
            delivery["model_warning"] = model_warning
            print(f"[codearts-bridge] 警告: {model_warning}", file=sys.stderr)
    if delivery.get("model_applied") is False:
        print(
            "[codearts-bridge] 警告: 请求模型 "
            f"{delivery['model_requested']} 未生效，实际用了 "
            f"{delivery['model_used']}",
            file=sys.stderr,
        )
    if delivery.get("fallback_used"):
        print(
            "[codearts-bridge] 提示: 本次投递不是首选模型完成的（请求 "
            f"{delivery.get('model_requested') or '未指定'}，实际 "
            f"{delivery.get('model_used') or '未知'}）",
            file=sys.stderr,
        )
    # 投递回执落盘（R4）：调用方按 intervention_id 对单，从这里读
    # "实际用的模型"。写失败只告警，不影响投递成功（与 inbox 副本口径一致）。
    try:
        delivery["receipt_file"] = write_delivery_receipt(
            workspace=workspace, delivery=delivery
        )
    except OSError as exc:
        print(
            f"[codearts-bridge] 警告: 写投递回执失败（不影响本次投递）: {exc}",
            file=sys.stderr,
        )
    try:
        # 体检是辅助信息：失败不能影响已经成功的投递。
        delivery["cron_residue"] = inspect_cron_residue(client, workspace=workspace)
    except BridgeError as exc:
        print(f"[codearts-bridge] 提示: 残留体检失败（不影响本次投递）: {exc}", file=sys.stderr)
    try:
        delivery["inbox_copy"] = write_inbox_copy(
            workspace=workspace,
            intervention_id=args.intervention_id,
            message=message,
            payload={k: v for k, v in delivery.items() if k != "response"},
        )
    except OSError as exc:
        print(f"[codearts-bridge] 警告: 写 inbox 副本失败: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps({"mode": "apply", **delivery}, ensure_ascii=False, indent=2))
    else:
        model_note = delivery.get("model_used") or "未指定"
        fallback_note = "（已降级）" if delivery.get("fallback_used") else ""
        if delivery.get("channel") == "cron":
            print(
                f"[codearts-bridge] 已投递（cron 通道）task_id="
                f"{delivery.get('task_id', '')} 模型={model_note}{fallback_note}"
            )
        else:
            print(
                f"[codearts-bridge] 已投递到 CodeArts 会话 "
                f"{delivery.get('session_id', '')} 模型={model_note}{fallback_note}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
