"""CLI `orchestration` 子命令组测试。

CLAUDE.md / PROTOCOL.md 承诺的 `python3 -m ai_collab.cli orchestration ...`
此前从未接入 CLI，这里覆盖其 status / roles / snapshot / history 行为。
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_collab import cli
from ai_collab.orchestration import OrchestrationConfig


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        config = OrchestrationConfig(workspace_path=str(workspace))
        config.load()
        config.save()
        yield workspace


def _args(workspace, **kwargs):
    payload = {"workspace": str(workspace), "subcommand": "status", "action": None}
    payload.update(kwargs)
    return SimpleNamespace(**payload)


class TestOrchestrationStatus:
    def test_status_lists_role_bindings(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="status"))

        assert result == 0
        out = capsys.readouterr().out
        assert "AGENT_EXEC" in out
        assert "AGENT_ARCH" in out
        assert "AGENT_TEST" in out

    def test_status_shows_command_prefixes(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="status"))

        assert result == 0
        out = capsys.readouterr().out
        assert "X.RUN" in out
        assert "A.RUN" in out
        assert "C.RUN" in out

    def test_unknown_subcommand_returns_error(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="nope"))

        assert result == 1
        assert "未知子命令" in capsys.readouterr().out


class TestOrchestrationRoles:
    def test_roles_list_defaults_to_list(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="roles"))

        assert result == 0
        assert "AGENT_EXEC" in capsys.readouterr().out

    def test_activate_persists_binding_to_disk(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_EXEC",
                provider="codearts_agent",
                model_variant=None,
            )
        )

        assert result == 0
        assert "AGENT_EXEC" in capsys.readouterr().out

        reloaded = OrchestrationConfig(workspace_path=str(temp_workspace))
        reloaded.load()
        assert reloaded.roles["AGENT_EXEC"].binding["provider"] == "codearts_agent"

    def test_activate_preserves_provider_registry(self, temp_workspace):
        registry_before = json.loads(
            (temp_workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8")
        ).get("provider_registry", {})

        cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_EXEC",
                provider="codearts_agent",
                model_variant=None,
            )
        )

        registry_after = json.loads(
            (temp_workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8")
        ).get("provider_registry", {})

        # load→save 往返不能抹掉 provider 元数据（如 fallback_ack_prefix）
        assert set(registry_after) == set(registry_before)
        assert registry_after["codearts_agent"]["display_name"] == "CodeArts Agent"
        assert registry_after["codearts_agent"]["fallback_ack_prefix"] == "A"

    def test_activate_rejects_unknown_role(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_NOPE",
                provider="codearts_agent",
                model_variant=None,
            )
        )

        assert result == 1
        assert "角色不存在" in capsys.readouterr().out

    def test_activate_requires_role_and_provider(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="",
                provider="",
                model_variant=None,
            )
        )

        assert result == 1
        assert "需要 --role-id 与 --provider" in capsys.readouterr().out


class TestOrchestrationSnapshot:
    def test_snapshot_create_writes_snapshot(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="snapshot", action="create", note="测试点"))

        assert result == 0
        assert "快照已创建" in capsys.readouterr().out

        payload = json.loads((temp_workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8"))
        assert len(payload["snapshots"]) == 1

    def test_snapshot_does_not_nest_previous_snapshots(self, temp_workspace):
        cli.cmd_orchestration(_args(temp_workspace, subcommand="snapshot", action="create", note="第一次"))
        cli.cmd_orchestration(_args(temp_workspace, subcommand="snapshot", action="create", note="第二次"))

        payload = json.loads((temp_workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8"))
        for snapshot in payload["snapshots"]:
            # 快照不复制 snapshots / history，否则配置体积指数膨胀
            assert "snapshots" not in snapshot["config_copy"]
            assert "history" not in snapshot["config_copy"]

    def test_rollback_restores_binding_and_persists(self, temp_workspace, capsys):
        cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_EXEC",
                provider="codearts_agent",
                model_variant=None,
            )
        )
        cli.cmd_orchestration(_args(temp_workspace, subcommand="snapshot", action="create", note="回滚点"))
        cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_EXEC",
                provider="claude_code",
                model_variant="sonnet",
            )
        )

        payload = json.loads((temp_workspace / "config" / "agent-orchestration.json").read_text(encoding="utf-8"))
        target = payload["snapshots"][-1]["snapshot_id"]

        result = cli.cmd_orchestration(
            _args(temp_workspace, subcommand="snapshot", action="rollback", snapshot_id=target)
        )

        assert result == 0
        assert "已回滚到快照" in capsys.readouterr().out

        reloaded = OrchestrationConfig(workspace_path=str(temp_workspace))
        reloaded.load()
        # 回滚后必须真正落盘，不能被 save() 用回滚前的旧对象覆盖
        assert reloaded.roles["AGENT_EXEC"].binding["provider"] == "codearts_agent"

    def test_rollback_rejects_unknown_snapshot(self, temp_workspace, capsys):
        result = cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="snapshot",
                action="rollback",
                snapshot_id="snap_999",
            )
        )

        assert result == 1
        assert "快照不存在" in capsys.readouterr().out


class TestOrchestrationHistory:
    def test_history_lists_events(self, temp_workspace, capsys):
        cli.cmd_orchestration(
            _args(
                temp_workspace,
                subcommand="roles",
                action="activate",
                role_id="AGENT_EXEC",
                provider="codearts_agent",
                model_variant=None,
            )
        )

        result = cli.cmd_orchestration(_args(temp_workspace, subcommand="history", limit=5))

        assert result == 0
        out = capsys.readouterr().out
        assert "role_activated" in out


# ---------------------------------------------------------------------------
# 可用性标注（台账 N44，2026-11-18）
#
# 守的是一条真实误读：`status` 用 `●` 标角色，读者自然把 `●` 读成「能干活」；
# 而 `●` 只表示 binding.status == active。与此同时 `detect` 报 unavailable。
# 两个输出说的事不同，却都不告诉读者，于是「主执行者绑在不可用服务商上」
# 被当成绑定错误去改绑，而真问题是诊断输出不可信。
# ---------------------------------------------------------------------------


@pytest.fixture
def bound_workspace():
    """AGENT_EXEC 绑定 codearts_agent 且状态 active 的工作区。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        config = OrchestrationConfig(workspace_path=str(workspace))
        config.load()
        config.roles["AGENT_EXEC"].activate("codearts_agent")
        config.save()
        yield workspace


