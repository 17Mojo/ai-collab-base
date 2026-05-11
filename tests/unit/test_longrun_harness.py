import json
import subprocess
from pathlib import Path


def _run(script: Path, workspace: Path, *args: str):
    cmd = ["python3", str(script), *args, "--workspace", str(workspace)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_bootstrap_creates_harness_files(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "longrun_harness.py"

    result = _run(script, workspace, "bootstrap", "--goal", "test goal")
    assert result.returncode == 0, result.stderr

    longrun_dir = workspace / "collaboration" / "longrun"
    assert (longrun_dir / "feature_list.json").exists()
    assert (longrun_dir / "session_progress.md").exists()
    assert (longrun_dir / "session_checklist.md").exists()
    assert (longrun_dir / "init.sh").exists()

    data = json.loads((longrun_dir / "feature_list.json").read_text(encoding="utf-8"))
    assert data["goal"] == "test goal"
    assert isinstance(data["features"], list) and data["features"]

    init_content = (longrun_dir / "init.sh").read_text(encoding="utf-8")
    assert "git log --oneline -20" in init_content
    assert "reconcile_state_drift.py" in init_content

    checklist_content = (longrun_dir / "session_checklist.md").read_text(encoding="utf-8")
    assert "reconcile_state_drift.py --workspace . --fail-on-drift" in checklist_content


def test_next_and_pass_flow(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "longrun_harness.py"

    bootstrap = _run(script, workspace, "bootstrap")
    assert bootstrap.returncode == 0, bootstrap.stderr

    next_result = _run(script, workspace, "next")
    assert next_result.returncode == 0, next_result.stderr

    runtime_progress = workspace / ".cc-claude-codex" / "codex-progress.md"
    assert runtime_progress.exists()
    content = runtime_progress.read_text(encoding="utf-8")
    assert "Step 1: Run startup baseline checks" in content

    pass_result = _run(script, workspace, "pass", "--id", "LR-001", "--note", "verified")
    assert pass_result.returncode == 0, pass_result.stderr

    features = json.loads((workspace / "collaboration" / "longrun" / "feature_list.json").read_text(encoding="utf-8"))
    lr_001 = next(item for item in features["features"] if item["id"] == "LR-001")
    assert lr_001["passes"] is True
    assert lr_001["notes"] == "verified"
