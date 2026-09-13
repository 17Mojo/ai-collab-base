#!/usr/bin/env python3
"""VSCode Native Host - bridges Chrome ext <-> VSCode ext.

Supports two protocols:
1. --stdio-json: line-delimited JSON
2. native: 4-byte little-endian length prefix + JSON payload
"""
import json
import socket
import struct
import sys
from urllib.parse import urlparse


def read_stdio_message():
    line = sys.stdin.readline()
    if not line:
        raise ValueError("empty stdin")
    return json.loads(line)


def read_native_message():
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        raise ValueError("incomplete length prefix")
    msg_len = struct.unpack("<I", raw_len)[0]
    body = sys.stdin.buffer.read(msg_len)
    if len(body) < msg_len:
        raise ValueError("incomplete message body")
    return json.loads(body.decode("utf-8"))


def probe_backend(backend_url, timeout_ms):
    """Probe backend health via TCP connect (lightweight)."""
    try:
        parsed = urlparse(backend_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        timeout = max(0.05, timeout_ms / 1000.0)
        with socket.create_connection((host, port), timeout=timeout):
            return "ok"
    except Exception:
        return "degraded"


def handle_message(msg, transport):
    action = msg.get("action", "")
    src = msg.get("source", "")

    if action == "ping":
        return {
            "ok": True,
            "message": "pong",
            "transport": transport,
        }
    elif action == "status":
        backend_url = msg.get("backend_url", "")
        timeout_ms = msg.get("timeout_ms", 500)
        probe = probe_backend(backend_url, timeout_ms)
        return {
            "ok": True,
            "transport": transport,
            "status": probe,
            "backend": {"url": backend_url.rstrip("/") + "/health"},
        }
    elif action == "forward":
        if "payload" not in msg:
            return {
                "ok": False,
                "error": {"code": "MISSING_PAYLOAD", "message": "payload required"},
                "transport": transport,
            }
        return {"ok": True, "transport": transport, "forwarded": True}
    else:
        return {
            "ok": False,
            "error": {"code": "UNKNOWN_ACTION", "message": f"unknown action: {action}"},
            "transport": transport,
        }


def main_stdio_json():
    try:
        msg = read_stdio_message()
        resp = handle_message(msg, "stdio-json")
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
        return 0  # always 0; errors reported in payload
    except Exception as e:
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)}) + "\n")
        return 1


def main_native():
    try:
        msg = read_native_message()
        resp = handle_message(msg, "native-messaging")
        body = json.dumps(resp).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("<I", len(body)) + body)
        sys.stdout.buffer.flush()
        return 0  # always 0; errors reported in payload
    except Exception as e:
        body = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("<I", len(body)) + body)
        return 1


def main():
    if "--stdio-json" in sys.argv:
        return main_stdio_json()
    return main_native()


if __name__ == "__main__":
    sys.exit(main())