def _no_vscode_env(monkeypatch):
    """模拟普通终端：没有任何 VSCode 标记。"""
    for key in ("VSCODE_PID", "CODEARTS_SESSION"):
        monkeypatch.delenv(key, raising=False)


def test_status_marks_bound_but_unavailable_provider(bound_workspace, capsys, monkeypatch):
    _no_vscode_env(monkeypatch)
    result = cli.cmd_orchestration(_args(bound_workspace, subcommand="status"))

    assert result == 0
    out = capsys.readouterr().out
    assert "⚠ unavailable" in out, "已绑定但探针不可用的角色必须被打出来"
    assert "AGENT_EXEC → codearts_agent" in out
    # 绑定激活标记不能因为不可用就消失——两者是正交维度
    assert "● AGENT_EXEC" in out


def test_status_explains_that_marker_is_not_availability(bound_workspace, capsys, monkeypatch):
    _no_vscode_env(monkeypatch)
    cli.cmd_orchestration(_args(bound_workspace, subcommand="status"))

    out = capsys.readouterr().out
    assert "与可用性无关" in out
    assert "VSCODE_PID" in out, "必须说明判据，否则 unavailable 仍会被读成通道故障"
    assert "不会让任务卡住" in out, "必须写明没有派单门禁，否则会被当成阻断"


def test_status_probes_instead_of_reading_the_persisted_snapshot(bound_workspace, capsys, monkeypatch):
    """落盘快照说 connected，探针说 unavailable —— 必须信探针。

    变异检查：把 status 里 `config.detect_providers()` 换成读
    `provider_registry[*].connection_status`，本用例立刻红。
    """
    _no_vscode_env(monkeypatch)
    config_file = bound_workspace / "config" / "agent-orchestration.json"
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    payload["provider_registry"]["codearts_agent"]["connection_status"] = "connected"
    config_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    cli.cmd_orchestration(_args(bound_workspace, subcommand="status"))

    out = capsys.readouterr().out
    exec_line = next(line for line in out.splitlines() if "AGENT_EXEC →" in line)
    assert "unavailable" in exec_line, f"读了落盘快照而不是现探：{exec_line}"
    assert "connected" not in exec_line.replace("unavailable", "")


def test_detect_prints_the_probe_criterion(capsys, temp_workspace):
    result = cli.cmd_orchestration(_args(temp_workspace, subcommand="detect"))

    assert result == 0
    out = capsys.readouterr().out
    assert "判据" in out
    assert "VSCODE_PID" in out, "codearts_agent 的判据必须显式写出来"
    assert "不等于 CodeArts 通道故障" in out
