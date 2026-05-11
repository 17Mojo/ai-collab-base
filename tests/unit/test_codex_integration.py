import json

from ai_collab.codex_integration import CodexIntegration


def _our_hook_entry(command: str, matcher: str = "") -> dict:
    return {"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": 1000}]}


def test_merge_hooks_replaces_our_entries(tmp_path):
    integration = CodexIntegration(str(tmp_path))
    settings = {
        "hooks": {
            "Stop": [
                _our_hook_entry('python3 "/tmp/ai_collab/hooks/stop_check.py"'),
                _our_hook_entry("echo external-stop"),
            ]
        }
    }

    merged = integration._merge_hooks(settings, integration._build_hook_config())
    stop_entries = merged["hooks"]["Stop"]

    assert sum(1 for entry in stop_entries if integration._entry_is_our_hook(entry)) == 1
    assert any(
        isinstance(entry, dict)
        and any(hook.get("command") == "echo external-stop" for hook in entry.get("hooks", []))
        for entry in stop_entries
    )


def test_remove_our_hooks_keeps_external_entries(tmp_path):
    integration = CodexIntegration(str(tmp_path))
    settings = {
        "hooks": {
            "Stop": [
                _our_hook_entry('python3 "/tmp/ai_collab/hooks/stop_check.py"'),
                _our_hook_entry("echo external-stop"),
            ],
            "PreCompact": [_our_hook_entry('python3 "/tmp/ai_collab/hooks/pre_compact.py"')],
            "SessionStart": [_our_hook_entry('python3 "/tmp/ai_collab/hooks/session_inject.py"')],
            "PreToolUse": [
                _our_hook_entry('python3 "/tmp/ai_collab/hooks/spawn_agent_preflight.py"', matcher="Agent"),
                _our_hook_entry("echo external-agent-hook", matcher="Agent"),
            ],
        }
    }

    cleaned = integration._remove_our_hooks(settings)

    assert "PreCompact" not in cleaned["hooks"]
    assert "SessionStart" not in cleaned["hooks"]
    assert len(cleaned["hooks"]["PreToolUse"]) == 1
    assert cleaned["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "echo external-agent-hook"
    assert len(cleaned["hooks"]["Stop"]) == 1
    assert cleaned["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo external-stop"


def test_doctor_hooks_repairs_malformed_settings(tmp_path, monkeypatch):
    integration = CodexIntegration(str(tmp_path))
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": {"matcher": "", "hooks": {"bad": "shape"}},
                    "SessionStart": [1, {"matcher": ""}],
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(CodexIntegration, "_claude_settings_file", lambda self: settings_file)

    result = integration.doctor_hooks(repair=True)
    repaired_settings = json.loads(settings_file.read_text(encoding="utf-8"))

    assert result.installed is True
    assert result.details["repaired"] is True
    assert isinstance(result.details["issues"], list) and result.details["issues"]
    assert isinstance(repaired_settings["hooks"]["Stop"], list)
    assert isinstance(repaired_settings["hooks"]["SessionStart"], list)
    assert isinstance(repaired_settings["hooks"]["PreToolUse"], list)
    assert any(integration._entry_is_our_hook(entry) for entry in repaired_settings["hooks"]["Stop"])
    assert any(integration._entry_is_our_hook(entry) for entry in repaired_settings["hooks"]["PreCompact"])
    assert any(integration._entry_is_our_hook(entry) for entry in repaired_settings["hooks"]["SessionStart"])
    assert any(integration._entry_is_our_hook(entry) for entry in repaired_settings["hooks"]["PreToolUse"])


def test_build_hook_config_includes_agent_pretooluse(tmp_path):
    integration = CodexIntegration(str(tmp_path))

    hook_config = integration._build_hook_config()

    assert "PreToolUse" in hook_config
    assert hook_config["PreToolUse"][0]["matcher"] == "Agent"
    command = hook_config["PreToolUse"][0]["hooks"][0]["command"]
    assert "spawn_agent_preflight.py" in command


def test_ensure_output_file_writes_fallback(tmp_path):
    integration = CodexIntegration(str(tmp_path))
    log_file = tmp_path / "run.log"
    out_file = tmp_path / "run-output.md"
    log_file.write_text("line-1\nline-2\n", encoding="utf-8")

    integration._ensure_output_file(log_file=log_file, out_file=out_file, exit_reason="hard_timeout(10s)")

    content = out_file.read_text(encoding="utf-8")
    assert "hard_timeout(10s)" in content
    assert "line-1" in content
