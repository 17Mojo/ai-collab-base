from pathlib import Path
from types import SimpleNamespace

import ai_collab.cli as cli


class DummyStateManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path


def _build_args(workspace: Path, **overrides):
    defaults = {
        "workspace": str(workspace),
        "subcommand": "exec",
        "goal": "pipeline goal",
        "intent": "实现接口并补测试",
        "operator": "user",
        "model": ["gpt-5-codex"],
        "force_lead": None,
        "emit_tasks": False,
        "context": None,
        "step": ["实现最小变更"],
        "steps_file": None,
        "tech_stack": "",
        "follow": "",
        "avoid": "",
        "file": [],
        "test_cmd": "",
        "readonly": False,
        "max_timeout": 30,
        "stale_timeout": 15,
        "sandbox": None,
        "sync": False,
        "task_id": "TASK-EXEC-TEST-001",
        "hook_action": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_fake_integration(run_code: int):
    class FakeIntegration:
        last_instance = None

        def __init__(self, workspace_path: str):
            self.workspace_path = workspace_path
            self.calls = []
            type(self).last_instance = self

        def plan_roles(self, intent, models, operator, force_lead):
            self.calls.append(("plan_roles", intent, tuple(models), operator, force_lead))
            runtime_dir = Path(self.workspace_path) / ".cc-claude-codex"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            return {
                "lead_agent": "codex",
                "support_agents": ["claude_code"],
                "intent_category": "implementation",
                "available_agents": ["codex", "claude_code"],
                "model_agents": ["codex"],
                "reasons": ["test"],
                "utilization_plan": [{"role": "lead", "agent": "codex", "task": "实现"}],
            }

        def write_progress(self, **kwargs):
            self.calls.append(("write_progress", kwargs["goal"], tuple(kwargs["steps"])))
            return Path(self.workspace_path) / ".cc-claude-codex" / "codex-progress.md"

        def validate_progress(self):
            self.calls.append(("validate_progress",))
            return {"issues": []}

        def run_codex(self, readonly, max_timeout, stale_timeout, sandbox):
            self.calls.append(("run_codex", readonly, max_timeout, stale_timeout, sandbox))
            exit_reason = "done" if run_code == 0 else f"error(code={run_code})"
            return SimpleNamespace(
                exit_reason=exit_reason,
                return_code=run_code,
                duration_seconds=1,
                log_file="log-file",
                output_file="output-file",
            )

        def sync_to_state(self, state, task_id=None):
            self.calls.append(("sync_to_state", task_id, state.workspace_path))
            return {
                "task_id": task_id or "TASK-EXEC-DEFAULT",
                "status": "completed" if run_code == 0 else "planning",
                "done_steps": 1 if run_code == 0 else 0,
                "total_steps": 1,
                "goal": "pipeline goal",
            }

    return FakeIntegration


def test_codex_exec_success_runs_full_pipeline(tmp_path, monkeypatch):
    fake_cls = _make_fake_integration(run_code=0)
    monkeypatch.setattr(cli._cli_main, "CodexIntegration", fake_cls)
    monkeypatch.setattr(cli._cli_main, "StateManager", DummyStateManager)
    monkeypatch.setattr(cli._cli_main, "_set_workspace_env", lambda workspace: None)

    rc = cli.cmd_codex(_build_args(tmp_path))
    instance = fake_cls.last_instance
    call_names = [item[0] for item in instance.calls]

    assert rc == 0
    assert call_names == ["plan_roles", "write_progress", "validate_progress", "run_codex", "sync_to_state"]


def test_codex_exec_failure_still_syncs(tmp_path, monkeypatch):
    fake_cls = _make_fake_integration(run_code=124)
    monkeypatch.setattr(cli._cli_main, "CodexIntegration", fake_cls)
    monkeypatch.setattr(cli._cli_main, "StateManager", DummyStateManager)
    monkeypatch.setattr(cli._cli_main, "_set_workspace_env", lambda workspace: None)

    rc = cli.cmd_codex(_build_args(tmp_path, task_id="TASK-EXEC-FAIL-001"))
    instance = fake_cls.last_instance
    call_names = [item[0] for item in instance.calls]

    assert rc == 1
    assert call_names[-1] == "sync_to_state"
