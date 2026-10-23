#!/usr/bin/env python3
"""探测 CodeArts Doer kernel（opencode）上各模型是否真的可用。

为什么需要这个脚本
-----------------
kernel 的 `GET /provider` 会把模型注册表列出来，但**注册 ≠ 可用**：
额度耗尽、key 失效、后端下线、模型下线，注册表里都还在。
只有真正发一次推理请求才知道能不能用。

本脚本对每个目标模型做一次**最小真实推理**（创建会话 → 指定 model → 发一句话），
记录 HTTP 状态、耗时与错误摘要，输出表格。

用法
----
    python3 scripts/check_codearts_models.py                    # 测默认三个
    python3 scripts/check_codearts_models.py --models glm-5.3 kimi-k3
    python3 scripts/check_codearts_models.py --watch 300        # 每 5 分钟一轮
    python3 scripts/check_codearts_models.py --json             # 机器可读
    python3 scripts/check_codearts_models.py --pick --models glm-5.3 kimi-k3
                                                                # 返回第一个真可用的模型

凭据
----
复用 `scripts/codearts_bridge_deliver.py` 自带的 `resolve_credentials()`：
密码只在进程内用于 HTTP Basic，**不会打印、不落盘**。

退出码
------
0 = 全部可用；1 = 有模型不可用；2 = 探测本身失败（连不上 kernel 等）。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# 图片里那三个模型对应的 kernel 注册表 ID
DEFAULT_MODELS = ("glm-5.3", "deepseek-v4.1-flash", "kimi-k3")

# 兼容不同 provider 的模型命名（图片显示名 -> 注册表 ID）
ALIASES = {
    "glm-5.3": "glm-5.3",
    "glm5.3": "glm-5.3",
    "deepseek-v4.1-flash": "deepseek-v4.1-flash",
    "deepseek-v4.1": "deepseek-v4.1-flash",
    "kimi-k3": "kimi-k3",
    "kimi3": "kimi-k3",
}

PROBE_PROMPT = "Reply with exactly one word: OK"


def _load_bridge():
    spec = importlib.util.spec_from_file_location(
        "codearts_bridge_deliver", REPO_ROOT / "scripts" / "codearts_bridge_deliver.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _normalize(name: str) -> str:
    return ALIASES.get(name.strip().lower(), name.strip().lower())


def _extract_text(payload: Any) -> str:
    """从 message 响应里尽量抠出文本；抠不出就返回空串。"""
    if not isinstance(payload, dict):
        return ""
    chunks: list[str] = []
    for key in ("parts", "content"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
    if not chunks:
        info = payload.get("info")
        if isinstance(info, dict) and isinstance(info.get("error"), dict):
            return ""
    return " ".join(chunks).strip()


def _extract_error(payload: Any) -> str:
    """opencode 常把 provider 报错放在 body 里但仍返回 HTTP 200。"""
    if not isinstance(payload, dict):
        return ""
    for holder in (payload, payload.get("info")):
        if not isinstance(holder, dict):
            continue
        error = holder.get("error")
        if isinstance(error, dict):
            name = error.get("name") or error.get("type") or "Error"
            data = error.get("data") or {}
            detail = ""
            if isinstance(data, dict):
                detail = str(data.get("message") or data.get("detail") or "")
            return f"{name}: {detail}".strip(": ")
        if isinstance(error, str) and error.strip():
            return error.strip()
    return ""


def _extract_model(payload: Any) -> str:
    """从回执里读出 kernel 实际使用的模型（防止静默回落到默认模型也算成功）。"""
    if not isinstance(payload, dict):
        return ""
    info = payload.get("info")
    holder = info if isinstance(info, dict) else payload
    provider_id = holder.get("providerID") or holder.get("providerId") or ""
    model_id = holder.get("modelID") or holder.get("modelId") or ""
    if provider_id and model_id:
        return f"{provider_id}/{model_id}"
    return str(model_id or "")


def _session_id(payload: Any) -> str:
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


def list_models(client, workspace: Path) -> tuple[dict[str, str], str]:
    """返回 (model_id -> provider_id 映射, 默认模型)。

    注册表**按工作区目录查**（真机实测 2026-10-23 18:31）：kernel 重启后，
    不带 directory 的 `GET /provider` 返回空注册表，带
    `?directory=<工作区>` 才拿得到该项目的 provider 与模型。查空会被误判成
    "模型不在注册表"，于是所有候选都判不可用 —— 看起来像模型全挂了，
    实际是查错了作用域。查不到再退回无目录查询（兼容全局作用域的老 kernel）。
    """
    payload = client.request("GET", "/provider", query={"directory": str(workspace)})
    mapping: dict[str, str] = {}
    default = ""
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
    if not mapping:
        # 作用域查不到 → 退回全局作用域再查一次（老 kernel 把 provider 配在全局）。
        payload = client.request("GET", "/provider")
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
                        str(item.get("id"))
                        for item in models
                        if isinstance(item, dict) and item.get("id")
                    ]
                else:
                    items = []
                for model_id in items:
                    mapping[str(model_id)] = provider_id
    defaults = payload.get("default") if isinstance(payload, dict) else None
    if isinstance(defaults, dict) and defaults:
        provider_id, model_id = next(iter(defaults.items()))
        default = f"{provider_id}/{model_id}"
    # 注册表键大小写敏感（如 "GLM-5.2" 与 "glm-5.3" 混用），加不区分大小写的兜底
    mapping_lower = {k.lower(): k for k in mapping}
    return mapping, default, mapping_lower


def probe_model(client, *, model_id: str, provider_id: str, workspace: Path, timeout: int) -> dict[str, Any]:
    """真实发一次最小推理，返回探测结果。"""
    result: dict[str, Any] = {
        "model": model_id,
        "provider": provider_id,
        "usable": False,
        "http_status": None,
        "latency_ms": None,
        "reply": "",
        "used_model": "",
        "error": "",
    }
    started = time.monotonic()
    try:
        created = client.request(
            "POST", "/session", query={"directory": str(workspace)}, body={"title": "model-probe"}
        )
        session_id = _session_id(created)
        if not session_id:
            result["error"] = "创建会话失败：响应里没有 session id"
            return result

        body = {
            "parts": [{"type": "text", "text": PROBE_PROMPT}],
            "agent": "build",
            "model": {"providerID": provider_id, "modelID": model_id},
        }
        response = client.request(
            "POST",
            f"/session/{session_id}/message",
            query={"directory": str(workspace)},
            body=body,
        )
        result["http_status"] = response.get("http_status")
        result["used_model"] = _extract_model(response)
        error = _extract_error(response)
        reply = _extract_text(response)
        if error:
            result["error"] = error[:300]
        elif reply:
            result["usable"] = True
            result["reply"] = reply[:80]
        else:
            result["error"] = "无回复文本且无显式错误（可能被上游静默拒绝）"
    except Exception as exc:  # noqa: BLE001 - 探测脚本要把任何失败都记下来
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    finally:
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
    return result


def render_table(results: list[dict[str, Any]], default_model: str) -> str:
    header = f"{'模型':<22} {'可用':<6} {'耗时':>8} {'实际模型（回执取证）':<34} 说明"
    lines = [header, "-" * 110]
    for item in results:
        flag = "✅" if item["usable"] else "❌"
        note = item["reply"] or item["error"] or ""
        used = item.get("used_model") or ""
        if used and used != f"{item['provider']}/{item['model']}":
            note = f"[实际用 {used}] " + note
        used = item.get("used_model") or "-"
        lines.append(
            f"{item['model']:<22} {flag:<6} {item['latency_ms']:>7}ms  {used:<34} {note}"
        )
    lines.append("-" * 110)
    ok = sum(1 for item in results if item["usable"])
    lines.append(f"可用 {ok}/{len(results)}；kernel 默认模型：{default_model or '未知'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="探测 kernel 上各模型是否真的可用")
    parser.add_argument("--models", nargs="*", default=list(DEFAULT_MODELS), help="要探测的模型 ID")
    parser.add_argument("--workspace", default=str(REPO_ROOT), help="工作区目录（默认仓库根）")
    parser.add_argument("--timeout", type=int, default=120, help="单次请求超时秒数")
    parser.add_argument("--watch", type=int, default=0, metavar="SECONDS", help="按间隔重复探测（0=只跑一轮）")
    parser.add_argument(
        "--pick",
        action="store_true",
        help=(
            "按 --models 的顺序逐个真实探测，返回第一个"
            "\"实际模型 == 请求模型\"的候选（providerID/modelID）；"
            "一个都不可用时退出码 1，且不输出任何模型 id"
        ),
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)
    if args.pick and args.watch:
        print(
            "--pick 与 --watch 互斥：--pick 只做单轮挑选（找到第一个可用即返回），"
            "--watch 是持续监测；请去掉其中一个",
            file=sys.stderr,
        )
        return 2

    workspace = Path(args.workspace).resolve()
    targets = [_normalize(name) for name in args.models]
    bridge = _load_bridge()
    try:
        username, password = bridge.resolve_credentials()
    except Exception as exc:  # noqa: BLE001
        print(f"无法获取 kernel 凭据：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    client = bridge.KernelClient(
        base_url=bridge.DEFAULT_KERNEL_URL,
        username=username,
        password=password,
        timeout=args.timeout,
        workspace=workspace,
    )

    while True:
        try:
            registry, default_model, registry_lower = list_models(client, workspace)
        except Exception as exc:  # noqa: BLE001
            print(f"读取 kernel 模型注册表失败：{type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

        results = []
        picked = ""
        for model_id in targets:
            provider_id = registry.get(model_id)
            if not provider_id:
                canonical = registry_lower.get(model_id.lower())
                if canonical:
                    model_id = canonical
                    provider_id = registry.get(canonical)
            if not provider_id:
                results.append(
                    {
                        "model": model_id,
                        "provider": "-",
                        "usable": False,
                        "http_status": None,
                        "latency_ms": 0,
                        "reply": "",
                        "used_model": "",
                        "error": "未在 kernel 注册表中找到该模型",
                    }
                )
                continue
            results.append(
                probe_model(
                    client,
                    model_id=model_id,
                    provider_id=provider_id,
                    workspace=workspace,
                    timeout=args.timeout,
                )
            )
            if args.pick:
                requested = f"{provider_id}/{model_id}"
                item = results[-1]
                # "真可用"= 真实推理成功且回执取证实际模型 == 请求模型
                # （注册表里有 ≠ 可用；静默回落到默认模型也不算）。
                if item["usable"] and item["used_model"] == requested:
                    picked = requested
                    break

        if args.pick:
            if picked:
                if args.json:
                    print(
                        json.dumps(
                            {"picked": picked, "probed": len(results)},
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                else:
                    print(picked)
                return 0
            # 一个都不可用：退出码 1，不输出任何模型 id
            # （绝不回落到 kernel 默认模型来充数）。
            if args.json:
                print(
                    json.dumps(
                        {"picked": None, "probed": len(results)},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(f"无可用模型：{len(results)} 个候选全部失败")
            return 1

        if args.json:
            print(json.dumps({"default_model": default_model, "results": results}, ensure_ascii=False, indent=2))
        else:
            print(render_table(results, default_model))

        if not args.watch:
            return 0 if all(item["usable"] for item in results) else 1
        time.sleep(max(30, args.watch))


if __name__ == "__main__":
    raise SystemExit(main())
