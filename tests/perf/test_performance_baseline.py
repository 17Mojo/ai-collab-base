"""
Performance baseline tests for AI collaboration system.

These tests establish performance baselines and detect regressions
in critical paths like task dispatch, state management, and CLI operations.
"""

import time
from pathlib import Path
from typing import Any, Dict

import pytest

# Performance thresholds (in seconds)
PERF_THRESHOLDS = {
    "task_dispatch_single": 0.5,
    "task_dispatch_batch_10": 2.0,
    "state_update_single": 0.1,
    "state_query_all": 0.3,
    "cli_help": 1.0,
    "cli_tasks_list": 1.5,
}


def measure_time(func, *args, **kwargs) -> tuple[Any, float]:
    """Measure execution time of a function."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def test_task_dispatch_performance(tmp_path):
    """Test single task dispatch performance."""
    from ai_collab.state_manager import StateManager

    workspace = tmp_path / "ws"
    workspace.mkdir()
    state = StateManager(workspace_path=str(workspace))

    # Measure single task registration
    _, elapsed = measure_time(
        state.register_task,
        task_id="PERF-DISPATCH-001",
        ai_type="codearts_agent",
        description="Performance test task",
        files=["test.py"],
    )

    assert elapsed < PERF_THRESHOLDS["task_dispatch_single"], (
        f"Single task dispatch took {elapsed:.3f}s, "
        f"threshold is {PERF_THRESHOLDS['task_dispatch_single']}s"
    )

    # Measure batch task registration (10 tasks)
    start = time.perf_counter()
    for i in range(10):
        state.register_task(
            task_id=f"PERF-BATCH-{i:03d}",
            ai_type="codearts_agent",
            description=f"Performance test task {i}",
            files=[f"test_{i}.py"],
        )
    elapsed = time.perf_counter() - start

    assert elapsed < PERF_THRESHOLDS["task_dispatch_batch_10"], (
        f"Batch task dispatch (10 tasks) took {elapsed:.3f}s, "
        f"threshold is {PERF_THRESHOLDS['task_dispatch_batch_10']}s"
    )


def test_state_update_performance(tmp_path):
    """Test state update performance."""
    from ai_collab.state_manager import StateManager, TaskStatus

    workspace = tmp_path / "ws"
    workspace.mkdir()
    state = StateManager(workspace_path=str(workspace))

    # Register a task first with complete contract
    state.register_task(
        task_id="PERF-UPDATE-001",
        ai_type="codearts_agent",
        description="Performance test task",
        files=["test.py"],
        change_id="bugfix/no-spec",
        assignee="codearts_agent",
        reviewer="codex",
        primary_skill="performance-expert",
        support_skills=["devops-architect"],
        acceptance_commands=["python3 -m pytest -q tests/perf/"],
        result_file="collaboration/results/RESULT_PERF-UPDATE-001.md",
    )

    # Measure state update
    _, elapsed = measure_time(
        state.update_task_status,
        "PERF-UPDATE-001",
        TaskStatus.IMPLEMENTING,
        note="Performance test update",
    )

    assert elapsed < PERF_THRESHOLDS["state_update_single"], (
        f"Single state update took {elapsed:.3f}s, "
        f"threshold is {PERF_THRESHOLDS['state_update_single']}s"
    )


def test_state_query_performance(tmp_path):
    """Test state query performance."""
    from ai_collab.state_manager import StateManager

    workspace = tmp_path / "ws"
    workspace.mkdir()
    state = StateManager(workspace_path=str(workspace))

    # Register multiple tasks
    for i in range(20):
        state.register_task(
            task_id=f"PERF-QUERY-{i:03d}",
            ai_type="codearts_agent",
            description=f"Performance test task {i}",
            files=[f"test_{i}.py"],
        )

    # Measure query all tasks
    _, elapsed = measure_time(state.get_all_tasks)

    assert elapsed < PERF_THRESHOLDS["state_query_all"], (
        f"Query all tasks took {elapsed:.3f}s, "
        f"threshold is {PERF_THRESHOLDS['state_query_all']}s"
    )


def test_cli_help_performance():
    """Test CLI help command performance."""
    import subprocess

    start = time.perf_counter()
    result = subprocess.run(
        ["python3", "-m", "ai_collab.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0, f"CLI help failed: {result.stderr}"
    assert elapsed < PERF_THRESHOLDS["cli_help"], (
        f"CLI help took {elapsed:.3f}s, " f"threshold is {PERF_THRESHOLDS['cli_help']}s"
    )


def test_cli_tasks_list_performance(tmp_path):
    """Test CLI tasks list performance."""
    import subprocess

    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Initialize state with some tasks
    from ai_collab.state_manager import StateManager

    state = StateManager(workspace_path=str(workspace))
    for i in range(10):
        state.register_task(
            task_id=f"PERF-LIST-{i:03d}",
            ai_type="codearts_agent",
            description=f"Performance test task {i}",
            files=[f"test_{i}.py"],
        )

    # Measure CLI tasks list (using -w flag for workspace)
    start = time.perf_counter()
    result = subprocess.run(
        [
            "python3",
            "-m",
            "ai_collab.cli",
            "-w",
            str(workspace),
            "tasks",
            "list",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0, f"CLI tasks list failed: {result.stderr}"
    assert elapsed < PERF_THRESHOLDS["cli_tasks_list"], (
        f"CLI tasks list took {elapsed:.3f}s, " f"threshold is {PERF_THRESHOLDS['cli_tasks_list']}s"
    )


def test_longrun_harness_performance(tmp_path):
    """Test longrun harness bootstrap performance."""
    import subprocess

    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "longrun_harness.py"

    # Measure bootstrap performance
    start = time.perf_counter()
    result = subprocess.run(
        ["python3", str(script), "bootstrap", "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0, f"Longrun harness bootstrap failed: {result.stderr}"
    assert elapsed < 2.0, f"Longrun harness bootstrap took {elapsed:.3f}s, threshold is 2.0s"


def generate_perf_report(results: Dict[str, float]) -> str:
    """Generate a performance report in markdown format."""
    lines = [
        "# Performance Baseline Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "",
        "## Results",
        "",
        "| Test | Elapsed (s) | Threshold (s) | Status |",
        "|------|-------------|---------------|--------|",
    ]

    for test_name, elapsed in results.items():
        threshold = PERF_THRESHOLDS.get(test_name, float("inf"))
        status = "✅ PASS" if elapsed < threshold else "❌ FAIL"
        lines.append(f"| {test_name} | {elapsed:.3f} | {threshold} | {status} |")

    return "\n".join(lines)


@pytest.fixture
def perf_report_path(tmp_path):
    """Provide a path for performance report output."""
    return tmp_path / "perf_report.md"


def test_generate_perf_report(tmp_path, perf_report_path):
    """Test performance report generation."""
    # Run all performance tests and collect results
    results = {}

    # Task dispatch
    from ai_collab.state_manager import StateManager

    workspace = tmp_path / "ws1"
    workspace.mkdir()
    state = StateManager(workspace_path=str(workspace))

    _, elapsed = measure_time(
        state.register_task,
        task_id="PERF-REPORT-001",
        ai_type="codearts_agent",
        description="Performance test task",
        files=["test.py"],
    )
    results["task_dispatch_single"] = elapsed

    # Generate report
    report = generate_perf_report(results)
    perf_report_path.write_text(report, encoding="utf-8")

    assert perf_report_path.exists()
    assert "# Performance Baseline Report" in report
    assert "task_dispatch_single" in report
