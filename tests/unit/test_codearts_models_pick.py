"""check_codearts_models.py --pick 的单元测试。

--pick 语义：按 --models 的顺序逐个真实探测（复用 probe_model，
以回执 info.modelID 取证），返回第一个「实际模型 == 请求模型」的候选；
一个都不可用时退出码 1，且不输出任何模型 id（绝不回落到 kernel
默认模型来充数）。--pick 与 --watch 互斥。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCRIPT = REPO_ROOT / "scripts" / "codearts_bridge_deliver.py"
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_codearts_models.py"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load_script("check_codearts_models", CHECK_SCRIPT)
bridge = _load_script("codearts_bridge_deliver_for_pick", BRIDGE_SCRIPT)


def _patch_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """把凭据 / 客户端 / 桥接模块加载全部替换成桩（不发起真实 HTTP）。"""
    monkeypatch.setattr(bridge, "resolve_credentials", lambda **_: ("codearts", "pw"))
    monkeypatch.setattr(bridge, "KernelClient", lambda **_: object())
    monkeypatch.setattr(check, "_load_bridge", lambda: bridge)


def _patch_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        check,
        "list_models",
        lambda client, workspace: (
            {"glm-5.3": "inferhub-provider", "kimi-k3": "inferhub-provider"},
            "inferhub-provider/silent-default",
            {},
        ),
    )


def _probe_result(model_id: str, provider_id: str, *, usable: bool, used_model: str) -> dict[str, Any]:
    return {
        "model": model_id,
        "provider": provider_id,
        "usable": usable,
        "http_status": 200 if usable else None,
        "latency_ms": 5,
        "reply": "OK" if usable else "",
        "used_model": used_model,
        "error": "" if usable else "402: quota exhausted",
    }


def test_pick_returns_first_model_with_matching_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 6：静默回落的候选不算可用，返回第一个「实际==请求」的候选。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)

    def _fake_probe(client, *, model_id, provider_id, workspace, timeout):
        # glm-5.3 真实推理成功但回执落在别的模型上（静默回落）→ 不算可用。
        if model_id == "glm-5.3":
            return _probe_result(
                model_id, provider_id, usable=True, used_model="inferhub-provider/silent-default"
            )
        return _probe_result(
            model_id, provider_id, usable=True, used_model=f"{provider_id}/{model_id}"
        )

    monkeypatch.setattr(check, "probe_model", _fake_probe)

    code = check.main(
        [
            "--pick",
            "--models", "glm-5.3", "kimi-k3",
            "--workspace", str(tmp_path),
            "--json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["picked"] == "inferhub-provider/kimi-k3"


def test_pick_outputs_plain_model_without_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """非 JSON 模式：stdout 只输出选中的模型（可直接供 shell 捕获）。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)
    monkeypatch.setattr(
        check,
        "probe_model",
        lambda client, *, model_id, provider_id, workspace, timeout: _probe_result(
            model_id, provider_id, usable=True, used_model=f"{provider_id}/{model_id}"
        ),
    )

    code = check.main(
        ["--pick", "--models", "glm-5.3", "kimi-k3", "--workspace", str(tmp_path)]
    )

    assert code == 0
    assert capsys.readouterr().out.strip() == "inferhub-provider/glm-5.3"


def test_pick_fails_without_any_usable_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """用例 7：全部不可用 → 退出码 1，输出里没有任何模型 id。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)
    monkeypatch.setattr(
        check,
        "probe_model",
        lambda client, *, model_id, provider_id, workspace, timeout: _probe_result(
            model_id, provider_id, usable=False, used_model=""
        ),
    )

    code = check.main(
        ["--pick", "--models", "glm-5.3", "kimi-k3", "--workspace", str(tmp_path)]
    )

    assert code == 1
    out = capsys.readouterr().out
    assert "glm-5.3" not in out
    assert "kimi-k3" not in out
    assert "silent-default" not in out  # 不回落到 kernel 默认模型充数


def test_pick_fails_without_any_usable_model_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """JSON 模式的全失败：picked 为 null，输出不含任何模型 id。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)
    monkeypatch.setattr(
        check,
        "probe_model",
        lambda client, *, model_id, provider_id, workspace, timeout: _probe_result(
            model_id, provider_id, usable=False, used_model=""
        ),
    )

    code = check.main(
        [
            "--pick",
            "--models", "glm-5.3", "kimi-k3",
            "--workspace", str(tmp_path),
            "--json",
        ]
    )

    assert code == 1
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["picked"] is None
    assert payload["probed"] == 2
    assert "glm-5.3" not in out
    assert "kimi-k3" not in out


def test_pick_skips_models_missing_from_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """注册表里没有的候选直接跳过（探测都省了），不算可用。"""
    _patch_kernel(monkeypatch)
    monkeypatch.setattr(
        check,
        "list_models",
        lambda client, workspace: ({"kimi-k3": "inferhub-provider"}, "", {}),
    )
    monkeypatch.setattr(
        check,
        "probe_model",
        lambda client, *, model_id, provider_id, workspace, timeout: _probe_result(
            model_id, provider_id, usable=True, used_model=f"{provider_id}/{model_id}"
        ),
    )

    code = check.main(
        ["--pick", "--models", "glm-5.3", "kimi-k3", "--workspace", str(tmp_path)]
    )

    assert code == 0
    assert capsys.readouterr().out.strip() == "inferhub-provider/kimi-k3"


def test_pick_stops_at_first_usable_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """找到第一个可用候选就停止，不再探测后面的（--pick 是挑选不是全测）。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)
    probed: list[str] = []

    def _fake_probe(client, *, model_id, provider_id, workspace, timeout):
        probed.append(model_id)
        return _probe_result(
            model_id, provider_id, usable=True, used_model=f"{provider_id}/{model_id}"
        )

    monkeypatch.setattr(check, "probe_model", _fake_probe)

    code = check.main(
        ["--pick", "--models", "glm-5.3", "kimi-k3", "--workspace", str(tmp_path)]
    )

    assert code == 0
    assert probed == ["glm-5.3"]


def test_pick_and_watch_are_mutually_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """--pick 与 --watch 同时给 → 退出码 2，报错说明。"""
    _patch_kernel(monkeypatch)
    _patch_registry(monkeypatch)

    code = check.main(
        ["--pick", "--watch", "300", "--workspace", str(tmp_path)]
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "互斥" in err


if __name__ == "__main__":
    pytest.main([__file__])
