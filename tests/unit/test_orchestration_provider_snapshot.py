"""编排配置的两个命名空间，以及「快照不是可用性」的边界（台账 N44）。

背景：`provider_registry` 同时被两种键当字典用——

* **assignee 命名空间**（`claude_code` / `codearts_agent` / `codex`）：
  由 `ack_protocol._ACK_PREFIX` 与 `SUPPORTED_ASSIGNEES` 定义，
  承载 `fallback_ack_prefix`。`config/agent-orchestration.json` 用的是这套。
* **探测器命名空间**（`claude_code` / `codex_cli` / `gemini_cli` / `codearts_agent`）：
  由 `AgentProvider.PROVIDER_DETECTORS` 定义，`detect_providers()` 写到
  `self.providers` 用的是这套。

两套只有三个键同名，所以「看着差不多」是假象。这里钉死两条：
① `save()` 不许把 assignee 键整片抹掉；
② 冷启动向导必须先跑探针再取可用列表，不能拿落盘快照当当前可用性。
"""

import json
from pathlib import Path

from ai_collab import orchestration as orch
from ai_collab.ack_protocol import _ACK_PREFIX
from ai_collab.orchestration import OrchestrationConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_CONFIG = REPO_ROOT / "config" / "agent-orchestration.json"


def _workspace_with_repo_config(tmp_path: Path) -> Path:
    """复制真实仓库配置到临时工作区——真实数据比手工构造的夹具更能抓住回归。"""
    workspace = tmp_path / "ws"
    (workspace / "config").mkdir(parents=True)
    (workspace / "config" / "agent-orchestration.json").write_text(
        REPO_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return workspace


class TestProviderRegistryNamespaces:
    def test_save_after_detect_keeps_assignee_namespace_entries(self, tmp_path, monkeypatch):
        """`load → detect_providers → save` 不许抹掉 `codex`。

        变异检查：把 `save()` 里的字典合并改回整体替换
        （`self.config["provider_registry"] = {pid: p.to_dict() ...}`），
        本用例立刻红——`codex` 会连同 ACK 前缀 `O` 一起消失。
        """
        for key in ("VSCODE_PID", "CODEARTS_SESSION"):
            monkeypatch.delenv(key, raising=False)

        workspace = _workspace_with_repo_config(tmp_path)
        config = OrchestrationConfig(workspace_path=str(workspace))
        assert config.load() is True
        before = set(config.config["provider_registry"])
        assert set(_ACK_PREFIX) <= before, "夹具前提：仓库配置必须用 assignee 命名空间"

        config.detect_providers()
        assert config.save() is True

        after = json.loads((workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8"))
        registry = after["provider_registry"]
        for assignee, prefix in _ACK_PREFIX.items():
            assert assignee in registry, f"save 抹掉了 assignee 键 {assignee}"
            assert registry[assignee].get("fallback_ack_prefix") == prefix, (
                f"{assignee} 的 ACK 前缀被改写成 {registry[assignee].get('fallback_ack_prefix')!r}"
            )

    def test_save_after_detect_still_writes_probe_results(self, tmp_path, monkeypatch):
        """合并不等于不写：探测器键该更新的还是要更新。"""
        for key in ("VSCODE_PID", "CODEARTS_SESSION"):
            monkeypatch.delenv(key, raising=False)

        workspace = _workspace_with_repo_config(tmp_path)
        config = OrchestrationConfig(workspace_path=str(workspace))
        config.load()
        config.detect_providers()
        config.save()

        registry = json.loads((workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8"))[
            "provider_registry"
        ]
        assert registry["codearts_agent"]["connection_status"] == "unavailable"
        assert "codex_cli" in registry, "探测器键应当被写进来"
        assert registry["codex_cli"]["connection_status"] == "unavailable"
        # 已知小瑕疵（不在本条范围）：探测器键写进来时 fallback_ack_prefix 是空串，
        # 因为 DEFAULT_FALLBACK_ACK_PREFIX 按 assignee 建键（codex 而非 codex_cli）。
        # 空串在 role_prefix.resolve_hints 里是 falsy，会退回静态兜底表，故无害。
        assert registry["codex_cli"].get("fallback_ack_prefix") in ("", None)


class TestColdStartWizardProbing:
    @staticmethod
    def _drive(wizard, monkeypatch, answers):
        feed = iter(answers)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(feed, "n"))
        return wizard.run()

    def test_wizard_probes_before_reading_available(self, tmp_path, monkeypatch):
        """向导必须先 `detect_providers()` 再 `get_available_providers()`。

        变异检查：删掉 `run()` 里那行 `self.config.detect_providers()`，
        顺序断言立刻红。
        """
        order: list[str] = []
        real_detect = OrchestrationConfig.detect_providers
        real_available = OrchestrationConfig.get_available_providers

        def spy_detect(self):
            order.append("detect")
            return real_detect(self)

        def spy_available(self):
            order.append("available")
            return real_available(self)

        monkeypatch.setattr(OrchestrationConfig, "detect_providers", spy_detect)
        monkeypatch.setattr(OrchestrationConfig, "get_available_providers", spy_available)

        config = OrchestrationConfig(workspace_path=str(tmp_path / "ws"))
        config.load()
        self._drive(orch.ColdStartWizard(config), monkeypatch, ["3", "n"])

        assert order[:2] == ["detect", "available"], f"向导的探测/取用顺序不对：{order}"

    def test_wizard_does_not_trust_stale_snapshot(self, tmp_path, monkeypatch, capsys):
        """快照说 codearts 可用（一个该 provider 永远产出不了的值），探针说不可用。"""
        for key in ("VSCODE_PID", "CODEARTS_SESSION"):
            monkeypatch.delenv(key, raising=False)

        workspace = _workspace_with_repo_config(tmp_path)
        config_file = workspace / "config" / "agent-orchestration.json"
        payload = json.loads(config_file.read_text(encoding="utf-8"))
        payload["provider_registry"]["codearts_agent"]["connection_status"] = "detected"
        config_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        config = OrchestrationConfig(workspace_path=str(workspace))
        config.load()
        self._drive(orch.ColdStartWizard(config), monkeypatch, ["3", "n"])

        out = capsys.readouterr().out
        assert "检测到" in out
        available_block = out.split("检测到", 1)[1].split("[步骤 2]", 1)[0]
        assert "CodeArts Agent" not in available_block, f"向导把落盘快照当成了当前可用性：\n{available_block}"
        assert "Claude Code" in available_block
