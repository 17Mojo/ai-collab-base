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
INBOX_DIR = "collaboration/monitoring/codearts_inbox"
SESSION_REGISTRY = "logs/session_registry_state.json"

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


class KernelClient:
    """CodeArts Doer kernel（opencode）HTTP 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
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

    def send_message(
        self,
        *,
        session_id: str,
        workspace: Path,
        message: str,
        agent: str,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "parts": [{"type": "text", "text": message}],
            "agent": agent,
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
) -> dict[str, Any]:
    """快路径：直发已有会话。"""
    response = client.send_message(
        session_id=session_id, workspace=workspace, message=message, agent=agent
    )
    return {"channel": "session", "session_id": session_id, "response": response}


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
    parser.add_argument("--timeout", type=int, default=120, help="请求超时（秒）")
    parser.add_argument(
        "--channel",
        choices=("auto", "cron", "session"),
        default="cron",
        help="投递通道；cron=由 kernel 新建会话（默认），session=直发已有会话，auto=有会话走 session",
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
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        return _fail(f"工作区不存在: {workspace}")

    if args.setup_credentials:
        return _setup_credentials(kernel_url=args.kernel_url)

    try:
        message = extract_message(
            event_file=Path(args.event_file) if args.event_file else None,
            artifact_file=Path(args.artifact_file) if args.artifact_file else None,
        )
    except BridgeError as exc:
        return _fail(str(exc))

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
            "channel": args.channel,
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
    )

    try:
        if args.channel == "session":
            session_id = resolve_direct_session(
                client, workspace=workspace, explicit=args.session_id
            )
            if not session_id:
                return _fail("未找到可用的 CodeArts 会话，且指定了 --channel session")
            delivery = deliver_via_session(
                client,
                workspace=workspace,
                message=message,
                session_id=session_id,
                agent=args.agent,
            )
        elif args.channel == "cron":
            delivery = deliver_via_cron(client, workspace=workspace, message=message)
        else:
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
                )
            else:
                delivery = deliver_via_cron(client, workspace=workspace, message=message)
    except BridgeError as exc:
        return _fail(str(exc))

    delivery["intervention_id"] = args.intervention_id
    delivery["assignee"] = args.assignee
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
        if delivery.get("channel") == "cron":
            print(
                f"[codearts-bridge] 已投递（cron 通道）task_id="
                f"{delivery.get('task_id', '')}"
            )
        else:
            print(
                f"[codearts-bridge] 已投递到 CodeArts 会话 "
                f"{delivery.get('session_id', '')}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
