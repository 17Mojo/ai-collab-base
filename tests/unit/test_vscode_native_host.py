import json
import struct
import subprocess
import sys
from pathlib import Path

HOST_SCRIPT = (
    Path(__file__).resolve().parents[2] / "products" / "vscode-extension" / "native_host.py"
)


def run_stdio(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOST_SCRIPT), "--stdio-json"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def run_native(payload: dict) -> dict:
    encoded = json.dumps(payload).encode("utf-8")
    framed = struct.pack("<I", len(encoded)) + encoded

    proc = subprocess.run(
        [sys.executable, str(HOST_SCRIPT)],
        input=framed,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    assert len(proc.stdout) >= 4
    response_length = struct.unpack("<I", proc.stdout[:4])[0]
    body = proc.stdout[4 : 4 + response_length]
    assert len(body) == response_length
    return json.loads(body.decode("utf-8"))


class TestVSCodeNativeHost:
    def test_stdio_ping(self):
        response = run_stdio({"action": "ping", "source": "pytest"})
        assert response["ok"] is True
        assert response["message"] == "pong"
        assert response["transport"] == "stdio-json"

    def test_stdio_forward_requires_payload(self):
        response = run_stdio({"action": "forward", "source": "pytest"})
        assert response["ok"] is False
        assert response["error"]["code"] == "MISSING_PAYLOAD"

    def test_stdio_status_includes_backend_probe(self):
        response = run_stdio(
            {
                "action": "status",
                "source": "pytest",
                "backend_url": "http://127.0.0.1:9",
                "timeout_ms": 200,
            }
        )
        assert response["ok"] is True
        assert response["status"] in {"ok", "degraded"}
        assert "backend" in response
        assert response["backend"]["url"].endswith("/health")

    def test_native_framed_ping(self):
        response = run_native({"action": "ping", "source": "pytest"})
        assert response["ok"] is True
        assert response["transport"] == "native-messaging"
